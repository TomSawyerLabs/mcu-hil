# v1 AVR Test HAT: software from the 2023 CI Pi's SD card

These files were copied on 2026-11-11 from the microSD card of the 2023 Pi that ran
dfu-programmer's hardware CI. The card was plugged into DeskyPi as `/dev/sda`, which
BenchBob mounts read-only at `/srv/nfs/drives/{boot,rootfs}`.

## The card

- Raspberry Pi OS (Debian 11 bullseye), 64-bit.
  - Hostname `AVRActionPi`.
  - Kernel and firmware from 2023-01-17.
  - 4.9 GB used of 15 GB.
- **The root filesystem is plain ext4.** There is no overlayfs: `/opt/update-system` has the overlay
  lines commented out.
- **Users:**
  - `pi` has passwordless sudo.
  - `action` (uid 1001) runs the runner. It is in groups `gpio` and `plugdev`.
- **Runner:**
  - Actions runner 2.300.2 (December 2022), registered to the **repo** as `AVRActionPi`
    (agentId 21) with `disableUpdate: true`.
  - Its last log is from 2023-02-21. GitHub now lists 0 runners on the repo, so the
    registration and the key on the card are dead.
- `system-update.timer` ran `/opt/update-system` every Sunday at 4 AM. That script:
  - runs apt upgrade;
  - upgrades cpp-coveralls with pip;
  - rebuilds avrdude from git;
  - reinstalls the runner from the latest tarball, using the saved credentials.

## What's here, and why it's worth keeping

| Path | What it is |
| --- | --- |
| `opt/action-scripts/{shared,before,after}.sh` | Job-start and job-end hooks (`ACTIONS_RUNNER_HOOK_JOB_STARTED/COMPLETED`). They hold the **authoritative GPIO map**, power the AVR on, select the bootloader and enable the ISP and serial buffers. GPIO26 doubles as a job lock and the activity LED. |
| `opt/reset.sh` | Pulses AVR reset (GPIO13). |
| `opt/avrdude.sh`, `home/pi/.config/avrdude/avrdude.rc` | avrdude wrapper (`-c avr-test-hat -p atmega8u2 -B 500kHz`) and the `avr-test-hat` programmer: `linuxspi` with `reset = 13`. |
| `etc/systemd/system/*` | Runner service (sets `AVRDUDE=/opt/avrdude.sh`, `TARGET=atmega8u2`) and the weekly update timer. |
| `etc/udev/rules.d/60-dfu.rules` | Atmel USB VID `03eb` → group `plugdev`. |
| `boot/config.txt`, `boot/cmdline.txt` | `dtparam=spi=on`, `enable_uart=1`, `arm_64bit=1`. |
| `home/pi/avr-test-hat/` | Unpublished TypeScript HAT tool (`pigpio`): `status`, `reset [boot]`, `clock <Hz>` (GPCLK0 on GPIO4, enable on GPIO17). Never committed anywhere. |
| `home/pi/dump-avr-boot/` | AVR firmware that streams the whole flash out over UART at 1 Mbaud, plus a TypeScript reader. Together they **read out the factory DFU bootloader**: `reader/ATmega8u2.hex`. |
| `home/pi/at90usb82-bl-usb-1_0_5.hex` | Atmel's published DFU bootloader for the AT90USB82 (same family). |
| `home/pi/{good,bad,dump,dump2}.hex`, `test-avr/`, `bisect-test.sh` | 2023 debugging artifacts: `good.hex` and `bad.hex` are byte-identical. |
| `OS Image/setup.sh` | An earlier (2023-01-17) image-setup script that sat uncommitted in the old `avr-test-hat` checkout. |

## GPIO map (from `shared.sh` and `pins.ts`)

| GPIO | Function |
| --- | --- |
| 27 | AVR VCC enable |
| 18 | AVR USB VBUS (UVCC) enable |
| 13 | AVR reset (avrdude's linuxspi reset pin) |
| 19 | Reset pull |
| 2 | HWB (low = run the bootloader) |
| 3 | HWB pull |
| 5 | SPI/ISP buffer disable (low = enabled) |
| 8 | Serial buffer disable (low = enabled) |
| 4 / 17 | Clock out (GPCLK0) / clock override enable |
| 10, 9, 11 | SPI0 MOSI, MISO, SCLK → AVR ISP |
| 14 / 15 | UART Tx / Rx ↔ AVR |
| 26 | Activity LED, also used as the job lock |

## Deliberately not copied

- The OS itself.
- `node_modules`.
- The runner binaries.
- The avrdude clone (upstream `5ec72e2`, 2023-01-14).
- The strace logs.
- The dead runner credentials (`.credentials*` and `/opt/action-runner.credentials.tar.gz`).
- `/etc/shadow`, the Wi-Fi config and `pi`'s shell history.
- `home.tar.gz`, a 2023-01-24 snapshot of the same home dir. Only its `avr-test/test.S` and `build.sh` were missing elsewhere; they're in `home/pi/avr-test-hat-avr-test-from-home.tar.txt`.
