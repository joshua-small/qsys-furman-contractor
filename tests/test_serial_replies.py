from pathlib import Path
import unittest
from lupa.lua53 import LuaRuntime
source=(Path(__file__).resolve().parents[1]/'content/FurmanContractorSmartSequencer.qplug').read_text()
def load(code,secondaries=0,model='CN-1800S'):
 l=LuaRuntime(unpack_returned_tuples=True);l.execute(code);g=l.globals();props=l.table()
 for _,d in g.GetProperties().items():props[d.Name]=l.table(Value=d.Value)
 props['Number of Secondary Sequencers'].Value=secondaries;props['Primary Sequencer Model'].Value=model
 props.plugin_show_debug=l.table(Value=False)
 return l,g,props
class Harness:
 def __init__(self,n=0):
  self.l,self.g,self.p=load(source,n);g=self.g;l=self.l;self.n=n
  defs=g.GetControls(self.p)
  l.execute('''
Controls = {}; Properties = ...
function NewControl() return {String='',Value=0,Boolean=false,IsIndeterminate=false,IsDisabled=false} end
Clock=100
Timer = {Now=function() return Clock end,New=function() return {Start=function(self,s) self.seconds=s;self.running=true end,Stop=function(self) self.running=false end} end}
Tx={};Wire=''
Port={IsOpen=false,BufferLength=0,
 Open=function(self,b,d,p,s) assert(b==19200 and d==8 and p=='N' and s==1);self.IsOpen=true;self.Connected(self) end,
 Close=function(self) self.IsOpen=false;self.Closed(self) end,
 Write=function(self,data) assert(self.IsOpen);Tx[#Tx+1]=data end,
 Read=function(self,n) local s=Wire:sub(1,n);Wire=Wire:sub(n+1);self.BufferLength=#Wire;return s end}
SerialPorts={Port}
function Feed(s) Wire=Wire..s;Port.BufferLength=#Wire;Port.Data(Port) end
function Press(c) c.Value=1;c.EventHandler(c);c.Value=0 end
''',self.p)
  for _,d in defs.items():
   if d.Count==1:g.Controls[d.Name]=g.NewControl()
   else:
    a=l.table()
    for i in range(1,d.Count+1):a[i]=g.NewControl()
    g.Controls[d.Name]=a
  l.execute("print = function(...) end")
  l.execute(source)
  assert len(g.Tx)==0
  g.OpenTimer.EventHandler();assert not g.OpenTimer.running
 def ctl(self,name,i=1):return self.g.SeqControl(name,i)
 def pending(self):return self.g.Pending.command if self.g.Pending else None
 def feed(self,s):self.g.Feed(s)
 def response(self,cmd):
  g=self.g
  if cmd in ('!ENUMERATE','?ROLLCALL'):
   return ''.join(f'$ACK {i},CN-1800S'+(',LAST' if i==self.n else '')+'\r' for i in range(self.n+1))+('\x04' if cmd.startswith('?') else '')
  if cmd=='?HELP':return 'Commands\r!RESET\r?POWER_VA\r\x04'
  verb=cmd.split()[0][1:];seq=int(cmd.split()[1]) if len(cmd.split())>1 else None
  if cmd.startswith('!'):
   if seq is None:return '$'+verb+'_DONE\r'
   if verb.startswith('SEQ_'):verb+='_DONE'
   if verb.startswith('BANK_'):verb+=' '+cmd.split()[2]+'=ON'
   return f'$ACK {seq},{verb}\r'
  if verb=='ID':return f'$ACK {seq},ID\rFURMAN\rCN-1800S\r12345678901234\r1.1.1\rFri Mar 16 10:47:00 2012\r\x04'
  if verb=='STATUS':return f'$ACK {seq},STATUS\rSEQ='+('PRIM' if seq==0 else 'SEC')+(',LAST' if seq==self.n else '')+f'\rPROTECT=OK\rEVS=OFF\rSMP RLY=ON\rALARM=OFF\rBANK1=OFF\rBANK2=ON\rBANK3=OFF\rREMOTE=0V\rPUSHBUTTON=OFF\rSECLINK='+('NOTOK' if seq==self.n else 'OK')+'\rUART0 PER=0.00%\rUART1 PER=0%\r\x04'
  if verb=='SETTINGS':return f'$ACK {seq},SETTINGS\rPOT ADJ=6%\rDIP MAX DELAY=10 SECONDS\rTOTAL DELAY=0.6 SECONDS\rDIP MODE=MOM\rDIP SEQ=PRIM\rDIP ALARM=N. OPEN\rDIP EVS=AUTO\rKEY=REM\r\x04'
  if verb=='BANK_STAT':return f'$ACK {seq},BANK_STAT\rBANK1=OFF\rBANK2=ON\rBANK3=OFF\r\x04'
  key,value={'VOLTAGE':('VOLTAGE','118.3'),'CURRENT':('CURRENT','2.4'),'POWER':('WATTS','1325'),'POWER_VA':('VA','125'),'PF':('PF','0.91')}[verb]
  return f'$ACK {seq},{key}={value}\r\x04'
 def flush(self):
  self.g.Clock=self.g.Clock+0.21
  if self.g.ReplyGapTimer and self.g.ReplyGapTimer.running:self.g.ReplyGapTimer.EventHandler()
 def drain(self):
  for i in range(4000):
   if self.g.Recovering and not self.g.RecoveryRequiresReconnect:self.g.RecoveryTimer.EventHandler()
   self.flush()
   if not self.pending():return
   self.feed(self.response(self.pending()))
  raise AssertionError('queue failed to drain')

class SerialReplies(unittest.TestCase):
 def ready(self,n=0):
  h=Harness(n);h.drain();return h
 def finish(self,h):h.flush()
 def test_segmented_status_survives_intermediate_eot(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0')
  data=h.response('?STATUS 0').replace('BANK3=OFF\r','BANK3=OFF\r\x04')
  first,tail=data.split('REMOTE=');h.feed(first)
  self.assertEqual(h.pending(),'?STATUS 0')
  h.feed('REMOTE='+tail);h.flush()
  self.assertIsNone(h.pending());self.assertEqual(h.ctl('PrimaryPER').String,'0.00%')
  self.assertFalse(h.ctl('RemoteInput').IsDisabled);self.assertEqual(g.Status.Value,0)
 def test_segmented_status_bytewise(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0')
  data='?STATUS 0\r'+h.response('?STATUS 0').replace('BANK3=OFF\r','BANK3=OFF\r\x04')
  for b in data:h.feed(b)
  h.flush();self.assertIsNone(h.pending());self.assertEqual(g.Status.Value,0)
 def test_late_continuation_after_quiet_retains_address_context(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0');head,tail=h.response('?STATUS 0').split('REMOTE=')
  h.feed(head+'\x04');h.flush();self.assertIsNone(h.pending())
  h.feed('REMOTE=12V\rPUSHBUTTON=ON\rSECLINK=NOTOK\rUART0 PER=1.13%\rUART1 PER=0%\r\x04');h.flush()
  self.assertTrue(h.ctl('RemoteInput').Boolean);self.assertEqual(h.ctl('PrimaryPER').String,'1.13%');self.assertNotEqual(g.Status.Value,4)
 def test_late_scalar_updates_without_acknowledging_other_query(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0')
  h.feed('$ACK 0,VA=355\r\x04');h.flush()
  self.assertEqual(h.pending(),'?PF 0');self.assertEqual(h.ctl('PowerVA').String,'355')
  h.feed('$ACK 0,PF=0.74\r\x04');h.flush();self.assertIsNone(h.pending())
 def test_unsolicited_known_scalar_updates_when_idle(self):
  h=self.ready();h.feed('$ACK 0,CURRENT=2.9\r\x04');h.flush()
  self.assertEqual(h.ctl('Current').String,'2.9')
 def test_multiple_frames_and_empty_delimiters_in_one_callback(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');g.Enqueue('?VOLTAGE 0')
  h.feed('\r\n\x04$ACK 0,VA=355\r\x04$ACK 0,PF=0.74\r\x04$ACK 0,CURRENT=2.9\r\x04')
  h.flush();self.assertEqual(h.pending(),'?VOLTAGE 0');self.assertEqual(h.ctl('PowerFactor').String,'0.74');self.assertEqual(h.ctl('Current').String,'2.9')
 def test_missing_optional_status_fields_are_not_connection_loss(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0')
  h.feed('$ACK 0,STATUS\rPROTECT=OK\rBANK1=ON\r\x04');h.flush()
  self.assertIsNone(h.pending());self.assertEqual(g.Status.Value,0);self.assertTrue(h.ctl('Bank1Status').Boolean)
 def test_partial_settings_applies_only_valid_fields(self):
  h=self.ready();g=h.g;g.Enqueue('?SETTINGS 0')
  h.feed('$ACK 0,SETTINGS\rPOT ADJ=31%\rNEW FIRMWARE FIELD=YES\r\x04');h.flush()
  self.assertIsNone(h.pending());self.assertEqual(h.ctl('DelayAdjust').String,'31%');self.assertEqual(h.ctl('KeySwitch').String,'REM')
 def test_missing_eot_can_settle_valid_delimited_frame_after_quiet(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');h.feed('$ACK 0,PF=0.74\r')
  self.assertEqual(h.pending(),'?PF 0');h.flush();self.assertIsNone(h.pending())
 def test_unterminated_partial_line_is_not_guessed(self):
  h=self.ready();g=h.g;g.Enqueue('?CURRENT 0');h.feed('$ACK 0,CURRENT=2.')
  h.flush();self.assertEqual(h.pending(),'?CURRENT 0');self.assertEqual(h.ctl('Current').String,'2.4')
  h.feed('9\r\x04');h.flush();self.assertEqual(h.ctl('Current').String,'2.9')
 def test_single_query_timeout_does_not_clear_recent_feedback(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');g.Clock=g.Clock+5;g.CommandTimer.EventHandler()
  self.assertEqual(g.Status.Value,1);self.assertFalse(g.Recovering);self.assertEqual(h.ctl('Voltage').String,'118.3');self.assertFalse(h.ctl('Voltage').IsDisabled)
 def test_sustained_silence_is_still_missing_and_invalidates(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');g.Clock=g.Clock+g.CommunicationGrace()+1;g.CommandTimer.EventHandler()
  self.assertEqual(g.Status.Value,4);self.assertTrue(g.Recovering);self.assertEqual(h.ctl('Voltage').String,'')
 def test_only_garbage_does_not_extend_liveness(self):
  h=self.ready();g=h.g;last=g.LastReplyAt;g.Clock=g.Clock+g.CommunicationGrace()+1
  g.Enqueue('?PF 0');h.feed('garbage\r?PF 0\r\x04');h.flush();self.assertEqual(g.LastReplyAt,last)
  g.CommandTimer.EventHandler();self.assertEqual(g.Status.Value,4)
 def test_unconfigured_address_cannot_update_feedback_or_complete(self):
  h=self.ready();g=h.g;g.Enqueue('?CURRENT 0');before=g.LastReplyAt;h.feed('$ACK 9,CURRENT=99\r\x04');h.flush()
  self.assertEqual(h.pending(),'?CURRENT 0');self.assertEqual(h.ctl('Current').String,'2.4');self.assertEqual(g.LastReplyAt,before)
 def test_other_configured_address_updates_its_own_controls(self):
  h=self.ready(1);g=h.g;g.Enqueue('?PF 0');h.feed('$ACK 1,CURRENT=3.1\r\x04');h.flush()
  self.assertEqual(h.ctl('Current',2).String,'3.1');self.assertEqual(h.ctl('Current',1).String,'2.4');self.assertEqual(h.pending(),'?PF 0')
 def test_orphan_eot_does_not_complete_pending(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');h.feed('\x04\r\n\x04');h.flush();self.assertEqual(h.pending(),'?PF 0')
 def test_echo_filtered_before_scalar(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');h.feed('?PF 0\r$ACK 0,PF=0.74\r\x04');h.flush()
  self.assertIsNone(h.pending());self.assertEqual(h.ctl('PowerFactor').String,'0.74')
 def test_invalid_numeric_field_does_not_get_accepted_as_value(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');h.feed('$ACK 0,PF=INVALID\r\x04');h.flush()
  self.assertTrue(h.ctl('PowerFactor').IsDisabled);self.assertNotEqual(g.Status.Value,4)
 def test_event_interleaves_with_segmented_status(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0');h.feed(h.response('?STATUS 0').replace('BANK1=OFF\r','BANK1=OFF\r*EVS 0\r\x04'));h.drain()
  self.assertEqual(g.Status.Value,0)
 def test_help_preserves_command_descriptions(self):
  h=self.ready();g=h.g;g.Enqueue('?HELP');h.feed('?HELP\rCommands\r?PF 0\r!RESET\r\x04');h.flush()
  self.assertIn('?PF 0',g.Controls.HelpResponse.String);self.assertIsNone(h.pending())
 def test_incomplete_id_does_not_shift_identity_fields(self):
  h=self.ready();g=h.g;g.Enqueue('?ID 0');h.feed('$ACK 0,ID\rFURMAN\rCN-1800S\r\x04');h.flush()
  self.assertEqual(h.ctl('SerialNumber').String,'12345678901234');self.assertNotEqual(g.Status.Value,4)
 def test_rollcall_still_requires_complete_topology(self):
  h=self.ready(1);g=h.g;g.Enqueue('?ROLLCALL');h.feed('$ACK 0,CN-1800S\r\x04');h.flush()
  self.assertEqual(h.pending(),'?ROLLCALL');self.assertIsNotNone(g.Devices[1])
 def test_complete_rollcall_multiple_delimiters(self):
  h=self.ready(1);g=h.g;g.Enqueue('?ROLLCALL');h.feed('$ACK 0,CN-1800S\r\x04$ACK 1,CN-1800S,LAST\r\x04');h.flush()
  self.assertIsNone(h.pending());self.assertTrue(g.Devices[1].last)
 def test_command_completion_is_not_inferred_from_query_feedback(self):
  h=self.ready();g=h.g;g.Press(g.Controls.GlobalSeqOn);h.feed('$ACK 0,PF=0.74\r\x04');h.flush();self.assertEqual(h.pending(),'!SEQ_ON')
  g.CommandTimer.EventHandler();self.assertTrue(g.RecoveryRequiresReconnect)
 def test_sequence_bare_done_still_completes(self):
  h=self.ready();g=h.g;g.Press(g.Controls.GlobalSeqOn);h.feed('$SEQ_ON_DONE\r');h.drain();self.assertEqual(g.Status.Value,0)
 def test_idle_partial_tail_still_expires(self):
  h=self.ready();g=h.g;h.feed('orphan-partial');g.Enqueue('?PF 0');h.flush();self.assertEqual(h.pending(),'?PF 0')
 def test_disconnect_cancels_context_and_quiet_timer(self):
  h=self.ready();g=h.g;h.feed('$ACK 0,STATUS\r');g.Port.Close(g.Port)
  self.assertIsNone(g.ActiveReplyFrame);self.assertIsNone(g.LastReplyAt);self.assertFalse(g.ReplyGapTimer.running);self.assertEqual(g.Status.Value,4)
 def test_reconnect_starts_fresh_discovery(self):
  h=self.ready();g=h.g;g.OnConnected();self.assertIsNone(g.ActiveReplyFrame);self.assertIsNone(g.LastReplyAt);self.assertEqual(h.pending(),'!ENUMERATE')
 def test_raw_receive_limit_preserved(self):
  h=self.ready();g=h.g;g.Enqueue('?HELP');h.feed('x'*32769);self.assertTrue(g.Recovering)
 def test_reply_frame_line_limit_preserved(self):
  h=self.ready();g=h.g;g.Enqueue('?HELP');h.feed('Commands\r'+'x\r'*257);self.assertIsNone(g.ActiveReplyFrame);self.assertIsNone(h.pending())
 def test_invalid_command_error_remains_warning_not_missing(self):
  h=self.ready();g=h.g;g.Enqueue('?PF 0');h.feed('$INVALID COMMAND\r\x04');h.flush();self.assertIsNone(h.pending());self.assertEqual(g.Status.Value,1)
 def test_partial_tail_timeout_recovery_cannot_stall_queue(self):
  h=self.ready();g=h.g;g.Enqueue('?CURRENT 0');h.feed('$ACK 0,CURRENT=2.');h.flush()
  g.Clock=g.Clock+g.CommunicationGrace()+1;g.CommandTimer.EventHandler()
  self.assertFalse(g.ReplyGapActive);self.assertFalse(g.ReplyGapTimer.running)
  before=len(g.Tx);g.RecoveryTimer.EventHandler()
  self.assertGreater(len(g.Tx),before);self.assertEqual(h.pending(),'!ENUMERATE')
  h.drain();self.assertEqual(g.Status.Value,0)
 def test_unaddressed_late_status_tail_does_not_finish_settings(self):
  h=self.ready();g=h.g;g.Enqueue('?STATUS 0');g.Enqueue('?SETTINGS 0')
  head,tail=h.response('?STATUS 0').split('REMOTE=');h.feed(head+'\x04');h.flush()
  self.assertEqual(h.pending(),'?SETTINGS 0')
  h.feed('REMOTE=12V\rUART0 PER=1.13%\r\x04');h.flush()
  self.assertEqual(h.pending(),'?SETTINGS 0');self.assertTrue(h.ctl('RemoteInput').Boolean)
  h.feed(h.response('?SETTINGS 0'));h.flush();self.assertIsNone(h.pending())
 def test_segmented_status_arbitrary_chunk_sizes(self):
  for size in (1,2,3,7,8,16,512):
   with self.subTest(size=size):
    h=self.ready();g=h.g;g.Enqueue('?STATUS 0')
    data='?STATUS 0\r'+h.response('?STATUS 0').replace('BANK3=OFF\r','BANK3=OFF\r\x04')
    for start in range(0,len(data),size):h.feed(data[start:start+size])
    h.flush();self.assertIsNone(h.pending());self.assertEqual(g.Status.Value,0)
    self.assertEqual(h.ctl('PrimaryPER').String,'0.00%')
 def test_recent_feedback_does_not_confirm_timed_out_sequence(self):
  h=self.ready();g=h.g;g.Press(g.Controls.GlobalSeqOn);h.feed('$ACK 0,PF=0.74\r\x04');h.flush()
  g.CommandTimer.EventHandler();self.assertEqual(g.Status.Value,1);self.assertTrue(g.RecoveryRequiresReconnect)
  before=len(g.Tx);g.Press(h.ctl('Bank1OnBtn'));self.assertEqual(len(g.Tx),before)
 def test_late_id_body_for_removed_device_is_ignored(self):
  h=self.ready();g=h.g;g.Enqueue('?ID 0');h.feed('$ACK 0,ID\rFURMAN\rCN-1800S\r1234\r1.0\r')
  g.Devices[0]=None;h.feed('Fri Jan 1\r\x04');h.flush()
  self.assertEqual(h.ctl('SerialNumber').String,'12345678901234')
 def test_liveness_expires_during_sequence_reconnect_hold_without_sending(self):
  h=self.ready();g=h.g;g.Press(g.Controls.GlobalSeqOn);h.feed('$ACK 0,PF=0.74\r\x04');h.flush();g.CommandTimer.EventHandler()
  before=len(g.Tx);g.Clock=g.Clock+g.CommunicationGrace()+1;g.LivenessTimer.EventHandler()
  self.assertEqual(g.Status.Value,4);self.assertEqual(h.ctl('Voltage').String,'');self.assertTrue(g.RecoveryRequiresReconnect);self.assertEqual(len(g.Tx),before)
 def test_liveness_does_not_interrupt_expected_long_sequence(self):
  h=self.ready();g=h.g;g.Press(g.Controls.GlobalSeqOn);g.Clock=g.Clock+g.CommunicationGrace()+1
  g.LivenessTimer.EventHandler();self.assertEqual(h.pending(),'!SEQ_ON');self.assertFalse(g.Recovering)
  h.feed('$SEQ_ON_DONE\r');h.drain();self.assertEqual(g.Status.Value,0)
 def test_liveness_timer_stops_on_disconnect(self):
  h=self.ready();g=h.g;self.assertTrue(g.LivenessTimer.running);g.Port.Close(g.Port);self.assertFalse(g.LivenessTimer.running)
 def test_idle_connection_silence_expires_even_without_pending_query(self):
  h=self.ready();g=h.g;g.Clock=g.Clock+g.CommunicationGrace()+1;g.LivenessTimer.EventHandler()
  self.assertEqual(g.Status.Value,4);self.assertTrue(g.Recovering);self.assertEqual(h.ctl('Voltage').String,'')
if __name__=='__main__':unittest.main(verbosity=2)
