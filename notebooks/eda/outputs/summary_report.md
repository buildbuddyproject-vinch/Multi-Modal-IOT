# EDA Summary Report (Step 3)

## PhysioNet 2019 (training/validation/testing source)
- Rows analyzed: 1552210
- Patients analyzed: 40336
- Patient-level sepsis prevalence: 0.0727
- Channel with most missing data: Bilirubin_direct
- Strongest correlated pair: Bilirubin_direct / Bilirubin_total
- Most important channel (RandomForest baseline): Temp
- Example patients plotted: ['p000009', 'p000011', 'p000001', 'p000002']

## MIMIC-IV Demo (schema/dashboard testing source)
- Patients: 100
- Channels with real coverage: 33

See stats/*.csv and plots/*.png for full detail.