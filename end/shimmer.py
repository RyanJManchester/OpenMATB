import os
import csv
import time
import threading
from typing import Dict, Any

from serial import Serial
from serial.tools import list_ports

from pyshimmer import (
    ShimmerBluetooth,
    DEFAULT_BAUDRATE,
    DataPacket,
    EChannelType,
)

# --------------------------------------------------------------------
# 1) Configure your devices and log file paths here
# --------------------------------------------------------------------

TARGET_DEVICES = {
    # last 4 chars of the Bluetooth name / label on the device
    "FBOB": {  # EDA Shimmer
        "role": "EDA",
        "outfile": r"C:\Users\rm534\Documents\ShimmerLogs\eda_FBOB.csv",
    },
    "6D84": {  # EMG Shimmer
        "role": "EMG",
        "outfile": r"C:\Users\rm534\Documents\ShimmerLogs\emg_6D84.csv",
    },
    "XXXX": {  # IMU Shimmer – replace XXXX with the last 4 chars
        "role": "IMU",
        "outfile": r"C:\Users\rm534\Documents\ShimmerLogs\imu_XXXX.csv",
    },
}

ROLE_CHANNELS = {
    "EDA": [
        EChannelType.TIMESTAMP,
        EChannelType.GSR_RAW,      # or GSR_CONDUCTANCE etc, depending on your config
    ],
    "EMG": [
        EChannelType.TIMESTAMP,
        # Pick your EMG channels once you know them, e.g.:
        # EChannelType.EXG1_CH1, EChannelType.EXG1_CH2,
    ],
    "IMU": [
        EChannelType.TIMESTAMP,
        EChannelType.ACCEL_LN_X,
        EChannelType.ACCEL_LN_Y,
        EChannelType.ACCEL_LN_Z,
        # Add gyro / mag if enabled:
        # EChannelType.GYRO_MPU9150_X, ...
    ],
}


# --------------------------------------------------------------------
# CSV logger
# --------------------------------------------------------------------

class CSVLogger:
    def __init__(self, path: str, channels: list[EChannelType]):
        self.path = path
        self.channels = channels
        self._fh = None
        self._writer = None
        self._lock = threading.Lock()

        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)

        self._open()

    def _open(self):
        self._fh = open(self.path, "w", newline="")
        self._writer = csv.writer(self._fh)
        header = [ch.name for ch in self.channels]
        self._writer.writerow(header)
        self._fh.flush()

    def log_packet(self, pkt: DataPacket):
        row: list[Any] = []
        for ch in self.channels:
            try:
                row.append(pkt[ch])
            except KeyError:
                row.append("")
        with self._lock:
            self._writer.writerow(row)
            self._fh.flush()

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None
            self._writer = None


# --------------------------------------------------------------------
# Discover Shimmers – WINDOWS VERSION
# Only try "Standard Serial over Bluetooth link" ports
# --------------------------------------------------------------------

def discover_shimmers() -> Dict[str, ShimmerBluetooth]:
    suffix_to_cfg = {k.upper(): v for k, v in TARGET_DEVICES.items()}
    role_to_device: Dict[str, ShimmerBluetooth] = {}

    all_ports = list_ports.comports()
    print("All serial ports found:")
    for p in all_ports:
        print(f"  - {p.device}: {p.description}")

    bt_ports = [
        p for p in all_ports
        if p.description and "Standard Serial over Bluetooth link" in p.description
    ]

    print("\nFiltered Bluetooth SPP ports:")
    if not bt_ports:
        print("  (none) – check that devices are paired in Windows Bluetooth settings.")
        return role_to_device

    for p in bt_ports:
        print(f"  - {p.device}: {p.description}")

    for port in bt_ports:
        dev_path = port.device
        print(f"\nTrying Bluetooth port: {dev_path}")
        ser = None
        shim = None

        try:
            # IMPORTANT: timeout=None (blocking) – pyshimmer expects this
            ser = Serial(dev_path, baudrate=DEFAULT_BAUDRATE, timeout=None)
            shim = ShimmerBluetooth(ser)
            shim.initialize()

            dev_name = shim.get_device_name()
            print(f"  Detected Shimmer name: {dev_name!r}")

            if not dev_name:
                raise RuntimeError("No device name returned")

            suffix = dev_name[-4:].upper()
            if suffix not in suffix_to_cfg:
                print(f"  Suffix {suffix} not in TARGET_DEVICES, closing this port.")
                shim.shutdown()
                ser.close()
                continue

            cfg = suffix_to_cfg[suffix]
            role = cfg["role"]
            print(f"  Matched as role: {role}")
            role_to_device[role] = shim

        except Exception as e:
            print(f"  Failed to use {dev_path} as Shimmer: {e}")
            if shim is not None:
                try:
                    shim.shutdown()
                except Exception:
                    pass
            if ser is not None and not ser.closed:
                try:
                    ser.close()
                except Exception:
                    pass

    return role_to_device


# --------------------------------------------------------------------
# Wiring devices to loggers & starting streaming
# --------------------------------------------------------------------

def make_handler(role: str, logger: CSVLogger):
    def handler(pkt: DataPacket) -> None:
        logger.log_packet(pkt)
    return handler


def main():
    print("Discovering Shimmer devices over Bluetooth...")
    devices = discover_shimmers()

    if not devices:
        print("\n❌ No Shimmer devices matched TARGET_DEVICES.")
        return

    print("\n✅ Connected devices:")
    for role, dev in devices.items():
        print(f"  - {role}: {dev}")

    loggers: Dict[str, CSVLogger] = {}
    try:
        for suffix, cfg in TARGET_DEVICES.items():
            role = cfg["role"]
            outfile = cfg["outfile"]
            if role not in devices:
                print(f"⚠️ Role {role} (suffix {suffix}) not connected, skipping...")
                continue

            channels = ROLE_CHANNELS.get(role)
            if not channels:
                print(f"⚠️ No channels configured for role {role}, skipping logger.")
                continue

            logger = CSVLogger(outfile, channels)
            loggers[role] = logger

            shim = devices[role]
            handler = make_handler(role, logger)
            shim.add_stream_callback(handler)

            print(f"Starting streaming for {role}")
            shim.start_streaming()

        if not loggers:
            print("❌ No loggers started; check ROLE_CHANNELS.")
            return

        print("\n📡 Streaming... press Ctrl+C to stop.")
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n🛑 Stopping streaming and closing log files...")
    finally:
        for role, dev in devices.items():
            try:
                dev.stop_streaming()
            except Exception:
                pass
            try:
                dev.shutdown()
            except Exception:
                pass

        for logger in loggers.values():
            logger.close()

        print("Cleanup complete.")


if __name__ == "__main__":
    main()
