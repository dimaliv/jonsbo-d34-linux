import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.install import install, uninstall, unit_quote


class InstallerTests(unittest.TestCase):
    def test_install_is_repeatable_and_preserves_config(self):
        with tempfile.TemporaryDirectory(prefix="jonsbo test ") as directory:
            root = Path(directory)
            app, config, unit = root / "app", root / "config", root / "service"
            config.write_text("UPDATE_INTERVAL=0.2\nCPU_FREQ_INTERVAL=3\n")
            for _ in range(2):
                install(app, config, unit)
            self.assertEqual(config.read_text(), "UPDATE_INTERVAL=0.2\nCPU_FREQ_INTERVAL=3\n")
            result = subprocess.run(
                [sys.executable, str(app / "panel.py"), "--version"],
                cwd=root,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("0.1.0", result.stdout)
            self.assertNotIn("@APP@", unit.read_text())
            self.assertIn(f"EnvironmentFile={config}\n", unit.read_text())
            with patch("scripts.install.systemctl"):
                uninstall(app, unit)
            self.assertFalse(app.exists())
            self.assertFalse(unit.exists())
            self.assertTrue(config.exists())

    def test_refuses_to_remove_unknown_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                uninstall(root, root / "unit")
            self.assertTrue(root.exists())

    def test_systemd_path_escaping(self):
        self.assertEqual(unit_quote('/tmp/a b%"c'), '"/tmp/a b%%\\"c"')
        with self.assertRaises(ValueError):
            unit_quote("/tmp/bad\npath")
