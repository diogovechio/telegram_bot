# Internal
from datetime import datetime, timedelta, timezone

# Project
from pedro.brain.constants.constants import DATE_FORMAT, HOUR_FORMAT


class DatetimeManager:
    def __init__(self):
        self.gmt3_offset = -3

    def now(self) -> datetime:
        utc_now = datetime.now(timezone.utc)

        gmt3_timezone = timezone(timedelta(hours=self.gmt3_offset))
        gmt3_now = utc_now.astimezone(gmt3_timezone)

        return gmt3_now

    def get_current_date_str(self, format_str: str = DATE_FORMAT) -> str:
        return self.now().strftime(format_str)

    def get_current_time_str(self, format_str: str = HOUR_FORMAT) -> str:
        return self.now().strftime(format_str)
