""" Tag Parser Module """

# For tag functions
from random import choice
from unicodedata import lookup
from . import math_handler

# For parser
from . import lexer
from collections import deque
from inspect import isawaitable
import re

_text_colors = dict(
    black = "\033[30m",
    red = "\033[31m",
    green = "\033[32m",
    yellow = "\033[33m",
    blue = "\033[34m",
    magenta = "\033[35m",
    cyan = "\033[36m",
    white = "\033[37m",

    b_black = "\033[90m",
    b_red = "\033[91m",
    b_green = "\033[92m",
    b_yellow = "\033[93m",
    b_blue = "\033[94m",
    b_magenta = "\033[95m",
    b_cyan = "\033[96m",
    b_white = "\033[97m",
)

_paint = lambda s, c: f"{_text_colors.get(c, _text_colors['white'])}{s}\033[0m"

KEYWORD_REGEX = re.compile(r"^\w+$")

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
    def __init__(self):
        self.fallback_text = None

    # Get and stuff is in bot

    # Join args
    def join(self, *args):
        return "".join(args)

    # Unicode name lookup
    def unicode(self, name):
        return lookup(name)

    # Safe, fast math parser
    def math(self, *args):
        parser = math_handler.MathParser("".join(str(arg) for arg in args[::-1]), debug=self.debug)
        return parser()

    # Fallback setter
    def fallback(self, content=None):
        self.fallback_text = str(content)

    # Random choice
    def rand(self, *args):
        return choice(args)

# Actual parser
class Parser:
    def __init__(self, tag_text, **kwargs):
        self.source = tag_text
        self.level = 0
        self.index = 0
        self.result = []
        self.arg_cache = deque()

        self.debug = kwargs.get("debug", False)
        self.logger = kwargs.get("logger", None)
        self.lexer = lexer.Lexer(self.source, debug=self.debug, logger=self.logger)
        self.tag_functions = kwargs.get("override", TagFunctions())

        self.tokens = deque(self.lexer())
        self.formatted = "".join(_paint(token.source, token.color_name) for token in self.tokens)

    # Debug log
    def log(self, text):
        if self.debug:
            if self.logger is not None:
                self.logger.log(text)
            else:
                print(text)

    # Alias of __call__
    async def run(self):
        return await self.__call__()

    # Fetch current token
    def pop(self):
        if len(self.tokens) > 0:
            token = self.tokens.popleft()
            self.log(f"[Pop] {token}")
            return token
        else:
            raise UnterminatedError("Unexpected end of input")

    # Fetch next token
    def peek(self):
        if len(self.tokens) > 0:
            token = self.tokens.popleft()
            self.log(f"[Peek] {token}")
            self.tokens.appendleft(token)
            return token
        else:
            raise UnterminatedError("Unexpected end of input")

    # Check pop safety
    def check(self):
        token_amnt = len(self.tokens)
        self.log(f"[Check] #Tokens: {token_amnt}")
        return token_amnt > 0

    # Store result
    def save(self, content):
        if isinstance(content, list):
            content = "" if len(content) == 0 else content[0]

        self.log(f"[Save] {content}")
        self.result.append(str(content))

    # Cache arguments
    def store(self, value):
        self.arg_cache.appendleft(value)

    # Process and call functions
    async def process_function(self, function, *args):
        arg_list = [self.arg_cache.popleft() if not isinstance(arg, lexer.Token) else arg.source.strip() for arg in args]
        arg_names = ["EXTERNAL" + str(self.level) if not isinstance(arg, lexer.Token) else arg.name for arg in args]
        func_name = function.source

        if KEYWORD_REGEX.fullmatch(func_name) is None:
            raise InvalidFunctionNameError("Function names must be alphanumeric")

        self.log(f"[Process] Calling {func_name} with args {list(zip(arg_names, arg_list))}")

        if hasattr(self.tag_functions, func_name):
            if callable(getattr(self.tag_functions, func_name)):
                try:
                    func_result = getattr(self.tag_functions, func_name)(*arg_list)

                    if isawaitable(func_result):
                        func_result = await func_result

                    return "" if func_result is None else func_result
                except Exception as e:
                    return str(e) if self.tag_functions.fallback_text is None else str(self.tag_functions.fallback_text)
            else:
                raise ParserError("An error occurred.")
        else:
            raise NonExistantFunctionError(f"Function {func_name} doesn't exist")

    # Function parsing
    async def __parse_function(self):
        level = self.level
        self.log(f"Level {self.level + 1}, Next {self.level + 2}")
        self.level += 1
        if self.peek().type != lexer.TokenType.function.value:
            raise UnexpectedTokenError(f"{token.name} was unexpected: Expected Function")

        else:
            function = self.pop()
            args = []
            return_args = []

            indicator = self.pop()
            if indicator.type != lexer.TokenType.indicator.value:
                raise UnexpectedTokenError(f"{indicator.name} was unexpected: Expected Indicator")

            while True:
                token = self.pop()

                if token.type == lexer.TokenType.argument.value:
                    args.append(token)
                    next_token = self.peek()
                    if next_token.type == lexer.TokenType.block_end.value:
                        self.log(f"Level {self.level - 1}, Next {self.level - 2}")
                        if self.level == 0:
                            raise UnexpectedTokenError("']' was unexpected: No matching opening bracket")
                        self.level -= 1

                        result = await self.process_function(function, *args)
                        return_args.append(result)
                        self.store(result)

                        if self.level == level:
                            self.pop()
                            return return_args

                elif token.type == lexer.TokenType.comma.value:
                    next_token = self.peek()
                    if next_token.type not in [lexer.TokenType.argument.value, lexer.TokenType.block_start.value]:
                        raise UnexpectedTokenError(f"{next_token.name} was unexpected: Unterminated argument list")

                elif token.type == lexer.TokenType.block_start.value:
                    args.append(await self._Parser__parse_function())

                elif token.type == lexer.TokenType.block_end.value:
                    self.log(f"Level {self.level - 1}, Next {self.level - 2}")
                    if self.level == 0:
                        raise UnexpectedTokenError("']' was unexpected: No matching opening bracket")

                    self.level -= 1
                    result = await self.process_function(function, *args)
                    return_args.append(result)
                    self.store(result)

                    if self.level == level:
                        return return_args

                else:
                    raise UnexpectedTokenError(f"{token.name} was unexpected: unrecognized token in argument list")

    # Actually process the tokens
    async def __call__(self):
        self.log(self.lexer.dump())
        while self.check():
            token = self.pop()

            if not isinstance(token, lexer.Token):
                raise InvalidTokenError(f"{repr(token)} is not a token")

            self.log(f"[Found] {token}")

            if token.type == lexer.TokenType.text.value:
                self.save(token.source)

            elif token.type == lexer.TokenType.block_start.value:
                self.save(await self._Parser__parse_function())

            elif token.type == lexer.TokenType.block_end.value:
                self.log(f"Level {self.level - 1}, Next {self.level - 2}")
                if self.level == 0:
                    raise UnexpectedTokenError("']' was unexpected: No matching opening bracket")
                else:
                    self.level -= 1

        return "".join(self.result)