"""Verify package identity and source integrity before publishing."""
from pathlib import Path
import hashlib
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
source = (root / "content/FurmanContractorSmartSequencer.qplug").read_bytes()
assert hashlib.sha256(source).hexdigest() == "ee31140ec8b9cd90b810924c3dc975cdca1cbe27464ce83f7ae57a40735cbe31", "Update the reviewed source digest for an intentional plugin revision"
info = re.search(r"PluginInfo\s*=\s*\{(.*?)\}", source.decode("utf-8-sig"), re.S)[1]
version = re.search(r'\bVersion\s*=\s*"([^"]+)"', info)[1]
project = ET.parse(root / "FurmanContractor.csproj").getroot()
assert version == project.findtext("PropertyGroup/Version"), "Plugin/package version mismatch"
assert project.findtext("PropertyGroup/PackageId") == "JoshuaSmall.Qsys.FurmanContractor"
assert (root / "icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
assert "https://joshua-small.github.io/qsys-furman-contractor/registration/joshuasmall.qsys.furmancontractor/index.json" in (root / "README.md").read_text()
print("Verified", "FurmanContractorSmartSequencer.qplug", version, hashlib.sha256(source).hexdigest())
