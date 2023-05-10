# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

import functools
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from .utils.logger import get_logger
from .utils.tex import LATEX_HEADER, Program

if TYPE_CHECKING:
    from ..snake import SnakeBot


log = get_logger()


class LatexMenu(discord.ui.View):
    def __init__(self, cog: "Math", uid: int, source: str):
        super().__init__()
        self.cog = cog
        self.uid = uid
        self.source = source
        self.staging_dir = Path(f"tex/staging/{uid}").resolve()
        self.deferred = False

    async def check_defer(self, interaction):
        if not self.deferred:
            await interaction.response.defer(ephemeral=True, thinking=True)
            self.deferred = True

    async def render_with_theme(self, dark=False):
        image_path = self.staging_dir / f"{self.uid}_{dark and 'dark' or 'light'}.png"

        if not image_path.exists():
            color = dark and "#212121" or "#f6f6f6"

            args = ["-background", color, "-alpha", "background"]
            if dark:
                args = ["-alpha", "deactivate", "+negate", *args]

            await self.cog.run_program(Program.Convert, str(self.staging_dir / f"{self.uid}.png"), *args, "-bordercolor", "transparent", "-border", "50", "-flatten", f"PNG32:{image_path}")

        return image_path


    @discord.ui.button(label="Source")
    async def get_source(self, interaction: discord.Interaction, button: discord.ui.Button):
        #await self.check_defer(interaction)
        await interaction.response.send_message(f"```latex\n{self.source}\n```", ephemeral=True)

    # @discord.ui.button(label="Redraw")
    # async def do_redraw(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     ...

    @discord.ui.button(label="Render Light")
    async def do_render_light_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        #await self.check_defer(interaction)

        image_path = await self.render_with_theme()

        await interaction.response.send_message(file=discord.File(image_path), ephemeral=True)

    @discord.ui.button(label="Render Dark")
    async def do_render_dark_theme(self, interaction: discord.Interaction, button: discord.ui.Button):
        #await self.check_defer(interaction)
        image_path = await self.render_with_theme(dark=True)

        await interaction.response.send_message(file=discord.File(image_path), ephemeral=True)

class LatexRenderError(RuntimeError):
    ...


class Math(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot
        self.COMPILE_PATH = Path("cogs/utils/tex/compile.sh").resolve()

    @staticmethod
    def clean(code):
        if code.startswith("```") and code.endswith("```"):
            return "\n".join(code.split("\n")[1:-1])

        return code.strip("` \n")

    async def clean_staging_dir(self):
        staging_dir = Path("tex/staging").resolve()
        subdirs = [str(p) for p in staging_dir.iterdir()]
        try:
            await self.run_program(Program.Rm, "-rf", *subdirs)

        except:
            pass

    async def run_subprocess(
        self,
        executable: str,
        args: list[str] | tuple[str],
        *,
        timeout: Optional[int] = None,
    ):
        command = [executable, *args]
        log.info(f"Preparing `{' '.join(command)}`")

        runner = functools.partial(
            subprocess.run,
            command,
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            timeout=timeout,
            check=True,
            universal_newlines=True,
        )

        try:
            _process = await self.bot.loop.run_in_executor(None, runner)

        except subprocess.TimeoutExpired as e:
            self.bot.log.error(f"Subprocess timed out after {e.timeout}s: `{e.cmd}`")
            log.error(f"Subprocess timed out: {e.output}")

            raise LatexRenderError(f"Timed out") from e

        except subprocess.CalledProcessError as e:
            self.bot.log.error(
                f"Subprocess exited with non-zero code {e.returncode}: `{e.cmd}`"
            )
            log.error(f"Subprocess exited non-zero {e.returncode}: {e.output}")

            raise LatexRenderError(f"Exited with non-zero status {e.returncode}: {e.output}")

    async def run_program(self, program: Program, *args: str, **kwargs):
        return await self.run_subprocess(str(program.value), args, **kwargs)

    async def render_latex(self, uid: str, source: str):
        staging_dir = Path(f"tex/staging/{uid}")

        await self.run_program(Program.MakeDir, "-p", str(staging_dir))

        latex = f"""{LATEX_HEADER}\n\\begin{{document}}\n{source}\n\\end{{document}}"""

        with (staging_dir / f"{uid}.tex").open("w") as f:
            f.write(latex)

        await self.run_program(Program.Sh, str(self.COMPILE_PATH), uid)

        return staging_dir / f"{uid}.png"

    @commands.hybrid_command(name="latex", brief="render latex", aliases=["tex"])
    async def latex_command(self, ctx: commands.Context, *, latex: str):
        try:
            image_path = await self.render_latex(str(ctx.message.id), self.clean(latex))

            attachment = discord.File(image_path)

        except Exception as e:
            await ctx.reply(
                f"\N{WARNING SIGN} Render Failed\n[{type(e).__name__}]: `{e}`",
                ephemeral=True
                #file=discord.File("tex/failed.png")
            )

        else:
            await ctx.send(file=attachment, view=LatexMenu(self, ctx.message.id, latex), reference=ctx.message, mention_author=False)



async def setup(bot):
    cog = Math(bot)
    await cog.clean_staging_dir()
    await bot.add_cog(cog)
