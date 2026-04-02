from __future__ import annotations

import tempfile
import unittest

from memory_eval.adapters import BaseMemoryAdapter, create_adapter_by_system, export_adapter_runtime_manifest


class AdapterRegistryTests(unittest.TestCase):
    def test_base_memory_adapter_normalizes_turns(self):
        adapter = BaseMemoryAdapter()
        turns = adapter.normalize_turns(
            [
                {"speaker": "Alice", "text": "hello"},
                {"role": "Bob", "content": "hi", "time": "2024-01-01"},
            ]
        )
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[0]["speaker"], "Alice")
        self.assertEqual(turns[1]["speaker"], "Bob")

    def test_registry_supports_flavor_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = create_adapter_by_system(
                "membox:stable_eval",
                {
                    "api_key": "k",
                    "base_url": "https://example.com",
                    "memory_dir": tmpdir,
                },
            )
            manifest = export_adapter_runtime_manifest(adapter)
            self.assertEqual(manifest["capabilities"]["family"], "membox")
            self.assertIn("stable", manifest["capabilities"]["flavor"])

    def test_omem_manifest_exports_capabilities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = create_adapter_by_system(
                "o_mem",
                {
                    "memory_dir": tmpdir,
                    "allow_fallback_lightweight": True,
                },
            )
            manifest = export_adapter_runtime_manifest(adapter)
            self.assertEqual(manifest["capabilities"]["family"], "o_mem")
            self.assertTrue(manifest["capabilities"]["supports_full_memory_export"])


if __name__ == "__main__":
    unittest.main()
