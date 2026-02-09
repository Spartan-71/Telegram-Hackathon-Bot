import importlib
import sys
from types import SimpleNamespace

import pytest

pytest.importorskip("sqlalchemy")
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.schema import MetaData


def load_fetch_and_store(monkeypatch):
    # fetch_and_store calls Base.metadata.create_all(...) at import time.
    # Patch it to keep tests independent from a running Postgres instance.
    monkeypatch.setattr(MetaData, "create_all", lambda _self, bind=None: None)
    sys.modules.pop("fetch_and_store", None)
    return importlib.import_module("fetch_and_store")


def test_process_source_returns_only_new_hackathons(monkeypatch):
    fetch_and_store = load_fetch_and_store(monkeypatch)
    sessions = []
    upsert_results = [(object(), True), (object(), False), (object(), True)]
    hacks = [SimpleNamespace(id="1"), SimpleNamespace(id="2"), SimpleNamespace(id="3")]

    def fake_session_local():
        session = SimpleNamespace(rollback=lambda: None, close=lambda: None)
        sessions.append(session)
        return session

    def fake_upsert(_db, _hack):
        return upsert_results.pop(0)

    monkeypatch.setattr(fetch_and_store, "SessionLocal", fake_session_local)
    monkeypatch.setattr(fetch_and_store, "upsert_hackathon", fake_upsert)

    result = fetch_and_store.process_source("TestSource", lambda: hacks)

    assert [h.id for h in result] == ["1", "3"]
    assert len(sessions) == 1


def test_process_source_retries_on_database_error(monkeypatch):
    fetch_and_store = load_fetch_and_store(monkeypatch)
    attempts = {"count": 0}
    sessions = []
    sleeps = []
    hack = SimpleNamespace(id="10")

    def fake_session_local():
        session = SimpleNamespace(rollback=lambda: None, close=lambda: None)
        sessions.append(session)
        return session

    def flaky_fetch():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise SQLAlchemyError("temporary db error")
        return [hack]

    monkeypatch.setattr(fetch_and_store, "SessionLocal", fake_session_local)
    monkeypatch.setattr(fetch_and_store, "upsert_hackathon", lambda _db, _h: (object(), True))
    monkeypatch.setattr(fetch_and_store.time, "sleep", lambda seconds: sleeps.append(seconds))

    result = fetch_and_store.process_source("TestSource", flaky_fetch)

    assert [h.id for h in result] == ["10"]
    assert attempts["count"] == 2
    assert sleeps == [1]
    assert len(sessions) == 2


def test_process_source_does_not_retry_on_non_database_error(monkeypatch):
    fetch_and_store = load_fetch_and_store(monkeypatch)
    attempts = {"count": 0}

    def fake_fetch():
        attempts["count"] += 1
        raise RuntimeError("non-db failure")

    monkeypatch.setattr(
        fetch_and_store,
        "SessionLocal",
        lambda: SimpleNamespace(rollback=lambda: None, close=lambda: None),
    )

    result = fetch_and_store.process_source("TestSource", fake_fetch)

    assert result == []
    assert attempts["count"] == 1
