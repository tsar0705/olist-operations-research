from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _nav_radio(at):
    assert at.sidebar.radio
    return at.sidebar.radio[0]


def test_streamlit_app_starts_and_exposes_release_navigation():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    assert not at.exception

    radio = _nav_radio(at)
    assert "Release & Architecture Status" in radio.options


def test_streamlit_release_page_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py")).run(timeout=30)
    radio = _nav_radio(at)

    radio.set_value("Release & Architecture Status")
    at.run(timeout=30)

    assert not at.exception
