"""
Auto-connect to multiple Shimmer3 devices (EDA, EMG, IMU)
based on the last 4 chars of their Bluetooth ID (e.g. FBOB, 6D84).

Tested pattern: uses pyshimmer's Bluetooth API, which expects a Serial
port and then calls get_device_name() on the device. 
"""

import sys
from typing import Dict

from serial import Serial
from serial.tools import list_ports

from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType


# === 1. Configure your devices here ==========================================
# Replace 'XXXX' with the last 4 characters of your IMU’s Bluetooth ID.
# Example: Shimmer3-FBOB, Shimmer3-6D84, Shimmer3-ABCD
TARGET_SUFFIXES = {
    "FBOB": "EDA",   # Shimmer EDA unit
    "6D84": "EMG",   # Shimmer EMG unit
    "AF57": "IMU",   # <- TODO: put your IMU’s last 4 digits here
}


# === 2. Discovery / connection helper =======================================

def connect_shimmers(
    target_suffixes: Dict[str, str],
    baudrate: int = DEFAULT_BAUDRATE,
    timeout: float = 1.0,
) -> Dict[str, ShimmerBluetooth]:
    """
    Scan all serial ports, try to initialize a ShimmerBluetooth on each,
    and keep the ones whose device name ends with one of the configured suffixes.

    Returns:
        dict mapping logical role ("EDA", "EMG", "IMU") -> ShimmerBluetooth instance
    """
    devices: Dict[str, ShimmerBluetooth] = {}
    suffixes_upper = {s.upper(): role for s, role in target_suffixes.items()}

    # List all candidate ports (USB, BT COM ports, etc.)
    ports = list_ports.comports()
    print("Found serial ports:")
    for p in ports:
        print(f"  - {p.device}: {p.description}")

    for port in ports:
        dev_path = port.device
        print(f"\nTrying port: {dev_path}")
        ser = None
        shim = None

        try:
            # Open serial port
            ser = Serial(dev_path, baudrate=baudrate, timeout=timeout)

            # Wrap with ShimmerBluetooth and initialize
            shim = ShimmerBluetooth(ser)
            shim.initialize()

            # Ask the Shimmer for its device name
            dev_name = shim.get_device_name()
            print(f"  Device name from Shimmer: {dev_name!r}")

            if not dev_name:
                raise RuntimeError("Empty device name, probably not a Shimmer.")

            suffix = dev_name[-4:].upper()

            if suffix in suffixes_upper:
                role = suffixes_upper[suffix]
                print(f"  Matched as {role} (suffix {suffix})")

                # Store this device and keep connection open
                devices[role] = shim

            else:
                print(f"  Suffix {suffix} not in target list, closing.")
                shim.shutdown()
                ser.close()

        except Exception as e:
            print(f"  Failed to use {dev_path} as Shimmer: {e}")
            # Clean up if partially opened/initialized
            try:
                if shim is not None:
                    shim.shutdown()
            except Exception:
                pass
            try:
                if ser is not None and not ser.closed:
                    ser.close()
            except Exception:
                pass

    return devices


# === 3. Example: connect & (optionally) start streaming ======================

def make_basic_handler(label: str):
    """Example callback that just prints timestamp + a small subset of data."""

    def handler(pkt: DataPacket) -> None:
        # Every packet contains a TIMESTAMP channel. 
        ts = pkt[EChannelType.TIMESTAMP]
        print(f"[{label}] ts={ts} pkt={pkt}")

    return handler


if __name__ == "__main__":
    devices = connect_shimmers(TARGET_SUFFIXES)

    if not devices:
        print("\nNo target Shimmers found. Check that:")
        print(" - Devices are powered on and paired over Bluetooth")
        print(" - Firmware is LogAndStream and compatible with pyshimmer")
        print(" - TARGET_SUFFIXES matches the last 4 chars on the device labels")
        sys.exit(1)

    print("\nConnected devices:")
    for role, shim in devices.items():
        print(f"  {role}: {shim}")

    # OPTIONAL: set up streaming callbacks
    # (Real configs would also call shim.set_sensors(...) etc.)

    for role, shim in devices.items():
        handler = make_basic_handler(role)
        shim.add_stream_callback(handler)

        # NOTE: You will usually want to configure which sensors/channels to stream
        # using pyshimmer’s SetSensorsCommand / SetSamplingRateCommand helpers
        # before calling start_streaming(). 
        try:
            print(f"Starting streaming for {role}")
            shim.start_streaming()
        except Exception as e:
            print(f"Could not start streaming for {role}: {e}")

    print("\nAll configured Shimmers are connected. You can now:")
    print(" - Leave them streaming (see handlers above), or")
    print(" - Add your own logic to log data, send markers, etc.")
