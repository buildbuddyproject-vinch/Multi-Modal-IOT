# Dataset Download Guide

Both datasets are already present in this project (see below for verified locations/sizes). This guide is for reproducing the setup on another machine.

## 1. PhysioNet/Computing in Cardiology Challenge 2019 (Sepsis)

- **Source**: https://physionet.org/content/challenge-2019/1.0.0/
- **License**: Open Data Commons Open Database License (ODbL) v1.0 — see `physionet/challenge-2019-1.0.0/LICENSE.txt`
- **Download** (from the PhysioNet page's "Files" section, or via `wget`):
  ```
  wget -r -N -c -np https://physionet.org/files/challenge-2019/1.0.0/
  ```
- **Expected structure** after download:
  ```
  physionet/challenge-2019-1.0.0/
  └── training/
      ├── training_setA/   (20,336 patient .psv files: p000001.psv ... )
      └── training_setB/   (20,000 patient .psv files: p100001.psv ... )
  ```
- **Integrity check**: `SHA256SUMS.txt` is included in the dataset root; verify with `sha256sum -c SHA256SUMS.txt` (Linux/WSL) or an equivalent PowerShell `Get-FileHash` loop on Windows.
- **Format**: pipe-separated (`|`), one row per ICU hour, 40 columns (34 clinical channels + 5 demographic/admin fields + `SepsisLabel`). See `src/data/schema.py` for the canonical column list.

## 2. MIMIC-IV Clinical Database Demo v2.2

- **Source**: https://physionet.org/content/mimic-iv-demo/2.2/
- **License**: ODbL v1.0 — see `mimic-iv-clinical-database-demo-2.2/LICENSE.txt`. Unlike the full MIMIC-IV database, the demo subset (100 patients) does **not** require PhysioNet credentialing/CITI training — it's freely downloadable.
- **Download**:
  ```
  wget -r -N -c -np https://physionet.org/files/mimic-iv-demo/2.2/
  ```
- **Expected structure**:
  ```
  mimic-iv-clinical-database-demo-2.2/
  ├── hosp/   (patients.csv, admissions.csv, labevents.csv, ...)
  ├── icu/    (icustays.csv, chartevents.csv, d_items.csv, ...)
  └── SHA256SUMS.txt
  ```
- **Integrity check**: same `SHA256SUMS.txt` pattern as above.

## 3. MIMIC-III

Out of scope for this build (see Step 1 decision) — only MIMIC-IV Demo and PhysioNet 2019 are used. If reintroduced later, MIMIC-III requires PhysioNet credentialed access (CITI training + data use agreement), unlike the MIMIC-IV demo subset.

## 4. What NOT to Do

- Do not move or rename the two dataset folders — `src/config/settings.py` resolves them by path from `.env` (`PHYSIONET_RAW_PATH`, `MIMIC_IV_RAW_PATH`), defaulting to their current locations at the project root.
- Do not commit raw dataset files to git — add them to `.gitignore` if version control is initialized (they total >300MB and are publicly re-downloadable).
