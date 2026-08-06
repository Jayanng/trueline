import os

import pytest


@pytest.fixture(scope="session")
def e2e_enabled():
    if os.getenv("TRUELINE_E2E") != "1":
        pytest.skip("set TRUELINE_E2E=1 to run against the live quickstart")
    return True
