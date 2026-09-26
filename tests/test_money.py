import pytest

from app.money import to_minor_units


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("-19.99", -1999), ("1000.50", 100050), ("0", 0), ("150.00", 15000)],
)
def test_to_minor_units(amount, expected):
    assert to_minor_units(amount) == expected
