from datetime import datetime
from zoneinfo import ZoneInfo


def today_in_new_york():
    return datetime.now(ZoneInfo("America/New_York")).date()
