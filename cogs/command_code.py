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
import sqlalchemy
import subprocess

from functools import partial

from discord.ext import commands

from .utils import checks
from .utils.logger import get_logger

logger = get_logger()

class Debug:
    def __init__(self, bot):
        self.bot = bot

        self.NL = "\n" # for embedding in f-strings

    # Strip formatting from codeblocks
    def clean(self, code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])

        return code.strip("` \n")

    # Utility function for length checking and uploading if required
    async def check_length(self, content):
        if len(content) > 2000:
            url = await self.bot.paste_text(content)
            return f"\N{WARNING SIGN} Output too long. View result at <{url}>"

        else:
            return content

    # Run code in eval mode
    @commands.command(name="debug", brief="eval mode")
    @checks.is_owner()
    async def run_debug(self, ctx, *, code:str):
        source = self.clean(code)

        scope = globals()
        scope.update(dict(
            bot=self,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        try:
            compiled = compile(source, "<eval>", "eval")
            scope["__compiled"] = compiled

            result = eval(compiled, scope)

        except SyntaxError as e:
            await ctx.send(f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```")

        except Exception as e:
            await ctx.send(f"```md\n- {type(e).__name__}: {e}\n```")


        else:
            if inspect.isawaitable(result):
                result = await result

            await ctx.send(await self.check_length(f"```py\n{str(result)}\n```"))

    # Run code in exec mode
    @commands.command(name="run", brief="exec mode")
    @checks.is_owner()
    async def run_exec(self, ctx, *, code:str):
        source = "async def __coro():\n  " + "\n  ".join(self.clean(code).split("\n"))

        scope = globals()
        scope.update(dict(
            bot=self,
            message=ctx.message,
            guild=ctx.guild,
            channel=ctx.channel,
            author=ctx.author,
            ctx=ctx,
            __code=source
        ))

        with self.bot.stdout_wrapper() as stdout, self.bot.stderr_wrapper() as stderr:
            try:
                compiled = compile(source, "<exec>", "exec")
                scope["__compiled"] = compiled

                exec(compiled, scope)

                await scope["__coro"]()

            except SyntaxError as e:
                await ctx.send(f"```py\n{e.text}\n{'^':>{e.offset}}\n{type(e).__name__}: {e}\n```")
                return

            except Exception as e:
                await ctx.send(f"```md\n- {type(e).__name__}: {e}\n```")
                return

        result_out = str(stdout.getvalue())
        result_err = str(stderr.getvalue())

        result = f"```py\n{result_out}\n{('########## Errors ##########' + self.NL + result_err) if result_err != '' else ''}\n```"

        await ctx.send(await self.check_length(result))




# Extension setup
def setup(bot):
    bot.add_cog(Debug(bot))