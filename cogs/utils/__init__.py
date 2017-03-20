import discord, re

from discord.ext import commands

FULL_ID = re.compile(r"^(?P<id>[0-9]{,23})$")
ROLE_ID = re.compile(r"^<@&(?P<id>[0-9]{,23})>$")
CHANNEL_ID = re.compile(r"^<#(?P<id>[0-9]{,23})>$")
MEMBER_ID = re.compile(r"^<@!?(?P<id>[0-9]{,23})>$")

class MultiMention(commands.Converter):
    def __init__(self, ctx, argument):
        super().__init__(ctx, argument)

    def convert(self): # its never going to be a private channel
        message = self.ctx.message
        channel = message.channel
        server = channel.server
        author = message.author

        full_id = FULL_ID.match(self.argument)
        role_mention = ROLE_ID.match(self.argument)
        channel_mention = CHANNEL_ID.match(self.argument)
        user_mention = MEMBER_ID.match(self.argument)

        if full_id is not None:
            obj = discord.utils.get(list(server.members) + list(server.channels) + server.roles, id=full_id.group("id"))
            if obj is None:
                raise commands.BadArgument(f"{self.argument} could not be found")
            else:
                return obj

        elif role_mention is not None:
            role = discord.utils.get(server.roles, id=role_mention.group("id"))
            if role is None:
                raise commands.BadArgument(f"Role {self.argument} could not be found")
            else:
                return role

        elif channel_mention is not None:
            channel = discord.utils.get(server.channels, id=channel_mention.group("id"))
            if channel is None:
                raise commands.BadArgument(f"Channel {self.argument} could not be found")
            else:
                return channel

        elif user_mention is not None:
            user = discord.utils.get(server.members, id=user_mention.group("id"))
            if user is None:
                raise commands.BadArgument(f"Member {self.argument} could not be found")
            else:
                return user

        elif self.argument.lower() == "server":
            return server

        elif self.argument.lower() == "channel":
            return channel

        elif self.argument.lower() == "role":
            return author.top_role

        else:
            raise commands.BadArgument(f"Unrecognized input '{self.argument}'")