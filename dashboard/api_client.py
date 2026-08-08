"""Thin HTTP client the dashboard uses to talk to the FastAPI backend (Step 8).
The dashboard never touches MongoDB directly -- every page is a pure consumer of
this same REST API that Phase 2's IoT gateway and Step 11's simulator also use,
so nothing here needs to change when real sensor data replaces simulated data.

`transport` lets tests substitute an httpx.MockTransport instead of hitting a
real server."""
from typing import Optional

import httpx

from dashboard.config import get_dashboard_settings


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class ApiClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, transport: Optional[httpx.BaseTransport] = None):
        base_url = base_url or get_dashboard_settings().api_base_url
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        # read timeout generous enough to survive a cold-started backend waking up
        # from idle on a free hosting tier (e.g. Render, ~50s worst case); connect
        # stays short since a refused/unreachable connection fails fast either way.
        timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=timeout, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            resp = self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(503, f"could not reach API backend: {exc}") from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise ApiError(resp.status_code, str(detail))
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    # --- auth ---
    def login(self, username: str, password: str) -> dict:
        return self._request("POST", "/auth/login", json={"username": username, "password": password})

    def get_me(self) -> dict:
        return self._request("GET", "/auth/me")

    def list_users(self) -> list[dict]:
        return self._request("GET", "/auth/users")

    def register_user(self, username: str, password: str, role: str) -> dict:
        return self._request("POST", "/auth/register", json={"username": username, "password": password, "role": role})

    # --- health ---
    def health(self) -> dict:
        return self._request("GET", "/health")

    # --- audit log ---
    def list_audit_logs(self, action: Optional[str] = None, limit: int = 100) -> list[dict]:
        params = {"limit": limit, **({"action": action} if action else {})}
        return self._request("GET", "/audit-logs", params=params)

    # --- patients ---
    def list_patients(self, status: Optional[str] = None, limit: int = 100) -> list[dict]:
        params = {"limit": limit, **({"status_filter": status} if status else {})}
        return self._request("GET", "/patients", params=params)

    def get_patient(self, patient_id: str) -> dict:
        return self._request("GET", f"/patients/{patient_id}")

    def create_patient(
        self, patient_id: str, source_dataset: str,
        age: Optional[float] = None, sex: Optional[str] = None,
        unit_admitted: Optional[str] = None, current_status: str = "active",
    ) -> dict:
        payload = {"patient_id": patient_id, "source_dataset": source_dataset, "current_status": current_status}
        if age is not None:
            payload["age"] = age
        if sex:
            payload["sex"] = sex
        if unit_admitted:
            payload["unit_admitted"] = unit_admitted
        return self._request("POST", "/patients", json=payload)

    # --- vitals ---
    def get_latest_vitals(self, patient_id: str) -> Optional[dict]:
        try:
            return self._request("GET", f"/vitals/{patient_id}/latest")
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_vitals_history(self, patient_id: str, limit: int = 1000) -> list[dict]:
        return self._request("GET", f"/vitals/{patient_id}/history", params={"limit": limit})

    # --- predictions ---
    def get_latest_prediction(self, patient_id: str) -> Optional[dict]:
        try:
            return self._request("GET", f"/predictions/{patient_id}/latest")
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_prediction_history(self, patient_id: str, limit: int = 100) -> list[dict]:
        return self._request("GET", f"/predictions/{patient_id}/history", params={"limit": limit})

    # --- shap ---
    def get_shap_by_prediction(self, prediction_id: str) -> Optional[dict]:
        try:
            return self._request("GET", f"/shap/prediction/{prediction_id}")
        except ApiError as exc:
            if exc.status_code == 404:
                return None
            raise

    def get_shap_by_patient(self, patient_id: str, limit: int = 50) -> list[dict]:
        return self._request("GET", f"/shap/patient/{patient_id}", params={"limit": limit})

    # --- alerts ---
    def list_alerts(
        self,
        patient_id: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        params = {"limit": limit}
        if patient_id is not None:
            params["patient_id"] = patient_id
        if acknowledged is not None:
            params["acknowledged"] = acknowledged
        if risk_level is not None:
            params["risk_level"] = risk_level
        return self._request("GET", "/alerts", params=params)

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> dict:
        return self._request("PATCH", f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": acknowledged_by})

    # --- reports ---
    def download_patient_report(self, patient_id: str) -> bytes:
        """Raw-bytes fetch (not the JSON-only `_request` helper) -- the API
        returns a PDF, not JSON."""
        try:
            resp = self._client.get(f"/patients/{patient_id}/report")
        except httpx.RequestError as exc:
            raise ApiError(503, f"could not reach API backend: {exc}") from exc
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise ApiError(resp.status_code, str(detail))
        return resp.content
