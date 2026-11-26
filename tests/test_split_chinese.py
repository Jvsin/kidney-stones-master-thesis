import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.split_chinese import stratify_patients  # noqa: E402


class SplitChineseTests(unittest.TestCase):
    @staticmethod
    def patients(with_stones=209, without_stones=51):
        positive = [
            {
                "patient_id": f"positive_{index:03d}",
                "image": f"positive_{index:03d}_image.nii.gz",
                "mask": f"positive_{index:03d}_mask.nii.gz",
                "has_stones": True,
            }
            for index in range(with_stones)
        ]
        negative = [
            {
                "patient_id": f"negative_{index:03d}",
                "image": f"negative_{index:03d}_image.nii.gz",
                "mask": f"negative_{index:03d}_mask.nii.gz",
                "has_stones": False,
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
            [146, 32, 31],
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


if __name__ == "__main__":
    unittest.main()
