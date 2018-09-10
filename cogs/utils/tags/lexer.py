# MIT License
#
# Copyright (c) 2018 AnonymousDapper
#
# Permission is hereby granted
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Stag syntax is rather lispy

 # Numbers        Operators           Examples
 # -------        ---------           --------
 # integers       +   add             (print 45 - 2 'asd')             -> 43 asd
 # floats         -   subtract        (print 45-2 asd)                 -> 43 <value of asd>
 # .1             *   multiply        (print 45 -2 "as\nd")            -> 45 -2 as\nd
 # 45e10          /   divide          (fn [arg1, λ] (λ arg1 / 2))      -> anonymous function that calls λ(arg1 / 2)
 # 4.5e11         //  floordivide     (def func (fn [α, λ] (λ θ - α))) -> declares a function named func
 # -5.4           %   modulo
 #                **  pow
 #                ~   bitnot
 #                ^   bitxor
 #                |   bitor
 #                &   bitand
 #                <<  bitlshift
 #                >>  bitrshift
 #                =   assign
 #                ==  equality
 #                <   lessthan
 #                >   greaterthan
 #                <=  lessthanorequal
 #                >=  greaterthanorequal



from enum import Enum


class StagSyntaxError(Exception):
    def __init__(self, message, line, offset):
        super().__init__(f"{message} at L{line}:{offset}")

class TokenType(Enum):
    Text = 0         # any text not being parsed
    LeftParen = 1    # (
    RightParen = 2   # )
    LeftBracket = 3  # [
    RightBracket = 4 # ]
    RightBrace = 5   # }
    LeftBrace = 6    # {
    Add = 7          # +
    Sub = 8          # - (N - N) (-N becomes a negative number)
    Mul = 9          # *
    Div = 10         # /
    FloorDiv = 11    # //
    Modulo = 12      # %
    Pow = 13         # **
    BitNot = 14      # ~
    BitXOr = 15      # ^
    BitAnd = 16      # &
    BitOr = 17       # |
    BitLShift = 18   # <<
    BitRShift = 19   # >>
    Assign = 20      # =
    Compare = 21     # ==
    LessThan = 22    # <
    GreaterThan = 23 # >
    LTEqualTo = 24   # <=
    GTEqualTo = 25   # >=
    Attribute = 26   # : attribute access is Name:name(:subname:...)
    Name = 27        # any text representing a variable/function
    Integer = 28     #
    Float = 29       #
    String = 30      #
    LogicalNot = 31  # not
    LogicalAnd = 32  # and
    LogicalOr = 33   # or
    Comma = 34       #

class Token:
    def __init__(self, token_type, source):
        self.token = token_type
        self.type = token_type.value
        self.source = source
        self.name = token_type.name

    def __repr__(self):
        return f"<Token(type={self.type}, name={self.name})>"

class Tokenizer:
    def __init__(self, content, **kwargs):
        self.source = content
        self.source_len = len(content)

        self.tokens = []
        self.index = 0
        self.line_no = 1
        self.line_offset = 0

        self.debug = kwargs.get("debug", False)
        self.logger = kwargs.get("logger", None)

    def log(self, text):
        if self.debug:
            self.logger.log(text)

    def run(self):
        return self.__call__()

    # Fetch the next character without changing the index
    def peek(self):
        return "" if self.index >= self.source_len else self.source[self.index]

    def inc(self):
        self.index += 1
        self.line_offset += 1

    def get(self):
        return self.source[self.index - 1]

    # Increment and return next character
    def next(self):
        self.inc()
        return self.get()

    def check(self):
        return self.index < self.source_len

    def push_token(self, token_type, source=None):
        token = Token(token_type, self.get() if source is None else source)
        #print("Pushing", token, repr(token.source))
        self.tokens.append(token)

    def dump(self):
        for token in self.tokens:
            print(f"{token} - {repr(token.source)}")

    # Handle any text outside tags
    def _handle_text(self, text_arr):
        if len(text_arr) > 0:
            self.push_token(TokenType.Text, "".join(text_arr))

    # Parse a number into an int or float
    def _parse_number(self):
        buf = []

        char = self.get()

        if char == "-":
            buf.append(char)
            char = self.next()

        while self.check() and (char.isdigit() or char == "." or char == "e" or char == "-"):
            buf.append(char)
            char = self.next()

        string = "".join(buf)

        try:
            value = int(string)
            token_type = TokenType.Integer

        except ValueError:
            try:
                value = float(string)
                token_type = TokenType.Float

            except ValueError:
                raise StagSyntaxError(f"Failed parsing number '{string}'", self.line_no, self.line_offset)

        self.push_token(token_type, value)

    # Parse a string
    def _parse_string(self):
        quote_char = self.get()
        buf = []

        while self.check():
            char = self.next()

            if char == "\\" and self.peek() == quote_char:
                buf.append(quote_char)
                self.inc()

            elif char == quote_char:
                break

            elif char == "\n":
                raise StagSyntaxError("Unexpected EOL while parsing string literal", self.line_no, self.line_offset)

            else:
                buf.append(char)

        self.push_token(TokenType.String, "".join(buf))

    # Parse an identifier
    def _parse_ident(self):
        buf = []
        char = self.get()

        while self.check() and char.isidentifier():
            buf.append(char)
            char = self.next()

        self.index -= 1
        string = "".join(buf)

        if string == "and":
            token_type = TokenType.LogicalAnd

        elif string == "not":
            token_type = TokenType.LogicalNot

        elif string == "or":
            token_type = TokenType.LogicalOr

        else:
            token_type = TokenType.Name

        self.push_token(token_type, string)

    def _parse_tag(self):
        while self.check():
            char = self.next()

            if char == "(":
                self.push_token(TokenType.LeftParen)

            elif char == ")":
                self.push_token(TokenType.RightParen)

            elif char == "[":
                self.push_token(TokenType.LeftBracket)

            elif char == "]":
                self.push_token(TokenType.RightBracket)

            elif char == "+":
                self.push_token(TokenType.Add)

            elif char == "-" and self.peek().isspace():
                self.push_token(TokenType.Sub)

            elif char == "*":
                if self.peek() == "*":
                    self.push_token(TokenType.Pow, "**")
                    self.inc()

                else:
                    self.push_token(TokenType.Mul)

            elif char == "/":
                if self.peek() == "/":
                    self.push_token(TokenType.FloorDiv, "//")
                    self.inc()

                else:
                    self.push_token(TokenType.Div)

            elif char == "%":
                self.push_token(TokenType.Modulo)

            elif char == "~":
                self.push_token(TokenType.BitNot)

            elif char == "^":
                self.push_token(TokenType.BitXOr)

            elif char == "&":
                self.push_token(TokenType.BitAnd)

            elif char == "|":
                self.push_token(TokenType.BitOr)

            elif char == "<":
                if self.peek() == "<":
                    self.push_token(TokenType.BitLShift, "<<")
                    self.inc()

                elif self.peek() == "=":
                    self.push_token(TokenType.LTEqualTo, "<=")
                    self.inc()

                else:
                    self.push_token(TokenType.LessThan)

            elif char == ">":
                if self.peek() == ">":
                    self.push_token(TokenType.BitRShift, ">>")
                    self.inc()

                elif self.peek() == "=":
                    self.push_token(TokenType.GTEqualTo, ">=")
                    self.inc()

                else:
                    self.push_token(TokenType.GreaterThan)

            elif char == "=":
                if self.peek() == "=":
                    self.push_token(TokenType.Compare, "==")
                    self.inc()

                else:
                    self.push_token(TokenType.Assign)

            elif char == ":":
                self.push_token(TokenType.Attribute)

            elif char.isdigit() or ((char == "-" or char == "." ) and not self.peek().isspace()):
                self._parse_number()

            elif char == '"' or char == "'":
                self._parse_string()

            elif char.isspace():
                continue

            elif char == "}":
                return

            else:
                self._parse_ident()

    def __call__(self):
        print(self.source)
        in_tag = False
        escaped = False

        text = []

        while self.check():
            char = self.next()

            if char == "{":
                if not escaped:
                    self._handle_text(text)
                    text = []

                    self._parse_tag()

                else:
                    text.append(char)
                    escaped = False

            elif char == "\\":
                escaped = True

            else:
                if char == "\n":
                    self.line_no += 1
                    self.line_offset = 0

                text.append(char)

        if len(text) > 0:
            self._handle_text(text)
            text = []

        return self.tokens

def lex(s):
    t = Tokenizer(s)
    t()
    t.dump()
