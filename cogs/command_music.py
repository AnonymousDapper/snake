import discord, asyncio, math, traceback
from discord.ext import commands

opus_loaded = discord.opus.is_loaded()

class VoicePlayer:
  def __init__(self, message, player, client):
    self.requester = message.author
    self.channel = message.channel
    self.player = player
    self.client = client

  def __repr__(self):
    duration = self.player.duration
    fmt = "**{0.title}** by **{0.uploader}**"
    if duration:
      fmt += " ({0[0]}m {0[1]}s)".format(divmod(duration, 60))
    return fmt.format(self.player)

  def __str__(self):
    duration = self.player.duration
    fmt = "**{0.title}** by **{0.uploader}** in #{1.name}\n{0.likes} \N{THUMBS UP SIGN}\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2} - {0.views} views - {0.dislikes} \N{THUMBS DOWN SIGN}\N{EMOJI MODIFIER FITZPATRICK TYPE-1-2}\nRequested by **{2.display_name}**"
    if duration:
      fmt += " ({0[0]}m {0[1]}s)".format(divmod(duration, 60))
    return fmt.format(self.player, self.client.channel, self.requester)

class VoiceState:
  def __init__(self, bot):
    self.current = None
    self.voice = None
    self.bot = bot
    self.play_next_song = asyncio.Event()
    self.songs = asyncio.Queue()
    self.song_list = []
    self.skip_votes = set()
    self.audio_player = self.bot.loop.create_task(self.audio_player_task())

  def is_playing(self):
    if self.voice is None or self.current is None:
      return False
    player = self.current.player
    return not player.is_done()

  @property
  def player(self):
    return self.current.player

  def skip(self):
    if self.is_playing():
      self.player.stop()
    self.skip_votes.clear()

  def toggle_next(self):
    self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

  async def audio_player_task(self):
    while True:
        old_volume = self.current.player.volume if self.current else 0.5
        self.play_next_song.clear()

        if self.current:
          self.bot.log.info("Finishing {} in {} #{}".format(repr(self.current), self.current.client.channel.server.name, self.current.client.channel.name))

        self.current = await self.songs.get()
        self.song_list.pop()

        if self.current:
          self.bot.log.info("Playing {} in {} #{}".format(repr(self.current), self.current.client.channel.server.name, self.current.client.channel.name))

        await self.bot.send_message(self.current.channel, "Playing " + str(self.current))
        self.current.player.volume = old_volume
        try:
          self.current.player.start()
        except Exception as e:
          print(type(e).__name__, e)
        await self.play_next_song.wait()

class Music:
  def __init__(self, bot):
    self.bot = bot
    self.voice_states = {}

  async def on_voice_state_update(self, original_member, new_member):
    server = new_member.server
    state = self.get_voice_state(server)
    if state.voice is not None:
      listeners = sum(1 for m in state.voice.channel.voice_members if not m.bot)
      if listeners == 0:
        if state.is_playing():
          state.player.stop()
        try:
          state.audio_player.cancel()
          del self.voice_states[server.id]
          await state.voice.disconnect()
        except Exception as e:
          print(type(e).__name__, e)

  def get_voice_state(self, server):
    state = self.voice_states.get(server.id)
    if state is None:
      state = VoiceState(self.bot)
      self.voice_states[server.id] = state
    return state

  async def create_client(self, channel):
    voice = await self.bot.join_voice_channel(channel)
    state = self.get_voice_state(channel.server)
    state.voice = voice

  def __unload(self):
    for state in self.voice_states.values():
      try:
        state.audio_player.cancel()
        if state.voice:
          self.bot.loop.create_task(state.voice.disconnect())
      except:
        pass

  def required_votes(self, channel):
      member_count = len([m.id for m in channel.voice_members if not m.bot])
      user_limit = channel.user_limit or member_count
      required_votes = math.ceil(min(user_limit, member_count) / 2)
      return required_votes

  @commands.command(pass_context=True, no_pm=True, brief="join a voice channel")
  async def join(self, ctx, *, channel : discord.Channel):
    try:
      await self.create_client(channel)
    except discord.ClientException:
      await self.bot.say("\N{CROSS MARK} already in a voice channel")
    except discord.InvalidArgument:
      await self.bot.say("\N{CROSS MARK} no a valid voice channel")
    else:
      await self.bot.say("Joined **{}** in **{}**".format(channel.name, channel.server.name))

  @commands.command(pass_context=True, no_pm=True, brief="join your voice channel")
  async def summon(self, ctx):
    summon_channel = ctx.message.author.voice_channel
    if summon_channel is None:
      await self.bot.say("\N{CROSS MARK} no voice channel available")
      return False
    state = self.get_voice_state(ctx.message.server)
    if state.voice is None:
      state.voice = await self.bot.join_voice_channel(summon_channel)
    else:
      await state.voice.move_to(summon_channel)
    return True

  @commands.command(pass_context=True, no_pm=True, name="play", brief="play music")
  async def play_music(self, ctx, *, song : str):
    state = self.get_voice_state(ctx.message.server)
    opts = {
      "default_search": "auto",
      "quiet": True
    }

    if state.voice is None:
      success = await ctx.invoke(self.summon)
      if not success:
        return
    try:
      player =  await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
    except Exception as e:
      traceback.print_tb(e.__traceback__)
      await self.bot.send_message(ctx.message.channel, "Could not play song: [{}]: {}".format(type(e).__name__, e))
    else:
      player.volume = 0.5
      player_state = VoicePlayer(ctx.message, player, state.voice)
      await self.bot.say("Queued **{}**".format(player.title))
      await state.songs.put(player_state)
      state.song_list.append(player_state)

  @commands.command(pass_context=True, no_pm=True, aliases=["vol"], brief="adjust music volume")
  async def volume(self, ctx, value : int = None):
    state = self.get_voice_state(ctx.message.server)
    if state.is_playing():
      if value is not None:
        player = state.player
        player.volume = value / 100
        await self.bot.say("Changed volume to {:.0%}".format(player.volume))
      else:
        await self.bot.say("Volume is {:.0%}".format(player.volume))

  @commands.command(pass_context=True, no_pm=True, brief="pause music")
  async def pause(self, ctx):
    state = self.get_voice_state(ctx.message.server)
    if state.is_playing():
      state.player.pause()

  @commands.command(pass_context=True, no_pm=True, brief="resume music")
  async def resume(self, ctx):
    state = self.get_voice_state(ctx.message.server)
    if state.is_playing():
      state.player.resume()

  @commands.command(pass_context=True, no_pm=True, brief="leave a voice channel", help="also clears the song queue")
  async def leave(self, ctx):
    author = ctx.message.author
    server = ctx.message.server
    state = self.get_voice_state(server)

    print((author.id not in [server.owner.id, state.current.requester.id, "163521874872107009"]) or (author.id not in [server.owner.id, state.current.requester.id, "163521874872107009"] and ctx.message.channel.permissions_for(author).administrator is False))
    if state.is_playing():
      if (author.id not in [server.owner.id, state.current.requester.id, "163521874872107009"]) or (author.id not in [server.owner.id, state.current.requester.id, "163521874872107009"] and ctx.message.channel.permissions_for(author).administrator is False):
        await self.bot.say("\N{CROSS MARK} only the song requester can exit the channel while the song is playing")
        return
    if state.is_playing():
      state.player.stop()
    try:
      state.audio_player.cancel()
      del self.voice_states[server.id]
      await state.voice.disconnect()
    except:
      pass

  @commands.command(pass_context=True, no_pm=True, brief="stop music")
  async def stop(self, ctx):
    server = ctx.message.server
    voter = ctx.message.author
    state = self.get_voice_state(server)
    if (voter.id in [server.owner.id, state.current.requester.id, "163521874872107009"]) or (voter.id not in [server.owner.id, state.current.requester.id, "163521874872107009"] and ctx.message.channel.permissions_for(voter).administrator):
      if state.is_playing():
       state.player.stop()
    else:
      await self.bot.say("\N{CROSS MARK} only the song requester can stop the song")

  @commands.command(pass_context=True, no_pm=True, brief="skip a song")
  async def skip(self, ctx):
    server = ctx.message.server
    state = self.get_voice_state(ctx.message.server)
    if not state.is_playing():
      await self.bot.say("\N{CROSS MARK} no song to skip")
      return
    voter = ctx.message.author
    if not voter.voice_channel == state.voice.channel:
      await self.bot.say("\N{CROSS MARK} you must be listening to the song to skip it")
      return

    if (voter.id in [server.owner.id, state.current.requester.id, "163521874872107009"]) or (voter.id not in [server.owner.id, state.current.requester.id, "163521874872107009"] and ctx.message.channel.permissions_for(voter).administrator):
      await self.bot.say("Skipping **{}**".format(state.current.player.title))
      state.skip()
      return
    if voter.id not in state.skip_votes:
      state.skip_votes.add(voter.id)
      required_votes = self.required_votes(state.voice.channel)
      total_votes = len(state.skip_votes)
      if total_votes >= required_votes:
        await self.bot.say("Skip vote passed ({}/{}), skipping **{}**".format(total_votes, required_votes, state.current.player.title))
        state.skip()
        return
      else:
        await self.bot.say("{} voted to skip. ({}/{})".format(voter.display_name, total_votes, required_votes))
        return
    else:
      await self.bot.say("\N{CROSS MARK} you have already voted to skip this song")

  @commands.command(pass_context=True, no_pm=True, brief="see what is playing")
  async def playing(self, ctx):
    state = self.get_voice_state(ctx.message.server)
    if state.current is None:
      await self.bot.say("Nothing is playing")
    elif state.is_playing():
      total_votes = len(state.skip_votes)
      required_votes = self.required_votes(state.voice.channel)
      await self.bot.say("Now playing {}\n\n{} skips out of {} required".format(str(state.current), total_votes, required_votes))
    else:
      await self.bot.say("Nothing is playing")

  @commands.command(no_pm=True, alises=["songs"], pass_context=True, brief="see the song queue")
  async def queue(self, ctx):
    state = self.get_voice_state(ctx.message.server)
    song_queue = state.song_list
    if len(song_queue) > 0:
      result = ["Songs Currently Queued In **{}**".format(state.voice.channel.name), '']
      for count, song in enumerate(song_queue, start=1):
        result.append("{}. {}".format(count, repr(song)))
      result = "\n".join(result)
    else:
      result = "No songs queued in **{}**".format(state.voice.channel.name)
    await self.bot.say(result)

def setup(bot):
  bot.add_cog(Music(bot))