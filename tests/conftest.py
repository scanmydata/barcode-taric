"""Κοινό pytest setup: απομονωμένο data-dir ανά test session."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _isolated_data_dir():
    tmp = Path(tempfile.mkdtemp(prefix="barcodetaric_test_"))
    os.environ["BARCODETARIC_DATA_DIR"] = str(tmp)
    # Force settings/db να ξαναδιαβάσουν το νέο dir.
    from barcodetaric import db
    db.init_db()
    yield tmp
