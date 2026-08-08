import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError, createPatient } from "../api/client";
import AlertBanner from "../components/AlertBanner";

const SOURCE_OPTIONS = [
  { label: "Live / manually admitted", value: "live" },
  { label: "PhysioNet 2019", value: "physionet_2019" },
  { label: "MIMIC-IV (demo)", value: "mimic_iv_demo" },
];

export default function AdmitPatient() {
  const { token } = useAuth();
  const [patientId, setPatientId] = useState("");
  const [sourceDataset, setSourceDataset] = useState("live");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [unitAdmitted, setUnitAdmitted] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!patientId.trim()) {
      setFeedback({ color: "warning", message: "Patient ID is required." });
      return;
    }
    setSubmitting(true);
    setFeedback(null);
    try {
      const patient = await createPatient(token, {
        patientId: patientId.trim(),
        sourceDataset,
        age: age === "" ? null : age,
        sex: sex || null,
        unitAdmitted: unitAdmitted || null,
      });
      setFeedback({ color: "success", patient });
      setPatientId("");
    } catch (err) {
      const detail = err instanceof ApiError && err.statusCode === 409 ? "A patient with that ID already exists." : err.message;
      setFeedback({ color: "danger", message: `Could not admit patient: ${detail}` });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="icu-page-header">
        <h2><i className="fa-solid fa-user-plus" />Admit Patient</h2>
        <div className="icu-page-subtitle">Every patient belongs to your account only — other clinicians and admins won&apos;t see this patient.</div>
      </div>

      <div className="icu-card" style={{ padding: "1.5rem" }}>
        <form onSubmit={handleSubmit}>
          <div className="row">
            <div className="col-md-6 mb-3">
              <label className="form-label" htmlFor="admit-patient-id">Patient ID</label>
              <input
                id="admit-patient-id"
                className="form-control"
                placeholder="e.g. p_jane_doe"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
              />
            </div>
            <div className="col-md-6 mb-3">
              <label className="form-label" htmlFor="admit-patient-source">Source</label>
              <select id="admit-patient-source" className="form-select" value={sourceDataset} onChange={(e) => setSourceDataset(e.target.value)}>
                {SOURCE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="row">
            <div className="col-md-4 mb-3">
              <label className="form-label" htmlFor="admit-patient-age">Age</label>
              <input id="admit-patient-age" className="form-control" type="number" min="0" max="130" value={age} onChange={(e) => setAge(e.target.value)} />
            </div>
            <div className="col-md-4 mb-3">
              <label className="form-label" htmlFor="admit-patient-sex">Sex</label>
              <select id="admit-patient-sex" className="form-select" value={sex} onChange={(e) => setSex(e.target.value)}>
                <option value="">Select...</option>
                <option value="M">Male</option>
                <option value="F">Female</option>
              </select>
            </div>
            <div className="col-md-4 mb-3">
              <label className="form-label" htmlFor="admit-patient-unit">Unit Admitted</label>
              <input id="admit-patient-unit" className="form-control" placeholder="e.g. MICU" value={unitAdmitted} onChange={(e) => setUnitAdmitted(e.target.value)} />
            </div>
          </div>

          <button type="submit" className="btn btn-info" disabled={submitting}>
            <i className="fa-solid fa-user-plus me-2" />
            {submitting ? "Admitting..." : "Admit Patient"}
          </button>

          {feedback ? (
            <div className="mt-3">
              {feedback.color === "success" ? (
                <AlertBanner color="success">
                  <i className="fa-solid fa-circle-check me-2" />
                  Admitted patient &apos;{feedback.patient.patient_id}&apos;.{" "}
                  <Link to={`/patients/${feedback.patient.patient_id}`} className="alert-link">View patient →</Link>
                </AlertBanner>
              ) : (
                <AlertBanner color={feedback.color}>{feedback.message}</AlertBanner>
              )}
            </div>
          ) : null}
        </form>
      </div>
    </div>
  );
}
