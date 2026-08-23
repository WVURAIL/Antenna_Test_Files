"""Regenerate S11 magnitude and Smith-chart images from Touchstone files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import skrf as rf


def render(
    touchstone_path: Path,
    s11_directory: Path,
    smith_directory: Path,
) -> tuple[Path, Path]:
    """Render both canonical plot types for a one-port Touchstone file."""
    network = rf.Network(str(touchstone_path))
    if network.nports != 1:
        raise ValueError(f"{touchstone_path} is not a one-port network")

    s11_directory.mkdir(parents=True, exist_ok=True)
    smith_directory.mkdir(parents=True, exist_ok=True)
    s11_path = s11_directory / f"S11_{touchstone_path.stem}.png"
    smith_path = smith_directory / f"{touchstone_path.stem}.jpg"

    magnitude = np.abs(network.s[:, 0, 0])
    with np.errstate(divide="ignore"):
        magnitude_db = 20.0 * np.log10(magnitude)
    figure, axis = plt.subplots()
    axis.plot(network.f / 1e6, magnitude_db)
    axis.set_xlabel("Frequency (MHz)")
    axis.set_ylabel("S11 magnitude (dB)")
    axis.set_title(f"S11_{touchstone_path.stem}")
    figure.savefig(s11_path, bbox_inches="tight")
    plt.close(figure)

    figure, axis = plt.subplots()
    network.plot_s_smith(m=0, n=0, ax=axis)
    axis.set_title(f"{touchstone_path.stem} Smith Chart")
    figure.savefig(smith_path, bbox_inches="tight")
    plt.close(figure)
    return s11_path, smith_path


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        type=Path,
        nargs="+",
        help="one-port Touchstone files to render",
    )
    parser.add_argument(
        "--s11-dir",
        type=Path,
        default=Path("Results") / "S11_Plots",
        help="magnitude-plot output directory",
    )
    parser.add_argument(
        "--smith-dir",
        type=Path,
        default=Path("Results") / "Smith_Charts",
        help="Smith-chart output directory",
    )
    return parser


def main() -> None:
    """Render each requested one-port file."""
    args = build_parser().parse_args()
    for touchstone_path in args.files:
        s11_path, smith_path = render(
            touchstone_path,
            args.s11_dir,
            args.smith_dir,
        )
        print(f"wrote {s11_path}")
        print(f"wrote {smith_path}")


if __name__ == "__main__":
    main()
