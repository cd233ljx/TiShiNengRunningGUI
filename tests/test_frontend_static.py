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


def test_docs_route_and_top_nav_are_registered():
    """DOCS must be reachable as an in-app route from the top navigation."""
    index = read_frontend("frontend/index.html")
    app = read_frontend("frontend/assets/app.js")

    assert '<a href="#/docs" data-nav>DOCS</a>' in index
    assert '"/docs":' in app
    assert 'import("./pages/docs.js")' in app


def test_disclaimer_gate_uses_versioned_local_storage_contract():
    """First-run disclaimer must block app rendering until current version is accepted."""
    app = read_frontend("frontend/assets/app.js")
    disclaimer = read_frontend("frontend/assets/disclaimer.js")

    assert 'DISCLAIMER_VERSION = "1"' in disclaimer
    assert 'ts_disclaimer_version' in app
    assert 'ts_disclaimer_accepted_at' in app
    assert 'renderDisclaimerGate' in app
    assert '我已阅读并同意' in app
    assert '暂不使用' in app


def test_docs_onboarding_emphasizes_phone_logout_warning():
    """The first-run Docs prompt must warn users not to log in on phone recently."""
    app = read_frontend("frontend/assets/app.js")
    docs = read_frontend("frontend/assets/pages/docs.js")
    readme = read_frontend("README.md")

    required = "最近一段时间内不要再次登录手机端"
    assert required in app
    assert required in docs
    assert required in readme
    assert "ts_docs_onboarding_seen" in app
    assert "打开 DOCS" in app


def test_settings_and_docs_reuse_shared_disclaimer_copy():
    """Disclaimer copy should live in one module and be reused by gate/settings/docs."""
    settings = read_frontend("frontend/assets/pages/settings.js")
    docs = read_frontend("frontend/assets/pages/docs.js")
    disclaimer = read_frontend("frontend/assets/disclaimer.js")

    assert 'from "../disclaimer.js"' in settings
    assert 'from "../disclaimer.js"' in docs
    assert "DISCLAIMER_ITEMS" in disclaimer
    assert "renderDisclaimerNotice" in disclaimer


def test_readme_is_gui_first_and_keeps_developer_commands():
    """README should be useful to GUI users first while retaining developer workflows."""
    readme = read_frontend("README.md")

    assert "GUI 快速开始" in readme
    assert "TiShiNeng.exe" in readme
    assert "DOCS" in readme
    assert "WebView2 Runtime" in readme
    assert "python gui_app.py --dev" in readme
    assert "python -m pytest tests/ -q" in readme
    assert "python -m PyInstaller tishineng.spec --clean --noconfirm" in readme


def test_disclaimer_acceptance_preserves_existing_hash():
    """Accepting the disclaimer must not clobber deep links or query params."""
    app = read_frontend("frontend/assets/app.js")

    assert 'location.hash !== "#/home"' not in app
    assert "renderAfterDisclaimerAccepted" in app


def test_safe_local_get_prefers_memory_fallback_over_stale_local_storage():
    """Memory fallback writes must shadow stale localStorage values after setItem fails."""
    app = read_frontend("frontend/assets/app.js")
    safe_get = app[app.index("function safeLocalGet"):app.index("function safeLocalSet")]

    assert "if (memoryLocalStorage.has(key))" in safe_get
    assert safe_get.index("if (memoryLocalStorage.has(key))") < safe_get.index("localStorage.getItem(key)")


def test_docs_onboarding_clears_on_route_leave_and_marks_seen_after_docs_render():
    """Docs onboarding should clear off-home and only mark seen after DOCS renders."""
    app = read_frontend("frontend/assets/app.js")
    onboarding = app[app.index("function maybeShowDocsOnboarding"):app.index("window.addEventListener")]
    off_home_branch = onboarding[
        onboarding.index('if (path !== "/home")'):onboarding.index("if (!pendingDocsOnboarding")
    ]
    open_docs_handler = onboarding[
        onboarding.index('document.getElementById("open-docs").addEventListener("click"'):
        onboarding.index('document.getElementById("skip-docs")')
    ]

    assert "clearDocsOnboarding" in app
    assert "pendingDocsSeenAfterDocsOpen" in app
    assert "clearDocsOnboarding();" in off_home_branch
    assert "markDocsOnboardingSeen();" not in open_docs_handler

def test_docs_toc_does_not_conflict_with_hash_router():
    """Docs TOC links must not be mistaken for top-level hash routes."""
    docs = read_frontend("frontend/assets/pages/docs.js")

    assert 'href="#${id}"' not in docs
    assert 'href="#before"' not in docs
    assert "data-doc-anchor" in docs
    assert "preventDefault()" in docs
    assert "scrollIntoView" in docs
