import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jonsbo_d34.device import DESCRIPTOR, open_panel


class DeviceTests(unittest.TestCase):
    def test_only_matching_descriptor_can_be_opened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "hidraw7/device"
            device.mkdir(parents=True)
            (device / "uevent").write_text("HID_ID=0003:00005131:00002007\n")
            (device / "report_descriptor").write_bytes(b"unsupported")
            with patch("jonsbo_d34.device.os.open") as opened:
                with self.assertRaisesRegex(RuntimeError, "Unexpected HID descriptor"):
                    open_panel(root)
                opened.assert_not_called()
                (device / "report_descriptor").write_bytes(DESCRIPTOR)
                opened.return_value = 42
                self.assertEqual(open_panel(root), 42)
                self.assertEqual(opened.call_args.args[0], Path("/dev/hidraw7"))

    def test_unrelated_devices_are_not_opened(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            device = root / "hidraw0/device"
            device.mkdir(parents=True)
            (device / "uevent").write_text("HID_ID=0003:0000046D:00000C084\n")
            with patch("jonsbo_d34.device.os.open") as opened:
                with self.assertRaises(FileNotFoundError):
                    open_panel(root)
                opened.assert_not_called()
