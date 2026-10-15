import json
from pathlib import Path
import tempfile
import unittest
from audit_local import inventory, audit_client, main, write_report

class AuditTests(unittest.TestCase):
    def test_synthetic_xdb_inventory_and_no_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "invented.xdb").write_text(
                '<QuestResource><objective type="demo.QuestCountSpecial"/></QuestResource>',
                encoding="utf-8")
            (root / "broken.xdb").write_text("<broken", encoding="utf-8")
            result = inventory(root, True)
            self.assertEqual(result["extensions"][".xdb"], 2)
            self.assertEqual(result["xml_checked"], 1)
            self.assertEqual(result["read_or_parse_errors"], 1)
            self.assertEqual(result["objective_occurrences"]["QuestCountSpecial"], 1)
            self.assertNotIn("invented.xdb", json.dumps(result))
            self.assertFalse(result["compatibility_verified"])

    def test_dtd_is_not_expanded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dtd.xdb").write_text(
                '<!DOCTYPE a [<!ENTITY b "invented">]><a>&b;</a>', encoding="utf-8")
            result = inventory(root, True)
            self.assertEqual(result["xml_skipped"], 1)
            self.assertEqual(result["xml_checked"], 0)

    def test_report_cannot_write_into_inputs_or_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "input"
            repo = root / "repo"
            inputs.mkdir()
            repo.mkdir()
            for destination in (inputs / "report.json", repo / "report.json"):
                with self.assertRaises(ValueError):
                    write_report(destination, {}, [inputs], repo)
            outside = root / "report.json"
            write_report(outside, {"ok": True}, [inputs], repo)
            with self.assertRaises(FileExistsError):
                write_report(outside, {}, [inputs], repo)

    def test_client_static_flags_do_not_claim_android_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "project.godot").write_text('config/features=PackedStringArray("Forward Plus")')
            (root / "network.cs").write_text("using System.Net.Quic;")
            (root / "export_presets.cfg").write_text('platform="Android"')
            result = audit_client(root)
            self.assertTrue(result["system_net_quic_reference"])
            self.assertTrue(result["android_preset_found"])
            self.assertFalse(result["android_ready"])

    def test_local_cli_writes_counts_without_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "example.bin").write_bytes(b"synthetic")
            output = root / "report.json"
            self.assertEqual(main(["--source", str(source), "--out", str(output)]), 0)
            report = output.read_text()
            self.assertNotIn(str(source), report)
            self.assertNotIn("synthetic", report)
            self.assertFalse(json.loads(report)["installed_version_verified"])

if __name__ == "__main__":
    unittest.main()
