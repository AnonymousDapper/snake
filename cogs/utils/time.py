from datetime import timedelta

time_format = "%a %B %d, %Y, %H:%M:%S"
utc_offset = timedelta(hours=-5)

def get_elapsed_time(date_1, date_2):
    delta = abs(date_2 - date_1)
    time = int(delta.total_seconds())
    track = []
    desc = lambda n, h: ('a' if n == 1 else str(int(n))) + ('n' if h == 1 and n == 1 else '') + ''
    mult = lambda n: 's' if n > 1 or n == 0 else ''
    years = (time // 31536000)
    track.append(f"{desc(years, 0)} year{mult(years)}")

    time = time - (years * 31536000)
    months = (time // 2592000)
    track.append(f"{desc(months, 0)} month{mult(months)}")

    time = time - (months * 2592000)
    weeks = (time // 606461.538462)
    track.append(f"{desc(weeks, 0)} week{mult(weeks)}")

    time = time - (weeks * 606461.538462)
    days = (time // 86400)
    track.append(f"{desc(days, 0)} day{mult(days)}")

    time = time - (days * 86400)
    hours = (time // 3600)
    track.append(f"{desc(hours, 1)} hours{mult(hours)}")

    time = time - (hours * 3600)
    minutes = (time // 60)
    track.append(f"{desc(minutes, 0)} minutes{mult(minutes)}")

    time = time - (minutes * 60)
    track.append(f"{desc(time, 0)} second{mult(time)}")

    return ", ".join(list(filter(lambda e: not e.startswith("0 "), track)))

def get_ping_time(time_1, time_2):
    elapsed_milliseconds = abs(time_1 - time_2).microseconds / 1000
    if elapsed_milliseconds < 1000:
        format_sep = "{:d}ms"
        elapsed_milliseconds = int(elapsed_milliseconds)
    elif elapsed_milliseconds > 1000:
        format_sep = "{:.2f}s"
        elapsed_milliseconds = elapsed_milliseconds / 1000
    elif elapsed_milliseconds > 60000:
        format_sep = "{:.2f}m"
        elapsed_milliseconds = elapsed_milliseconds / 60000
    return format_sep.format(elapsed_milliseconds)