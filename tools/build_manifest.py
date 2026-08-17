"""Build the deterministic archive manifest for every file under ``Results``."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import re
import subprocess
import sys
import tarfile
from pathlib import Path


BASE_COMMIT = "c58a019127a291ce088e26e93aa42ecaedd9d9eb"
HEADERS = [
    "path",
    "sha256",
    "size_bytes",
    "kind",
    "status",
    "antenna",
    "port",
    "point_count",
    "declared_frequency_unit",
    "raw_frequency_min",
    "raw_frequency_max",
    "source_sha256_at_c58a019",
    "provenance_note",
    "validation_flags",
]
MOVED_SOURCES = {
    "Results/Corrupt_Artifacts/ANT1481H_P2.jpg.nul":
        "Results/Smith_Charts/ANT1481H_P2.jpg",
    "Results/Corrupt_Artifacts/ANT1481H_P2.s1p.nul":
        "Results/Touchstone_Files/ANT1481H_P2.s1p",
    "Results/Test_Artifacts/testing_work_P1.s1p":
        "Results/Touchstone_Files/testing_work_P1.s1p",
    "Results/Test_Artifacts/testing_work_P2.s1p":
        "Results/Touchstone_Files/testing_work_P2.s1p",
}
REGENERATED_PLOTS = {
    "Results/S11_Plots/S11_ANT1342H_P1.png",
    "Results/S11_Plots/S11_ANT1342H_P2.png",
    "Results/Smith_Charts/ANT1342H_P1.jpg",
    "Results/Smith_Charts/ANT1342H_P2.jpg",
}
LEGACY_TOUCHSTONE_HEADER = re.compile(
    br"(?m)^# GHz S RI R 50\.0[ \t]*(\r?)$"
)


def sha256(data: bytes) -> str:
    """Return a lowercase SHA-256 hex digest."""
    return hashlib.sha256(data).hexdigest()


def repository_root() -> Path:
    """Find the current Git worktree root."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return Path(result.stdout.strip()).resolve()


def source_snapshot(repo: Path, base_ref: str) -> dict[str, bytes]:
    """Read the base Results tree without checking it out or changing the worktree."""
    exists = subprocess.run(
        ["git", "cat-file", "-e", f"{base_ref}^{{commit}}"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if exists.returncode:
        return {}
    archive = subprocess.run(
        ["git", "archive", "--format=tar", base_ref, "Results"],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    snapshot: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source_tar:
        for member in source_tar.getmembers():
            if not member.isfile():
                continue
            extracted = source_tar.extractfile(member)
            if extracted is not None:
                snapshot[member.name] = extracted.read()
    return snapshot


def identifiers(path: Path) -> tuple[str, str]:
    """Extract an antenna identifier and port where the filename encodes them."""
    name = path.name
    for suffix in (".s1p.nul", ".jpg.nul", ".s1p", ".png", ".jpg"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    if name.startswith("S11_"):
        name = name[4:]

    antenna_match = re.search(r"(?i)(?:^|_)ANT\d+[A-Z]?", name)
    antenna = antenna_match.group(0).lstrip("_") if antenna_match else ""
    port_match = re.search(r"(?i)(?:^|_)P([12])(?=$|[^0-9])", name)
    port = f"P{port_match.group(1)}" if port_match else ""
    return antenna, port


def parse_touchstone(data: bytes) -> tuple[str, int, str, str, list[str]]:
    """Parse and validate the simple RI one-port files used by this archive."""
    unit = ""
    frequencies: list[float] = []
    raw_frequencies: list[str] = []
    flags: list[str] = []
    all_values_finite = True
    rows_well_formed = True

    for raw_line in data.splitlines():
        line = raw_line.decode("ascii").strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("#"):
            fields = line.split()
            unit = fields[1] if len(fields) > 1 else ""
            continue
        fields = line.split()
        if len(fields) != 3:
            rows_well_formed = False
            continue
        try:
            values = [float(value) for value in fields]
        except ValueError:
            rows_well_formed = False
            continue
        all_values_finite = all_values_finite and all(math.isfinite(v) for v in values)
        frequencies.append(values[0])
        raw_frequencies.append(fields[0])

    if rows_well_formed:
        flags.append("three_columns_per_data_row")
    if all_values_finite:
        flags.append("finite_numeric_data")
    if frequencies and all(a < b for a, b in zip(frequencies, frequencies[1:])):
        flags.append("strictly_increasing_frequency")
    if unit == "Hz":
        flags.append("declared_unit_Hz")

    if frequencies:
        min_index = min(range(len(frequencies)), key=frequencies.__getitem__)
        max_index = max(range(len(frequencies)), key=frequencies.__getitem__)
        raw_min = raw_frequencies[min_index]
        raw_max = raw_frequencies[max_index]
    else:
        raw_min = ""
        raw_max = ""
    return unit, len(raw_frequencies), raw_min, raw_max, flags


def classify(path_string: str) -> tuple[str, str]:
    """Return the artifact kind and archive status for a Results path."""
    if path_string.endswith(".s1p.nul"):
        return "corrupt_touchstone_bytes", "quarantined_corrupt"
    if path_string.endswith(".jpg.nul"):
        return "corrupt_smith_chart_bytes", "quarantined_corrupt"
    if "/Test_Artifacts/" in path_string:
        return "touchstone_s1p", "test_artifact"
    if "/Touchstone_Files/" in path_string:
        return "touchstone_s1p", "canonical_valid"
    if "/S11_Plots/" in path_string:
        if path_string.endswith("S11_ANT1444H_P1.png"):
            return "s11_plot_png", "restored_valid"
        if path_string in REGENERATED_PLOTS:
            return "s11_plot_png", "regenerated_valid"
        return "s11_plot_png", "reference_plot_valid"
    if "/Smith_Charts/" in path_string:
        if path_string in REGENERATED_PLOTS:
            return "smith_chart_jpeg", "regenerated_valid"
        return "smith_chart_jpeg", "reference_plot_valid"
    return "other", "unclassified"


def make_row(
    repo: Path,
    snapshot: dict[str, bytes],
    path: Path,
) -> dict[str, str | int]:
    """Create one manifest row."""
    relative = path.relative_to(repo).as_posix()
    data = path.read_bytes()
    digest = sha256(data)
    source_relative = MOVED_SOURCES.get(relative, relative)
    source_data = snapshot.get(source_relative)
    source_digest = sha256(source_data) if source_data is not None else ""
    kind, status = classify(relative)
    antenna, port = identifiers(path)
    flags: list[str] = []
    point_count: str | int = ""
    unit = ""
    raw_min = ""
    raw_max = ""

    if kind == "touchstone_s1p":
        unit, point_count, raw_min, raw_max, parsed_flags = parse_touchstone(data)
        flags.extend(parsed_flags)
        if source_data is not None:
            corrected_source = LEGACY_TOUCHSTONE_HEADER.sub(
                br"# Hz S RI R 50.0\1", source_data, count=1
            )
            if corrected_source == data:
                flags.extend(
                    (
                        "corrected_frequency_unit_header",
                        "numeric_rows_preserved_from_c58a019",
                    )
                )
        if status == "test_artifact":
            flags.extend(("excluded_from_canonical_dataset", "duplicate_test_artifact"))
            provenance = (
                f"Moved from {source_relative}; legacy GHz header corrected to Hz; "
                "numeric rows preserved from c58a019."
            )
        else:
            provenance = (
                "Legacy GHz header corrected to Hz; numeric rows preserved from c58a019."
            )
    elif status == "quarantined_corrupt":
        if data and not any(data):
            flags.append("all_NUL_bytes")
        if source_data == data:
            flags.append("bytes_preserved_from_c58a019")
        flags.extend(("excluded_from_canonical_dataset", "invalid_original_format"))
        provenance = (
            f"Moved from {source_relative} and renamed .nul; all legacy bytes preserved "
            "from c58a019."
        )
    elif status == "regenerated_valid":
        if kind == "s11_plot_png":
            if data.startswith(b"\x89PNG\r\n\x1a\n") and data[-8:-4] == b"IEND":
                flags.append("valid_png_container")
            flags.append("S11_magnitude_label_dB")
        elif data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
            flags.append("valid_jpeg_container")
        flags.extend(("regenerated_from_current_touchstone", "replaces_stale_pre_retest_plot"))
        provenance = (
            "Regenerated from the current ANT1342H Touchstone file with "
            "tools/render_s1p_plots.py; replaces the stale pre-retest plot at c58a019."
        )
    elif kind == "s11_plot_png":
        if data.startswith(b"\x89PNG\r\n\x1a\n") and data[-8:-4] == b"IEND":
            flags.append("valid_png_container")
        flags.append("legacy_axis_label_dBm")
        if status == "restored_valid":
            flags.extend(("restored_from_git_history", "replaces_incorrect_duplicate"))
            provenance = (
                "Restored from Git blob a3d7a8b8a3a5c72321d843f1e52948c87fce3f98 "
                "(commit 6689539); replaces the incorrect ANT1445 duplicate at c58a019."
            )
        else:
            if source_data == data:
                flags.append("unchanged_from_c58a019")
            provenance = "Preserved from c58a019."
    elif kind == "smith_chart_jpeg":
        if data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
            flags.append("valid_jpeg_container")
        if source_data == data:
            flags.append("unchanged_from_c58a019")
        provenance = "Preserved from c58a019."
    else:
        if source_data == data:
            flags.append("unchanged_from_c58a019")
        provenance = "Preserved from c58a019."

    if source_data is None:
        flags.append("base_commit_unavailable_or_path_absent")

    return {
        "path": relative,
        "sha256": digest,
        "size_bytes": len(data),
        "kind": kind,
        "status": status,
        "antenna": antenna,
        "port": port,
        "point_count": point_count,
        "declared_frequency_unit": unit,
        "raw_frequency_min": raw_min,
        "raw_frequency_max": raw_max,
        "source_sha256_at_c58a019": source_digest,
        "provenance_note": provenance,
        "validation_flags": ";".join(flags),
    }


def render_manifest(repo: Path, base_ref: str) -> str:
    """Return the complete manifest as deterministic CSV text."""
    snapshot = source_snapshot(repo, base_ref)
    paths = sorted(path for path in (repo / "Results").rglob("*") if path.is_file())
    rows = [make_row(repo, snapshot, path) for path in paths]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        default=BASE_COMMIT,
        help="historical commit used for pre-correction source hashes",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("MANIFEST.csv"),
        help="manifest path relative to the repository root",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing if the existing manifest is out of date",
    )
    return parser


def main() -> None:
    """Write the manifest or verify that it is current."""
    args = build_parser().parse_args()
    repo = repository_root()
    output_path = args.output if args.output.is_absolute() else repo / args.output
    expected = render_manifest(repo, args.base_ref)
    if args.check:
        actual = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        if actual != expected:
            print(f"manifest is out of date: {output_path}", file=sys.stderr)
            raise SystemExit(1)
        print(f"manifest is current: {output_path}")
        return
    with output_path.open("w", encoding="utf-8", newline="") as output:
        output.write(expected)
    print(f"wrote {len(expected.splitlines()) - 1} rows to {output_path}")


if __name__ == "__main__":
    main()
