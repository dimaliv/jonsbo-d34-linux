import unittest
from datetime import datetime
from unittest.mock import patch

from jonsbo_d34.protocol import packet
from jonsbo_d34.sensors import Sensors


class ProtocolTests(unittest.TestCase):
    def test_cpu_frequency_reused_between_measurements(self):
        # Exercise sampling cadence without requiring real CPU/GPU hardware.
        sensors = Sensors.__new__(Sensors)
        sensors.cpu_freq_interval = 1.0
        sensors.cached_cpu_mhz = None
        sensors.next_cpu_freq_read = 0.0
        with (
            patch(
                "jonsbo_d34.sensors.time.monotonic", side_effect=[10, 10.2, 10.4, 10.6, 10.8, 11]
            ),
            patch(
                "jonsbo_d34.sensors.read",
                side_effect=["cpu MHz : 4000\ncpu MHz : 5000", "cpu MHz : 3000\ncpu MHz : 4000"],
            ) as reader,
        ):
            readings = [sensors.cpu_frequency() for _ in range(6)]
        self.assertEqual(readings, [4500] * 5 + [3500])
        self.assertEqual(reader.call_count, 2)

    def test_known_values_and_sunday(self):
        frame = packet(
            dict(cpu_temp=48.25, gpu_temp=32.5, cpu_mhz=5234, gpu_mhz=2401, gpu_power=321.75),
            datetime(2026, 9, 6, 23, 59, 58),
        )
        self.assertEqual(len(frame), 65)
        self.assertEqual(frame[:4], bytes([0, 0, 1, 2]))
        v = frame[4:37]
        self.assertEqual(v[:3], bytes([48, 25, 0]))
        self.assertEqual(v[6:8], bytes([52, 34]))
        self.assertEqual(v[10:13], bytes([32, 50, 0]))
        self.assertEqual(v[14:18], bytes([21, 75, 24, 1]))
        self.assertEqual(v[32], 3)
        self.assertEqual(v[22:30], bytes([20, 26, 9, 6, 23, 59, 58, 0]))
        self.assertEqual(frame[37:], bytes(28))

    def test_out_of_range_values(self):
        frame = packet(
            dict(cpu_temp=-10, gpu_temp=999, cpu_mhz=99999, cpu_usage=200, gpu_usage=-1),
            datetime(2026, 9, 5),
        )
        v = frame[4:37]
        self.assertEqual(v[:2], bytes([0, 0]))
        self.assertEqual(v[10:12], bytes([255, 99]))
        self.assertEqual(v[6:8], bytes([255, 99]))
        self.assertEqual(v[3], 100)
        self.assertEqual(v[13], 0)


if __name__ == "__main__":
    unittest.main()
