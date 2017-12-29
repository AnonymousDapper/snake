import discord, re

from discord.ext import commands

FULL_ID = re.compile(r"^(?P<id>[0-9]{,23})$")
ROLE_ID = re.compile(r"^<@&(?P<id>[0-9]{,23})>$")
CHANNEL_ID = re.compile(r"^<#(?P<id>[0-9]{,23})>$")
MEMBER_ID = re.compile(r"^<@!?(?P<id>[0-9]{,23})>$")

class MultiMention(commands.Converter):
    async def convert(self, ctx, argument): # its never going to be a private channel
        message = ctx.message
        channel = message.channel
        guild = channel.guild
        author = message.author

        full_id = FULL_ID.match(argument)
        role_mention = ROLE_ID.match(argument)
        channel_mention = CHANNEL_ID.match(argument)
        user_mention = MEMBER_ID.match(argument)

        if full_id is not None:
            obj = discord.utils.get(list(guild.members) + list(guild.channels) + guild.roles, id=int(full_id.group("id")))
            if obj is None:
                raise commands.BadArgument(f"{argument} could not be found")
            else:
                return obj

        elif role_mention is not None:
            role = discord.utils.get(guild.roles, id=int(role_mention.group("id")))
            if role is None:
                raise commands.BadArgument(f"Role {argument} could not be found")
            else:
                return role

        elif channel_mention is not None:
            channel = discord.utils.get(guild.channels, id=int(channel_mention.group("id")))
            if channel is None:
                raise commands.BadArgument(f"Channel {argument} could not be found")
            else:
                return channel

        elif user_mention is not None:
            user = discord.utils.get(guild.members, id=int(user_mention.group("id")))
            if user is None:
                raise commands.BadArgument(f"Member {argument} could not be found")
            else:
                return user

        elif argument.lower() == "guild":
            return guild

        elif argument.lower() == "channel":
            return channel

        elif argument.lower() == "role":
            return author.top_role

        else:
            raise commands.BadArgument(f"Unrecognized input '{argument}'")