# Building a standalone executable

PyInstaller bundles Python and the project's Python dependencies. Build on each target operating system; do not expect a Windows build to produce a macOS app or vice versa.

## Windows

1. Install a supported Python 3 version from python.org.
2. Extract this project folder.
3. Double-click `build_windows.bat`.
4. When complete, distribute the entire folder:
   `dist/CH552G-CDC-Controller/`

The executable is:
`dist/CH552G-CDC-Controller/CH552G-CDC-Controller.exe`

## macOS

1. Install Python 3.
2. Open Terminal in this project folder.
3. Run:

```bash
chmod +x build_macos_linux.sh
./build_macos_linux.sh
```

The app is created at:
`dist/CH552G-CDC-Controller.app`

For distribution to other Macs, test on a clean Mac. Depending on distribution method and macOS security settings, code signing and notarization may be required. Build separately for Apple Silicon and Intel if both architectures must be supported, or use a suitable universal build workflow.

## Linux

Run the same script. It creates:
`dist/CH552G-CDC-Controller/`

Distribute the entire directory. The target Linux system may need compatible system libraries and appropriate permissions to access `/dev/ttyACM*` or `/dev/ttyUSB*`.

## Important

- USB VID/PID defaults are `0x16C0` and `0x27DD`; adjust in `main.py` if the firmware uses different values.
- The GUI's example LED command protocol must be implemented by the firmware before LED buttons will work.
- Validate USB enumeration and serial communication on each target OS after packaging.
