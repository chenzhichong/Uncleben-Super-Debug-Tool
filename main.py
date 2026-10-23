#!/usr/bin/env python3
"""Cross-platform CH552G CDC GUI prototype using PySide6 + pyserial."""
import sys, time
from dataclasses import dataclass
from typing import Optional
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QPlainTextEdit,
    QVBoxLayout, QWidget, QCheckBox)
from serial import Serial, SerialException
from serial.tools import list_ports

# From the cdc_echo config.h shown by the user. Change if the firmware differs.
USB_VID, USB_PID = 0x16C0, 0x27DD
BAUDRATE = 115200
RESPONSE_TIMEOUT = 0.6
CMD_LED, CMD_GET_STATUS = 0x01, 0x02
RSP_LED, RSP_STATUS = 0x81, 0x82

@dataclass
class Device:
    port: str
    description: str
    serial_number: Optional[str]

def discover_devices():
    found = [Device(p.device, p.description or "CDC serial device", p.serial_number)
             for p in list_ports.comports() if p.vid == USB_VID and p.pid == USB_PID]
    return sorted(found, key=lambda d: d.port.casefold())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CH552G CDC Controller")
        self.resize(780, 580)
        self.ser = None
        self.active_port = None
        self.busy = False
        self._build_ui()
        self.timer = QTimer(self)
        self.timer.setInterval(3000)
        self.timer.timeout.connect(self.refresh_devices)
        self.timer.start()
        self.refresh_devices()
        self.set_connected(False)

    def _build_ui(self):
        root_widget = QWidget()
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)
        title = QLabel("CH552G CDC Controller")
        title.setFont(QFont("", 18, QFont.Weight.DemiBold))
        subtitle = QLabel("Cross-platform USB CDC control and diagnostics")
        root.addWidget(title)
        root.addWidget(subtitle)

        group = QGroupBox("USB device")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("Detected device:"), 0, 0)
        self.devices = QComboBox()
        self.devices.setMinimumWidth(380)
        grid.addWidget(self.devices, 0, 1)
        self.scan_button = QPushButton("Rescan")
        self.scan_button.clicked.connect(self.refresh_devices)
        grid.addWidget(self.scan_button, 0, 2)
        self.status = QLabel("Not connected")
        grid.addWidget(self.status, 1, 0, 1, 2)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        grid.addWidget(self.connect_button, 1, 2)
        self.auto_scan = QCheckBox("Automatically scan every 3 seconds")
        self.auto_scan.setChecked(True)
        self.auto_scan.toggled.connect(lambda on: self.timer.start() if on else self.timer.stop())
        grid.addWidget(self.auto_scan, 2, 0, 1, 3)
        root.addWidget(group)

        led_group = QGroupBox("P32 LED")
        led_row = QHBoxLayout(led_group)
        self.led_icon = QLabel("●")
        self.led_icon.setStyleSheet("color: #888888;")
        self.led_icon.setFont(QFont("", 26))
        self.led_state = QLabel("Unknown")
        self.led_state.setMinimumWidth(90)
        self.on_button = QPushButton("LED ON")
        self.off_button = QPushButton("LED OFF")
        self.query_button = QPushButton("Query status")
        self.on_button.clicked.connect(lambda: self.send(bytes([CMD_LED, 1]), "LED ON"))
        self.off_button.clicked.connect(lambda: self.send(bytes([CMD_LED, 0]), "LED OFF"))
        self.query_button.clicked.connect(lambda: self.send(bytes([CMD_GET_STATUS, 0]), "Query status"))
        led_row.addWidget(self.led_icon)
        led_row.addWidget(self.led_state)
        led_row.addStretch(1)
        led_row.addWidget(self.on_button)
        led_row.addWidget(self.off_button)
        led_row.addWidget(self.query_button)
        root.addWidget(led_group)

        raw_group = QGroupBox("Raw HEX command")
        raw_row = QHBoxLayout(raw_group)
        self.raw_input = QComboBox()
        self.raw_input.setEditable(True)
        self.raw_input.addItems(["01 01", "01 00", "02 00"])
        self.send_raw_button = QPushButton("Send")
        self.send_raw_button.clicked.connect(self.send_raw)
        raw_row.addWidget(QLabel("Bytes:"))
        raw_row.addWidget(self.raw_input, 1)
        raw_row.addWidget(self.send_raw_button)
        root.addWidget(raw_group)

        log_group = QGroupBox("Communication log")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        log_layout.addWidget(self.log_view)
        log_buttons = QHBoxLayout()
        log_buttons.addStretch(1)
        clear_button = QPushButton("Clear log")
        clear_button.clicked.connect(self.log_view.clear)
        log_buttons.addWidget(clear_button)
        log_layout.addLayout(log_buttons)
        root.addWidget(log_group, 1)
        self.setCentralWidget(root_widget)
        self.setStyleSheet("QGroupBox { font-weight: 600; border: 1px solid palette(mid); border-radius: 8px; margin-top: 8px; padding-top: 8px; } QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; } QPushButton { padding: 7px 12px; }")

    def log(self, message):
        self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {message}")

    def refresh_devices(self):
        devices = discover_devices()
        previous = self.devices.currentData()
        self.devices.blockSignals(True)
        self.devices.clear()
        if not devices:
            self.devices.addItem(f"No matching device (VID 0x{USB_VID:04X}, PID 0x{USB_PID:04X})", None)
        for d in devices:
            serial = d.serial_number or "serial unavailable/shared"
            self.devices.addItem(f"{d.port} — {d.description} [{serial}]", d.port)
        if previous:
            index = self.devices.findData(previous)
            if index >= 0:
                self.devices.setCurrentIndex(index)
        self.devices.blockSignals(False)
        if self.ser and self.active_port not in {d.port for d in devices}:
            self.log(f"Device {self.active_port} disappeared")
            self.disconnect_device()

    def toggle_connection(self):
        if self.ser:
            self.disconnect_device()
            return
        port = self.devices.currentData()
        if not port:
            QMessageBox.information(self, "No device", "No matching CDC device found. Check the USB connection and VID/PID.")
            return
        try:
            self.ser = Serial(port, BAUDRATE, timeout=0.05, write_timeout=1.0)
            self.active_port = port
            time.sleep(0.12)
            self.ser.reset_input_buffer()
            self.set_connected(True)
            self.log(f"Connected to {port} at {BAUDRATE} baud")
        except SerialException as exc:
            self.ser = None
            self.active_port = None
            self.set_connected(False)
            QMessageBox.critical(self, "Connection failed", f"Could not open {port}. It may be in use.\n\n{exc}")
            self.log(f"ERROR opening {port}: {exc}")

    def disconnect_device(self):
        old = self.active_port
        if self.ser:
            try: self.ser.close()
            except SerialException: pass
        self.ser = None
        self.active_port = None
        self.set_connected(False)
        if old: self.log(f"Disconnected from {old}")

    def set_connected(self, yes):
        self.connect_button.setText("Disconnect" if yes else "Connect")
        self.status.setText(f"Connected: {self.active_port}" if yes else "Not connected")
        for w in (self.on_button, self.off_button, self.query_button, self.send_raw_button):
            w.setEnabled(yes)

    def send(self, payload, label):
        if not self.ser or not self.ser.is_open or self.busy: return
        self.busy = True
        try:
            self.ser.reset_input_buffer()
            self.ser.write(payload)
            self.ser.flush()
            self.log(f"TX {payload.hex(' ').upper()} — {label}")
            deadline = time.monotonic() + RESPONSE_TIMEOUT
            response = bytearray()
            last_byte = None
            while time.monotonic() < deadline:
                count = self.ser.in_waiting
                if count:
                    chunk = self.ser.read(count)
                    response.extend(chunk)
                    last_byte = time.monotonic()
                elif response and last_byte and time.monotonic() - last_byte > 0.08:
                    break
                else:
                    time.sleep(0.01)
            if response:
                data = bytes(response)
                self.log(f"RX {data.hex(' ').upper()}")
                self.parse_response(data)
            else:
                self.log("RX timeout — no response received")
        except SerialException as exc:
            self.log(f"Serial error: {exc}")
            QMessageBox.warning(self, "Communication error", str(exc))
            self.disconnect_device()
        finally:
            self.busy = False

    def parse_response(self, data):
        # Example response protocol; update to match the firmware implementation.
        if len(data) >= 2 and data[0] in (RSP_LED, RSP_STATUS):
            on = bool(data[1] & 1)
            self.led_icon.setStyleSheet("color: #16a34a;" if on else "color: #888888;")
            self.led_state.setText("ON" if on else "OFF")
            self.log(f"LED state parsed as {'ON' if on else 'OFF'}")
        else:
            self.log("Unrecognized response; raw bytes are shown above")

    def send_raw(self):
        try:
            parts = self.raw_input.currentText().replace(",", " ").split()
            payload = bytes(int(part, 16) for part in parts)
            if not payload: raise ValueError("empty input")
        except ValueError:
            QMessageBox.warning(self, "Invalid HEX", "Enter hex bytes separated by spaces, e.g. 01 01")
            return
        self.send(payload, "Raw HEX command")

    def closeEvent(self, event):
        self.disconnect_device()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CH552G CDC Controller")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
