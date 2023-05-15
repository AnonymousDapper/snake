# MIT License
#
# Copyright (c) 2016-2023 AnonymousDapper
#


from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from PIL import Image, ImageColor
from yarl import URL

from .utils.logger import get_logger

if TYPE_CHECKING:
    from ..snake import SnakeBot

log = get_logger()


class Images(commands.Cog):
    def __init__(self, bot: SnakeBot):
        self.bot = bot

    @commands.hybrid_command(name="color", brief="show color swatch")
    async def get_color(self, ctx: commands.Context, *, color: str):
        color = color.strip("`")
        try:
            color_val = ImageColor.getrgb(color)

        except ValueError as e:
            await ctx.reply(f"\N{CROSS MARK} Can't parse color: `{e}`", ephemeral=True)

        else:
            frame = Image.new("RGBA", (256, 256), color_val)
            buf = BytesIO()
            frame.save(buf, format="PNG")
            buf.seek(0)

            attachment = discord.File(buf, filename="color.png", spoiler=False)

            int_color = (color_val[0] << 16) | (color_val[1] << 8) | (color_val[2])

            embed = discord.Embed(
                title=f"`{color}` : **#{int_color:0>6x}**", color=int_color
            )
            embed.set_image(url="attachment://color.png")

            await ctx.send(file=attachment, embed=embed)

    @commands.hybrid_command(name="xkcd", brief="Fetch a comic from xkcd.com")
    async def slash_xkcd(self, ctx: commands.Context, comic: Optional[int] = None):
        if comic is None:
            async with self.bot.aio_session.get(
                "https://c.xkcd.com/random/comic", allow_redirects=False
            ) as header_response:
                comic_url = URL(header_response.headers["Location"])
        else:
            comic_url = URL(f"https://xkcd.com/{comic}/")

        if comic_url is None:
            await ctx.send("\N{CROSS MARK} URL could not be parsed. ", ephemeral=True)
            log.error(f"XKCD comic url: {comic_url} ({type(comic_url)}")
        else:
            self.comic = int(comic_url.parts[-2])

            async with self.bot.aio_session.get(comic_url / "info.0.json") as response:
                if response.status != 200:
                    if response.status == 404:
                        await ctx.send(
                            "\N{CROSS MARK} That comic could not be found",
                            ephemeral=True,
                        )

                    else:
                        await ctx.send(
                            "\N{CROSS MARK} Could not connect to server, please try again later.",
                            ephemeral=True,
                        )

                    return

                data = await response.json()
                result_embed = discord.Embed(
                    title=f"{data['title']} - {data['num']}",
                    url=str(comic_url),
                    description=data["alt"],
                )
                result_embed.set_footer(
                    icon_url="https://xkcd.com/s/919f27.ico", text="Served by XKCD"
                )
                result_embed.set_image(url=data["img"])

                await ctx.send(embed=result_embed)


async def setup(bot):
    await bot.add_cog(Images(bot))
