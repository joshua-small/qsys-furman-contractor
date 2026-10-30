# Furman Contractor Series for Q-SYS

Control a configured chain of Furman Contractor Series SmartSequencers, with global commands and per-device controls, identification and measurements. Choose CN-1800S, CN-2400S or CN-3600SE for the primary sequencer and configure the number of secondary sequencers.

Plugin and package version: **1.2.0.5**.

## Changes in 1.2.0.5

- Handles segmented, fragmented, coalesced and delayed serial replies, including status data that continues after an intermediate EOT.
- Updates valid known fields independently, filters command echo, and routes late feedback to its addressed device without acknowledging an unrelated request.
- Separates connection health from individual poll completion. An isolated delayed poll retains recent feedback; sustained silence still reports Missing and invalidates it.
- Preserves command/sequence confirmation, configured model/count properties, control pins and page layout.

Reply handling was reported working in a live Core test. Broader model/firmware coverage, physical switching behavior and saved-instance migration remain subject to verification on the target system.

## Install with Q-SYS Library

1. Sign in to [Q-SYS Library](https://library.qsys.com/my-library).
2. Open **My Packages → Add Personal Package**.
3. Enter **Furman Contractor Series** and this package URL:

   ```text
   https://joshua-small.github.io/qsys-furman-contractor/registration/joshuasmall.qsys.furmancontractor/index.json
   ```

4. In Designer, sign in with the same QSC ID and open **Tools → Show Asset Installer**.
5. Refresh **Available Assets**, select the package and install it.

For manual installation, download `FurmanContractorSmartSequencer.qplug` from [Releases](https://github.com/joshua-small/qsys-furman-contractor/releases) and place only that file in your Documents folder under `QSC/Q-Sys Designer/Plugins`. Keep backups and support files outside Plugins. Use one installation method to avoid duplicate copies. Refreshing/installing a package does not deploy changes to a Core; update and test the design before **Save to Core & Run**.

## Connect and operate

1. Add **Furman > Contractor Series SmartSequencer** to a test design.
2. Set **Primary Sequencer Model** and **Number of Secondary Sequencers** in Properties. Configure these before running the design.
3. Connect a Q-SYS Serial Port component to **Serial Port**. The protocol uses **19200 baud, 8N1, no flow control**.
4. Run the design. Use Roll Call to check the chain and inspect discovered devices and connection status. Enumeration changes device addresses; use it only when commissioning the chain.
5. Use Global for chain-wide actions and the sequencer pages for individual devices, banks, measurements and physical settings. Event reporting and polling provide feedback.

The configured secondary count determines the available controls. Discovery does not create additional controls dynamically. The default polling interval is 10 seconds. Commands can switch connected electrical loads; confirm the selected chain and device before operating it.

## Compatibility

Targets Q-SYS Designer/Core 10.5. The current source includes the prior nil-check and status-color corrections. Offline source checks do not establish serial timing, saved-instance migration or physical Furman operation. Verify the target chain before deployment.

## Support

Report bugs through [Issues](https://github.com/joshua-small/qsys-furman-contractor/issues), including plugin version, Q-SYS version, device/broker model and firmware, and reproduction steps. Remove credentials from logs and design files before sharing them.

This is an independent personal package, not a Q-SYS Verified Asset or a manufacturer-endorsed release. Manufacturer names and logos identify compatible products. Existing source attribution is retained.

### Offline package checks

Run `python3 scripts/verify.py` and `python3 -m unittest discover -s tests -p test_package_identity.py`. Before a release, run `python3 scripts/verify.py --release-tag v<VERSION>`. The exact tag, project package version and `PluginInfo.Version` must agree. `BuildVersion` is a separate optional SDK field. These checks do not establish Designer or hardware acceptance.

### Serial reply regression tests

Run `uv run --python 3.10 --with lupa python tests/test_serial_replies.py` for 40 synthetic Lua 5.3 tests covering segmented/late/coalesced replies, partial fields, echo, address routing, recovery and connection-liveness expiry. No device connection is used by these tests.

Receive framing settles after 200 ms of quiet. Connection-liveness grace is the greater of three polling intervals and 15 seconds, checked every five seconds; the default polling interval gives 30 seconds. Expected long-running commands retain their own completion deadlines. A timed-out sequence requires explicit reconnect before another command; stale feedback can still expire during that hold.

The protocol has no transaction IDs. Unaddressed continuation lines use the most recent compatible reply context, and sufficiently delayed same-address/same-kind duplicates cannot be distinguished perfectly from fresh replies. Connection health is connection-wide, not a per-device/per-field freshness guarantee. Rx debug includes hexadecimal received bytes to help diagnose firmware framing differences.
