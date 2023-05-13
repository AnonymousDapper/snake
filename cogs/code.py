# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

import dis
import inspect
import os
import subprocess
from ast import PyCF_ALLOW_TOP_LEVEL_AWAIT
from contextlib import redirect_stderr, redirect_stdout, suppress
from datetime import datetime, timedelta
from functools import partial
from io import StringIO
from types import BuiltinFunctionType
from typing import TYPE_CHECKING, Any, Tuple

import discord
import import_expression as ie
from discord.ext import commands

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot
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
    (("__ixor__",), "^="),
]


class Code(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot
        self.NL = "\n"

    # Strip formatting from codeblocks
    @staticmethod
    def clean(code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])

        return code.strip("` \n")

    # Utility function for length checking and uploading if required
    async def check_length(self, content) -> str:
        if len(content) > 2000:
            paste = await self.bot.myst_client.create_paste(
                filename="output.txt",
                content=self.clean(content),
                expires=datetime.utcnow() + timedelta(minutes=30),
            )
            return f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} Output too long. View result at <{paste.url}>"

        else:
            return content

    # Utility function to eval code
    async def do_eval(self, scope, code) -> Tuple[bool, str, Any]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):
                try:
                    compiled = ie.compile(code, "<eval>", "eval")
                    scope["__compiled"] = compiled

                    result = eval(compiled, ie.update_globals(scope))

                except SyntaxError as e:
                    return (
                        True,
                        f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```",
                        None,
                    )

                except Exception as e:
                    return True, f"```md\n- {type(e).__name__}: {e}\n```", None

                else:
                    if inspect.isawaitable(result):
                        result = await result

        result_out = (
            (o := str(stdout.getvalue())) and f"**+ Output +**\n```py\n{o}\n```" or ""
        )
        result_err = (
            (e := str(stderr.getvalue())) and f"**! Error !**\n```py\n{e}\n```" or ""
        )

        stdout.close()
        stderr.close()

        return False, f"{result_err}\n{result_out}", result

    # Utility function to exec code
    async def do_exec(self, scope, code) -> Tuple[bool, str, Any]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):
                try:
                    compiled = ie.compile(code, "<exec>", "exec")
                    scope["__compiled"] = compiled

                    exec(compiled, ie.update_globals(scope))

                    raw_result = await scope["__coro"]()

                except SyntaxError as e:
                    return (
                        True,
                        f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```",
                        None,
                    )

                except BaseException as e:
                    return True, f"```md\n- {type(e).__name__}: {e}\n```", None

        result_out = (
            (o := str(stdout.getvalue())) and f"**+ Output +**\n```py\n{o}\n```" or ""
        )
        result_err = (
            (e := str(stderr.getvalue())) and f"**! Error !**\n```py\n{e}\n```" or ""
        )

        stdout.close()
        stderr.close()

        return (
            False,
            f"**= Result =**\n```py\n{raw_result!r}\n```\n{result_err}\n{result_out}",
            raw_result,
        )

    # Utility function to scrape information from a code result
    def get_info(self, result):
        data = repr(result)

        info = []

        info.append(("Type", type(result).__name__))
        info.append(("Memory", hex(id(result))))

        is_builtin = isinstance(result, BuiltinFunctionType)

        # Get module name, suppressing errors
        with suppress(TypeError, AttributeError):
            info.append(("Module", inspect.getmodule(result).__name__))  # type: ignore

        # Get source file
        with suppress(TypeError):
            location = inspect.getfile(result)
            cwd = os.getcwd()

            if location.startswith(cwd):
                location = f".{location[len(cwd):]}"

            info.append(("File", location))

        # Get source lines
        with suppress(OSError, TypeError):
            lines, offset = inspect.getsourcelines(result)

            info.append(("Lines", f"L{offset} - L{offset + len(lines)}"))

        # Get signature
        with suppress(TypeError, AttributeError, ValueError):
            info.append(
                (
                    "Signature",
                    f"{result.__name__ if hasattr(result, '__name__') else type(result).__name__}{inspect.signature(result)}",
                )
            )

        # Get inheritance order
        with suppress(TypeError, AttributeError):
            if is_builtin:
                info.append(("Inheritance", "is builtin"))

            else:
                if inspect.isclass(result):
                    obj = result

                else:
                    obj = type(result)

                info.append(
                    (
                        "Inheritance",
                        " -> ".join(thing.__name__ for thing in inspect.getmro(obj)),
                    )
                )

        # Get supported operators
        info.append(
            (
                "Operators",
                " ".join(
                    block[1]
                    for block in MAGIC_OPERATOR_NAMES
                    if any(hasattr(result, name) for name in block[0])
                ),
            )
        )

        # Get length
        if isinstance(result, (str, tuple, list, bytes, set)):
            info.append(("Length", len(result)))

        return f"```prolog\n{data}\n\n======== Data ========\n\n{self.NL.join(f'{a:12.12} = {b}' for a, b in info)}\n```"

    # Run code in eval mode
    @commands.command(name="debug", brief="eval mode")
    @commands.is_owner()
    async def run_debug(self, ctx: commands.Context, *, code: str):
        source = self.clean(code)

        scope = globals()
        scope.update(
            dict(
                self=self,
                bot=self.bot,
                message=ctx.message,
                guild=ctx.guild,
                channel=ctx.channel,
                author=ctx.author,
                ctx=ctx,
                __code=source,
            )
        )

        error, output, result = await self.do_eval(scope, source)

        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)
            return

        if not error:
            text = await self.check_length(f"```py\n{result}\n```")
            output = f"{text}\n{output}"

        await ctx.send(output)

    # Run code in exec mode
    @commands.command(name="run", brief="exec mode")
    @commands.is_owner()
    async def run_exec(self, ctx: commands.Context, *, code: str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(
            dict(
                self=self,
                bot=self.bot,
                message=ctx.message,
                guild=ctx.guild,
                channel=ctx.channel,
                author=ctx.author,
                ctx=ctx,
                __code=source,
            )
        )

        error, result, raw = await self.do_exec(scope, source)

        if isinstance(raw, discord.Embed):
            await ctx.send(embed=raw)

        if isinstance(raw, discord.ui.View):
            await ctx.send(view=raw)
            await raw.wait()

        if not error:
            result = await self.check_length(result)

        await ctx.send(result)

    # Run shell commands
    @commands.command(name="sh", brief="system terminal")
    @commands.is_owner()
    async def run_shell(self, ctx: commands.Context, *, command: str):
        command = self.clean(command)

        result = await self.bot.loop.run_in_executor(
            None,
            partial(
                subprocess.run,
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                universal_newlines=True,
            ),
        )

        out_result = (
            result.stdout
            and f"```ansi\n\x1b[32;1;4m+ ----- stdout ----- +\x1b[0m\n\n{result.stdout}\n```"
            or ""
        )
        err_result = (
            result.stderr
            and f"```ansi\n\x1b[31;1;4m! ----- stderr ----- !\x1b[0m\n\n{result.stderr}\n```"
            or ""
        )

        if len(out_result) == 0 and len(err_result) == 0:
            if result.returncode == 0:
                await self.bot.post_reaction(ctx.message, success=True)

            else:
                await ctx.send(
                    f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} No output; process exited with code {result.returncode}"
                )

        else:
            await ctx.send(await self.check_length(f"{out_result}\n{err_result}"))

    @commands.command(name="dis", brief="disassemble code")
    @commands.is_owner()
    async def disassemble_code(self, ctx: commands.Context, *, code: str):
        source = self.clean(code)

        buf = StringIO()

        try:
            code_obj = compile(source, "<exec>", "exec", PyCF_ALLOW_TOP_LEVEL_AWAIT)

        except SyntaxError as e:
            await ctx.send(
                f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```"
            )

        else:
            dis.disassemble(code_obj, file=buf)

            await ctx.send(await self.check_length(f"```py\n{buf.getvalue()}\n```"))

        finally:
            buf.close()

    # Expression inspection group
    @commands.group(
        name="inspect", brief="inspect an expression", invoke_without_command=True
    )
    @commands.is_owner()
    async def inspect_group(self, ctx: commands.Context, *, expression: str):
        await ctx.invoke(self.inspect_debug, code=expression)

    # Actual command to inspect a debug result
    @inspect_group.command(name="debug", brief="inspect an eval result")
    @commands.is_owner()
    async def inspect_debug(self, ctx: commands.Context, *, code: str):
        source = self.clean(code)

        scope = globals()
        scope.update(
            dict(
                self=self,
                bot=self.bot,
                message=ctx.message,
                guild=ctx.guild,
                channel=ctx.channel,
                author=ctx.author,
                ctx=ctx,
                __code=source,
            )
        )

        error, output, result = await self.do_eval(scope, source)

        if isinstance(result, discord.Embed):
            await ctx.send(embed=result)

        if error:
            await ctx.send(output)

        else:
            await ctx.send(await self.check_length(self.get_info(result)))

    # Actual command to inspect a run result
    @inspect_group.command(name="run", brief="inspect an exec result")
    @commands.is_owner()
    async def inspect_run(self, ctx: commands.Context, *, code: str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(
            dict(
                self=self,
                bot=self.bot,
                message=ctx.message,
                guild=ctx.guild,
                channel=ctx.channel,
                author=ctx.author,
                ctx=ctx,
                __code=source,
            )
        )

        error, result, raw = await self.do_exec(scope, source)

        if isinstance(raw, discord.Embed):
            await ctx.send(embed=raw)

        if error:
            await ctx.send(result)

        else:
            await ctx.send(await self.check_length(self.get_info(raw)))


async def setup(bot):
    await bot.add_cog(Code(bot))
