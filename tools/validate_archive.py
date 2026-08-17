"""Validate the archived measurement corpus without hardware dependencies."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
import struct
import subprocess
import sys
import zlib


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIRECTORY = REPOSITORY_ROOT / "Results"
TOUCHSTONE_DIRECTORY = RESULTS_DIRECTORY / "Touchstone_Files"
S11_PLOT_DIRECTORY = RESULTS_DIRECTORY / "S11_Plots"
SMITH_CHART_DIRECTORY = RESULTS_DIRECTORY / "Smith_Charts"
MANIFEST_PATH = REPOSITORY_ROOT / "MANIFEST.csv"
EXPECTED_TOUCHSTONE_COUNT = 558
EXPECTED_START_HZ = 10_000_000.0
EXPECTED_STOP_HZ = 2_000_000_000.0
EXPECTED_POINT_COUNTS = {201, 401}
MANIFEST_FIELDS = {
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
}


def file_sha256(path: Path) -> str:
    """Return a lowercase SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    """Return a repository-relative POSIX path."""
    return path.relative_to(REPOSITORY_ROOT).as_posix()


def parse_touchstone(path: Path, errors: list[str]) -> dict[str, object] | None:
    """Parse the repository's Touchstone 1.x one-port subset."""
    option_tokens: list[str] | None = None
    rows: list[tuple[float, float, float]] = []
    try:
        with path.open("r", encoding="ascii") as stream:
            for line_number, original_line in enumerate(stream, start=1):
                line = original_line.split("!", 1)[0].strip()
                if not line:
                    continue
                if line.startswith("#"):
                    if option_tokens is not None:
                        errors.append(
                            f"{relative_path(path)}:{line_number}: multiple option lines"
                        )
                    option_tokens = line[1:].split()
                    continue
                if line.startswith("["):
                    errors.append(
                        f"{relative_path(path)}:{line_number}: unsupported Touchstone 2 section"
                    )
                    continue
                columns = line.split()
                if len(columns) != 3:
                    errors.append(
                        f"{relative_path(path)}:{line_number}: expected 3 numeric columns, "
                        f"found {len(columns)}"
                    )
                    continue
                try:
                    row = tuple(float(column) for column in columns)
                except ValueError:
                    errors.append(
                        f"{relative_path(path)}:{line_number}: nonnumeric data row"
                    )
                    continue
                if not all(math.isfinite(value) for value in row):
                    errors.append(
                        f"{relative_path(path)}:{line_number}: non-finite numeric value"
                    )
                    continue
                rows.append(row)
    except (OSError, UnicodeError) as exc:
        errors.append(f"{relative_path(path)}: cannot read as ASCII Touchstone: {exc}")
        return None

    if option_tokens is None:
        errors.append(f"{relative_path(path)}: missing Touchstone option line")
        return None
    normalized = [token.upper() for token in option_tokens]
    if len(normalized) != 5:
        errors.append(
            f"{relative_path(path)}: expected option line '# Hz S RI R 50.0'"
        )
        return None
    unit, parameter, data_format, resistance_marker, resistance_text = normalized
    if (unit, parameter, data_format, resistance_marker) != ("HZ", "S", "RI", "R"):
        errors.append(
            f"{relative_path(path)}: option line must declare '# Hz S RI R 50.0'"
        )
    try:
        resistance = float(resistance_text)
    except ValueError:
        errors.append(f"{relative_path(path)}: invalid reference resistance")
        resistance = math.nan
    if not math.isclose(resistance, 50.0, rel_tol=0.0, abs_tol=1e-9):
        errors.append(f"{relative_path(path)}: reference resistance is not 50 ohms")

    if not rows:
        errors.append(f"{relative_path(path)}: contains no usable data rows")
        return None
    frequencies = [row[0] for row in rows]
    if any(current <= previous for previous, current in zip(frequencies, frequencies[1:])):
        errors.append(f"{relative_path(path)}: frequencies are not strictly increasing")
    if not math.isclose(
        frequencies[0], EXPECTED_START_HZ, rel_tol=0.0, abs_tol=1.0
    ):
        errors.append(
            f"{relative_path(path)}: first frequency is {frequencies[0]:g} Hz, "
            f"expected {EXPECTED_START_HZ:g} Hz"
        )
    if not math.isclose(
        frequencies[-1], EXPECTED_STOP_HZ, rel_tol=0.0, abs_tol=1.0
    ):
        errors.append(
            f"{relative_path(path)}: last frequency is {frequencies[-1]:g} Hz, "
            f"expected {EXPECTED_STOP_HZ:g} Hz"
        )
    if len(rows) not in EXPECTED_POINT_COUNTS:
        errors.append(
            f"{relative_path(path)}: has {len(rows)} points; expected 201 or 401"
        )
    return {
        "point_count": len(rows),
        "declared_frequency_unit": unit,
        "raw_frequency_min": frequencies[0],
        "raw_frequency_max": frequencies[-1],
    }


def validate_png(path: Path, errors: list[str]) -> None:
    """Validate a PNG's signature, chunk bounds, CRCs, and dimensions."""
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        errors.append(f"{relative_path(path)}: invalid PNG signature")
        return
    offset = 8
    saw_header = False
    saw_end = False
    while offset < len(data):
        if offset + 12 > len(data):
            errors.append(f"{relative_path(path)}: truncated PNG chunk")
            return
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            errors.append(f"{relative_path(path)}: PNG chunk exceeds file length")
            return
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            errors.append(f"{relative_path(path)}: PNG chunk CRC mismatch")
            return
        if not saw_header:
            if chunk_type != b"IHDR" or length != 13:
                errors.append(f"{relative_path(path)}: missing initial PNG IHDR")
                return
            width, height = struct.unpack(">II", payload[:8])
            if width == 0 or height == 0:
                errors.append(f"{relative_path(path)}: PNG has zero dimensions")
                return
            saw_header = True
        if chunk_type == b"IEND":
            saw_end = True
            if length != 0 or chunk_end != len(data):
                errors.append(f"{relative_path(path)}: malformed PNG IEND")
            break
        offset = chunk_end
    if not saw_end:
        errors.append(f"{relative_path(path)}: missing PNG IEND")


def validate_jpeg_signature(path: Path, errors: list[str]) -> None:
    """Validate the required JPEG start/end markers."""
    data = path.read_bytes()
    if len(data) < 4 or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
        errors.append(f"{relative_path(path)}: invalid or truncated JPEG markers")


def validate_images(errors: list[str]) -> int:
    """Validate canonical PNG and JPEG artifacts, optionally using Pillow."""
    image_paths = sorted(S11_PLOT_DIRECTORY.glob("*.png")) + sorted(
        SMITH_CHART_DIRECTORY.glob("*.jpg")
    )
    for path in image_paths:
        if path.suffix.lower() == ".png":
            validate_png(path, errors)
        else:
            validate_jpeg_signature(path, errors)

    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        print("note: Pillow is not installed; signature-level image checks only")
    else:
        for path in image_paths:
            try:
                with Image.open(path) as image:
                    image.verify()
            except (OSError, SyntaxError, UnidentifiedImageError) as exc:
                errors.append(f"{relative_path(path)}: Pillow verification failed: {exc}")
    return len(image_paths)


def canonical_result_files() -> list[Path]:
    """Return files intended as canonical measurements or derived plots."""
    directories = (
        TOUCHSTONE_DIRECTORY,
        S11_PLOT_DIRECTORY,
        SMITH_CHART_DIRECTORY,
    )
    return sorted(
        path
        for directory in directories
        for path in directory.iterdir()
        if path.is_file()
    )


def validate_duplicates(errors: list[str]) -> None:
    """Reject byte-identical files in the canonical corpus."""
    paths_by_digest: dict[str, list[Path]] = {}
    for path in canonical_result_files():
        paths_by_digest.setdefault(file_sha256(path), []).append(path)
    for paths in paths_by_digest.values():
        if len(paths) > 1:
            joined = ", ".join(relative_path(path) for path in paths)
            errors.append(f"byte-identical canonical files: {joined}")


def validate_quarantine(errors: list[str]) -> None:
    """Ensure the known NUL-filled artifacts are preserved outside canonical data."""
    expected_paths = (
        RESULTS_DIRECTORY / "Corrupt_Artifacts" / "ANT1481H_P2.s1p.nul",
        RESULTS_DIRECTORY / "Corrupt_Artifacts" / "ANT1481H_P2.jpg.nul",
    )
    for path in expected_paths:
        if not path.is_file():
            errors.append(f"missing quarantined artifact: {relative_path(path)}")
            continue
        data = path.read_bytes()
        if not data or any(data):
            errors.append(
                f"{relative_path(path)}: quarantined artifact is not entirely NUL bytes"
            )
    canonical_names = {
        TOUCHSTONE_DIRECTORY / "ANT1481H_P2.s1p",
        SMITH_CHART_DIRECTORY / "ANT1481H_P2.jpg",
    }
    for path in canonical_names:
        if path.exists():
            errors.append(f"known corrupt artifact remains canonical: {relative_path(path)}")


def _manifest_number(
    row: dict[str, str], field: str, path_text: str, errors: list[str]
) -> float | None:
    """Read a numeric manifest field and report malformed values."""
    try:
        return float(row[field])
    except (KeyError, TypeError, ValueError):
        errors.append(f"MANIFEST.csv: {path_text}: invalid {field}")
        return None


def validate_manifest(
    touchstone_metadata: dict[str, dict[str, object]], errors: list[str]
) -> None:
    """Verify the manifest covers and fingerprints every Results file."""
    if not MANIFEST_PATH.is_file():
        errors.append("MANIFEST.csv is missing")
        return
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = set(reader.fieldnames or [])
            missing_fields = MANIFEST_FIELDS - fields
            if missing_fields:
                errors.append(
                    "MANIFEST.csv: missing columns: " + ", ".join(sorted(missing_fields))
                )
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        errors.append(f"MANIFEST.csv cannot be read: {exc}")
        return

    rows_by_path: dict[str, dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        path_text = (row.get("path") or "").strip()
        if not path_text:
            errors.append(f"MANIFEST.csv:{row_number}: empty path")
            continue
        if path_text in rows_by_path:
            errors.append(f"MANIFEST.csv:{row_number}: duplicate path {path_text}")
            continue
        rows_by_path[path_text] = row

    result_paths = {
        relative_path(path): path
        for path in RESULTS_DIRECTORY.rglob("*")
        if path.is_file()
    }
    for path_text in sorted(result_paths.keys() - rows_by_path.keys()):
        errors.append(f"MANIFEST.csv: missing Results file {path_text}")
    for path_text in sorted(rows_by_path.keys() - result_paths.keys()):
        errors.append(f"MANIFEST.csv: references missing Results file {path_text}")

    for path_text in sorted(result_paths.keys() & rows_by_path.keys()):
        path = result_paths[path_text]
        row = rows_by_path[path_text]
        if not (row.get("kind") or "").strip():
            errors.append(f"MANIFEST.csv: {path_text}: empty kind")
        if not (row.get("status") or "").strip():
            errors.append(f"MANIFEST.csv: {path_text}: empty status")
        if (row.get("sha256") or "").lower() != file_sha256(path):
            errors.append(f"MANIFEST.csv: {path_text}: stale SHA-256")
        size = _manifest_number(row, "size_bytes", path_text, errors)
        if size is not None and size != path.stat().st_size:
            errors.append(f"MANIFEST.csv: {path_text}: stale size_bytes")

        metadata = touchstone_metadata.get(path_text)
        if metadata is None:
            continue
        point_count = _manifest_number(row, "point_count", path_text, errors)
        minimum = _manifest_number(row, "raw_frequency_min", path_text, errors)
        maximum = _manifest_number(row, "raw_frequency_max", path_text, errors)
        if point_count is not None and point_count != metadata["point_count"]:
            errors.append(f"MANIFEST.csv: {path_text}: stale point_count")
        if minimum is not None and minimum != metadata["raw_frequency_min"]:
            errors.append(f"MANIFEST.csv: {path_text}: stale raw_frequency_min")
        if maximum is not None and maximum != metadata["raw_frequency_max"]:
            errors.append(f"MANIFEST.csv: {path_text}: stale raw_frequency_max")
        declared_unit = (row.get("declared_frequency_unit") or "").upper()
        if declared_unit != metadata["declared_frequency_unit"]:
            errors.append(
                f"MANIFEST.csv: {path_text}: stale declared_frequency_unit"
            )


def validate_manifest_builder(errors: list[str]) -> None:
    """Run the deterministic manifest generator in drift-check mode."""
    builder = REPOSITORY_ROOT / "tools" / "build_manifest.py"
    if not builder.is_file():
        errors.append("tools/build_manifest.py is missing")
        return
    result = subprocess.run(
        [sys.executable, str(builder), "--check"],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        errors.append(f"deterministic manifest check failed: {detail}")


def main() -> int:
    """Run all checks and return a process exit status."""
    errors: list[str] = []
    touchstone_paths = sorted(TOUCHSTONE_DIRECTORY.glob("*.s1p"))
    if len(touchstone_paths) != EXPECTED_TOUCHSTONE_COUNT:
        errors.append(
            f"canonical Touchstone count is {len(touchstone_paths)}; "
            f"expected {EXPECTED_TOUCHSTONE_COUNT}"
        )

    touchstone_metadata: dict[str, dict[str, object]] = {}
    for path in touchstone_paths:
        metadata = parse_touchstone(path, errors)
        if metadata is not None:
            touchstone_metadata[relative_path(path)] = metadata

    image_count = validate_images(errors)
    validate_quarantine(errors)
    validate_duplicates(errors)
    validate_manifest(touchstone_metadata, errors)
    validate_manifest_builder(errors)

    if errors:
        print(f"archive validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"archive validation passed: {len(touchstone_paths)} Touchstone files, "
        f"{image_count} images, fresh manifest"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
