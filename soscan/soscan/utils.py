import datetime

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""


def dtnow():
    return datetime.datetime.now(datetime.timezone.utc)


def datetimeToJsonStr(dt):
    if dt is None:
        return None
    return dt.strftime(JSON_TIME_FORMAT)
