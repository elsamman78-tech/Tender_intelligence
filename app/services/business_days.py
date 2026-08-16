from datetime import date, timedelta

FRI_SAT = {'egypt','saudi arabia','saudi','ksa','libya','bangladesh'}
SAT_SUN = set()


def _holiday_dates(country: str, start: date, end: date) -> set[date]:
    try:
        import holidays  # optional, free/open-source package
        aliases = {
            'egypt':'EG', 'saudi arabia':'SA', 'saudi':'SA', 'ksa':'SA',
            'united arab emirates':'AE', 'uae':'AE', 'libya':'LY',
            'bangladesh':'BD', 'india':'IN', 'iran':'IR'
        }
        code = aliases.get((country or '').strip().lower())
        if not code:
            return set()
        years = list(range(start.year, end.year + 1))
        cal = holidays.country_holidays(code, years=years)
        return {d for d in cal.keys() if start <= d <= end}
    except Exception:
        return set()


def weekend_days(country: str) -> set[int]:
    # Python weekday: Monday=0 ... Sunday=6
    return {4,5} if (country or '').strip().lower() in FRI_SAT else {5,6}


def calculate_business_days(country: str, start: date, deadline: date) -> int:
    if deadline <= start:
        return 0
    weekends = weekend_days(country)
    holiday_set = _holiday_dates(country, start, deadline)
    cur = start + timedelta(days=1)
    total = 0
    while cur <= deadline:
        if cur.weekday() not in weekends and cur not in holiday_set:
            total += 1
        cur += timedelta(days=1)
    return total


def urgency(days: int | None) -> str:
    if days is None:
        return 'UNKNOWN'
    if days <= 0:
        return 'EXPIRED'
    if days <= 4:
        return 'CRITICAL'
    if days <= 9:
        return 'URGENT'
    if days <= 14:
        return 'ATTENTION'
    return 'NORMAL'
