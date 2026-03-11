from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from .common import FirmwareSpec, require_exe, run_process

def _renode_script(
    *,
    platform: str,
    fw: FirmwareSpec,
    uart_log: Optional[Path],
    gdb_port: Optional[int],
    checkpoint_out: Optional[Path],
    checkpoint_in: Optional[Path],
    start: bool,
) -> str:
    """Generate a Renode .resc script.

    Notes:
    - If checkpoint_in is provided, it is assumed to contain the full machine state.
    - For raw .bin images, fw.bin_load_addr must be provided.
    """

    lines: list[str] = []

    if checkpoint_in:
        # Snapshot contains platform + peripherals + memory state.
        lines.append("mach create")
        lines.append(f"Load @{{checkpoint_in.as_posix()}}")
    else:
        lines.append(f"$platform = \"{{platform}}\"")
        lines.append("using sysbus")
        lines.append("mach create")

        # Allow passing either a built-in platform name (loadPlatformDescription <name>)
        # or a path to a .repl file (loadPlatformDescription @file.repl)
        lines.append("try {")
        lines.append("    mach loadPlatformDescription $platform")
        lines.append("} catch {")
        lines.append("    mach loadPlatformDescription @{{$platform}}")
        lines.append("}")

        # Firmware load
        if fw.elf:
            lines.append(f"sysbus LoadELF @{{fw.elf.as_posix()}}")
        else:
            lines.append(f"sysbus LoadBinary @{{fw.bin.as_posix()}} {{fw.bin_load_addr}}")

    # UART capture (best effort; platform-specific wiring may be required)
    if uart_log:
        lines.append(f"emulation CreateUartAnalyzer \"uart\" \"{{uart_log.as_posix()}}\"")

    # Debugger
    if gdb_port:
        lines.append(f"machine StartGdbServer {{gdb_port}}")

    # Start execution
    if start:
        lines.append("start")

    # Optional checkpoint
    if checkpoint_out:
        lines.append(f"Save @{{checkpoint_out.as_posix()}}")

    lines.append("")
    return "\n".join(lines)

def renode_run(
    *,
    platform: str,
    fw: FirmwareSpec,
    uart_log: Optional[Path],
    gdb_port: Optional[int],
    checkpoint_out: Optional[Path],
) -> int:
    """Run Renode with a generated script."""
    require_exe("renode")
    fw.validate()

    script = _renode_script(
        platform=platform,
        fw=fw,
        uart_log=uart_log,
        gdb_port=gdb_port,
        checkpoint_out=checkpoint_out,
        checkpoint_in=None,
        start=True,
    )

    with tempfile.TemporaryDirectory(prefix="firmware-lab-renode-") as td:
        script_path = Path(td) / "run.resc"
        script_path.write_text(script, encoding="utf-8")

        p = run_process(["renode", "--console", "--disable-xwt", str(script_path)])
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="")
        return p.wait()

def renode_restore(*, checkpoint_in: Path, gdb_port: Optional[int]) -> int:
    """Restore a previously saved Renode snapshot and start execution.

    This is the basis for clone (start new instance from snapshot) and migrate
    (stop old instance, start new one from snapshot).
    """
    require_exe("renode")
    if not checkpoint_in.exists():
        raise FileNotFoundError(checkpoint_in)

    script = _renode_script(
        platform="",
        fw=FirmwareSpec(elf=Path(__file__)),
        uart_log=None,
        gdb_port=gdb_port,
        checkpoint_out=None,
        checkpoint_in=checkpoint_in,
        start=True,
    )

    with tempfile.TemporaryDirectory(prefix="firmware-lab-renode-") as td:
        script_path = Path(td) / "restore.resc"
        script_path.write_text(script, encoding="utf-8")
        p = run_process(["renode", "--console", "--disable-xwt", str(script_path)])
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="")
        return p.wait()