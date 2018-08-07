import discord.utils

from discord.ext import commands

def is_owner_check(ctx):
    return ctx.message.author.id in ctx.bot.author_ids

def is_server_owner_check(message):
    if isinstance(channel, discord.abc.PrivateChannel):
        return False

    return message.author.id == message.guild.owner.id

def check_custom_permissions(ctx, **perms):
    if is_owner_check(ctx) or is_server_owner_check(ctx.message):
        return True

    author = ctx.message.author
    permissions = ctx.bot.permissions(author)
    print(permissions)
    return all(getattr(permissions, perm_name) == perm_value for perm_name, perm_value in perms.items())

def permissions(**perms):
    def predicate(ctx):
        return check_custom_permissions(ctx, **perms)
    return commands.check(predicate)

def check_permissions(ctx, perms):
    message = ctx.message
    if is_owner_check(ctx) or is_server_owner_check(message):
        return True
    channel = message.channel
    author = message.author
    resolved = channel.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())

def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True
    channel = ctx.message.channel
    author = ctx.message.author
    if isinstance(channel, discord.abc.PrivateChannel):
        return False
    role = discord.utils.find(check, author.roles)

def is_owner():
    return commands.check(lambda ctx: is_owner_check(ctx))

def is_server_owner():
    return commands.check(lambda ctx: is_server_owner_check(ctx.message) or is_owner_check(ctx.message))

def mod_or_permissions(mod_name, admin_name, **perms):
    def predicate(ctx):
        return role_or_permissions(ctx, lambda r: r.name in (mod_name, admin_name), **perms)
    return commands.check(predicate)

def admin_or_permissions(admin_name, **perms):
    def predicate(ctx):
        return role_or_permissions(ctx, lambda r: r.name == admin_name, **perms)
    return commands.check(predicate)
