"""Static safety checks for the no-build frontend.

The frontend is plain ES modules without a JS test runner, so these tests pin
the security/interaction contracts that previously regressed in review.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_school_options_do_not_interpolate_remote_names_with_inner_html():
    """Remote school names must not be string-interpolated into option HTML."""
    source = read_frontend("frontend/assets/pages/accounts.js")

    assert '<option value="${s.school_id}">${s.school_name}' not in source
    assert "createElement(\"option\")" in source
    assert ".textContent" in source


def test_terminal_run_button_uses_single_click_handler():
    """After terminal states, the run button must not retain cancel + onclick handlers."""
    source = read_frontend("frontend/assets/pages/run-active.js")

    assert "$cancel.onclick" not in source
    assert "let terminalAction" in source
