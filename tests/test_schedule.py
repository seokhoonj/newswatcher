import pytest

from newswatch.errors import ScheduleError
from newswatch.schedule import DEFAULT_INTERVAL_MINUTES, parse_interval


def test_parse_interval_accepts_plain_minutes():
    assert parse_interval("15") == 15
    assert parse_interval("30m") == 30
    assert parse_interval("1h") == 60


def test_parse_interval_rejects_zero_and_garbage():
    with pytest.raises(ScheduleError):
        parse_interval("0")
    with pytest.raises(ScheduleError):
        parse_interval("soon")


def test_default_interval_is_positive():
    assert DEFAULT_INTERVAL_MINUTES >= 1
