import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

from tools.verify_chinese import verify


class VerifyChineseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dataset = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def save(self, kind, values, affine=None):
        image = nib.Nifti1Image(np.asarray(values, dtype=np.uint8), np.eye(4) if affine is None else affine)
        image.header.set_xyzt_units("mm")
        nib.save(image, self.dataset / f"patient_ps_{kind}.nii.gz")

    def run_verification(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = verify(self.dataset, 1)
        return status, output.getvalue()

    def test_nonempty_mask_without_stone_is_reported_not_assumed_invalid(self):
        self.save("image", [[[0, 0]]])
        self.save("mask", [[[0, 1]]])
        status, output = self.run_verification()
        self.assertEqual(status, 0)
        self.assertIn("Without label 2 (1): patient_ps", output)
        self.assertIn("Stone label not specified", output)

    def test_empty_mask_and_geometry_mismatch_are_reported(self):
        self.save("image", [[[0, 0]]])
        affine = np.eye(4)
        affine[0, 3] = 2
        self.save("mask", [[[0, 0]]], affine)
        status, output = self.run_verification()
        self.assertEqual(status, 1)
        self.assertIn("empty mask", output)
        self.assertIn("geometry=MISMATCH", output)

    def test_missing_mask_is_reported(self):
        self.save("image", [[[0]]])
        status, output = self.run_verification()
        self.assertEqual(status, 1)
        self.assertIn("missing mask", output)
        self.assertIn("pairs checked: 0", output)

    def test_unexpected_label_is_reported(self):
        self.save("image", [[[0, 0]]])
        self.save("mask", [[[0, 3]]])
        status, output = self.run_verification()
        self.assertEqual(status, 1)
        self.assertIn("unexpected labels", output)

    def test_spacing_comparison_uses_stated_precision(self):
        affine = np.diag([0.371094, 0.371094, 0.415725, 1])
        self.save("image", [[[0, 0]]], affine)
        self.save("mask", [[[0, 1]]], affine)
        status, output = self.run_verification()
        self.assertEqual(status, 0)
        self.assertIn("Outside expected Z range [0.42, 2.5] mm after rounding to 2 decimals: 0", output)


if __name__ == "__main__":
    unittest.main()
