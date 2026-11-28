from datetime import date
from load_dimensions import build_date_row

def test_christmas_row():
    assert build_date_row(date(2025, 12, 25)) == (20251225, date(2025, 12, 25), "Thursday", 2025, 4, 12, True, False), "This day is holiday"

