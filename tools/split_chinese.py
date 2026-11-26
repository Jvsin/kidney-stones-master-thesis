"""Create a deterministic, patient-level stratified split for the Chinese dataset."""

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RATIOS = (0.70, 0.15, 0.15)
SPLIT_NAMES = ("train", "val", "test")
SIZE_CLASSES = ("none", "small", "medium", "large")
SMALL_MAX_MM3 = 28.0
MEDIUM_MAX_MM3 = 315.0


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
            mask_data = np.asanyarray(mask.dataobj)
            stone_voxels = np.argwhere(mask_data == stone_label)
            if len(stone_voxels):
                minimum = stone_voxels.min(axis=0)
                maximum = stone_voxels.max(axis=0) + 1
                region = tuple(slice(start, stop) for start, stop in zip(minimum, maximum))
                stone_mask = mask_data[region] == stone_label
                components, component_count = ndimage.label(
                    stone_mask, structure=ndimage.generate_binary_structure(3, 1)
                )
                component_voxels = np.bincount(components.ravel(), minlength=component_count + 1)[1:]
                voxel_volume = float(np.prod(mask.header.get_zooms()[:3]))
                largest_stone_voxels = int(component_voxels.max())
                largest_stone_mm3 = largest_stone_voxels * voxel_volume
            else:
                largest_stone_voxels = 0
                largest_stone_mm3 = 0.0
        except (OSError, EOFError, ValueError, nib.filebasedimages.ImageFileError) as exc:
            raise ValueError(f"{patient['patient_id']}: cannot read mask: {exc}") from exc
        if largest_stone_mm3 == 0:
            stone_size_class = "none"
        elif largest_stone_mm3 <= SMALL_MAX_MM3:
            stone_size_class = "small"
        elif largest_stone_mm3 <= MEDIUM_MAX_MM3:
            stone_size_class = "medium"
        else:
            stone_size_class = "large"
        classified.append(
            {
                **patient,
                "has_stones": stone_size_class != "none",
                "stone_size_class": stone_size_class,
                "largest_stone_voxels": largest_stone_voxels,
                "largest_stone_mm3": round(largest_stone_mm3, 6),
            }
        )
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
    ideals = [[class_count * ratio for ratio in ratios] for class_count in class_counts]
    matrix = [[0 for _ in split_totals] for _ in class_counts]
    row_remaining = list(class_counts)
    column_remaining = list(split_totals)

    while sum(row_remaining):
        candidates = [
            (
                ideals[row][column] - matrix[row][column],
                -row,
                -column,
                row,
                column,
            )
            for row in range(len(class_counts))
            for column in range(len(split_totals))
            if row_remaining[row] and column_remaining[column]
        ]
        if not candidates:
            raise ValueError("Cannot satisfy split totals while preserving class stratification")
        _, _, _, row, column = max(candidates)
        matrix[row][column] += 1
        row_remaining[row] -= 1
        column_remaining[column] -= 1
    return matrix


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

    stratum_key = "stone_size_class" if any(
        "stone_size_class" in patient for patient in patients
    ) else "has_stones"
    strata = SIZE_CLASSES if stratum_key == "stone_size_class" else (False, True)
    grouped = {stratum: [] for stratum in strata}
    for patient in patients:
        if stratum_key == "stone_size_class":
            stratum = patient.get(stratum_key)
            if stratum not in grouped:
                raise ValueError(f"Unknown stone size class: {stratum!r}")
        else:
            stratum = bool(patient["has_stones"])
        grouped[stratum].append(patient)

    strata = tuple(stratum for stratum in strata if grouped[stratum])
    if not strata:
        raise ValueError("No patients available for stratification")
    class_counts = [len(grouped[stratum]) for stratum in strata]
    split_totals = _largest_remainder_counts(len(patients), ratios)
    if any(total < len(class_counts) for total in split_totals):
        raise ValueError("Each split must contain enough patients for every class")

    allocation = _allocation_matrix(class_counts, split_totals, ratios)
    rng = random.Random(seed)
    for stratum in strata:
        rng.shuffle(grouped[stratum])

    splits: dict[str, list[dict[str, Any]]] = {name: [] for name in SPLIT_NAMES}
    offsets = [0 for _ in class_counts]
    for split_index, name in enumerate(SPLIT_NAMES):
        for class_index, stratum in enumerate(strata):
            group = grouped[stratum]
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
        size_distribution = Counter(patient["stone_size_class"] for patient in split)
        summary[name] = {
            "patients": len(split),
            "with_stones": with_stones,
            "without_stones": len(split) - with_stones,
            "stone_prevalence": with_stones / len(split),
            "size_distribution": {
                size_class: size_distribution[size_class] for size_class in SIZE_CLASSES
            },
        }
    return {
        "dataset": str(dataset.resolve()),
        "seed": seed,
        "stone_label": stone_label,
        "ratios": dict(zip(SPLIT_NAMES, ratios)),
        "stratification": "largest_stone_volume_mm3",
        "connectivity": "face (6-connected)",
        "size_thresholds_mm3": {
            "small": f"0 < volume <= {SMALL_MAX_MM3:g}",
            "medium": f"{SMALL_MAX_MM3:g} < volume <= {MEDIUM_MAX_MM3:g}",
            "large": f"volume > {MEDIUM_MAX_MM3:g}",
        },
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
