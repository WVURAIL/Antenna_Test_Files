# CHIME Antenna Test Measurements

This repository preserves one-port antenna measurements and related plots collected by the WVU Radio Astronomy Instrumentation Laboratory. It is maintained as a historical dataset, not as an active acquisition service or a supported software package.

## Archive status

The repository is undergoing final preservation checks before it is made read-only. The measurement files are the archival record; the included Python programs are legacy acquisition and plotting utilities. They have been made safer to inspect and reuse, but they were not exercised against laboratory hardware during archive preparation.

Before relying on the dataset, read [KNOWN_ISSUES.md](KNOWN_ISSUES.md), [NOTICE](NOTICE), and [LICENSE](LICENSE). No repository-wide reuse license has yet been confirmed.

## What is here

| Location | Contents | Archival role |
| --- | --- | --- |
| `Results/Touchstone_Files/` | One-port Touchstone (`.s1p`) measurements | Canonical scientific data |
| `Results/S11_Plots/` | Historical S11 magnitude plots (`.png`) | Derived convenience images |
| `Results/Smith_Charts/` | Historical Smith charts (`.jpg`) | Derived convenience images |
| `Results/Test_Artifacts/` | Files explicitly identified as test output | Non-production examples |
| `Results/Corrupt_Artifacts/` | Unreadable artifacts retained for provenance | Quarantined; do not parse as data |
| `MANIFEST.csv` | Paths, SHA-256 hashes, validation fields, and provenance notes | Machine-readable inventory |
| Root Python files | Instrument acquisition and plot-generation utilities | Legacy supporting software |
| `tools/validate_archive.py` | Offline structural and consistency checks | Archive validator |

The repository originally contained 561 Touchstone files, 303 S11 PNG plots, and 227 Smith-chart JPEGs. One Touchstone file and one JPEG were entirely NUL bytes and have been quarantined; 560 Touchstone files and 226 Smith-chart JPEGs remain structurally readable. Plot coverage is incomplete, so absence of a plot does not imply absence of a measurement.

Treat the Touchstone data as canonical. The stored plots may use legacy labels, may not cover every measurement, and in some cases may have been generated at a different point in the repository's history.

## Measurement representation

The readable `.s1p` files contain complex S11 values in real/imaginary (`RI`) form with a 50-ohm reference impedance. Their numeric frequency columns span 10 MHz through 2 GHz and are expressed in Hz. The archive-preparation correction changed their option lines from:

```text
# GHz S RI R 50.0
```

to:

```text
# Hz S RI R 50.0
```

Only that unit token was changed; the numeric rows were not rescaled or otherwise modified. The previous header would have caused a standards-compliant Touchstone reader to interpret the frequencies one billion times too high. `MANIFEST.csv` records current hashes, and where applicable the corresponding hash from commit `c58a019`, so the correction can be audited.

Filenames generally encode an antenna identifier and port (`P1` or `P2`), but historical capitalization, spacing, suffixes, and test names are not fully consistent. Use the manifest rather than inferring a complete schema from filenames.

## Historical acquisition procedure

The following summarizes the procedure that was recorded in the original 2022 README. It is retained as provenance, not as a current laboratory protocol:

1. Power on a Keysight FieldFox N9923A vector network analyzer. The notes called for equal-length, approximately three-foot Port 1 and Port 2 cables, a coaxial terminal connector, and a 50-ohm load.
2. Perform the instrument's quick S11 calibration, connecting the 50-ohm load when prompted.
3. Move the apparatus outdoors, level the reflector toward the sky, and choose a location away from obvious interference. The notes identify the grassy area between WVU's AERB and PRT as the commonly used site.
4. Attach the antenna, run `Measure_S11.py`, enter the antenna serial number when prompted, and terminate the unused port with the 50-ohm load.
5. Preserve the Touchstone output and related files in the project repositories used by the lab.

The historical notes specified a 100 MHz–1 GHz sweep, while the preserved readable files and later acquisition script use 10 MHz–2 GHz. This archive documents that discrepancy; it does not infer undocumented per-run instrument settings.

## Validate and reuse

Use a current Python environment rather than the original machine-specific setup:

```bash
python -m pip install -r requirements.txt
python tools/validate_archive.py
```

`requirements-lock.txt` records the exact Python 3.12 environment used for
the final software and archive checks on 2026-08-16. Use it when exact
reproduction is more important than selecting newer compatible releases.

The validator checks the manifest, Touchstone structure and frequency metadata, image integrity, known quarantined artifacts, and selected cross-file consistency rules. Existing measurements can also be opened with a standards-compliant Touchstone reader such as scikit-rf after installing the dependencies.

The acquisition tools expose their configuration through command-line help:

```bash
python Measure_S11.py --help
python Measure_S.py --help
python graph_Multi_Networks.py --help
python plot2networks.py --help
```

`Measure_S11.py` is the one-port antenna acquisition utility associated with this dataset. `Measure_S.py` is a separate legacy two-port/LNA utility; its presence does not establish that it produced the archived antenna files. The two plotting programs operate on user-selected Touchstone paths.

Acquiring new data requires compatible Keysight hardware, an appropriate VISA implementation and instrument driver, suitable calibrated cables and standards, and an operator-qualified procedure. VISA library and resource identifiers, sweep settings, and output locations must be supplied for the local system. Do not assume the defaults constitute a validated laboratory protocol.

## Provenance and limitations

The repository history is the best available provenance record, but it is not a complete acquisition log. Most measurements lack a separately recorded acquisition timestamp, operator, calibration identifier, environmental conditions, instrument serial number, or uncertainty estimate. Git timestamps record repository activity and must not be treated as measurement timestamps.

Two 2024 commits are important to the re-test record:

- `e2d2d22` — “Updated re-testing,” attributed by Git to Kevin Bandura.
- `17f0a758` — Linux/Keysight I/O driver adaptation, also attributed by Git to Kevin Bandura.

Those commits were restored to the current branch ancestry during archive preparation so their attribution, timestamps, and original changes remain visible. Additional contributor evidence is summarized in [CONTRIBUTORS.md](CONTRIBUTORS.md); scientific roles and author order still require confirmation.

Other limitations, including incomplete plot coverage, legacy `dBm` plot labels, orphan plots, filename quirks, and quarantined corrupt files, are recorded in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Citation

No `CITATION.cff` is supplied because the responsible creator list and author order have not been confirmed. Until a project-approved citation is available, cite the repository organization, repository title, immutable release tag or commit hash, access date, and repository URL. Do not infer individual scientific authorship from commit counts alone.

## Final archival steps and support

Before the GitHub repository is archived, the maintainer should:

1. confirm rights and the intended licenses for the data, plots, and software;
2. run `python tools/validate_archive.py` successfully on the final tree;
3. review collaborator access and repository metadata;
4. create an immutable archival tag or release with checksums and correction notes; and
5. retain an independent preservation copy.

After archival, no ongoing support, new measurements, or hardware compatibility work is promised. Questions about rights, provenance, or scientific interpretation should be directed to the repository owner rather than assumed from the legacy scripts.
