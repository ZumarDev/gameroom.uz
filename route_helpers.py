from datetime import datetime, timedelta
import math

import pytz
from werkzeug.security import generate_password_hash

from app import TASHKENT_TZ


def set_user_password(user, raw_password, *, is_temp_password=False):
    password = (raw_password or "").strip()
    if not password:
        return
    user.password_hash = generate_password_hash(password)
    user.password_plain = password
    user.is_temp_password = is_temp_password


def subscription_days_left(user):
    expires_at = getattr(user, "subscription_expires_at", None)
    if not expires_at:
        return None
    now_utc = datetime.utcnow()
    seconds_left = (expires_at - now_utc).total_seconds()
    return int(math.ceil(seconds_left / 86400.0))


def utc_range_for_tashkent_date(local_date):
    start_local = TASHKENT_TZ.localize(datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0))
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
    return start_utc, end_utc


def utc_range_for_tashkent_dates(start_date_inclusive, end_date_inclusive):
    start_utc, _ = utc_range_for_tashkent_date(start_date_inclusive)
    end_utc, _ = utc_range_for_tashkent_date(end_date_inclusive + timedelta(days=1))
    return start_utc, end_utc


def utc_range_for_tashkent_month(year, month):
    start_local = TASHKENT_TZ.localize(datetime(year, month, 1, 0, 0, 0))
    if month == 12:
        end_local = TASHKENT_TZ.localize(datetime(year + 1, 1, 1, 0, 0, 0))
    else:
        end_local = TASHKENT_TZ.localize(datetime(year, month + 1, 1, 0, 0, 0))
    start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
    return start_utc, end_utc
