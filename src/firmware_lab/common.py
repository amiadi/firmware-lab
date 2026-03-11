from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ToolError(RuntimeError):
    pass

def require_exe(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ToolError(f"Required executable not found in PATH: {name}")
    return path

def run_process(args: list[str], *, cwd: Optional[Path] = None, env: Optional[dict[str, str]] = None) -> subprocess.Popen:
    p = subprocess.Popen(
        args,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return p

@dataclass(frozen=True)
class FirmwareSpec:
    elf: Optional[Path] = None
    bin: Optional[Path] = None
    bin_load_addr: Optional[int] = None

    def validate(self) -> None:
        if bool(self.elf) == bool(self.bin):
            raise ValueError("Provide exactly one of --elf or --bin")

        if self.bin:
            if self.bin_load_addr is None:
                raise ValueError("--bin-load-addr is required when using --bin")
            if not self.bin.exists():
                raise FileNotFoundError(self.bin)
        if self.elf and not self.elf.exists():
            raise FileNotFoundError(self.elf)

def parse_int(s: str) -> int:
    s = s.strip().lower()
    if s.startswith("0x"):
        return int(s, 16)
    return int(s, 10)