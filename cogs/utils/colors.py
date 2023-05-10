# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

__all__ = "Colorize", "Style", "Styles", "Color"

from collections import namedtuple
from enum import Enum
from functools import wraps
from re import finditer
from typing import Optional

TrueColor = namedtuple("TrueColor", "r g b")

StyleFlagData = namedtuple("StyleFlagData", "mask value")


class Styles(Enum):
    """
    VT seqences for styling
    """

    Clear = StyleFlagData(0, "")
    Bold = StyleFlagData(1, "1")
    Dimmed = StyleFlagData(64, "2")
    Italic = StyleFlagData(8, "3")
    Underline = StyleFlagData(2, "4")
    Blink = StyleFlagData(16, "5")
    Reversed = StyleFlagData(4, "7")
    Hidden = StyleFlagData(32, "8")
    Strikethrough = StyleFlagData(128, "7")

    @classmethod
    def from_int(cls, value):
        if value != 0:
            styles = tuple(filter(lambda s: value & s.value.mask, Styles))

            if styles:
                return styles

        return None

    def to_int(self) -> int:
        return self.value.mask

    def to_str(self) -> str:
        return self.value.value


class Style:
    style: int

    def __init__(self, style: Styles):
        self.style = style.to_int()

    def contains(self, style: Styles) -> bool:
        return style in self

    def add(self, other: Styles):
        self += other

    def __contains__(self, item: Styles) -> bool:
        if isinstance(item, Styles):
            val = item.to_int()

            return self.style & val == val

        return NotImplemented

    def __iadd__(self, other: Styles):
        if isinstance(other, Styles):
            self.style |= other.value.mask
            return self

        return NotImplemented

    def __eq__(self, other: Styles) -> bool:
        if isinstance(other, Styles):
            return self.style == other.to_int()

        return NotImplemented

    def __str__(self):
        styles = Styles.from_int(self.style)

        if styles:
            return ";".join(map(Styles.to_str, styles))

        return Styles.Clear.to_str()


class Color(Enum):
    """
    VT sequences for coloring
    """

    Black = 0
    Red = 1
    Green = 2
    Yellow = 3
    Blue = 4
    Magenta = 5
    Cyan = 6
    White = 7

    BrightBlack = 60
    BrightRed = 61
    BrightGreen = 62
    BrightYellow = 63
    BrightBlue = 64
    BrightMagenta = 65
    BrightCyan = 66
    BrightWhite = 67

    TrueColor = TrueColor

    @classmethod
    def true_color(cls, color) -> Color:
        self = cls.TrueColor

        setattr(self, "color", color)

        return self

    def fg(self):
        if self != Color.TrueColor:
            return str(self.value + 30)
        else:
            return f"38;2;{self.color.r};{self.color.g};{self.color.b}"  # type: ignore

    def bg(self):
        if self != Color.TrueColor:
            return str(self.value + 40)
        else:
            return f"48;2;{self.color.r};{self.color.g};{self.color.b}"  # type: ignore


class Colorize:
    def __init__(
        self,
        text,
        *,
        fg_color: Optional[Color] = None,
        bg_color: Optional[Color] = None,
        style: Optional[Style] = None,
    ):
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.style = style or Style(Styles.Clear)
        self.inner = str(text)

    def is_plain(self) -> bool:
        return (
            self.fg_color is None
            and self.bg_color is None
            and self.style == Styles.Clear
        )

    def _from(self, text: str) -> Colorize:
        return Colorize(
            text, fg_color=self.fg_color, bg_color=self.bg_color, style=self.style
        )

    def compute_style(self) -> str:
        if self.is_plain():
            return ""

        buf = ["\x1B["]
        wrote = False

        if self.style != Styles.Clear:
            buf.append(str(self.style))
            wrote = True

        if self.bg_color is not None:
            if wrote:
                buf.append(";")

            buf.append(self.bg_color.bg())
            wrote = True

        if self.fg_color is not None:
            if wrote:
                buf.append(";")

            buf.append(self.fg_color.fg())

        buf.append("m")
        return "".join(buf)

    def escape_inner_resets(self) -> str:
        if self.is_plain():
            return self.inner

        reset = "\x1B\\[0m"
        r_len = 4

        style = self.compute_style()

        matches = tuple(m.start() for m in finditer(reset, self.inner))

        if not matches:
            return self.inner

        tmp = list(self.inner)

        for idx, offset in enumerate(matches):
            offset = offset + r_len + idx * len(style)

            for c in style:
                tmp.insert(offset, c)
                offset += 1

        return "".join(tmp)

    def __repr__(self):
        return repr(str(self))

    def __str__(self):
        if self.is_plain():
            return self.inner

        return f"{self.compute_style()}{self.escape_inner_resets()}\x1B[0m"

    @wraps(str.capitalize)
    def capitalize(self):
        self.inner = self.inner.capitalize()
        return self

    @wraps(str.casefold)
    def casefold(self):
        self.inner = self.inner.casefold()
        return self

    @wraps(str.center)
    def center(self, *args):
        self.inner = self.inner.center(*args)
        return self

    @wraps(str.count)
    def count(self, *args):
        return self.inner.count(*args)

    @wraps(str.encode)
    def encode(self, *args, **kwargs):
        self.inner = self.inner.encode(*args, **kwargs)
        return self

    @wraps(str.endswith)
    def endswith(self, *args):
        return self.inner.endswith(*args)

    @wraps(str.expandtabs)
    def expandtabs(self, *args, **kwargs):
        self.inner = self.inner.expandtabs(*args, **kwargs)
        return self

    @wraps(str.find)
    def find(self, *args):
        return self.inner.find(*args)

    @wraps(str.format)
    def format(self, *args, **kwargs):
        self.inner = self.inner.format(*args, **kwargs)
        return self

    @wraps(str.format_map)
    def format_map(self, mapping):
        self.inner = self.inner.format_map(mapping)
        return self

    @wraps(str.index)
    def index(self, *args):
        return self.inner.index(*args)

    @wraps(str.isalnum)
    def isalnum(self):
        return self.inner.isalnum()

    @wraps(str.isalpha)
    def isalpha(self):
        return self.inner.isalpha()

    @wraps(str.isascii)
    def isascii(self):
        return self.inner.isascii()

    @wraps(str.isdecimal)
    def isdecimal(self):
        return self.inner.isdecimal()

    @wraps(str.isdigit)
    def isdigit(self):
        return self.inner.isdigit()

    @wraps(str.isidentifier)
    def isidentifier(self):
        return self.inner.isidentifier()

    @wraps(str.islower)
    def islower(self):
        return self.inner.islower()

    @wraps(str.isnumeric)
    def isnumeric(self):
        return self.inner.isnumeric()

    @wraps(str.isprintable)
    def isprintable(self):
        return self.inner.isprintable()

    @wraps(str.isspace)
    def isspace(self):
        return self.inner.isspace()

    @wraps(str.istitle)
    def istitle(self):
        return self.inner.istitle()

    @wraps(str.isupper)
    def isupper(self):
        return self.inner.isupper()

    @wraps(str.join)
    def join(self, _iter):
        self.inner = self.inner.join(_iter)
        return self

    @wraps(str.ljust)
    def ljust(self, *args):
        self.inner = self.inner.ljust(*args)
        return self

    @wraps(str.lower)
    def lower(self):
        self.inner = self.inner.lower()
        return self

    @wraps(str.lstrip)
    def lstrip(self, *args):
        self.inner = self.inner.lstrip(*args)
        return self

    @wraps(str.maketrans)
    def maketrans(self, *args, **kwargs):
        self.inner = self.inner.maketrans(*args, **kwargs)
        return self

    @wraps(str.partition)
    def partition(self, *args):
        self.inner = self.inner.partition(*args)
        return self

    @wraps(str.removeprefix)
    def removeprefix(self, *args):
        self.inner = self.inner.removeprefix(*args)
        return self

    @wraps(str.removesuffix)
    def removesuffix(self, *args):
        self.inner = self.inner.removesuffix(*args)
        return self

    @wraps(str.replace)
    def replace(self, *args):
        self.inner = self.inner.replace(*args)
        return self

    @wraps(str.rfind)
    def rfind(self, *args):
        return self.inner.rfind(*args)

    @wraps(str.rindex)
    def rindex(self, *args):
        return self.inner.rindex(*args)

    @wraps(str.rjust)
    def rjust(self, *args):
        self.inner = self.inner.rjust(*args)
        return self

    @wraps(str.rpartition)
    def rpartition(self, *args):
        self.inner = self.inner.rpartition(*args)
        return self

    @wraps(str.rsplit)
    def rsplit(self, *args, **kwargs):
        return self.inner.rsplit(*args, **kwargs)

    @wraps(str.rstrip)
    def rstrip(self, *args):
        self.inner = self.inner.rstrip(*args)
        return self

    @wraps(str.split)
    def split(self, *args, **kwargs):
        return self.inner.split(*args, **kwargs)

    @wraps(str.splitlines)
    def splitlines(self, *args, **kwargs):
        return self.inner.splitlines(*args, **kwargs)

    @wraps(str.startswith)
    def startswith(self, *args):
        return self.inner.startswith(*args)

    @wraps(str.strip)
    def strip(self, *args):
        self.inner = self.inner.strip(*args)
        return self

    @wraps(str.swapcase)
    def swapcase(self):
        self.inner = self.inner.swapcase()
        return self

    @wraps(str.title)
    def title(self):
        self.inner = self.inner.title()
        return self

    @wraps(str.translate)
    def translate(self, *args):
        self.inner = self.inner.translate(*args)
        return self

    @wraps(str.upper)
    def upper(self):
        self.inner = self.inner.upper()
        return self

    @wraps(str.zfill)
    def zfill(self, *args):
        self.inner = self.inner.zfill(*args)
        return self

    @wraps(str.__format__)
    def __format__(self, spec):
        new = self._from(self.inner.__format__(spec))
        return str(new)

    @wraps(str.__add__)
    def __add__(self, other):
        return str(self).__add__(other)

    @wraps(str.__contains__)
    def __contains__(self, other):
        return self.inner.__contains__(other)

    @wraps(str.__eq__)
    def __eq__(self, other):
        return self.inner.__eq__(other)

    @wraps(str.__ge__)
    def __ge__(self, other):
        return self.inner.__ge__(other)

    @wraps(str.__getitem__)
    def __getitem__(self, other):
        return self._from(self.inner.__getitem__(other))

    @wraps(str.__gt__)
    def __gt__(self, other):
        return self.inner.__gt__(other)

    @wraps(str.__hash__)
    def __hash__(self):
        return self.inner.__hash__()

    @wraps(str.__iter__)
    def __iter__(self):
        return iter(self._from(char) for char in self.inner.__iter__())

    @wraps(str.__le__)
    def __le__(self, other):
        return self.inner.__le__(other)

    @wraps(str.__len__)
    def __len__(self, other):
        return self.inner.__len__(other)

    @wraps(str.__lt__)
    def __lt__(self, other):
        return self.inner.__lt__(other)

    @wraps(str.__mod__)
    def __mod__(self, other):
        return self._from(self.inner.__mod__(other))

    @wraps(str.__mul__)
    def __mul__(self, other):
        return self._from(self.inner.__mul__(other))

    @wraps(str.__ne__)
    def __ne__(self, other):
        return self.inner.__ne__(other)

    def color(self, color: Color) -> Colorize:
        self.fg_color = color
        return self

    def on_color(self, color: Color) -> Colorize:
        self.bg_color = color
        return self

    def clear(self) -> Colorize:
        return Colorize(self.inner)

    def bold(self) -> Colorize:
        self.style += Styles.Bold
        return self

    def dimmed(self) -> Colorize:
        self.style += Styles.Dimmed
        return self

    def italic(self) -> Colorize:
        self.style += Styles.Italic
        return self

    def underline(self) -> Colorize:
        self.style += Styles.Underline
        return self

    def blink(self) -> Colorize:
        self.style += Styles.Blink
        return self

    def reversed(self) -> Colorize:
        self.style += Styles.Reversed
        return self

    def hidden(self) -> Colorize:
        self.style += Styles.Hidden
        return self

    def strikethrough(self) -> Colorize:
        self.style += Styles.Strikethrough
        return self

    def black(self) -> Colorize:
        return self.color(Color.Black)

    def red(self) -> Colorize:
        return self.color(Color.Red)

    def green(self) -> Colorize:
        return self.color(Color.Green)

    def yellow(self) -> Colorize:
        return self.color(Color.Yellow)

    def blue(self) -> Colorize:
        return self.color(Color.Blue)

    def magenta(self) -> Colorize:
        return self.color(Color.Magenta)

    def cyan(self) -> Colorize:
        return self.color(Color.Cyan)

    def white(self) -> Colorize:
        return self.color(Color.White)

    def bright_black(self) -> Colorize:
        return self.color(Color.BrightBlack)

    def bright_red(self) -> Colorize:
        return self.color(Color.BrightRed)

    def bright_green(self) -> Colorize:
        return self.color(Color.BrightGreen)

    def bright_yellow(self) -> Colorize:
        return self.color(Color.BrightYellow)

    def bright_blue(self) -> Colorize:
        return self.color(Color.BrightBlue)

    def bright_magenta(self) -> Colorize:
        return self.color(Color.BrightMagenta)

    def bright_cyan(self) -> Colorize:
        return self.color(Color.BrightCyan)

    def bright_white(self) -> Colorize:
        return self.color(Color.BrightWhite)

    def truecolor(self, r: int, b: int, g: int) -> Colorize:
        return self.color(Color.true_color(TrueColor(r, g, b)))

    def on_black(self) -> Colorize:
        return self.on_color(Color.Black)

    def on_red(self) -> Colorize:
        return self.on_color(Color.Red)

    def on_green(self) -> Colorize:
        return self.on_color(Color.Green)

    def on_yellow(self) -> Colorize:
        return self.on_color(Color.Yellow)

    def on_blue(self) -> Colorize:
        return self.on_color(Color.Blue)

    def on_magenta(self) -> Colorize:
        return self.on_color(Color.Magenta)

    def on_cyan(self) -> Colorize:
        return self.on_color(Color.Cyan)

    def on_white(self) -> Colorize:
        return self.on_color(Color.White)

    def on_bright_black(self) -> Colorize:
        return self.on_color(Color.BrightBlack)

    def on_bright_red(self) -> Colorize:
        return self.on_color(Color.BrightRed)

    def on_bright_green(self) -> Colorize:
        return self.on_color(Color.BrightGreen)

    def on_bright_yellow(self) -> Colorize:
        return self.on_color(Color.BrightYellow)

    def on_bright_blue(self) -> Colorize:
        return self.on_color(Color.BrightBlue)

    def on_bright_magenta(self) -> Colorize:
        return self.on_color(Color.BrightMagenta)

    def on_bright_cyan(self) -> Colorize:
        return self.on_color(Color.BrightCyan)

    def on_bright_white(self) -> Colorize:
        return self.on_color(Color.BrightWhite)

    def on_truecolor(self, r: int, b: int, g: int) -> Colorize:
        return self.on_color(Color.true_color(TrueColor(r, g, b)))
