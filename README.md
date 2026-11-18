# CrealityScan Linux Wrapper

Run **CrealityScan for Windows** with a **Creality Pika** 3D scanner on Linux, as a
normal app in your app menu. CrealityScan runs in Wine inside a sandbox, opens as
ordinary desktop windows and saves scans to `Documents/CrealityScan`.

This is an unofficial community project, not affiliated with Creality or Orbbec.
You download CrealityScan yourself from Creality; it is never bundled here.

It is a fork of
[doolan-oss/crealityscan-linux-compat](https://github.com/doolan-oss/crealityscan-linux-compat),
which wrote the USB camera bridge, sandbox and OpenCL fixes. This fork adds:

- **Any CrealityScan version.** The SDK proxy is generated at install time from the
  installed SDK, so new versions no longer need a rebuild. Tested versions are
  accepted automatically; others with `--allow-untested`.
- **Any GPU with Vulkan and OpenCL**, detected automatically: AMD, NVIDIA (including
  hybrid laptops) and Intel.
- **A self-installing package** (`.run`) that works offline, with an uninstaller.
- **Internet access** for calibration-board data and firmware updates (on by default;
  an offline launch is one click away).

## Install

1. **Install the system packages** (once).

   Ubuntu / Debian:
   ```sh
   sudo apt install bubblewrap python3 psmisc procps
   sudo dpkg --add-architecture i386 && sudo apt update
   sudo apt install libc6:i386 libfreetype6:i386 libx11-6:i386 libxext6:i386 libxcursor1:i386 \
     libxrandr2:i386 libxi6:i386 libxfixes3:i386 libxrender1:i386 libxcomposite1:i386 \
     libxinerama1:i386 libxkbcommon0:i386 libfontconfig1:i386 libudev1:i386 libusb-1.0-0:i386 \
     libasound2t64:i386 libpulse0:i386 libgl1:i386 libvulkan1:i386 libwayland-client0:i386 \
     libglib2.0-0t64:i386
   ```
   Arch / CachyOS (enable `[multilib]` first; this 32-bit list is untested):
   ```sh
   sudo pacman -S --needed bubblewrap python psmisc procps-ng lib32-glibc lib32-freetype2 \
     lib32-libx11 lib32-vulkan-icd-loader
   ```
   The 32-bit libraries are for Wine, which runs CrealityScan's 32-bit installer.

2. **Install your GPU's OpenCL driver.** CrealityScan processes scans with OpenCL.

   | GPU | Ubuntu / Debian | Arch / CachyOS |
   |---|---|---|
   | Intel | `intel-opencl-icd` | `intel-compute-runtime` |
   | AMD | ROCm OpenCL | `rocm-opencl-runtime` |
   | NVIDIA | proprietary driver with OpenCL | `opencl-nvidia` |

   A Vulkan driver is also needed; desktop distributions normally have one.

3. **Download CrealityScan for Windows** from
   [Creality](https://www.creality.com/download/creality-pika) into your Downloads
   folder (`CrealityScan_win_<version>.exe`).

4. **Run the installer package** from the
   [Releases page](https://github.com/GhVost/crealityscan-linux-wrapper/releases):

   ```sh
   sh crealityscan-linux-*.run
   ```

   It unpacks to `~/.local/share/crealityscan-linux/app`, installs CrealityScan,
   checks your GPU and adds **CrealityScan** to your app menu. It needs no
   internet connection and about 3 GB of disk space; installing takes a few minutes.

5. **Allow scanner access** (once). If the installer prints a `sudo` command, run
   it, then unplug and replug the scanner:

   ```sh
   sudo cp ~/.local/share/crealityscan-linux/app/config/70-creality-pika.rules /etc/udev/rules.d/
   sudo udevadm control --reload
   ```

6. **Connect the scanner by USB**, switch it on, and open **CrealityScan** from your
   app menu.

To update, run a newer `.run` the same way. Your settings and scans are kept.
To uninstall, run `sh crealityscan-linux-*.run --uninstall` (or
`~/.local/share/crealityscan-linux/app/uninstall.sh`). Scans in
`Documents/CrealityScan` are kept.

### CrealityScan versions

| Version | Status |
|---|---|
| 4.3.3 | Tested: install, GPU checks, Pika detection, buttons, live preview, scanning, calibration |
| 4.3.2 | Tested by the original project, including full scans and STL export |

A version not listed is refused, because nobody has checked it yet. To try it:

```sh
sh crealityscan-linux-*.run --allow-untested
```

If it works (or doesn't), please file a
[hardware report](https://github.com/GhVost/crealityscan-linux-wrapper/issues/new?template=hardware-report.yml).

## Using it

- **Plug in your laptop's charger.** CrealityScan refuses its performance test on
  battery power, on Windows too.
- **Close the app before switching the scanner off.** Switching it off while the app
  runs makes the app crash.
- **Saving:** choose **Documents** in the save dialog. That is
  `~/Documents/CrealityScan`; projects are in its `Projects` folder. To import a
  model, copy it into that folder first.
- **Window behind others?** Click it. The app pauses loading while in the background.
- **Scanner buttons:** middle starts and pauses, down zooms, **left deletes the
  scan**. End a scan with the on-screen tick instead.
- **Problems:** you'll usually get a desktop notification. Logs are in
  `~/.local/share/crealityscan-linux/data/logs`.

### Internet access (calibration, firmware updates)

The app is **online by default**, so calibration can download your calibration
board's data from Creality and the app can check for firmware updates. With
network access the app shares your computer's network and can reach local
services; the rest of the sandbox (files, devices, display) stays in place. See
the *Wi-Fi and online mode* section of [SECURITY.md](SECURITY.md).

- **One offline session:** right-click **CrealityScan** in your app menu and choose
  **Open offline (no internet access)**.
- **Calibration works** (tested once with firmware 1.1.13). **Decline firmware
  updates** the app offers: flashing through the bridge is untested.
- **Always offline:** set `"allow_host_network": false` in
  `~/.local/share/crealityscan-linux/app/config.local.json`. Scanning works
  offline with the scanner's factory calibration; calibration then fails.

## Scanners

Only the **Creality Pika** works over USB so far: the USB bridge implements the
Pika's camera and control interfaces, and other scanners differ. CrealityScan also
supports the Raptor, Otter and Ferret families. If you own one, run this and paste
the output into a hardware report with the model name:

```sh
python3 ~/.local/share/crealityscan-linux/app/scripts/creality.py survey
```

It only reads USB descriptions (IDs, camera formats) and contains no serial numbers.
Wi-Fi mode doesn't use the USB bridge, so scanners with Wi-Fi may work in Wi-Fi
mode; that is untested. See [SETUP.md](docs/SETUP.md).

## Tested systems

| System | GPU | Result |
|---|---|---|
| CachyOS, KDE Plasma | AMD RX 6800 XT (ROCm) | full scans, 80–110 FPS (original project, 4.3.2) |
| TUXEDO OS, KDE | NVIDIA T600 laptop | setup and GPU checks (original project) |
| Ubuntu 26.04 | Intel Arc (ARL) integrated | 4.3.3: install, GPU checks, live Pika preview and scanning, ~30 FPS |

Known issues and untested areas are in [LIMITATIONS.md](docs/LIMITATIONS.md).
Please file a
[hardware report](https://github.com/GhVost/crealityscan-linux-wrapper/issues/new?template=hardware-report.yml)
whether it works or not.

## Install from source

```sh
git clone https://github.com/GhVost/crealityscan-linux-wrapper.git
cd crealityscan-linux-wrapper
python3 scripts/creality.py setup        # add --allow-untested for other versions
```

Without a `build/` folder, setup compiles the helpers, which needs
`clang lld llvm gcc libyuv-dev libjpeg-dev opencl-c-headers` (Ubuntu names; Arch:
`clang lld llvm gcc libyuv opencl-headers`). Keep the folder; the menu entry runs
from it. The full manual recipe is in [SETUP.md](docs/SETUP.md).

## For developers

```sh
python3 scripts/creality.py build --portable   # helpers into build/
python3 -m unittest discover -s tests          # offline tests
python3 scripts/pack.py                        # dist/: .run, .tar.gz, SHA256SUMS
```

`pack.py` bundles the project, the built helpers and the pinned Wine and DXVK
archives (downloaded and checksummed if needed). To add a tested CrealityScan
version, install it with `--allow-untested`, test it with a scanner, and add its
installer and SDK hashes to `crealityscan_tested` in
[config/versions.lock.json](config/versions.lock.json) (newest first).

How it works:

- `src/usb-bridge/`: Windows Media Foundation and device-enumeration bridge that
  feeds the Pika's Linux V4L2 cameras and controls to the Windows SDK.
- `src/usb-bridge/sdk-proxy.c` + `scripts/pe_exports.py`: a stub DLL that loads the
  bridge, given the installed SDK's export table at install time.
- `src/opencl/`: opt-in OpenCL fixes (blue-laser kernel for known kernel
  fingerprints, RX 6800 XT allocation); anything unrecognised passes through.
- `src/probes/`: Windows OpenCL/OpenGL/Media Foundation probes used by the GPU check.
- `scripts/`: setup, sandbox, launcher, packaging. `tools/pika-recorder/`: a
  [native recorder](docs/NATIVE_RECORDER.md) that needs no Wine.

Security model, mount allowlist and network rules: [SECURITY.md](SECURITY.md).

## License

Original work is MIT-licensed; see [LICENSE](LICENSE), [NOTICE.md](NOTICE.md),
the [provenance audit](docs/PROVENANCE.md) and
[third-party notices](THIRD_PARTY_NOTICES.md). CrealityScan, the Orbbec SDK, Wine
and DXVK keep their own licenses and are not part of this repository.
