"""V1.2: record the tool versions of the verification run as vf.env.* keys (ANALYTICAL: they describe the environment).
usage: PYTHONPATH=src python scripts/vf_env_record.py"""
import platform
import re
import subprocess
from importlib import metadata

from crashguard.results import record_many

def wsl(cmd: str) -> str:
    return subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd], capture_output=True, text=True).stdout.strip()

src = "scripts/vf_env_record.py"
tam = re.search(r"tamarin-prover ([\d.]+)", wsl("/opt/tamarin/tamarin-prover --version 2>&1 | head -3")).group(1)
maude = wsl("maude --version 2>&1 | head -1")
pv = re.search(r"Proverif ([\d.]+)", wsl("/opt/pv/proverif2.05/proverif -help 2>&1 | head -1")).group(1).rstrip(".")
gpp = re.search(r"([\d.]+)", wsl("g++ --version | head -1").split(")")[1]).group(1)
cmake = re.search(r"([\d.]+)", wsl("cmake --version | head -1")).group(1)
ub = wsl("lsb_release -ds 2>/dev/null || grep PRETTY /etc/os-release")
wslv = subprocess.run(["wsl", "--version"], capture_output=True).stdout.decode("utf-16-le", "ignore").replace("\x00", "")
wslv = re.search(r"WSL version: ([\d.]+)", wslv)
vals = {"os": platform.platform(), "python": platform.python_version(), "numpy": metadata.version("numpy"), "scipy": metadata.version("scipy"), "scikit-learn": metadata.version("scikit-learn"),
        "tamarin": tam, "maude": maude, "proverif": pv, "ns3": "ns-3.48 + lorawan v0.3.7-2-ge45b4af + local patch", "gpp": gpp, "cmake": cmake, "wsl_distro": ub, "wsl": wslv.group(1) if wslv else "?"}
record_many([dict(name=f"vf.env.{k}", value=v, unit="text", origin="ANALYTICAL", source_file=src, notes="environment of the verification run") for k, v in vals.items()], purge_prefixes=("vf.env.",))
print(vals)
