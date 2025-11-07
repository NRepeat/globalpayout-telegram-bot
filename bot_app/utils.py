import datetime


def format_unix_timestamp(unix_ms: int) -> str:
    # Convert milliseconds to seconds by dividing by 1000
    unix_seconds = unix_ms / 1000
    # Convert to datetime object
    dt = datetime.datetime.fromtimestamp(unix_seconds)
    # Format to match the desired output
    formatted_date = dt.strftime("%a %b %d %Y %H:%M:%S")
    return formatted_date
