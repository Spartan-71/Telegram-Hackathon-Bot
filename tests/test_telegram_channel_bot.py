import asyncio
import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
pytest.importorskip("sqlalchemy")
from sqlalchemy.sql.schema import MetaData

pytest.importorskip("telegram")


def load_channel_bot_module():
    # telegram-channel-bot imports fetch_and_store, which runs create_all at import time.
    # Patch it so tests do not require a live database server.
    sys.modules.pop("fetch_and_store", None)
    monkeypatched_create_all = lambda _self, bind=None: None
    original_create_all = MetaData.create_all
    MetaData.create_all = monkeypatched_create_all

    module_path = Path(__file__).resolve().parents[1] / "telegram-channel-bot.py"
    spec = importlib.util.spec_from_file_location("telegram_channel_bot", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        MetaData.create_all = original_create_all


def make_hackathon(
    banner_url="https://example.com/banner.png",
    prize_pool="$5,000",
    team_size="1-4",
    eligibility="Students",
):
    return SimpleNamespace(
        title="Global Hack 2026",
        start_date=date(2026, 4, 10),
        end_date=date(2026, 4, 12),
        location="Remote",
        mode="Online",
        status="Open",
        source="Devpost",
        prize_pool=prize_pool,
        team_size=team_size,
        eligibility=eligibility,
        banner_url=banner_url,
        url="https://example.com/hack",
    )


def test_format_hackathon_message_contains_expected_fields(monkeypatch):
    module = load_channel_bot_module()
    monkeypatch.setattr("random.choice", lambda emojis: emojis[0])
    hack = make_hackathon()

    text, photo_url, hackathon_url = module.format_hackathon_message(hack)

    assert text.startswith("🎉 <b>Global Hack 2026</b>")
    assert "<b>Duration:</b> April 10 - April 12, 2026" in text
    assert "<b>Prizes:</b>" in text
    assert "<b>Team Size:</b> 1-4" in text
    assert "<b>Eligibility:</b> Students" in text
    assert photo_url == "https://example.com/banner.png"
    assert hackathon_url == "https://example.com/hack"


def test_format_hackathon_message_omits_optional_sections(monkeypatch):
    module = load_channel_bot_module()
    monkeypatch.setattr("random.choice", lambda emojis: emojis[0])
    hack = make_hackathon(banner_url=None, prize_pool=None, team_size=None, eligibility=None)

    text, photo_url, _ = module.format_hackathon_message(hack)

    assert "<b>Prizes:</b>" not in text
    assert "<b>Team Size:</b>" not in text
    assert "<b>Eligibility:</b>" not in text
    assert photo_url is None


def test_send_to_channel_uses_photo_when_available(monkeypatch):
    module = load_channel_bot_module()
    bot = AsyncMock()
    hack = make_hackathon()

    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    asyncio.run(module.send_to_channel(bot, "@hackradar", [hack]))

    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_not_awaited()
    call_kwargs = bot.send_photo.await_args.kwargs
    assert call_kwargs["chat_id"] == "@hackradar"
    assert call_kwargs["photo"] == "https://example.com/banner.png"


def test_send_to_channel_returns_early_for_empty_list():
    module = load_channel_bot_module()
    bot = AsyncMock()

    asyncio.run(module.send_to_channel(bot, "@hackradar", []))

    bot.send_photo.assert_not_awaited()
    bot.send_message.assert_not_awaited()
