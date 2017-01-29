""" Tag Lexer Module """

from enum import Enum

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
    # Actual Token class
    def __init__(self, token_type, source):
        self.token = token_type
        self.type = token_type.value
        self.source = source
        self.name = token_type.name
        self.color_name = ["b_magenta", "b_green", "b_yellow", "b_red", "b_blue", "b_white", "b_cyan"][self.type]

    def __str__(self):
        return f"{self.name} [{self.type}]: '{self.source}' ({self.color_name})"

    def __repr__(self):
        return f"<Token(type={self.type}, name='{self.name}', color_name='{self.color_name}')>"

class Lexer:
    def __init__(self, content, **kwargs):
        self.source = content
        self.tokens = []
        self.index = 0
        self.debug = kwargs.get("debug", False)
        self.logger = kwargs.get("logger", None)

    # Debug log
    def log(self, text):
        if self.debug:
            if self.logger is not None:
                self.logger.log(text)
            else:
                print(text)

    # Alias of __call__
    def run(self):
        return self.__call__()

    # Fetch next
    def peek(self, k=1):
        char = "" if (self.index + k) == len(self.source) else self.source[self.index + k]
        self.log(f"[Peek] K {k}, Index {self.index + k}, Char '{char}'")

    # Fetch previous
    def sneak(self, k=1):
        char = "" if (self.index - k) < 0 else self.source[self.index - k]
        self.log(f"[Sneak] K {k}, Index {self.index - k}, Char '{char}'")

    # Increment counter
    def inc(self, k=1):
        self.index += k

    # Decrement counter
    def dec(self, k=1):
        self.index -= k

    # Get current counter character
    def get(self):
        char = self.source[self.index]
        self.log(f"[Get] Char '{char}', Index {self.index}")
        return char

    # Find length of text
    def find(self, char, **kwargs):
        end = kwargs.get("end", len(self.source))
        start = kwargs.get("start", self.index)
        result = self.source.find(char, start, end)
        self.log(f"[Find] End {end}, Start {start}, Char '{char}', Result '{result}'")
        return result

    # Fetch more text
    def grab(self, k):
        result = self.source[self.index:k]
        self.log(f"[Grab] K {k}, Result '{result}'")
        return result

    # Check for safety
    def check(self):
        return self.index < len(self.source)

    # Store token
    def push_token(self, token_type, source):
        token = Token(token_type, source)
        self.log(f"[Push] Token {token}")
        self.tokens.append(token)

    # Formatted list of tokens
    def dump(self, **kwargs):
        result = []
        token_output = []
        for token in self.tokens:
            result.append(f"{_paint(token.name, token.color_name)} [{_paint(token.type, 'magenta')}] \"{_paint(token.source, 'cyan')}\"")
            token_output.append(_paint(token.source, token.color_name))
        result.append(f"Output: {''.join(token_output)}")
        return kwargs.get("sep", "\n").join(result)

    # Parsing of inner content
    def __parse_tag(self):
        char = self.get()
        if char == "[":
            self.push_token(TokenType.block_start, char)
            self.inc()

        func_name = ""

        while True:
            if not self.check():
                self.push_token(TokenType.function, func_name)
                break
            else:
                char = self.get()
                if char == ":":
                    self.push_token(TokenType.function, func_name)
                    self.push_token(TokenType.indicator, char)
                    self.inc()
                    break
                else:
                    func_name += char
                    self.inc()

        self.log(f"Function {func_name}, Index {self.index}")

        arg = ""
        while True:
            if self.check() is False:
                if arg.strip() != "":
                    self.push_token(TokenType.argument, arg.strip())
                break

            char = self.get()

            if char == ",":
                if arg.strip() != "":
                    self.push_token(TokenType.argument, arg.strip())
                self.push_token(TokenType.comma, char)
                arg = ""
                self.inc()
            elif char == "[":
                self._Lexer__parse_tag()
            elif char == "]":
                if arg.strip() != "":
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

            if char == "[":
                self._Lexer__parse_tag()

            elif char == "]":
                self.push_token(TokenType.block_end, char)
                self.inc()

            else:
                self.push_token(TokenType.text, char)
                self.inc()

        return self.tokens