from streamlit.testing.v1 import AppTest
from src.config import ROOT


def test_app_renders_and_new_conversation_resets_session():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45).run()
    assert not app.exception
    assert app.title[0].value if app.title else any("work through" in item.value for item in app.markdown)
    assert len(app.tabs) == 3
    before = app.session_state["session_id"]
    button = next(b for b in app.button if "New conversation" in b.label)
    button.click().run()
    assert not app.exception
    assert app.session_state["session_id"] != before
