"""Plot one S-parameter from two Touchstone files for comparison."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import skrf as rf


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path, help="first Touchstone file")
    parser.add_argument("second", type=Path, help="second Touchstone file")
    parser.add_argument("--first-label", help="legend label for the first network")
    parser.add_argument("--second-label", help="legend label for the second network")
    parser.add_argument("--title", help="plot title")
    parser.add_argument("--output", type=Path, help="optional output image path")
    parser.add_argument("--m", type=int, default=0, help="output-port index")
    parser.add_argument("--n", type=int, default=0, help="input-port index")
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="save without opening an interactive plot window",
    )
    return parser


def main() -> None:
    """Load and compare two requested networks."""
    args = build_parser().parse_args()
    paths = (args.first, args.second)
    labels = (
        args.first_label or args.first.stem,
        args.second_label or args.second.stem,
    )

    figure, axis = plt.subplots()
    for path, label in zip(paths, labels):
        network = rf.Network(str(path))
        if args.m >= network.nports or args.n >= network.nports:
            raise SystemExit(
                f"{path} has {network.nports} port(s), so S{args.m + 1}{args.n + 1} "
                "is unavailable"
            )
        network.plot_s_db(m=args.m, n=args.n, label=label, ax=axis)

    axis.set_title(args.title or f"{labels[0]} vs. {labels[1]}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.output, bbox_inches="tight")
    if not args.no_show:
        plt.show()
    plt.close(figure)


if __name__ == "__main__":
    main()
