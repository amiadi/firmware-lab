# QEMU patterns for bare-metal .bin / .elf

These are examples; actual working combinations depend on your target.

## RISC-V (virt) + ELF

```bash
qemu-system-riscv64 -M virt -nographic \
  -kernel fw.elf
```

## RISC-V (virt) + raw bin at address

```bash
qemu-system-riscv64 -M virt -nographic \
  -device loader,file=fw.bin,addr=0x80000000
```

## Enable QMP + gdbstub

```bash
qemu-system-riscv64 -M virt -nographic \
  -qmp tcp:127.0.0.1:4444,server=on,wait=off \
  -gdb tcp::1234 -S \
  -kernel fw.elf
```

## Destination for migration (incoming)

Start destination QEMU first, listening for incoming migration:

```bash
qemu-system-riscv64 -M virt -nographic \
  -qmp tcp:127.0.0.1:4445,server=on,wait=off \
  -incoming tcp:0:5555
```

Then migrate from source via QMP:
- `migrate uri=tcp:127.0.0.1:5555`