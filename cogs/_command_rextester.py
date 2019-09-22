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


import re

from enum import Enum

#from discord.ext import commands

WHITESPACE_REGEXP = re.compile(r"\s+")
STATS_REGEXP = re.compile(r"(?:compilation time: (?P<compile_time>[\d.]+) sec, )*?absolute running time: (?P<run_time>[\d.]+) sec, cpu time: (?P<cpu_time>[\d.]+) sec, memory peak: (?P<mem_use>[\w\d ]+)", re.IGNORECASE)

class Language(Enum):
    # EnumName = [aliases], number, display_name, compiler_args
    DSharp = ["d#"], 3, "D#", ""
    C = ["c"], 6, "C", "-Wall, -std=gnu99 -O2 -o a.out source_file.c"
    CPlusPlus = ["cpp", "c++"], 7, "C++", "-Wall -std=c++14 -O2 -o a.out source_file.cpp"
    Php = ["php"], 8, "PHP", ""
    Pascal = ["pascal"], 9, "Pascal", ""
    ObjC = ["objc"], 10, "Objective-C", "-MMD -MP -DGNUSTEP -DGNUSTEP_BASE_LIBRARY=1 -DGNU_GUI_LIBRARY=1 -DGNU_RUNTIME=1 -DGNUSTEP_BASE_LIBRARY=1 -fno-strict-aliasing -fexceptions -fobjc-exceptions -D_NATIVE_OBJC_EXCEPTIONS -pthread -fPIC -Wall -DGSWARN -DGSDIAGNOSE -Wno-import -g -O2 -fgnu-runtime -fconstant-string-class=NSConstantString -I. -I /usr/include/GNUstep -I/usr/include/GNUstep -o a.out source_file.m -lobjc -lgnustep-base"
    Haskell = ["haskell", "hs"], 11, "Haskell", "-o a.out source_file.hs"
    Ruby = ["ruby"], 12, "Ruby", ""
    Perl = ["perl"], 13, "Perl", ""
    Lua = ["lua"], 14, "Lua", ""
    Assembly = ["x86asm", "asm"], 15, "x86 Assembly", ""
    Lisp = ["lisp"], 18, "Common Lisp", ""
    Prolog = ["prolog"], 19, "Prolog", ""
    Go = ["go"], 20, "Go", "-a a.out source_file.go"
    Scheme = ["scheme"], 22, "Scheme", ""
    Js = ["js", "javascript"], 23, "Javascript (Node)", ""
    Python = ["py", "python"], 24, "Python 3", ""
    Octave = ["octave"], 25, "Octave", ""
    D = ["d"], 30, "D", "source_file.d -fa.out"
    R = ["r"], 31, "R", ""
    Tcl = ["tcl"], 32, "Tcl", ""
    MySql = ["sql", "mysql"], 33, "MySQL", ""
    Swift = ["swift"], 37, "Swift", ""
    Bash = ["bash", "sh"], 38, "Bash", ""
    Erlang = ["erlang"], 40, "Erlang", ""
    Elixir = ["elixir"], 41, "Elixir", ""
    Ocaml = ["ocaml"], 42, "OCaml", ""
    Kotlin = ["kotlin"], 43, "Kotlin", ""
    Fortran = ["fortran"], 45, "Fortran", ""

    def __init__(self, aliases, number, display_name, compile_args):
        self.aliases = aliases
        self.number = number
        self.display_name = display_name
        self.compile_args = compile_args