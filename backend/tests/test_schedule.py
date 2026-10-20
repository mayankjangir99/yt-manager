from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def test_timezone_available():
    assert datetime.now(ZoneInfo("Asia/Kolkata")).tzinfo is not None
