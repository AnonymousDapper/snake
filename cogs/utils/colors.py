""" ANSI Color codes module """
class _Text:
  """
  ANSI text color codes for easy formatting
  """

  black = '\033[30m'
  red = '\033[31m'
  green = '\033[32m'
  yellow = '\033[33m'
  blue = '\033[34m'
  magenta = '\033[35m'
  cyan = '\033[36m'
  white = '\033[37m'
  default = '\033[37m'

class _Background:
  """
  ANSI background color codes for easy formatting
  """
  black = '\033[40m'
  red = '\033[41m'
  green = '\033[42m'
  yellow = '\033[43m'
  blue = '\033[44m'
  magenta = '\033[45m'
  cyan = '\033[46m'
  white = '\033[47m'
  default = '\033[40m'

class _Attributes:
  """
  ANSI console attribute codes for easy formatting
  """
  off = '\033[0m'
  bold = '\033[1m'
  score = '\033[4m'
  blink = '\033[5m'
  reverse = '\033[7m'
  hidden = '\033[8m'


def paint(text, color):
  if hasattr(_Text, color):
    return "{}{}{}".format(getattr(_Text, color), text, _Attributes.off)
  raise ValueError("invalid color name: {}".format(color))

def back(text, color):
  if hasattr(_Background, color):
    return "{}{}{}".format(getattr(_Background, color), text, _Attributes.off)
  raise ValueError("invalid background color name: {}".format(color))

def attr(text, attribute):
  if hasattr(_Attributes, attribute):
    return "{}{}{}".format(getattr(_Attributes, attribute), text, _Attributes.off)
  raise ValueError("invalid attribute name: {}".format(attribute))
