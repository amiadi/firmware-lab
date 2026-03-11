# firmware-lab

Automate embedded firmware execution without hardware, with snapshot-based clone/migrate.

Supports:
- Renode automation (recommended for Cortex-M / STM32-class bare metal)
  - Load `.elf` directly
  - Load raw `.bin` with explicit load address (e.g., 0x08000000)
  - Start/stop, UART capture
  - Optional GDB server
  - Checkpoints via `Save`/`Load` snapshots (clone/migrate)

- QEMU automation with QMP (recommended for MIPS / RISC-V / ARMv7-v8 where a QEMU machine exists)
  - Load `.elf` when supported by machine/loader path
  - Load `.bin` via device/loader options when applicable (varies by machine)
  - Optional GDB stub
  - Migration to another instance (migrate)
  - Clone via snapshot/migration-to-file style export + restore

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## CLI overview

```bash
# Renode: run an ELF on a platform, enable GDB, save snapshot checkpoint
firmware-lab renode run \
  --platform stm32f4_discovery \
  --elf ./firmware.elf \
  --gdb 3333 \
  --checkpoint-out ./chkpt.save

# Renode: load checkpoint into a new instance (clone)
firmware-lab renode restore \
  --checkpoint-in ./chkpt.save

# QEMU: start a VM with QMP + optional gdbstub
firmware-lab qemu run \
  --arch riscv64 \
  --machine virt \
  --elf ./fw.elf \
  --qmp 127.0.0.1:4444 \
  --gdb 1234

# QEMU: migrate VM to another instance (destination must be running in "incoming" mode)
firmware-lab qemu migrate \
  --qmp 127.0.0.1:4444 \
  --uri tcp:127.0.0.1:5555

# QEMU: clone by exporting migration state to a file and restoring into a new instance
firmware-lab qemu clone \
  --qmp 127.0.0.1:4444 \
  --out ./qemu.mig
```

## Notes / constraints

- Raw `.bin` requires a load address. For STM32 flash typical is `0x08000000`, SRAM typical is `0x20000000`.
- QEMU firmware loading differs by machine/arch; this repo provides common patterns and a QMP workflow, but you must choose a compatible `-M` machine and loader method for your target.
- "Clone" is implemented as a controlled pause + export + restore. True concurrent fork at an exact cycle boundary depends on the emulator backend.