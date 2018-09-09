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

import inspect
import os
import subprocess
import textwrap

from contextlib import redirect_stdout, redirect_stderr, suppress
from functools import partial
from io import StringIO
from types import BuiltinFunctionType

import discord
import sqlalchemy

from discord.ext import commands

from .utils import checks
from .utils.logger import get_logger
from .utils.math_parser import MathParser

log = get_logger()

# Inspect function implementation source from Jishaku (https://github.com/Gorialis/jishaku)
# Copyright (c) 2017 Devon R

MAGIC_OPERATOR_NAMES = [
    (("__eq__",), "=="),
    (("__ne__",), "!="),
    (("__lt__",), "<"),
    (("__gt__",), ">"),
    (("__le__",), "<="),
    (("__ge__",), ">="),
    (("__pos__",), "+N"),
    (("__neg__",), "-N"),
    (("__invert__",), "~"),
    (("__add__", "__radd__"), "+"),
    (("__sub__", "__rsub__"), "-"),
    (("__mul__", "__rmul__"), "*"),
    (("__floordiv__", "__rfloordiv__"), "//"),
    (("__div__", "__rdiv__"), "/"),
    (("__mod__", "__rmod__"), "%"),
    (("__pow__", "__rpow__"), "**"),
    (("__lshift__", "__rlshift__"), "<<"),
    (("__rshift__", "__rrshift__"), ">>"),
    (("__and__", "__rand__"), "&"),
    (("__or__", "__ror__"), "|"),
    (("__xor__", "__rxor__"), "^"),
    (("__iadd__",), "+="),
    (("__isub__",), "-="),
    (("__imul__",), "*="),
    (("__ifloordiv__",), "//="),
    (("__idiv__",), "/="),
    ("__imod__", "%="),
    (("__ipow__",), "**="),
    (("__ilshift__",), "<<="),
    (("__irshift__",), ">>="),
    (("__iand__",), "&="),
    (("__ior__",), "|="),
    (("__ixor__",), "^=")
]

CALC_HELP = """
    Operators |  Explanation || Values | Explanation
    ----------+--------------++--------+-----------------------
     X +  X   | add          ||     pi | pi (3.14..)
     X -  X   | subtract     ||      e | Euler's number
     X *  X   | multiply     ||    inf | Infinity
     X /  X   | divide       ||    nan | Not A Number
     X // X   | floor div    ||    tau | tau (2 * pi)
     X %  X   | modulo       ||      c | Speed of light (m/s)
     X ** X   | pow (exp)    ||      g | Standard gravity (m/s²)
         ~X   | bit invert   ||      a | Avogadro's number
     X ^  X   | bit xor      ||    atm | Standard atmosphere (Pa)
     X |  X   | bit or       ||      h | Planck's constant (Js)
     X &  X   | bit and      ||--------+-------------------------
     X << X   | bit L shift  || Check out the Python docs for more info
     X >> X   | bit R shift  || https://docs.python.org/3.7/library/math.html
    ----------+--------------|| (Most of the math module functions are usable)
"""

class Debug:
    def __init__(self, bot):
        self.bot = bot
        self.math_parser = MathParser()

        self.NL = "\n" # for embedding in f-strings

    # Strip formatting from codeblocks
    @staticmethod
    def clean(code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])

        return code.strip("` \n")

    # Utility function for length checking and uploading if required
    async def check_length(self, content):
        if len(content) > 2000:
            url = await self.bot.paste_text(self.clean(content))
            return f"\N{WARNING SIGN} Output too long. View result at <{url}>"

        else:
            return content

    # Utility function to eval code
    async def do_eval(self, scope, code):
        try:
            compiled = compile(code, "<eval>", "eval")
            scope["__compiled"] = compiled

            result = eval(compiled, scope)

        except SyntaxError as e:
            return True, f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"

        except Exception as e:
            return True, f"```md\n- {type(e).__name__}: {e}\n```"

        else:
            if inspect.isawaitable(result):
                result = await result

            return False, result

    # Utility function to exec code
    async def do_exec(self, scope, code):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):
                try:
                    compiled = compile(code, "<exec>", "exec")
                    scope["__compiled"] = compiled

                    exec(compiled, scope)

                    raw_result = await scope["__coro"]()

                except SyntaxError as e:
                    return True, f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```", None

                except BaseException as e:
                    return True, f"```md\n- {type(e).__name__}: {e}\n```", None

        result_out = str(stdout.getvalue())
        result_err = str(stderr.getvalue())

        result = f"```py\n{result_out}{f'{self.NL}======== Errors ========{self.NL}{result_err}' if result_err != '' else ''}{f'{self.NL}======== Returned Value ========{self.NL}{repr(raw_result)}' if raw_result is not None else ''}\n```"

        return False, result, raw_result

    # Utility function to scrape information from a code result
    def get_info(self, result):
        data = repr(result)

        info = []

        info.append(("Type", type(result).__name__))
        info.append(("Memory", hex(id(result))))

        is_builtin = isinstance(result, BuiltinFunctionType)

        # Get module name, suppressing errors
        with suppress(TypeError, AttributeError):
            info.append(("Module", inspect.getmodule(result).__name__))

        # Get source file
        with suppress(TypeError):
            location = inspect.getfile(result)
            cwd = os.getcwd

            if location.startswith(cwd):
                location = f".{location[len(cwd):]}"

            info.append(("File", location))

        # Get source lines
        with suppress(OSError, TypeError):
            lines, offset = inspect.getsourcelines(result)

            info.append(("Lines", f"L{offset} - L{offset + len(lines)}"))

        # Get signature
        with suppress(TypeError, AttributeError, ValueError):
            info.append(("Signature", f"{result.__name__ if hasattr(result, '__name__') else type(result).__name__}{inspect.signature(result)}"))

        # Get inheritance order
        with suppress(TypeError, AttributeError):
            if is_builtin:
                info.append(("Inheritance", "is builtin"))

            else:
                if inspect.isclass(result):
                    obj = result

                else:
                    obj = type(result)

                info.append(("Inheritance", " -> ".join(thing.__name__ for thing in inspect.getmro(obj))))

        # Get supported operators
        info.append(("Operators",  " ".join(block[1] for block in MAGIC_OPERATOR_NAMES if any(hasattr(result, name) for name in block[0]))))


        # Get length
        if isinstance(result, (str, tuple, list, bytes, set)):
            info.append(("Length", len(result)))

        return f"```prolog\n{data}\n\n======== Data ========\n\n{self.NL.join(f'{a:12.12} = {b}' for a, b in info)}\n```"

    # Run code in eval mode
    @commands.command(name="debug", brief="eval mode")
    @checks.is_developer()
    async def run_debug(self, ctx, *, code: str):
        source = self.clean(code)

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_eval(scope, source)

        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)
            return

        if not error:
            result = await self.check_length(f"```py\n{result}\n```")

        await ctx.send(result)

    # Run code in exec mode
    @commands.command(name="run", brief="exec mode")
    @checks.is_developer()
    async def run_exec(self, ctx, *, code: str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result, raw = await self.do_exec(scope, source)

        if isinstance(raw, discord.Embed):
            await ctx.send(embed=raw)

        if not error:
            result = await self.check_length(result)

        await ctx.send(result)

    # Run SQL query
    @commands.command(name="sql", brief="execute sql")
    @checks.is_developer()
    async def run_sql(self, ctx, *, query: str):
        sql = self.clean(query)

        if not sql.endswith(";"):
            sql += ";"

        try:
            results = await self.bot.loop.run_in_executor(None, partial(self.bot.db.engine.execute, sql))


        except sqlalchemy.exc.ProgrammingError as e:
            await ctx.send(f"```diff\n- {e.orig.message}\n```\n{e.orig.details.get('hint', 'Unknown fix')}\n\nDouble check your query:\n```sql\n{e.statement}\n{' ' * (int(e.orig.details.get('position', '0')) - 1)}^\n```")
            return

        except Exception as e:
            await ctx.send(f"```diff\n- {type(e).__name__}: {e}\n```")
            return

        if not results.returns_rows:
            await self.bot.post_reaction(ctx.message, success=True)

        else:
            result_list = results.fetchall()

            if len(result_list) == 0:
                await ctx.send("\N{WARNING SIGN} Query returned 0 rows")

            else:
                row_names = results.keys()

                # format a list of items
                clr = lambda arr: ", ".join(str(item) for item in arr)

                # f-string to format total result lsit
                result = f"```md\n# Columns: {', '.join(row_names)}\n# {len(result_list)} total rows\n\n{self.NL.join('- ' + clr(arg) for arg in result_list)}\n```"

                await ctx.send(await self.check_length(result))

    # Run shell commands
    @commands.command(name="sh", brief="system terminal")
    @commands.is_owner()
    async def run_shell(self, ctx, *, command: str):
        command = self.clean(command)

        result = await self.bot.loop.run_in_executor(None,
            partial(
                subprocess.run,
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                universal_newlines=True
            )
        )

        out_result = result.stdout
        err_result = result.stderr
        result = f"```diff\n+ ----- stdout -----\n{out_result}\n{('- ----- stderr -----' + self.NL + err_result) if err_result != '' else ''}\n```"

        await ctx.send(await self.check_length(result))

    # Expression inspection group
    @commands.group(name="inspect", brief="inspect an expression", invoke_without_command=True)
    @checks.is_developer()
    async def inspect_group(self, ctx, *, expression: str):
        await ctx.invoke(self.inspect_debug, code=expression)

    # Actual command to inspect a debug result
    @inspect_group.command(name="debug", brief="inspect an eval result")
    @checks.is_developer()
    async def inspect_debug(self, ctx, *, code: str):
        source = self.clean(code)

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result = await self.do_eval(scope, source)

        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)

        if error:
            await ctx.send(result)

        else:
            await ctx.send(await self.check_length(self.get_info(result)))

    # Actual command to inspect a run result
    @inspect_group.command(name="run", brief="inspect an exec result")
    @checks.is_developer()
    async def inspect_run(self, ctx, *, code: str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(dict(
            self=self,
            bot=self.bot,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        error, result, raw = await self.do_exec(scope, source)

        if isinstance(raw, discord.Embed):
            await ctx.send(embed=result)

        if error:
            await ctx.send(result)

        else:
            await ctx.send(await self.check_length(self.get_info(raw)))

    # Public math command
    @commands.group(name="calc", brief="run math calcs", invoke_without_command=True)
    async def calc_group(self, ctx, *, expression: str):
        source = self.clean(expression)

        try:
            result = self.math_parser(source)
            await ctx.send(await self.check_length(f"```matlab\n{source}\n%%======== Output ========\n{result}\n```"))

        except Exception as e:
            await ctx.send(f"```diff\n- [{type(e).__name__}]: {e}\n```\n*Hint: use the subcommand 'what' for more info*")

    # Calc reference command
    @calc_group.command(name="what", brief="reference for calc")
    async def calc_ref(self, ctx):
        await ctx.send(f"```prolog\n{textwrap.dedent(CALC_HELP)}\n```")



# Extension setup
def setup(bot):
    bot.add_cog(Debug(bot))
