"""Lease term in months drives installment count and term totals."""

import pytest

from thinknxg_estate.core.charge_utils import lease_months, term_years_between


@pytest.mark.parametrize("start,end,months", [
	("2026-11-24", "2027-11-24", 12),  # ends on the anniversary (was 13 with month_diff)
	("2026-11-24", "2027-11-23", 12),  # ends the day before
	("2026-01-01", "2026-12-31", 12),
	("2026-01-01", "2026-06-30", 6),
	("2026-02-01", "2026-02-28", 1),
	("2026-01-01", "2026-01-10", 1),   # never less than one month
	("2026-01-15", "2026-03-01", 2),   # 1 month 15 days rounds up
	("2026-03-01", "2028-02-29", 24),
])
def test_lease_months(start, end, months):
	assert lease_months(start, end) == months


def test_one_year_term_is_one_year():
	assert term_years_between("2026-11-24", "2027-11-24") == 1
