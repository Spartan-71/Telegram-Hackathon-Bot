from datetime import date

import pytest

pytest.importorskip("pydantic")
from backend.schemas import Hackathon


def test_hackathon_splits_and_normalizes_tags_from_string():
    hack = Hackathon(
        id="abc-1",
        title="AI Sprint",
        start_date=date(2026, 2, 10),
        end_date=date(2026, 2, 12),
        location="Remote",
        url="https://example.com",
        mode="Online",
        status="Open",
        source="Devpost",
        tags="AI, Web3 ,  Cloud  ",
    )

    assert hack.tags == ["ai", "web3", "cloud"]


def test_hackathon_keeps_tags_list_as_is():
    hack = Hackathon(
        id="abc-2",
        title="Build Night",
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 3),
        location="SF",
        url="https://example.com/h2",
        mode="Hybrid",
        status="Open",
        source="MLH",
        tags=["ml", "iot"],
    )

    assert hack.tags == ["ml", "iot"]
