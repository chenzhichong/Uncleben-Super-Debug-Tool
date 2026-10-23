# CH552G CDC Controller GUI

Cross-platform desktop GUI prototype using PySide6 and pyserial.

## Install and run

```bash
python -m pip install -r requirements.txt
python main.py
```

Use `python3` instead of `python` if needed.

## Device discovery

Defaults are based on the `cdc_echo/src/config.h` screenshot:
- VID: `0x16C0`
- PID: `0x27DD`

The program scans ports dynamically and lists all matching devices. It does not hard-code COM names and does not depend on a unique serial number. If multiple identical modules are connected, select the intended port in the list before connecting. If only one is connected, select it and press Connect.

Change `USB_VID` / `USB_PID` in `main.py` if the firmware uses different IDs.

## Example protocol (must match firmware)

| Request | Meaning | Example reply |
|---|---|---|
| `01 01` | P32 LED ON | `81 01` |
| `01 00` | P32 LED OFF | `81 00` |
| `02 00` | Query LED state | `82 00` or `82 01` |

The current `cdc_echo` example may only echo bytes and may not implement these commands. Until firmware implements this protocol, the GUI's serial connection and raw HEX send are real, but LED control/status parsing will not work as intended. Confirm the CDC firmware's baud-rate behavior before changing `BAUDRATE`.

## Build an app

```bash
python -m pip install pyinstaller
pyinstaller --noconfirm --windowed --name CH552G-CDC-Controller main.py
```

Build separately on Windows, macOS, and Linux, then test serial permissions and USB access on each target OS.


## Build a standalone executable

See [BUILDING.md](BUILDING.md). Build separately on Windows, macOS, and Linux using the included `build_windows.bat` or `build_macos_linux.sh` script.
