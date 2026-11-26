"""Interactive viewer for a NIfTI volume and selected mask label."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from matplotlib.widgets import RadioButtons, Slider


def resolve_pair(image: Path, mask: Path | None) -> tuple[Path, Path]:
    if image.name.endswith("_mask.nii.gz"):
        inferred_mask = image
        image = image.with_name(image.name.replace("_mask.nii.gz", "_image.nii.gz"))
    elif image.name.endswith("_image.nii.gz"):
        inferred_mask = image.with_name(image.name.replace("_image.nii.gz", "_mask.nii.gz"))
    elif mask is not None:
        inferred_mask = mask
    else:
        raise ValueError("Cannot infer the paired image/mask from filenames; provide --mask")

    selected_mask = mask or inferred_mask
    if not image.is_file():
        raise ValueError(f"Image file does not exist: {image}")
    if not selected_mask.is_file():
        raise ValueError(f"Mask file does not exist: {selected_mask}")
    return image, selected_mask


def load_volumes(image_path: Path, mask_path: Path) -> tuple[np.ndarray, np.ndarray, list[int]]:
    image_nifti = nib.load(str(image_path))
    mask_nifti = nib.load(str(mask_path))
    image = np.asarray(image_nifti.dataobj, dtype=np.float32)
    mask = np.asarray(mask_nifti.dataobj)
    if image.shape != mask.shape:
        raise ValueError(f"Image and mask shapes differ: {image.shape} != {mask.shape}")

    labels = [int(value) for value in np.unique(mask) if value != 0]
    if not labels:
        raise ValueError("Mask contains no non-zero labels")
    return image, mask, labels


def initial_window(image: np.ndarray) -> tuple[float, float]:
    finite = image[np.isfinite(image)]
    if not finite.size:
        raise ValueError("Image contains no finite voxels")
    low, high = np.percentile(finite, (1, 99))
    if low == high:
        high = low + 1
    return float((low + high) / 2), float(high - low)


def extract_views(
    image: np.ndarray, mask: np.ndarray, indices: tuple[int, int, int], label: int
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    x, y, z = indices
    images = [image[x, :, :].T, image[:, y, :].T, image[:, :, z].T]
    masks = [mask[x, :, :].T == label, mask[:, y, :].T == label, mask[:, :, z].T == label]
    return images, masks


def show_viewer(
    image_path: Path, mask_path: Path, selected_label: int | None = None
) -> None:
    image, mask, labels = load_volumes(image_path, mask_path)
    if selected_label is None:
        selected_label = labels[0]
    elif selected_label not in labels:
        raise ValueError(f"Mask label {selected_label} is not present; available labels: {labels}")

    indices = [image.shape[0] // 2, image.shape[1] // 2, image.shape[2] // 2]
    level, window = initial_window(image)
    figure, axes = plt.subplots(1, 3, figsize=(16, 7))
    figure.subplots_adjust(left=0.05, right=0.97, top=0.88, bottom=0.23, wspace=0.08)
    titles = ("Sagittal X", "Coronal Y", "Axial Z")
    image_artists = []
    mask_artists = []
    current_label = selected_label

    def limits() -> tuple[float, float]:
        return level_slider.val - window_slider.val / 2, level_slider.val + window_slider.val / 2

    images, masks = extract_views(image, mask, tuple(indices), current_label)
    for axis_index, (axis, title, image_slice, mask_slice) in enumerate(
        zip(axes, titles, images, masks)
    ):
        image_artist = axis.imshow(image_slice, cmap="gray", origin="lower")
        mask_artist = axis.imshow(
            np.ma.masked_where(~mask_slice, np.ones_like(image_slice)),
            cmap="Reds",
            vmin=0,
            vmax=1,
            alpha=0.55,
            origin="lower",
        )
        axis.set_title(f"{title}: {indices[axis_index]}")
        axis.axis("off")
        image_artists.append(image_artist)
        mask_artists.append(mask_artist)

    slider_axes = [
        figure.add_axes([0.08, 0.14, 0.72, 0.025]),
        figure.add_axes([0.08, 0.095, 0.72, 0.025]),
        figure.add_axes([0.08, 0.05, 0.72, 0.025]),
    ]
    sliders = [
        Slider(slider_axes[0], "X", 0, image.shape[0] - 1, valinit=indices[0], valstep=1),
        Slider(slider_axes[1], "Y", 0, image.shape[1] - 1, valinit=indices[1], valstep=1),
        Slider(slider_axes[2], "Z", 0, image.shape[2] - 1, valinit=indices[2], valstep=1),
    ]
    low, high = float(np.nanmin(image)), float(np.nanmax(image))
    value_range = max(high - low, 1.0)
    level_axis = figure.add_axes([0.86, 0.14, 0.1, 0.025])
    window_axis = figure.add_axes([0.86, 0.095, 0.1, 0.025])
    level_slider = Slider(level_axis, "Level", low, high, valinit=level)
    window_slider = Slider(window_axis, "Window", value_range / 100, value_range, valinit=window)

    def refresh(_event=None) -> None:
        images, masks = extract_views(image, mask, tuple(int(slider.val) for slider in sliders), current_label)
        vmin, vmax = limits()
        for axis_index, (axis, image_artist, mask_artist, image_slice, mask_slice) in enumerate(
            zip(axes, image_artists, mask_artists, images, masks)
        ):
            image_artist.set_data(image_slice)
            image_artist.set_clim(vmin, vmax)
            mask_artist.set_data(np.ma.masked_where(~mask_slice, np.ones_like(image_slice)))
            axis.set_title(f"{titles[axis_index]}: {int(sliders[axis_index].val)}")
        figure.canvas.draw_idle()

    for slider in sliders + [level_slider, window_slider]:
        slider.on_changed(refresh)
    refresh()

    radio_axis = figure.add_axes([0.86, 0.35, 0.1, 0.18])
    radio = RadioButtons(radio_axis, [f"Label {label}" for label in labels], active=labels.index(current_label))
    radio_axis.set_title("Mask")

    def select_label(label_text: str) -> None:
        nonlocal current_label
        current_label = int(label_text.removeprefix("Label "))
        refresh()

    radio.on_clicked(select_label)

    def on_scroll(event) -> None:
        axis_index = next(
            (index for index, axis in enumerate(axes) if event.inaxes == axis), None
        )
        if axis_index is None:
            return
        step = 1 if event.button == "up" else -1
        sliders[axis_index].set_val(
            np.clip(sliders[axis_index].val + step, 0, image.shape[axis_index] - 1)
        )

    figure.canvas.mpl_connect("scroll_event", on_scroll)
    figure.suptitle(
        f"{image_path.name} | {mask_path.name}\n"
        "Mouse wheel on a view selects adjacent slice; choose the displayed mask label on the right."
    )
    plt.show()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "image",
        type=Path,
        help="Path to *_image.nii.gz or *_mask.nii.gz; the paired file is inferred.",
    )
    parser.add_argument("--mask", type=Path, help="Explicit mask path")
    parser.add_argument("--label", type=int, help="Mask label to show initially")
    args = parser.parse_args()

    try:
        image, mask = resolve_pair(args.image, args.mask)
        show_viewer(image, mask, args.label)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
