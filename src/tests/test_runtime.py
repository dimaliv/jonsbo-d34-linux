import tempfile
import unittest
from unittest.mock import call, patch

from jonsbo_d34.cli import main


class RuntimeTests(unittest.TestCase):
    def test_write_failure_closes_device_then_reconnects(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", {"XDG_RUNTIME_DIR": directory}),
            patch("jonsbo_d34.cli.Sensors") as sensors,
            patch("jonsbo_d34.cli.open_panel", side_effect=[41, 42]) as opened,
            patch("jonsbo_d34.cli.os.write", side_effect=[OSError("disconnected"), 65]),
            patch("jonsbo_d34.cli.os.close") as closed,
            patch("jonsbo_d34.cli.signal.signal"),
            patch("jonsbo_d34.cli.threading.Event") as event,
        ):
            sensors.return_value.sample.return_value = {
                "cpu_temp": 40,
                "gpu_temp": 30,
                "cpu_mhz": 4500,
            }
            event.return_value.is_set.side_effect = [False, False, True]
            main([])
            self.assertEqual(opened.call_count, 2)
            self.assertEqual(sensors.call_count, 2)
            self.assertEqual(closed.call_args_list, [call(41), call(42)])
            self.assertEqual(event.return_value.wait.call_args_list, [call(3), call(0.2)])

    def test_stop_signal_interrupts_wait(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", {"XDG_RUNTIME_DIR": directory}),
            patch("jonsbo_d34.cli.Sensors") as sensors,
            patch("jonsbo_d34.cli.open_panel", return_value=41),
            patch("jonsbo_d34.cli.os.write", return_value=65),
            patch("jonsbo_d34.cli.os.close") as closed,
            patch("jonsbo_d34.cli.signal.signal") as signals,
            patch("jonsbo_d34.cli.threading.Event") as event,
        ):
            sensors.return_value.sample.return_value = {
                "cpu_temp": 40,
                "gpu_temp": 30,
                "cpu_mhz": 4500,
            }
            event.return_value.is_set.side_effect = [False, True]
            event.return_value.wait.side_effect = lambda _: signals.call_args.args[1](15, None)
            main(["--interval", "100"])
            event.return_value.set.assert_called_once()
            closed.assert_called_once_with(41)
