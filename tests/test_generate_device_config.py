from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_device_config.py"
sys.path.insert(0, str(ROOT / "scripts"))

from generate_device_config import validate_config  # noqa: E402

TEST_KEY = "sphr_" + "x" * 24


class GenerateDeviceConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))
        self.config = {
            "config_version": 2,
            "server_url": "https://sphere.example.invalid",
            "ws_path": "/ws/android",
            "enrollment_api_key": TEST_KEY,
            "device_id": None,
            "workstation_id": "lab-01",
            "instance_index": 0,
            "location": "lab",
            "environment": "production",
            "config_poll_interval_seconds": 86400,
            "features": {
                "telemetry_enabled": True,
                "streaming_enabled": True,
                "ota_enabled": False,
                "auto_register": True,
            },
            "meta": {},
        }

    def run_cli(
        self,
        args: list[str],
        *,
        server_url: str = "https://sphere.example.invalid",
        key: str = TEST_KEY,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["SPHERE_SERVER_URL"] = server_url
        env["SPHERE_ENROLLMENT_API_KEY"] = key
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_environment_defaults_do_not_contain_credentials_or_unverified_hosts(self) -> None:
        for path in (ROOT / "environments").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("enrollment_api_key", data, path.name)
            self.assertEqual("", data["server_url"], path.name)

    def test_valid_legacy_config_passes_validation(self) -> None:
        self.assertEqual([], validate_config(self.config, self.schema))

    def test_invalid_key_is_never_echoed_in_validation_error(self) -> None:
        sentinel = "private-sentinel-do-not-log"
        invalid = {**self.config, "enrollment_api_key": sentinel}
        errors = validate_config(invalid, self.schema)
        self.assertTrue(errors)
        self.assertNotIn(sentinel, " ".join(errors))

    def test_production_rejects_http(self) -> None:
        invalid = {**self.config, "server_url": "http://sphere.example.invalid"}
        self.assertIn("Для production и staging требуется HTTPS", validate_config(invalid, self.schema))

    def test_malformed_server_url_returns_validation_error(self) -> None:
        invalid = {**self.config, "server_url": "https://[broken"}
        errors = validate_config(invalid, self.schema)
        self.assertIn("server_url должен быть абсолютным HTTP(S) URL", errors)

    def test_batch_generates_distinct_indices_and_keeps_secret_out_of_console(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            result = self.run_cli([
                "--env", "development", "--workstation-id", "lab-01", "--count", "3",
                "--start-index", "5", "--output-dir", output_dir,
            ])
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn(TEST_KEY, result.stdout + result.stderr)
            generated = sorted(Path(output_dir).glob("sphere-agent-config-*.json"))
            self.assertEqual(3, len(generated))
            configs = [json.loads(path.read_text(encoding="utf-8")) for path in generated]
            self.assertEqual([5, 6, 7], [config["instance_index"] for config in configs])
            self.assertEqual({"lab-01"}, {config["workstation_id"] for config in configs})

    def test_batch_requires_workstation_to_prevent_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            result = self.run_cli([
                "--env", "development", "--count", "2", "--output-dir", output_dir,
            ])
            self.assertNotEqual(0, result.returncode)
            self.assertIn("--workstation-id", result.stderr)
            self.assertEqual([], list(Path(output_dir).iterdir()))

    def test_output_file_rejects_path_components(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            result = self.run_cli([
                "--env", "development", "--output-dir", output_dir,
                "--output-file", "../outside.json",
            ])
            self.assertNotEqual(0, result.returncode)
            self.assertIn("--output-file", result.stderr)
            self.assertEqual([], list(Path(output_dir).iterdir()))

    def test_missing_key_fails_without_echoing_environment_value(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            result = self.run_cli([
                "--env", "development", "--output-dir", output_dir,
            ], key="private-sentinel-do-not-log")
            self.assertNotEqual(0, result.returncode)
            self.assertNotIn("private-sentinel-do-not-log", result.stdout + result.stderr)
            self.assertEqual([], list(Path(output_dir).iterdir()))


if __name__ == "__main__":
    unittest.main()
