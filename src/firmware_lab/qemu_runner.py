from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .common import FirmwareSpec, ToolError, require_exe, run_process
from .qmp import QMPClient

def qemu_binary_for_arch(arch: str) -> str:
    # Expect user to have relevant QEMU system binaries installed.
    # Examples: qemu-system-riscv64, qemu-system-mips, qemu-system-arm, qemu-system-aarch64
    return f"qemu-system-{arch}"

def qemu_run(
    *,
    arch: str,
    machine: str,
    fw: FirmwareSpec,
    qmp_host: str,
    qmp_port: int,
    gdb_port: Optional[int],
    extra_args: list[str],
) -> subprocess.Popen:
    fw.validate()
    qemu_bin = qemu_binary_for_arch(arch)
    require_exe(qemu_bin)

    # NOTE: Loading .bin/.elf is machine-dependent in QEMU.
    # We provide common patterns:
    # - For many bare-metal cases, `-kernel` can load an ELF.
    # - For raw binaries, many machines accept `-device loader,file=...,addr=...`
    args = [qemu_bin, "-M", machine, "-nographic"]

    # QMP server
    args += ["-qmp", f"tcp:{qmp_host}:{qmp_port},server=on,wait=off"]

    if gdb_port is not None:
        # QEMU gdb stub; -S halts CPU at start until debugger continues
        args += ["-gdb", f"tcp::{{gdb_port}}", "-S"]

    if fw.elf:
        args += ["-kernel", str(fw.elf)]
    else:
        args += ["-device", f"loader,file={{fw.bin}},addr=0x{{fw.bin_load_addr:x}}"]

    args += extra_args

    return run_process(args)

def qemu_migrate(*, qmp_host: str, qmp_port: int, uri: str) -> None:
    c = QMPClient(qmp_host, qmp_port)
    c.connect()
    try:
        # Stop VM for a clean migrate (optional; users can remove for live migrate if device model supports it)
        c.execute("stop")
        c.execute("migrate", {"uri": uri})

        # Poll migrate status
        for _ in range(120):
            st = c.execute("query-migrate")
            status = st.get("status")
            if status in ("completed", "failed", "cancelled"):
                if status != "completed":
                    raise ToolError(f"Migration did not complete: {{st}}")
                break
        else:
            raise ToolError("Migration timed out")
    finally:
        c.close()

def qemu_clone_to_file(*, qmp_host: str, qmp_port: int, out_path: Path) -> None:
    """Clone" by exporting VM state as a migration stream to a file.

    Then you can start a new QEMU instance with something like:
      qemu-system-ARCH ... -incoming 'exec:cat file'

    Exact restore depends on platform and QEMU build.
    """

    c = QMPClient(qmp_host, qmp_port)
    c.connect()
    try:
        c.execute("stop")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write migration stream to file via exec redirection.
        uri = f"exec:cat > {{shlex.quote(str(out_path))}}"
        c.execute("migrate", {"uri": uri})

        for _ in range(120):
            st = c.execute("query-migrate")
            status = st.get("status")
            if status in ("completed", "failed", "cancelled"):
                if status != "completed":
                    raise ToolError(f"Clone export did not complete: {{st}}")
                break
        else:
            raise ToolError("Clone export timed out")

        c.execute("cont")
    finally:
        c.close()
