"""Step 9 CLI entry point: run the Plotly Dash dashboard.
Requires the FastAPI backend (scripts: uvicorn src.api.main:app) to be running
and reachable at API_BASE_URL.

Usage: python scripts/run_dashboard.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard.app import app
from dashboard.config import get_dashboard_settings

if __name__ == "__main__":
    settings = get_dashboard_settings()
    app.run(host=settings.dashboard_host, port=settings.dashboard_port, debug=False, threaded=True)
