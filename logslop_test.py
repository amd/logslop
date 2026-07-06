# Copyright (C) 2025 Advanced Micro Devices, Inc.
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
"""Unit tests for standalone logslop."""

import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("standalone_logslop", Path(__file__).parent / "logslop.py")
_standalone = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_standalone)
tokenize = _standalone.tokenize
jaccard = _standalone.jaccard
process = _standalone.process


class TestTokenize(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(tokenize("foo 123 bar", True), tokenize("foo 456 bar", True))
        self.assertNotEqual(tokenize("foo 123 bar", True), tokenize("foo 123 bar", False))

    def test_no_normalize(self):
        self.assertEqual(tokenize("foo 123 bar", False), ["foo", "123", "bar"])

    def test_hex_normalization(self):
        """Hex sequences (0x...) collapse to single placeholder like digit sequences."""
        t1 = tokenize("amd_diag_apply_pgprot: 0x413d12000", True)
        t2 = tokenize("amd_diag_apply_pgprot: 0x413d22000", True)
        self.assertEqual(t1, t2, "hex addresses should normalize to same tokens")

    def test_hex_and_digits_same_structure(self):
        """Different hex values produce identical token sequences."""
        self.assertEqual(
            tokenize("pre_set_pgprot: phy_base -- 0x413d12000 and phy_type -- 0x4", True),
            tokenize("pre_set_pgprot: phy_base -- 0x413d22000 and phy_type -- 0x5", True),
        )


class TestJaccard(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(jaccard(["a", "b"], ["a", "b"]), 1.0)

    def test_partial(self):
        self.assertEqual(jaccard(["a", "b"], ["a", "c"]), 1 / 3)

    def test_empty(self):
        self.assertEqual(jaccard([], []), 1.0)


class TestProcess(unittest.TestCase):
    def test_dedupes_similar(self):
        lines = ["foo 123 bar", "foo 456 bar", "foo 789 bar", "baz qux", "foo 999 bar"]
        self.assertEqual(list(process(lines)), ["foo 123 bar", "  ...2...3", "baz qux", "  ...5...5"])

    def test_no_normalize_keeps_all(self):
        lines = ["line 1", "line 2", "line 3"]
        self.assertEqual(list(process(lines, normalize_digits=False)), lines)

    def test_threshold_stricter(self):
        lines = ["foo bar baz", "foo bar qux", "foo bar"]
        self.assertEqual(list(process(lines, threshold=0.9)), lines)
        self.assertEqual(list(process(lines, threshold=0.5)), ["foo bar baz", "  ...2...3"])

    def test_max_clusters(self):
        lines = [f"unique_{i}" for i in range(5)]
        self.assertEqual(len(list(process(lines, max_clusters=2, normalize_digits=False))), 5)
        self.assertEqual(list(process([f"x {i}" for i in range(5)], max_clusters=2)), ["x 0", "  ...2...5"])

    def test_hex_lines_deduped(self):
        """Lines differing only in hex addresses are deduped."""
        lines = [
            "amd_diag_apply_pgprot: 0x413d12000",
            "amd_diag_apply_pgprot: 0x413d22000",
            "amd_diag_apply_pgprot: 0x413d72000",
        ]
        self.assertEqual(list(process(lines)), ["amd_diag_apply_pgprot: 0x413d12000", "  ...2...3"])


if __name__ == "__main__":
    unittest.main()
