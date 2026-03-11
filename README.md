# Firmware Lab

Firmware Lab is a small Python CLI for experimenting with firmware execution without physical hardware. The repository currently focuses on two emulator-driven workflows:

- **Renode** for running firmware, saving checkpoints, and restoring snapshots
- **QEMU/QMP** helpers for run, migration, and clone workflows

The package name is `firmware-lab` and it installs a `firmware-lab` command line entrypoint.

## Status

The Renode implementation is present in this repository and is the most complete part of the project today.

The QEMU side is still in flux. In particular, `src/firmware_lab/qemu_runner.py` is currently a placeholder module, so the packaged CLI cannot be imported successfully until that implementation is completed. The repository already carries a warning about the QEMU path being broken; this README keeps that limitation explicit so the documented state matches the current project.

## Requirements

- Python 3.10+
- [Renode](https://renode.io/) in `PATH` for Renode workflows
- QEMU in `PATH` for eventual QEMU workflows

## Installation

Install the project in editable mode while working from the repository root:

```bash
cd /path/to/firmware-lab
python -m pip install -e .
```

Project metadata lives in `pyproject.toml`, and the console script entrypoint is:

```toml
[project.scripts]
firmware-lab = "firmware_lab.cli:main"
```

## Project Layout

```text
src/firmware_lab/cli.py            Main command-line interface
src/firmware_lab/common.py         Shared helpers and firmware argument validation
src/firmware_lab/renode_runner.py  Renode run/restore implementation
src/firmware_lab/qmp.py            Minimal QMP client
src/firmware_lab/qemu_runner.py    QEMU runner placeholder (currently incomplete)
templates/qemu/example_qemu_args.md
```

## Firmware Inputs

The CLI is designed around a single firmware image per run:

- `--elf PATH` for an ELF firmware image
- `--bin PATH --bin-load-addr ADDR` for a raw binary image

`FirmwareSpec.validate()` enforces that you provide **exactly one** of `--elf` or `--bin`, and that raw binaries always include `--bin-load-addr`.

## Renode Workflows

The Renode CLI surface is defined in `src/firmware_lab/cli.py` and implemented in `src/firmware_lab/renode_runner.py`.

### Run firmware in Renode

```bash
firmware-lab renode run \
  --platform PLATFORM_OR_REPL \
  --elf /path/to/fw.elf
```

Or, for a raw binary:

```bash
firmware-lab renode run \
  --platform PLATFORM_OR_REPL \
  --bin /path/to/fw.bin \
  --bin-load-addr 0x08000000
```

Supported Renode run options:

- `--platform`: built-in Renode platform name or path to a `.repl` file
- `--uart-log PATH`: capture UART output to a file
- `--gdb PORT`: start Renode's GDB server on the chosen port
- `--checkpoint-out PATH`: save a Renode snapshot after startup

Internally, the runner generates a temporary `.resc` script and launches:

```bash
renode --console --disable-xwt <generated-script>
```

### Restore a Renode checkpoint

```bash
firmware-lab renode restore \
  --checkpoint-in /path/to/snapshot \
  --gdb 3333
```

This restores a previously saved Renode snapshot and starts execution again.

### UART logging

When `--uart-log` is provided, the generated Renode script adds a UART analyzer output file. Platform-specific UART wiring may still be required depending on the target platform description.

## QEMU Workflows

The intended CLI structure in `src/firmware_lab/cli.py` exposes the following QEMU commands:

- `firmware-lab qemu run`
- `firmware-lab qemu migrate`
- `firmware-lab qemu clone`

Intended arguments include:

- `--arch` such as `riscv64`, `mips`, `arm`, or `aarch64`
- `--machine` such as `virt` or `malta`
- `--qmp HOST:PORT`
- `--gdb PORT`
- repeatable `--extra-arg`

However, the current repository state does **not** include a working `qemu_runner.py` implementation for those commands, so they should be treated as planned interface rather than verified functionality.

For raw QEMU command-line examples, see:

- `templates/qemu/example_qemu_args.md`

That template includes examples for:

- RISC-V `virt` with an ELF kernel
- RISC-V `virt` with a raw binary load address
- QMP plus gdbstub setup
- incoming migration targets

## QMP Support

The repository includes a small QMP client in `src/firmware_lab/qmp.py` that:

- opens a TCP connection to a QMP server
- consumes the greeting
- enables `qmp_capabilities`
- sends commands and waits for a `return` or `error` response

This is the basis for the planned QEMU migration and clone automation.

## Current Limitation

At the moment, invoking `firmware-lab --help` fails during import because `cli.py` imports QEMU helper functions that are not yet defined in `src/firmware_lab/qemu_runner.py`.

## Troubleshooting

- **`Required executable not found in PATH`**: install the required emulator (`renode`, and later QEMU) and ensure it is available on your shell `PATH`.
- **`Provide exactly one of --elf or --bin`**: choose one firmware input format per command.
- **`--bin-load-addr is required when using --bin`**: raw binaries must include an explicit load address.
- **CLI import failure**: this is currently caused by the incomplete `qemu_runner.py` module.
