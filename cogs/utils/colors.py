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

# Set foreground color
def paint(text, color):
    if hasattr(_Text, color):
        return f"{getattr(_Text, color)}{text}{_Attributes.off}"
    raise ValueError(f"invalid color name: {color}")

# Set background color
def back(text, color):
    if hasattr(_Background, color):
        return f"{getattr(_Background, color)}{text}{_Attributes.off}"
    raise ValueError(f"invalid color name: {color}")

# Set text attributes
def attr(text, attribute):
    if hasattr(_Attributes, attribute):
        return f"{getattr(_Attributes, color)}{text}{_Attributes.off}"
    raise ValueError(f"invalid attribute name: {attribute}")
