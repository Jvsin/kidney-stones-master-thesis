import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.view_nifti import extract_views, initial_window, resolve_pair  # noqa: E402


class ViewNiftiTests(unittest.TestCase):
    def test_resolves_mask_to_image_pair(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source_image = directory / "patient_image.nii.gz"
            source_mask = directory / "patient_mask.nii.gz"
            source_image.touch()
            source_mask.touch()

            mask = source_mask
            image, resolved_mask = resolve_pair(mask, None)
            self.assertEqual(image, source_image)
            self.assertEqual(resolved_mask, mask)

    def test_extract_views_uses_selected_label_only(self):
        image = np.arange(27).reshape((3, 3, 3))
        mask = np.zeros((3, 3, 3), dtype=np.uint8)
        mask[1, :, :] = 1
        mask[:, 2, :] = 2

        images, masks = extract_views(image, mask, (1, 1, 1), 2)

        self.assertTrue(np.all(masks[0][:, 2]))
        self.assertTrue(np.all(images[2] == image[:, :, 1].T))

    def test_initial_window_handles_constant_image(self):
        self.assertEqual(initial_window(np.ones((2, 2, 2))), (1.5, 1.0))


if __name__ == "__main__":
    unittest.main()
