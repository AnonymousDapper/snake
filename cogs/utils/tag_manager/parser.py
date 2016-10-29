""" Tag Parser Module """

# Imports for tag functions
from random import choice
from unicodedata import lookup as unicode_lookup
from . import math_handler

# Standard imports
from . import lexer
from collections import deque
from inspect import isawaitable as is_coro
import re

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


tag_values = {}

class ParserError(Exception):
  pass

class GrammarError(ParserError):
  pass

class UnexpectedTokenError(ParserError):
  pass

class InvalidTokenError(ParserError):
  pass

class InvalidFunctionNameError(ParserError):
  pass

class NonExistantFunctionError(ParserError):
  pass

class UnterminatedError(ParserError):
  pass

class TagFunctions:
  def __init__(self, **kwargs):
    self.debug = kwargs.pop("debug", False)
    self.fallback_ = None
    self.rand = lambda *args: choice(args)

  # Get variables
  def get(self, name, default=None):
    return tag_values.get(name, default)

  # Set variables
  def set(self, name, value):
    tag_values[name] = value

  # Join all values into a string
  def join(self, *args):
    print(repr(args))
    return ''.join(args)

  # Unicode character lookup
  def unicode(self, name):
    return unicode_lookup(name)

 # Math parser
  def math(self, *args):
    parser = math_handler.MathParser(''.join(args), debug=self.debug)
    return parser()

  # Error fallback
  def fallback(self, content=None):
    self.fallback_ = content

class Parser:
  def __init__(self, tag_text, **kwargs):
    self.source = tag_text
    self.level = 0
    self.index = 0
    self.result = []
    self.arg_cache = deque()
    self.debug = kwargs.pop("debug", False)
    self.logger = kwargs.pop("logger", None)
    self.func_regex = re.compile(r"[a-z_]+", re.IGNORECASE)
    self.lexer = lexer.Lexer(tag_text, debug=self.debug, logger=self.logger)
    self.tokens = deque(self.lexer())
    self.tag_fallback = TagFunctions(debug=self.debug)
    self.tag_functions = kwargs.pop("override", self.tag_fallback)
    self.formatted = ''.join(_paint(token.source, token.color_name) for token in self.tokens)

  # Debug log
  def log(self, text):
    if self.debug:
      if self.logger is not None:
        self.logger.log(text)
      else:
        print(text)

  # Alias for __call__
  async def run(self):
    return await self.__call__()

  # Get  next token
  def pop(self):
    if len(self.tokens) > 0:
      token = self.tokens.popleft()
      self.log(_paint("[Pop] {}".format(token), "cyan"))
      return token
    else:
      raise UnterminatedError("Unexpected end of input")

  # Check the next element in the queue
  def peek(self):
    if len(self.tokens) > 0:
      token = self.tokens.popleft()
      self.log(_paint("[Peek] {}".format(token), "red"))
      self.tokens.appendleft(token)
      return token
    else:
      raise UnterminatedError("Unexpected end of input")

  # Make sure we have room to pop()
  def check(self):
    self.log(_paint("[Check] #Tokens: {}".format(len(self.tokens)), "white)"))
    return len(self.tokens) > 0

  # Store result
  def save(self, content):
    if isinstance(content, list):
      content = '' if len(content) == 0 else content[0]

    self.log(_paint("[Save] {}".format(content), "green"))
    self.result.append(str(content))

  # Store reference arguments
  def store_arg(self, value):
    self.arg_cache.append(value)

  # Process and call functions
  async def process_function(self, function, *args):
    arg_list = [self.arg_cache.popleft() if not isinstance(arg, lexer.Token) else arg.source.strip() for arg in args]
    arg_names = ["EXTERNAL" + str(self.level) if not isinstance(arg, lexer.Token) else arg.name for arg in args]
    func_name = function.source

    if self.func_regex.fullmatch(func_name) is None:
      raise InvalidFunctionNameError("Function names must be alphanumeric")

    self.log(_paint("[Process] Calling {} with args {!r} ".format(func_name, list(zip(arg_names, arg_list))), "white"))
    if hasattr(self.tag_functions, func_name):
      try:
        func_result = getattr(self.tag_functions, func_name)(*arg_list)
        if is_coro(func_result):
          func_result = await func_result
        return '' if func_result is None else func_result
      except Exception as e:
        return str(e) if self.tag_functions.fallback_ is None else str(self.tag_functions.fallback_)

  # Parse function groups into proper tokens
  async def __parse_function(self):
    level = self.level
    self.log("Level: {}, NextLvl: {}".format(self.level + 1, self.level + 2))
    self.level += 1
    if self.peek().type != lexer.TokenType.function.value:
      raise UnexpectedTokenError("{} was unexpected, expecting Function".format(token.name))

    else:
      function = self.pop()
      args = []
      return_args = []

      indicator = self.pop()
      if indicator.type != lexer.TokenType.indicator.value:
        raise UnexpectedTokenError("{} was unexpected; expected Indicator".format(indicator.name))

      while True:
        token = self.pop()

        if token.type == lexer.TokenType.argument.value:
          args.append(token)
          self.log(token)
          #print([str(a) for a in args])
          next_token = self.peek()
          if next_token.type == lexer.TokenType.block_end.value:
            self.log("Level: {}, NextLvl: {}".format(self.level - 1, self.level - 2))
            if self.level == 0:
              raise UnexpectedTokenError("']' was unexpected; no opening bracket")

            self.level -= 1
            result = await self.process_function(function, *args)
            return_args.append(result)
            self.store_arg(result)
            #print('-')
            if self.level == level:
              #print("-- breaking")
              self.pop()
              return return_args
              #break

        elif token.type == lexer.TokenType.comma.value:
          self.log("Found comma")
          next_token = self.peek()
          if next_token.type not in [lexer.TokenType.argument.value, lexer.TokenType.block_start.value]:
            raise UnexpectedTokenError("{} was unexpected; unterminated argument list".format(next_token.name))

        elif token.type == lexer.TokenType.block_start.value:
          args.append(await self._Parser__parse_function())

        elif token.type == lexer.TokenType.block_end.value:
          self.log("Level: {}, NextLvl: {}".format(self.level - 1, self.level - 2))
          if self.level == 0:
            raise UnexpectedTokenError("']' was unexpected; no opening bracket")

          self.level -= 1
          result = await self.process_function(function, *args)
          return_args.append(result)
          self.store_arg(result)
          #print('+')
          if self.level == level:
            #print("--- breaking")
            return return_args
            #break

        else:
          raise UnexpectedTokenError("{} was unexpected; unrecognized token in argument list".format(token.name))

  # Process tokens
  async def __call__(self):
    self.log(self.lexer.dump())
    while self.check():
      token = self.pop()

      if not isinstance(token, lexer.Token):
        raise InvalidTokenError("{!r} is not a token".format(token))

      self.log(_paint("[Found] {}".format(token), "magenta"))

      if token.type == lexer.TokenType.text.value:
        self.save(token.source)

      elif token.type == lexer.TokenType.block_start.value:
        self.save(await self._Parser__parse_function())

      elif token.type == lexer.TokenType.block_end.value:
        self.log("Level: {}, NextLvl: {}".format(self.level - 1, self.level - 2))
        if self.level == 0:
          raise UnexpectedTokenError("']' was unexpected; no opening bracket")
        else:
          self.level -= 1
    return "".join(self.result)