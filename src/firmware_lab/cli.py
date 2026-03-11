from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .common import FirmwareSpec, ToolError, parse_int
from .renode_runner import renode_restore, renode_run
from .qemu_runner import qemu_clone_to_file, qemu_migrate, qemu_run

def _add_firmware_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--elf", type=Path, default=None, help="Path to firmware ELF")
    p.add_argument("--bin", type=Path, default=None, help="Path to raw firmware bin")
    p.add_argument("--bin-load-addr", type=parse_int, default=None, help="Load address for raw bin (e.g. 0x08000000)")

def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    ap = argparse.ArgumentParser(prog="firmware-lab")
    sp = ap.add_subparsers(dest="tool", required=True)

    # Renode
    ren = sp.add_parser("renode")
    ren_sp = ren.add_subparsers(dest="cmd", required=True)

    ren_run_p = ren_sp.add_parser("run")
    ren_run_p.add_argument("--platform", required=True, help="Renode platform name or path to .repl")
    _add_firmware_args(ren_run_p)
    ren_run_p.add_argument("--uart-log", type=Path, default=None)
    ren_run_p.add_argument("--gdb", type=int, default=None, help="Start Renode GDB server on port")
    ren_run_p.add_argument("--checkpoint-out", type=Path, default=None, help="Save Renode snapshot to this path")

    ren_rest_p = ren_sp.add_parser("restore")
    ren_rest_p.add_argument("--checkpoint-in", type=Path, required=True)
    ren_rest_p.add_argument("--gdb", type=int, default=None)

    # QEMU
    q = sp.add_parser("qemu")
    q_sp = q.add_subparsers(dest="cmd", required=True)

    q_run_p = q_sp.add_parser("run")
    q_run_p.add_argument("--arch", required=True, help="QEMU arch suffix, e.g. riscv64, mips, arm, aarch64")
    q_run_p.add_argument("--machine", required=True, help="QEMU machine name, e.g. virt, malta")
    _add_firmware_args(q_run_p)
    q_run_p.add_argument("--qmp", required=True, help="QMP host:port, e.g. 127.0.0.1:4444")
    q_run_p.add_argument("--gdb", type=int, default=None, help="Start QEMU gdbstub on port (halts CPU at start)")
    q_run_p.add_argument("--extra-arg", action="append", default=[], help="Additional QEMU args (repeatable)")

    q_mig_p = q_sp.add_parser("migrate")
    q_mig_p.add_argument("--qmp", required=True, help="QMP host:port of source VM")
    q_mig_p.add_argument("--uri", required=True, help="Migration URI, e.g. tcp:DESTHOST:5555")

    q_clone_p = q_sp.add_parser("clone")
    q_clone_p.add_argument("--qmp", required=True, help="QMP host:port of source VM")
    q_clone_p.add_argument("--out", type=Path, required=True, help="Path to write migration stream file")

    ns = ap.parse_args(argv)

    try:
        if ns.tool == "renode":
            if ns.cmd == "run":
                fw = FirmwareSpec(elf=ns.elf, bin=ns.bin, bin_load_addr=ns.bin_load_addr)
                return renode_run(
                    platform=ns.platform,
                    fw=fw,
                    uart_log=ns.uart_log,
                    gdb_port=ns.gdb,
                    checkpoint_out=ns.checkpoint_out,
                )
            if ns.cmd == "restore":
                return renode_restore(checkpoint_in=ns.checkpoint_in, gdb_port=ns.gdb)

        if ns.tool == "qemu":
            if ns.cmd == "run":
                host, port_s = ns.qmp.split(':')
                port = int(port_s)
                fw = FirmwareSpec(elf=ns.elf, bin=ns.bin, bin_load_addr=ns.bin_load_addr)
                p = qemu_run(
                    arch=ns.arch,
                    machine=ns.machine,
                    fw=fw,
                    qmp_host=host,
                    qmp_port=port,
                    gdb_port=ns.gdb,
                    extra_args=ns.extra_arg,
                )
                assert p.stdout is not None
                for line in p.stdout:
                    print(line, end="")
                return p.wait()

            if ns.cmd == "migrate":
                host, port_s = ns.qmp.split(':')
                qemu_migrate(qmp_host=host, qmp_port=int(port_s), uri=ns.uri)
                return 0

            if ns.cmd == "clone":
                host, port_s = ns.qmp.split(':')
                qemu_clone_to_file(qmp_host=host, qmp_port=int(port_s), out_path=ns.out)
                return 0

        raise ToolError("Unknown command")
    except (ToolError, ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
