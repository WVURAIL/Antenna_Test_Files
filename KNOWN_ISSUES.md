# Known Issues and Corrections

This file distinguishes unresolved limitations from corrections made during archive preparation. It does not reconstruct facts that were not recorded in the repository.

## Unresolved limitations

### Quarantined corrupt artifacts

The following historical files consisted entirely of NUL bytes and could not be interpreted as Touchstone or JPEG content:

- `Results/Touchstone_Files/ANT1481H_P2.s1p`
- `Results/Smith_Charts/ANT1481H_P2.jpg`

They are retained as `Results/Corrupt_Artifacts/ANT1481H_P2.s1p.nul` and `Results/Corrupt_Artifacts/ANT1481H_P2.jpg.nul`. The `.nul` suffix prevents ordinary readers from treating them as valid data or images. No replacement measurement or acquisition backup was available in the Git history. The valid `Results/S11_Plots/S11_ANT1481H_P2.png` preserves a magnitude visualization but cannot reconstruct the missing complex S11 values.

### Plots are incomplete, derived, and historically labeled

The Touchstone measurements are canonical; the PNG and JPEG plots are convenience products. Before reclassification and quarantine, 271 Touchstone paths had no filename-matched S11 plot and 335 had no filename-matched Smith chart. Conversely, 13 S11 plots with `L1`/`L2` and `Covered`/`Uncovered` names and one `LNA_TEST_P1` Smith chart had no filename-matched Touchstone source.

Historical S11 plots label log-magnitude values as `dBm`. S-parameter log magnitude is a relative quantity and should be labeled `dB`; the legacy images were not bulk rewritten because doing so would erase their historical byte identity. Use the numeric Touchstone files for analysis.

### Acquisition metadata are incomplete

Most files have no authoritative acquisition timestamp, operator, instrument serial number, calibration record, cable/fixture characterization, weather or interference notes, firmware version, or uncertainty estimate. Git commit timestamps indicate when files were recorded in version control, not necessarily when measurements were acquired.

The original procedure named a Keysight FieldFox N9923A and described a 100 MHz–1 GHz sweep. The readable data and later script contain 10 MHz–2 GHz frequency grids. There is not enough recorded evidence to assign the discrepancy to particular acquisition sessions.

### Test files and uncertain scope

`testing_work_P1.s1p` and `testing_work_P2.s1p` are byte-equivalent test outputs after unit correction and have been moved to `Results/Test_Artifacts/`. Other names—including `labtest`, `testagain`, `Covered`, `Uncovered`, and repeated `(2)` suffixes—suggest experiments, retries, or operator tests, but the repository does not provide enough metadata to classify them reliably as production or non-production measurements. The manifest preserves and flags these names rather than guessing.

### Filename and pairing quirks

Capitalization and naming are not normalized. Examples include `ANt` versus `ANT`, spaces and parentheses, repeated suffixes, and descriptive test names. `testagain_P1` has no corresponding P2 file. Renaming these files would make historical references and hashes harder to trace, so downstream users should rely on `MANIFEST.csv` and explicit paths.

## Corrections made during archive preparation

### Touchstone frequency-unit header

The readable `.s1p` files stored numeric frequencies from 10,000,000 through 2,000,000,000 while declaring `GHz` in the Touchstone option line. The declaration was changed from `GHz` to `Hz`. Numeric frequency and complex S11 rows were left unchanged. Current and source hashes are recorded in `MANIFEST.csv` so the transformation is auditable.

This is a metadata correction, not a rescaling or remeasurement. Historical versions remain available through Git.

### ANT1444H P1 plot restoration

`Results/S11_Plots/S11_ANT1444H_P1.png` had been overwritten with a byte-identical copy of the ANT1445H P1 plot, including an ANT1445 title. Archive preparation restored the prior ANT1444H P1 image from Git blob `a3d7a8b8a3a5c72321d843f1e52948c87fce3f98` rather than generating a new scientific product.

### ANT1342H re-test plot regeneration

The legacy S11 and Smith-chart images for ANT1342H P1 and P2 were confirmed to match the measurements that predated the 2024 re-test, not the current re-test Touchstone files. The four images at their existing canonical paths were regenerated from the current ANT1342H P1/P2 Touchstone data during archive preparation. This replacement is a documented derived-product update; the superseded images remain recoverable from Git history.

### 2024 re-test provenance

The current branch restores the following commits to its ancestry:

- `e2d2d22ff00a0afedd4a7f592b11ed6eef9ec160` — “Updated re-testing”
- `17f0a75895d7c08b6a6a7b51cb56b60b8307041c` — “changed to run on linux with keysight io drivers”

Git attributes both commits to Kevin Bandura. Restoring the commits preserves the original attribution and history rather than representing the 2024 re-test files as newly authored maintenance changes. Commit history alone does not establish scientific authorship or ownership.

## Reporting additional problems

Because this repository is intended to become read-only, newly discovered issues should be documented against an immutable commit or release identifier. Preserve the affected file's path and SHA-256 hash, and do not silently replace scientific data.
