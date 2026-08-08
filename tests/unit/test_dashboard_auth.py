import pytest
from flask import Flask

from dashboard import auth

_app = Flask(__name__)
_app.secret_key = "test-secret"


@pytest.fixture
def request_ctx():
    with _app.test_request_context("/"):
        yield


def test_not_authenticated_by_default(request_ctx):
    assert auth.is_authenticated() is False
    assert auth.current_token() is None


def test_log_in_populates_session(request_ctx):
    auth.log_in("jwt-token", "dr_smith", "clinician")
    assert auth.is_authenticated() is True
    assert auth.current_token() == "jwt-token"
    assert auth.current_username() == "dr_smith"
    assert auth.current_role() == "clinician"
    assert auth.is_admin() is False


def test_admin_role_detected(request_ctx):
    auth.log_in("jwt-token", "admin", "admin")
    assert auth.is_admin() is True


def test_log_out_clears_session(request_ctx):
    auth.log_in("jwt-token", "dr_smith", "clinician")
    auth.log_out()
    assert auth.is_authenticated() is False
    assert auth.current_username() is None
