"""Verify image/mask pairs in the Chinese kidney stone dataset."""

import argparse
from collections import Counter
from pathlib import Path

import nibabel as nib
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def verify(dataset: Path, expected_count: int, stone_label: int | None = None) -> int:
    if not dataset.is_dir():
        print(f"ERROR: Dataset directory does not exist: {dataset}")
        return 1

    pairs = {}
    problems = []
    for path in sorted(dataset.rglob("*.nii.gz")):
        for kind in ("image", "mask"):
            suffix = f"_{kind}.nii.gz"
            if path.name.endswith(suffix):
                key = (path.parent, path.name[: -len(suffix)])
                pairs.setdefault(key, {})[kind] = path
                break
        else:
            problems.append(f"Unrecognized NIfTI filename: {path}")

    if len(pairs) != expected_count:
        problems.append(f"Expected {expected_count} patients, found {len(pairs)}.")

    identifiers = Counter(name for _, name in pairs)
    for name, count in sorted(identifiers.items()):
        if count > 1:
            problems.append(f"Duplicate patient identifier: {name} ({count} directories)")

    spacings = []
    label_totals = Counter()
    empty_masks = []
    missing_labels = {1: [], 2: []}
    checked = 0

    for (directory, name), files in sorted(pairs.items()):
        patient = f"{directory.relative_to(dataset) / name}"
        if set(files) != {"image", "mask"}:
            problems.append(f"{patient}: missing {'image' if 'image' not in files else 'mask'}")
            print(f"{patient}: ERROR: incomplete pair")
            continue

        try:
            image = nib.load(str(files["image"]))
            mask = nib.load(str(files["mask"]))
            if len(image.shape) != 3 or len(mask.shape) != 3:
                raise ValueError(f"expected 3D images, got {image.shape} and {mask.shape}")
            units = image.header.get_xyzt_units()[0]
            mask_units = mask.header.get_xyzt_units()[0]
            spacing = np.asarray(image.header.get_zooms()[:3], dtype=float)
            if not np.all(np.isfinite(spacing)) or np.any(spacing <= 0):
                raise ValueError(f"invalid voxel spacing: {spacing}")
            values, counts = np.unique(np.asanyarray(mask.dataobj), return_counts=True)
            if not np.all(np.isfinite(values)):
                raise ValueError("mask contains non-finite labels")
        except (OSError, EOFError, ValueError, nib.filebasedimages.ImageFileError) as exc:
            problems.append(f"{patient}: {exc}")
            print(f"{patient}: ERROR: {exc}")
            continue

        checked += 1
        labels = {float(value): int(count) for value, count in zip(values, counts)}
        label_totals.update(labels)
        foreground = sum(count for label, count in labels.items() if label != 0)
        if not foreground:
            empty_masks.append(patient)
            problems.append(f"{patient}: empty mask")
        for label in missing_labels:
            if not labels.get(label, 0):
                missing_labels[label].append(patient)
        if not set(labels).issubset({0.0, 1.0, 2.0}):
            problems.append(f"{patient}: unexpected labels {list(labels)}")
        geometry_ok = (
            image.shape == mask.shape
            and units == mask_units
            and np.allclose(image.header.get_zooms()[:3], mask.header.get_zooms()[:3], rtol=0, atol=1e-4)
            and np.allclose(image.affine, mask.affine, rtol=0, atol=1e-4)
        )
        if not geometry_ok:
            problems.append(
                f"{patient}: image/mask geometry differs "
                f"(shapes {image.shape} vs {mask.shape}; "
                f"spacing {tuple(image.header.get_zooms()[:3])} vs "
                f"{tuple(mask.header.get_zooms()[:3])}; "
                f"units {units} vs {mask_units}; "
                f"max affine difference {np.max(np.abs(image.affine - mask.affine)):.6f})"
            )
        if units == "mm":
            spacings.append(spacing)
        else:
            problems.append(f"{patient}: image spatial unit is {units!r}, not mm")
        print(
            f"{patient} | image={image.shape} mask={mask.shape} | "
            f"spacing={tuple(round(float(x), 6) for x in spacing)} {units} | "
            f"labels={labels} | foreground={foreground} | "
            f"geometry={'OK' if geometry_ok else 'MISMATCH'}"
        )

    print(f"\nPatients found: {len(pairs)}; pairs checked: {checked}; expected: {expected_count}")
    print(f"Total label voxel counts: {dict(sorted(label_totals.items()))}")
    print(f"Empty masks ({len(empty_masks)}): {', '.join(empty_masks) or 'none'}")
    for label, patients in missing_labels.items():
        print(f"Without label {label} ({len(patients)}): {', '.join(patients) or 'none'}")
    if stone_label is None:
        print("Stone label not specified; presence of stones cannot be determined.")
    else:
        print(f"Assumed stone label: {stone_label}")
    if spacings:
        data = np.asarray(spacings)
        for axis, values in zip("XYZ", data.T):
            print(
                f"Spacing {axis} (mm): min={values.min():.6f}, "
                f"median={np.median(values):.6f}, max={values.max():.6f}"
            )
            distribution = Counter(round(float(value), 6) for value in values)
            print(f"  Distribution (mm: patients): {dict(sorted(distribution.items()))}")
        for axis, values in zip("XYZ", data.T):
            low, high = (0.42, 2.50) if axis == "Z" else (0.371, 0.977)
            decimals = 2 if axis == "Z" else 3
            rounded = np.round(values, decimals)
            outside = int(np.count_nonzero((rounded < low) | (rounded > high)))
            print(f"  Outside expected {axis} range [{low}, {high}] mm after rounding to {decimals} decimals: {outside}")
    print(f"Problems ({len(problems)}):")
    for problem in problems:
        print(f"  - {problem}")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", nargs="?", type=Path, default=ROOT / "datasets" / "chinese")
    parser.add_argument("--expected-count", type=int, default=260)
    parser.add_argument("--stone-label", type=int, choices=(1, 2))
    args = parser.parse_args()
    return verify(args.dataset, args.expected_count, args.stone_label)


if __name__ == "__main__":
    raise SystemExit(main())
