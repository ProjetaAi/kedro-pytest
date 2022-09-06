"""TestKedro tests."""
from pathlib import Path
from kedro.framework.session import KedroSession
from kedro_pytest.test_kedro import TestKedro


def test_session(tkedro: TestKedro):
    """Tests if a session can be instantiated using TestKedro."""
    tkedro.new('proj')
    with KedroSession.create('proj', Path.cwd()) as session:
        assert session is not None
