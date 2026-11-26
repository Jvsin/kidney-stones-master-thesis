"""Create a deterministic, patient-level stratified split for the Chinese dataset."""

import argparse
import itertools
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATIOS = (0.70, 0.15, 0.15)
SPLIT_NAMES = ("train", "val", "test")


def discover_patients(dataset: Path) -> list[dict[str, Any]]:
    if not dataset.is_dir():
        raise ValueError(f"Dataset directory does not exist: {dataset}")

    pairs: dict[tuple[Path, str], dict[str, Path]] = {}
    for path in sorted(dataset.rglob("*.nii.gz")):
        for kind in ("image", "mask"):
            suffix = f"_{kind}.nii.gz"
            if path.name.endswith(suffix):
                pairs.setdefault((path.parent, path.name[: -len(suffix)]), {})[kind] = path
                break
        else:
            raise ValueError(f"Unrecognized NIfTI filename: {path.relative_to(dataset)}")

    identifiers = Counter(patient_id for _, patient_id in pairs)
    duplicates = sorted(patient_id for patient_id, count in identifiers.items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate patient identifiers: {', '.join(duplicates)}")

    patients = []
    for (directory, patient_id), files in sorted(pairs.items()):
        if set(files) != {"image", "mask"}:
            missing = "image" if "image" not in files else "mask"
            raise ValueError(f"{patient_id}: missing {missing}")
        patients.append(
            {
                "patient_id": patient_id,
                "image": (files["image"].relative_to(dataset)).as_posix(),
                "mask": (files["mask"].relative_to(dataset)).as_posix(),
            }
        )
    return patients


def classify_patients(
    dataset: Path, patients: list[dict[str, Any]], stone_label: int
) -> list[dict[str, Any]]:
    classified = []
    for patient in patients:
        mask_path = dataset / patient["mask"]
        try:
            mask = nib.load(str(mask_path))
            has_stones = bool(np.any(np.asanyarray(mask.dataobj) == stone_label))
        except (OSError, EOFError, ValueError, nib.filebasedimages.ImageFileError) as exc:
            raise ValueError(f"{patient['patient_id']}: cannot read mask: {exc}") from exc
        classified.append({**patient, "has_stones": has_stones})
    return classified


def _largest_remainder_counts(total: int, ratios: tuple[float, float, float]) -> list[int]:
    exact = [total * ratio for ratio in ratios]
    counts = [int(value) for value in exact]
    remaining = total - sum(counts)
    order = sorted(range(len(counts)), key=lambda index: (-(exact[index] - counts[index]), index))
    for index in order[:remaining]:
        counts[index] += 1
    return counts


def _allocation_matrix(
    class_counts: list[int], split_totals: list[int], ratios: tuple[float, float, float]
) -> list[list[int]]:
    if len(class_counts) != 2:
        raise ValueError("Exactly two classes are required for stratification")

    ideals = [
        [class_count * ratio for ratio in ratios]
        for class_count in class_counts
    ]
    floors = [[int(value) for value in row] for row in ideals]
    candidates = []
    for increments in itertools.product((0, 1), repeat=len(split_totals)):
        first_row = [
            floors[0][index] + increment
            for index, increment in enumerate(increments)
        ]
        if sum(first_row) != class_counts[0]:
            continue
        second_row = [
            split_total - first_count
            for split_total, first_count in zip(split_totals, first_row)
        ]
        if min(second_row) < 0 or sum(second_row) != class_counts[1]:
            continue
        matrix = [first_row, second_row]
        error = sum(
            abs(matrix[row][column] - ideals[row][column])
            for row in range(2)
            for column in range(len(split_totals))
        )
        candidates.append((error, first_row, matrix))

    if not candidates:
        raise ValueError("Cannot satisfy split totals while preserving class stratification")
    return min(candidates)[2]


def stratify_patients(
    patients: list[dict[str, Any]],
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    if len(ratios) != len(SPLIT_NAMES):
        raise ValueError(f"Expected {len(SPLIT_NAMES)} split ratios")
    if any(ratio <= 0 for ratio in ratios) or not np.isclose(sum(ratios), 1.0):
        raise ValueError("Split ratios must be positive and sum to 1")

    patient_ids = [patient["patient_id"] for patient in patients]
    if len(patient_ids) != len(set(patient_ids)):
        raise ValueError("Patient identifiers must be unique before splitting")

    grouped = [[], []]
    for patient in patients:
        grouped[int(bool(patient["has_stones"]))].append(patient)

    class_counts = [len(grouped[0]), len(grouped[1])]
    if 0 in class_counts:
        raise ValueError("Both patients with and without stones are required for stratification")
    split_totals = _largest_remainder_counts(len(patients), ratios)
    if any(total < len(class_counts) for total in split_totals):
        raise ValueError("Each split must contain enough patients for every class")

    allocation = _allocation_matrix(class_counts, split_totals, ratios)
    rng = random.Random(seed)
    for group in grouped:
        rng.shuffle(group)

    splits: dict[str, list[dict[str, Any]]] = {name: [] for name in SPLIT_NAMES}
    offsets = [0, 0]
    for split_index, name in enumerate(SPLIT_NAMES):
        for class_index, group in enumerate(grouped):
            count = allocation[class_index][split_index]
            start = offsets[class_index]
            splits[name].extend(group[start : start + count])
            offsets[class_index] += count
        splits[name].sort(key=lambda patient: patient["patient_id"])
    return splits


def create_split_manifest(
    dataset: Path,
    stone_label: int = 1,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    seed: int = 42,
    expected_count: int | None = None,
) -> dict[str, Any]:
    patients = classify_patients(dataset, discover_patients(dataset), stone_label)
    if expected_count is not None and len(patients) != expected_count:
        raise ValueError(f"Expected {expected_count} patients, found {len(patients)}")
    splits = stratify_patients(patients, ratios, seed)
    summary = {}
    for name, split in splits.items():
        with_stones = sum(patient["has_stones"] for patient in split)
        summary[name] = {
            "patients": len(split),
            "with_stones": with_stones,
            "without_stones": len(split) - with_stones,
            "stone_prevalence": with_stones / len(split),
        }
    return {
        "dataset": str(dataset.resolve()),
        "seed": seed,
        "stone_label": stone_label,
        "ratios": dict(zip(SPLIT_NAMES, ratios)),
        "summary": summary,
        "splits": splits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", type=Path, default=ROOT / "datasets" / "chinese")
    parser.add_argument("--stone-label", type=int, choices=(1, 2), default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--expected-count", type=int, default=260)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "datasets" / "chinese" / "patient_splits.json",
    )
    args = parser.parse_args()

    try:
        manifest = create_split_manifest(
            args.dataset, args.stone_label, DEFAULT_RATIOS, args.seed, args.expected_count
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(manifest["summary"], indent=2))
    print(f"Saved patient split manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
