import sys
import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.split_chinese import MEDIUM_MAX_MM3, SMALL_MAX_MM3, classify_patients, stratify_patients  # noqa: E402


class SplitChineseTests(unittest.TestCase):
    @staticmethod
    def patients(with_stones=209, without_stones=51):
        positive = [
            {
                "patient_id": f"positive_{index:03d}",
                "image": f"positive_{index:03d}_image.nii.gz",
                "mask": f"positive_{index:03d}_mask.nii.gz",
                "has_stones": True,
                "stone_size_class": "small",
            }
            for index in range(with_stones)
        ]
        negative = [
            {
                "patient_id": f"negative_{index:03d}",
                "image": f"negative_{index:03d}_image.nii.gz",
                "mask": f"negative_{index:03d}_mask.nii.gz",
                "has_stones": False,
                "stone_size_class": "none",
            }
            for index in range(without_stones)
        ]
        return positive + negative

    def test_split_is_stratified_at_patient_level(self):
        patients = self.patients()
        splits = stratify_patients(patients)

        self.assertEqual([len(splits[name]) for name in ("train", "val", "test")], [182, 39, 39])
        self.assertEqual(
            [sum(patient["has_stones"] for patient in splits[name]) for name in ("train", "val", "test")],
            [146, 31, 32],
        )
        self.assertEqual(
            sum(
                sum(not patient["has_stones"] for patient in splits[name])
                for name in ("train", "val", "test")
            ),
            51,
        )

        assigned = [
            patient["patient_id"] for name in ("train", "val", "test") for patient in splits[name]
        ]
        self.assertCountEqual(assigned, [patient["patient_id"] for patient in patients])
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_split_is_deterministic_for_same_seed(self):
        patients = self.patients()
        self.assertEqual(stratify_patients(patients, seed=7), stratify_patients(patients, seed=7))

    def test_duplicate_patient_identifier_is_rejected(self):
        patients = self.patients(5, 5)
        patients.append(dict(patients[0]))
        with self.assertRaisesRegex(ValueError, "Patient identifiers must be unique"):
            stratify_patients(patients)

    def test_split_preserves_all_stone_size_classes(self):
        patients = self.patients(80, 20)
        for index, patient in enumerate(patients[:80]):
            patient["stone_size_class"] = ("small", "medium", "large")[index % 3]
            patient["largest_stone_mm3"] = (SMALL_MAX_MM3, MEDIUM_MAX_MM3, MEDIUM_MAX_MM3 + 1)[index % 3]

        splits = stratify_patients(patients)
        for name in ("train", "val", "test"):
            self.assertEqual(
                {patient["stone_size_class"] for patient in splits[name]},
                {"none", "small", "medium", "large"},
            )

    def test_classification_uses_largest_face_connected_component(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset = Path(temporary_directory)
            mask = np.zeros((8, 8, 8), dtype=np.uint8)
            mask[0:3, 0:3, 0:4] = 1
            mask[6, 6, 6] = 1
            affine = np.diag([1, 1, 1, 1])
            nib.save(nib.Nifti1Image(mask, affine), dataset / "patient_ps_mask.nii.gz")
            patient = {
                "patient_id": "patient_ps",
                "image": "patient_ps_image.nii.gz",
                "mask": "patient_ps_mask.nii.gz",
            }

            classified = classify_patients(dataset, [patient], stone_label=1)[0]

            self.assertEqual(classified["stone_size_class"], "medium")
            self.assertEqual(classified["largest_stone_voxels"], 36)
            self.assertEqual(classified["largest_stone_mm3"], 36.0)


if __name__ == "__main__":
    unittest.main()
