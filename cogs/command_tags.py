from discord.ext import commands
from .utils import sql
from .utils.tag_manager import parser as tag_parser

import json

ALLOWED_ATTRIBUTES = [
    # Object
    "id",
    "created_at",
    # User
    "name",
    "discriminator",
    "avatar",
    "bot",
    "avatar_url",
    "default_avatar",
    "default_avatar_url",
    "mention",
    "display_name",
    # Message
    "edited_at",
    "tts",
    "content",
    "mention_everyone",
    "mentions",
    "channel_mentions",
    "role_mentions",
    "pinned",
    "clean_content",
    # Reaction
    "custom_emoji",
    "count",
    "me",
    # Embed
    "title",
    "description",
    "url",
    "color",
    # Guild
    "name",
    "afk_timeout",
    "region",
    "afk_channel",
    "icon",
    "owner",
    "unavailable",
    "large",
    "mfa_level",
    "splash",
    "default_channel",
    "icon_url",
    "splash_url",
    "member_count",
    # Member
    "joined_at",
    "status",
    "game",
    "nick",
    # Channel
    "topic",
    "is_private",
    "position",
    "bitrate",
    "user_limit",
    "is_default"
    # TODO: add attributes per-type and global
]

class Tag:
    def __init__(self, tag):
        self.name = tag.name
        self.author_id = tag.author_id
        self.content = tag.content
        self.uses = tag.uses
        self.timestamp = tag.timestamp

    def __repr__(self):
        return f"<Tag(name='{self.name}', author_id={self.author_id}, uses={self.uses}, timestamp='{self.timestamp}')>"

class TagOverrides(tag_parser.TagFunctions):
    def __init__(self, bot, ctx, tag, **kwargs):
        super().__init__()

        self.bot = bot
        self.ctx = ctx
        self.tag = tag
        self.debug = kwargs.get("debug", False)
        self.data_cache = {}

        setattr(self, "if", self._TagOverrides__compare)

    def get(self, key, default='Does not exist'):
        with self.bot.db_scope() as session:
            tag_dict = session.query(sql.TagVariable).filter_by(tag_name=self.tag.name).first()

            if tag_dict is None:
                tag_dict = sql.TagVariable(tag_name=self.tag.name, data={})
                session.add(tag_dict)

            return tag_dict.data.get(key, default)

    def set(self, key, value):
        with self.bot.db_scope() as session:
            tag_dict = session.query(sql.TagVariable).filter_by(tag_name=self.tag.name).first()
            if tag_dict is None:
                tag_dict = sql.TagVariable(tag_name=self.tag.name, data={})
                session.add(tag_dict)

            tag_dict.data[key] = value

            self.bot.db.flag(tag_dict, "data") # force it to re-commit

    def fetch(self, key):
        return self.data_cache[key]

    def cache(self, key, value):
        self.data_cache[key] = value

    def attr(self, obj, key):
        if key not in ALLOWED_ATTRIBUTES:
            raise ValueError(f"Illegal attribute {key}")
        else:
            return getattr(obj, key)

    def author(self):
        return self.ctx.author

    def self(self):
        return self.tag

    def channel(self):
        return self.ctx.channel

    def guild(self):
        return self.ctx.guild

    def __compare(self, condition, result, else_=''):
        if condition:
            return result
        else:
            return else_

    def eq(self, first, second):
        return first == second or str(first).lower() == str(second).lower()

    def gt(self, first, second):
        return float(first) > float(second)

    def lt(self, first, second):
        return float(first) < float(second)

    def gte(self, first, second):
        return float(first) >= float(second)

    def lte(self, first, second):
        return float(first) <= float(second)

    def len(self, item):
        try:
            return len(item)
        except:
            return len(str(item))

class Tags:
    def __init__(self, bot):
        self.bot = bot

    async def get_tag(self, tag_name):
        with self.bot.db_scope() as session:
            tag = session.query(sql.Tag).filter_by(name=tag_name).first()
            if tag is not None:
                tag.uses = tag.uses + 1
                return Tag(tag)
            else:
                return None

    @commands.group(name="tag", brief="tag manager", invoke_without_command=True)
    async def tag_group(self, ctx, tag_name:str):
        tag = await self.get_tag(tag_name)
        if tag is not None:
            try:
                parser = tag_parser.Parser(tag.content, debug=self.bot._DEBUG, override=TagOverrides(self.bot, ctx, tag, debug=self.bot._DEBUG))
                result = await parser()
            except Exception as e:
                await ctx.send(f"```diff\n- [{type(e).__name__}]: {e}\n```")
                return

            result = str(result)
            await ctx.send(f"\* {tag.name} is empty \*" if result == "" else result)

        else:
            await ctx.send(f"\N{CROSS MARK} Sorry, '{tag_name}' doesn't exist")

    @tag_group.command(name="raw", brief="view raw contents")
    async def raw_tag(self, ctx, tag_name:str):
        tag = await self.get_tag(tag_name)
        if tag is not None:
            await ctx.send(f"**{tag.name}**\n`{tag.content}`")

        else:
            await ctx.send(f"\N{CROSS MARK} Sorry, '{tag_name}' doesn't exist")

    @tag_group.command(name="test", brief="run a test parse")
    async def test_tag(self, ctx, *, text:str):
        tag = await self.get_tag("test")
        try:
            parser = tag_parser.Parser(text, debug=self.bot._DEBUG, override=TagOverrides(self.bot, ctx, tag, debug=self.bot._DEBUG))
            result = await parser()
        except Exception as e:
            await ctx.send(f"```diff\n- [{type(e).__name__}]: {e}\n```")
            return

        result = str(result)
        await ctx.send(f"\* {tag.name} is empty \*" if result == "" else result)

def setup(bot):
    bot.add_cog(Tags(bot))