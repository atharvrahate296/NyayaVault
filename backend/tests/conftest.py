import os
import pytest
from httpx import AsyncClient, ASGITransport

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.exit(
        "TEST_DATABASE_URL must point to an isolated PostgreSQL database; refusing to use backend/.env.",
        returncode=2,
    )
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.config.settings import settings
from app.db import session as db_session
from app.main import app
from app.db.init_db import init_db_schema, seed_db


@pytest.fixture(autouse=True)
async def initialize_test_database():
    try:
        await init_db_schema()
        async with db_session.AsyncSessionLocal() as session:
            await seed_db(session)
    except Exception as e:
        pytest.fail(f"Test database is not accessible or could not be initialized: {e}")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
