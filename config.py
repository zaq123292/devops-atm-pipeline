import os
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    DATABASE = os.environ.get("DATABASE_URL", "atm.db")
    DAILY_WITHDRAWAL_LIMIT = int(os.environ.get("DAILY_WITHDRAWAL_LIMIT", "100000"))
class TestConfig(Config):
    TESTING = True
    # SQLite's :memory: is connection-local; a test client opens more than one
    # request connection, so use an isolated local file for integration tests.
    DATABASE = "test_atm.db"
    DAILY_WITHDRAWAL_LIMIT = 10_000_000
