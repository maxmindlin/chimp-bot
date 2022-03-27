import asyncio
from functools import partial

import discord
import youtube_dl
from discord.ext import commands, tasks

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'filter': 'audioonly',
    'highWaterMark': 1<<25,
    'format': 'bestaudio',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicModule(commands.Cog):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.play_loop.start()
        self.skips = set()

    @tasks.loop()
    async def play_loop(self):
        self.next.clear()
        (ctx, url) = await self.queue.get()
        if url in self.skips:
            self.skips.remove(url)
            return
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
        embed = discord.Embed(title=f"Now playing: {player.title}", colour=0x87CEEB)
        await ctx.send(embed=embed)
        await self.next.wait()
        
    @play_loop.before_loop
    async def before_play_loop(self):
        await self.bot.wait_until_ready()
    
    @commands.command(name="play")
    async def play(self, ctx, *, val):
        embed = discord.Embed(title=f"Added to queue: {val}", colour=0x87CEEB)
        await ctx.send(embed=embed)
        await self.queue.put((ctx, val))
    
    @commands.command(name="skip")
    async def skip(self, ctx, *, name=None):
        if name is None:
            ctx.voice_client.stop()
        else:
            embed = discord.Embed(title=f"Added to skips: {name}", colour=0x87CEEB)
            await ctx.send(embed=embed)
            self.skips.add(name)

    @commands.command(name="stop")
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

    @commands.command(name="pause")
    async def pause(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.pause()

    @commands.command(name="resume")
    async def resume(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.resume()

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                embed = discord.Embed(title="You are not connected to a voice channel.", colour=0x87CEEB)
                await ctx.send(embed=embed)
                raise commands.CommandError("Author not connected to a voice channel.")