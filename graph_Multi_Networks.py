"""Plot the same S-parameter from any number of Touchstone files."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import skrf as rf


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="+", help="Touchstone input files")
    parser.add_argument(
        "--labels",
        nargs="+",
        help="legend labels in the same order as the input files",
    )
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
    """Load the requested networks and plot them together."""
    args = build_parser().parse_args()
    if args.labels and len(args.labels) != len(args.files):
        raise SystemExit("--labels must provide exactly one label per input file")

    labels = args.labels or [path.stem for path in args.files]
    figure, axis = plt.subplots()
    for path, label in zip(args.files, labels):
        network = rf.Network(str(path))
        if args.m >= network.nports or args.n >= network.nports:
            raise SystemExit(
                f"{path} has {network.nports} port(s), so S{args.m + 1}{args.n + 1} "
                "is unavailable"
            )
        network.plot_s_db(m=args.m, n=args.n, label=label, ax=axis)

    axis.set_title(args.title or "S-parameter comparison")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.output, bbox_inches="tight")
    if not args.no_show:
        plt.show()
    plt.close(figure)


if __name__ == "__main__":
    main()
