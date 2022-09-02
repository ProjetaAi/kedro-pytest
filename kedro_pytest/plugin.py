"""Pytest interface for tmpfs."""
from pathlib import Path
import pytest
from kedro_pytest import TestKedro


@pytest.fixture(scope="function")
def tkedro(tmp_path: Path) -> TestKedro:
    """Creates a temporary file system for testing."""
    return TestKedro(tmp_path)  # pragma: no cover
