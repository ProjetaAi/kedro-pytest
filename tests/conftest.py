"""Test setup for kedro_pytest."""
from kedro_pytest.plugin import tkedro  # noqa: F401
import pytest
from kedro_pytest.test_kedro import TestKedro


@pytest.fixture(autouse=True)
def add_to_doctests(doctest_namespace: dict, tkedro: TestKedro):  # noqa: F811
    """Add the kedro fixture to the doctest namespace."""
    doctest_namespace["kedro"] = tkedro
