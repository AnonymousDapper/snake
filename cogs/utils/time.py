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
  track.append("{} year{}".format(desc(years, 0), mult(years)))

  time = time - (years * 31536000)
  months = (time // 2592000)
  track.append("{} month{}".format(desc(months, 0), mult(months)))

  time = time - (months * 2592000)
  weeks = (time // 606461.538462)
  track.append("{} week{}".format(desc(weeks, 0), mult(weeks)))

  time = time - (weeks * 606461.538462)
  days = (time // 86400)
  track.append("{} day{}".format(desc(days, 0), mult(days)))

  time = time - (days * 86400)
  hours = (time // 3600)
  track.append("{} hour{}".format(desc(hours, 1), mult(hours)))

  time = time - (hours * 3600)
  minutes = (time // 60)
  track.append("{} minute{}".format(desc(minutes, 0), mult(minutes)))

  time = time - (minutes * 60)
  track.append("{} second{}".format(desc(time, 0), mult(time)))

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