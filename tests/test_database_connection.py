import os
from pathlib import Path

import pytest
from sqlalchemy import text


def test_database_connection() -> None:
    if "DATABASE_URL" not in os.environ and not Path(".env").is_file():
        pytest.skip("DATABASE_URL is not configured locally")

    from app.db.session import engine

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
