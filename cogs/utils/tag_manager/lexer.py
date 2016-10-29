""" Tag Lexer Module """

from enum import Enum


_text_colors = dict(
  black="\033[30m",
  red="\033[31m",
  green="\033[32m",
  yellow="\033[33m",
  blue="\033[34m",
  magenta="\033[35m",
  cyan="\033[36m",
  white="\033[37m"
)
_paint = lambda s, c: "{}{}\033[0m".format(_text_colors.get(c, "\033[37m"), s)

class TokenType(Enum):
  # Token definitions
  function = 0
  argument = 1
  block_start = 2
  block_end = 3
  comma = 4
  text = 5
  indicator = 6

  def __str__(self):
    return self.name

class Token:
  # Token class to pass to parser
    def __init__(self, token_type : TokenType, source):
      self.token = token_type
      self.type = token_type.value
      self.source = source
      self.name = token_type.name
      self.color_name = ["red", "green", "yellow", "white", "magenta", "cyan", "blue"][token_type.value]

    def __str__(self):
      return "{0.name} [{0.type}] : '{0.source}' ({0.color_name})".format(self)

class Lexer:
  # Lexer class that handles tokenizing of source text
  def __init__(self, content, **kwargs):
    self.source = content
    self.tokens = []
    self.index = 0
    self.debug = kwargs.pop("debug", False)
    self.logger = kwargs.pop("logger", None)

  # Debug log
  def log(self, text):
    if self.debug:
      if self.logger is not None:
        self.logger.log(text)
      else:
        print(text)

  # Alias for __call__
  def run(self):
    return self.__call__()

  # Get the next character
  def peek(self, k=1):
    char = '' if (self.index + k) == len(self.source) else self.source[self.index + k]
    self.log(_paint("[Peek] K {}; Index {}; Char '{}'".format(k, self.index + k, char), "red"))
    return char

  # Get the previous character
  def sneak(self, k=1):
    char = '' if (self.index - k) < 0 else self.source[self.index - k]
    self.log(_paint("[Sneak] K {}; Index {}; Char '{}'".format(k, self.index + k, char), "red"))
    return char

  # Increment counter
  def inc(self, k=1):
    self.index += k

  # Decrement counter
  def dec(self, k=1):
    self.index -= k

  # Get character at current counter index
  def get(self):
    char = self.source[self.index]
    self.log(_paint("[Get] Char '{}'; Index {}".format(char, self.index), "green"))
    return char

  # Find text
  def find(self, char, **kwargs):
    end = kwargs.pop("end", len(self.source))
    start = kwargs.pop("start", self.index)
    result = self.source.find(char, start, end)
    self.log(_paint("[Find] End {}; Start {}; Char '{}'; Result {}".format(end, start, char, result), "yellow"))
    return result

  # Fetch a length of text
  def grab(self, k):
    result = self.source[self.index:k]
    self.log(_paint("[Grab] K {}; Result '{}'".format(k, result), "white"))
    return result

  # Check length
  def check(self):
    return self.index < len(self.source)

  # Store token
  def push_token(self, token_type, source):
    token  = Token(token_type, source)
    self.log(_paint("[Push] Token {}".format(token), "magenta"))
    self.tokens.append(token)

  # Formatted list of tokens
  def dump(self, **kwargs):
    result = []
    token_output = []
    for token in self.tokens:
      result.append("{} [{}] \"{}\"".format(_paint(token.name, token.color_name), _paint(token.type, "red"), _paint(token.source, "cyan")))
      token_output.append(_paint(token.source, token.color_name))
    result.append("Output: {}".format(''.join(token_output)))
    return kwargs.pop("sep", "\n").join(result)

  # Parse tag inner content
  def __parse_tag(self):
    char = self.get()
    if char == '[':
      self.push_token(TokenType.block_start, char)
      self.inc()

    func_name = ''

    while True:
      if not self.check():
        self.log('pushing')
        self.push_token(TokenType.function, func_name)
        break
      else:
        char_ = self.get()
        if char_ == ':':
          self.push_token(TokenType.function, func_name)
          self.push_token(TokenType.indicator, char_)
          self.inc()
          break
        else:
          func_name += char_
          self.inc()

    self.log(_paint("Func {}; Index {}".format(func_name, self.index), "cyan"))

    arg = ''
    while True:
      if self.check() is False:
        if arg.strip() != '':
          self.push_token(TokenType.argument, arg.strip())
        break

      char = self.get()

      if char == ',':
        self.log(_paint("Argument {}; Seperator {}".format(arg, char), "blue"))
        if arg.strip() != '':
          self.push_token(TokenType.argument, arg.strip())
        self.push_token(TokenType.comma, char)
        arg = ''
        self.inc()
      elif char == '[':
        self._Lexer__parse_tag()

      elif char == ']':
        if arg.strip() != '':
          self.push_token(TokenType.argument, arg.strip())

        self.push_token(TokenType.block_end, char)
        self.inc()
        break

      else:
        arg += char
        self.inc()

  # Start lexer
  def __call__(self):
    while self.check():
      char = self.get()

      if char == '[':
        self._Lexer__parse_tag()

      elif char == ']':
        self.push_token(TokenType.block_end, char)
        self.inc()

      else:
        self.push_token(TokenType.text, char)
        self.inc()

    return self.tokens