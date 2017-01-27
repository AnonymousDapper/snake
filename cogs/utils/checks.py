import discord.utils

from discord.ext import commands

def is_owner_check(message):
  return message.author.id in ["163521874872107009", "190966952649293824"]

def is_server_owner_check(message):
  return message.author.id == message.server.owner.id


def check_permissions(ctx, perms):
  message = ctx.message
  if is_owner_check(message) or is_server_owner_check(message):
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
  if channel.is_private:
    return False
  role = discord.utils.find(check, author.roles)

def is_owner():
  return commands.check(lambda ctx: is_owner_check(ctx.message))

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
