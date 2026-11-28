from datetime import date
from load_dimensions import build_date_row
import pytest


@pytest.mark.parametrize("d, expected", [
    (date(2025, 12, 25), (20251225, date(2025, 12, 25), "Thursday", 2025, 4, 12, True, False)),
    (date(2025, 1, 4), (20250104, date(2025, 1, 4), "Saturday", 2025, 1, 1, False, True)),
    (date(2025, 1, 5), (20250105, date(2025, 1, 5), "Sunday", 2025, 1, 1, False, True)),
], ids=["christmas", "saturday", "sunday"])
def test_build_date_row(d, expected):
    assert build_date_row(d) == expected