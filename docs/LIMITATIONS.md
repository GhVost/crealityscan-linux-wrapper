# Compatibility and acceptance boundaries

CrealityScan 4.3.3 (bundled Orbbec SDK SHA-256 6987…d740, which adds six exports
over 4.3.2) has passed install, all three diagnostics (OpenCL, OpenGL,
synthetic Media Foundation) and a startup smoke test on Ubuntu 26.04 with Intel
Arc graphics (intel-opencl-icd). With a physical Pika (firmware not upgraded)
over USB 3: SDK detection through the proxy, scanner controls, the scanner's
buttons, IR and colour preview, and starting and pausing Blue Laser scans with
markers. 4.3.3's blue-laser OpenCL program is byte-identical to 4.3.2's: the
pinned fingerprint matched and the 16-bit atomic fix applied. Not yet confirmed
on 4.3.3: meshing, STL export and reopening a project. Those scanner sessions used
a compiler-built proxy; the install-time generated proxy that replaced it has an
identical export table (checked by reading both back) and passed install, the
diagnostics and startup, but has not yet been used with a physical scanner.

Untested CrealityScan versions (`--allow-untested`) get the same generated proxy,
but the bridge and the blue-laser OpenCL fix depend on SDK and kernel behaviour
that a new version may change; the OpenCL fix stays inactive for an unknown
kernel. Treat any new version as unverified until a scan has been exported.

4.3.3 observations: the device rejects SDK properties 151 and 152 (error 3) at
each stream start, with no visible effect so far; the app's performance test
refuses to run on battery (`OB_SCAN_ERROR_NO_PLUG_IN_POWER`, as on Windows);
calibration needs Creality's server for board data, which the default USB
sandbox blocks (scanning with the factory calibration works). USB sessions are now
online by default, which allows it, but calibration that way has not been tested yet. Switching the scanner
off during a session makes the app crash or stop with a USB "No such device"
error and the launcher exit with code 3; switch it on and relaunch. The notes
below describe the 4.3.2 results.

Known original setup: CrealityScan 4.3.2, SDK 3.5.3.260921, Pika firmware 1.1.1,
CachyOS x86-64, RX 6800 XT, ROCm OpenCL, standalone Wine 11 with Proton 11.0's
DXVK, XWayland. The pinned official DXVK 3.1.1 with CI-built helpers has since
passed live USB scanning in every mode the user tried, at about 80–90 FPS in
Laser Lines mode, the same as the earlier install. Prebuilt helpers are built
on Ubuntu 24.04 and need glibc 2.39 or newer; GPU detection in setup picks one GPU and can be overridden with
`--gpu-name`. NVIDIA: one user's T600 laptop GPU (TUXEDO OS, KDE Wayland) passed
setup and diagnostics with NVIDIA device access and PRIME offload; scanning on
NVIDIA is not yet reported, and the RX 6800 XT allocation fix does not apply.
USB support covers only the Pika (USB ID 2bc5:0c0b). With another Creality
scanner connected, USB launch stops with a message pointing to
`creality.py survey`, a read-only report owners can share to help add support.
Other scanners, firmware, GPU families, OpenCL stacks and app versions are not
validated by making configuration portable. The allocation change remains
restricted to AMD gfx1030/RX 6800 XT contexts. Other hardware requires new evidence.

In the original development setup, Wi-Fi infrared capture/fusion/export/reopen,
blue-laser acquisition, USB preview/acquisition, marker-free preview and Local
Detail operation were observed. The USB Fast allocator reached about 30 fps
marker-free preview after a device-memory change. Full moving acquisition,
fusion/export and extended stability were not all revalidated on that final
allocator build. These historical results do not automatically validate this
freshly packaged prefix. In the packaged fresh prefix, a short USB Blue Laser
with markers scan passed preview (approximately 110 FPS reported by the user),
point-cloud acquisition, mesh generation, STL export and reopening. See
[VALIDATION.md](VALIDATION.md) for evidence and remaining untested cases.

Known issues: reconnect can leave the SDK in a frame-pairing failure state;
a physical scanner power cycle recovered one occurrence. Another reconnect
session reported Wine's SuspendThread loop failure. Dense capture once produced
a ROCm SDMA memory fault; process-local HSA_ENABLE_SDMA=0 supported a later
successful capture but is not a proven universal cure. Preserve projects and
logs before investigating, and do not silently modify a working installation.

The hardened sandbox hides other host-home files. The app can save only to its
Windows Documents folder (the exports folder, which also holds its projects) and
its own prefix; its save dialog
may open in the install folder first, so choose Documents. Importing a model
needs it copied into the exports folder. Wi-Fi requires the user's existing
network setup and shares host networking; see [SECURITY.md](../SECURITY.md) for
this weaker boundary. USB mode deliberately has no network, so vendor
cloud/login/update services may log expected failures.

The default desktop display shares your X server with other X11 apps; the
optional isolated display (xwayland-satellite) needs XWayland 23.1+ and is not
packaged by Ubuntu, so Ubuntu 22.04 cannot use it. Window behavior has been
checked only on KDE Plasma (Wayland) on CachyOS; GNOME/Ubuntu is untested.
Unity pauses startup while its window lacks focus; a window that opens in the
background waits until clicked. Live scanning, export and the post-export folder
window have not yet been retested on either display mode.

No scanner performance test, live preview, acquisition, tracking quality, mesh
accuracy or export can be established by synthetic camera/OpenCL/GUI smoke tests.
For a fresh prefix, perform those hardware checks separately with a suitable
marked object. GUI smoke only checks startup logs, not sustained responsiveness.

The optional native recorder/replay tool is independent of Wine and vendor DLLs.
It records raw stereo/colour/metadata and replays them; it does not reconstruct
3D, supply calibration or implement a mobile scanner app. Its recording data,
calibration investigations and private engineering handoff are not in this repo.

The live scan results above predate the security hardening. Fresh installation,
GPU diagnostics and startup must be distinguished from a new live scan acceptance
test; see the security-hardening section in VALIDATION.md.
