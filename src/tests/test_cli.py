import contextlib
import io
import unittest
from unittest.mock import patch

from jonsbo_d34.cli import main


class CliTests(unittest.TestCase):
    def test_rejects_invalid_intervals_before_accessing_hardware(self):
        for flag in ("--interval", "--cpu-freq-interval"):
            for value in ("0", "-1", "nan", "inf", "bad"):
                with (
                    self.subTest(flag=flag, value=value),
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    with patch("jonsbo_d34.cli.Sensors") as sensors:
                        with self.assertRaises(SystemExit) as result:
                            main([flag, value])
                        self.assertEqual(result.exception.code, 2)
                        sensors.assert_not_called()

    def test_diagnosis_does_not_open_usb(self):
        with (
            patch("jonsbo_d34.cli.Sensors") as sensors,
            patch("jonsbo_d34.cli.open_panel") as device,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            sensors.return_value.sample.return_value = {
                "cpu_temp": 40,
                "gpu_temp": 30,
                "cpu_mhz": 4500,
            }
            main(["--diagnose"])
            device.assert_not_called()
            self.assertIn('"cpu_mhz": 4500', output.getvalue())
