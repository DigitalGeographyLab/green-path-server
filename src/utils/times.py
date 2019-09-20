from datetime import datetime, date, time, timedelta

def get_next_weekday(skipdays=None, weekend_days=0):
    weekday = datetime.weekday(date.today())
    if (weekday == 4):
        weekend_days = 3
    if (weekday == 5):
        weekend_days = 2
    if (weekday == 6):
        weekend_days = 1
    next_weekday = date.today() + timedelta(days=weekend_days + skipdays)
    return next_weekday

def get_next_saturday():
    weekday = datetime.weekday(date.today())
    skipdays = 5 - weekday
    next_saturday = date.today() + timedelta(days=skipdays)
    return next_saturday

def get_next_sunday():
    weekday = datetime.weekday(date.today())
    skipdays = 6 - weekday
    next_saturday = date.today() + timedelta(days=skipdays)
    return next_saturday

def get_datetime(day, hh, mm):
    return datetime.combine(day, time(hh, mm))

def get_next_weekday_datetime(hh, mm, skipdays=1):
    next_weekday_datetime = datetime.combine(get_next_weekday(skipdays), time(hh, mm))
    return next_weekday_datetime
