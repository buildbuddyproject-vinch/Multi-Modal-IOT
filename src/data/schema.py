"""Canonical vitals/labs schema shared by every data source (PhysioNet, MIMIC-IV, and,
in Phase 2, live IoT sensors). This is the schema referenced by
docs/architecture/database_design.md (`vitals.channels`) and
docs/architecture/mqtt_architecture.md (`icu/{patient_id}/vitals` payload).

Any loader (PhysioNet, MIMIC-IV, or a future ESP32 gateway) must ultimately produce
rows shaped like: patient_id, a time index, VITAL_CHANNELS + LAB_CHANNELS (float or
NaN), so the rest of the pipeline never needs to know where the data came from.
"""

VITAL_CHANNELS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2"]

LAB_CHANNELS = [
    "BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2", "AST", "BUN",
    "Alkalinephos", "Calcium", "Chloride", "Creatinine", "Bilirubin_direct",
    "Glucose", "Lactate", "Magnesium", "Phosphate", "Potassium",
    "Bilirubin_total", "TroponinI", "Hct", "Hgb", "PTT", "WBC",
    "Fibrinogen", "Platelets",
]

CLINICAL_CHANNELS = VITAL_CHANNELS + LAB_CHANNELS  # 34 per-timestep numeric channels

DEMOGRAPHIC_FEATURES = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]

TIME_COLUMN = "ICULOS"       # integer ICU length-of-stay in hours, the model's time index
LABEL_COLUMN = "SepsisLabel"  # 1 if sepsis onset predicted within the challenge's 6h window
PATIENT_ID_COLUMN = "patient_id"

ALL_COLUMNS = [PATIENT_ID_COLUMN, TIME_COLUMN] + CLINICAL_CHANNELS + DEMOGRAPHIC_FEATURES + [LABEL_COLUMN]

assert len(CLINICAL_CHANNELS) == 34
