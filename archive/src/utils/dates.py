from datetime import datetime, timedelta


def date_range(start_date, end_date):
    """
    Yields dates from start_date to end_date inclusive.

    Dates should be strings like:
    20260601
    """
    start = datetime.strptime(start_date, "%Y%m%d").date()
    end = datetime.strptime(end_date, "%Y%m%d").date()

    current = start

    while current <= end:
        yield current.strftime("%Y%m%d")
        current += timedelta(days=1)