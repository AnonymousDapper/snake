""" ANSI Color codes module """
class _Text:
  """
  ANSI text color codes for easy formatting
  """

  black = "\033[30m"
  red = "\033[31m"
  green = "\033[32m"
  yellow = "\033[33m"
  blue = "\033[34m"
  magenta = "\033[35m"
  cyan = "\033[36m"
  white = "\033[37m"

  b_black = "\033[90m"
  b_red = "\033[91m"
  b_green = "\033[92m"
  b_yellow = "\033[93m"
  b_blue = "\033[94m"
  b_magenta = "\033[95m"
  b_cyan = "\033[96m"
  b_white = "\033[97m"
  default = "\033[37m"

class _Background:
  """
  ANSI background color codes for easy formatting
  """
  black = "\033[40m"
  red = "\033[41m"
  green = "\033[42m"
  yellow = "\033[43m"
  blue = "\033[44m"
  magenta = "\033[45m"
  cyan = "\033[46m"
  white = "\033[47m"
  default = "\033[40m"
  b_black = "\033[100m"
  b_red = "\033[101m"
  b_green = "\033[102m"
  b_yellow = "\033[103m"
  b_blue = "\033[104m"
  b_magenta = "\033[105m"
  b_cyan = "\033[106m"
  b_white = "\033[107m"

class _Attributes:
  """
  ANSI console attribute codes for easy formatting
  """
  off = "\033[0m"
  bold = "\033[1m"
  score = "\033[4m"
  blink = "\033[5m"
  reverse = "\033[7m"
  hidden = "\033[8m"


def paint(text, color):
  if hasattr(_Text, color):
    return f"{getattr(_Text, color)}{text}{_Attributes.off}"
  raise ValueError("invalid color name: {color}")

def back(text, color):
  if hasattr(_Background, color):
    return f"{getattr(_Background, color)}{text}{_Attributes.off}"
  raise ValueError("invalid color name: {color}")

def attr(text, attribute):
  if hasattr(_Attributes, attribute):
    return f"{getattr(_Attributes, color)}{text}{_Attributes.off}"
  raise ValueError("invalid attribute name: {attribute}")
