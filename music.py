import discord
import os
from discord.ext import commands
import yt_dlp
import asyncio
import re
from discord import Embed
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
COOKIE_PATH = 'cookies.txt'
USE_COOKIES = os.path.exists(COOKIE_PATH)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'files/%(id)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'verbose': True,
}

if USE_COOKIES:
    ## logger.info("✅ Menggunakan cookies.txt untuk yt_dlp")
    ytdl_format_options['cookiefile'] = COOKIE_PATH
else:
    logger.warning("⚠️ cookies.txt tidak ditemukan, lanjut tanpa cookie!")

ffmpeg_options = {
    'options': '-vn -b:a 384k',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

def is_youtube_url(text):
    youtube_regex = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+"
    return re.match(youtube_regex, text)

def normalize_youtube_url(query: str) -> str:
    query = query.replace("music.youtube.com", "www.youtube.com")
    match = re.search(r"v=([\w\-]+)", query)
    if match:
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    return query

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_autoplay = False
        self.autoplay_ctx = None
        self.last_video_info = None
        self.queue = asyncio.Queue()
        self.is_playing = False

    @commands.command()
    async def ping(self, ctx):
        embed = Embed(title="💠 Ping", color=9786367)
        embed.description = f"{round(self.bot.latency * 1000)}ms"
        await ctx.send(embed=embed)
    
    @commands.command()
    async def botinfo(self, ctx):
        embed = Embed(
            title="Rein Music",
            description=(
                "**Rein Music** is a free music bot that prioritizes **Quality** for the streaming experience "
                "on every voice channel.\n\n"
                "**Prefix Usage:**\n"
                "`r!play (URL)` or `(Music Title)`, `r!join` or `r!join (URL) / (Music Title)`, `r!leave`, `r!autoplay`.\n\n"
                "The application is still under development. For bug reporting or suggestions contact "
                "<@&1374411351660957818> if in the **Kirashore** Discord Server"
            ),
            color=12321023
        )

        embed.set_author(
            name="Bot Info",
            icon_url="https://drive.google.com/uc?id=1tyUl_vaV1KHqxC1aXurDedmpH-JHsFBE"
        )

        embed.set_thumbnail(url="https://drive.google.com/uc?id=1tuX4d61p_TC2DzLK1QnaMxPgMu0qF3bt")
        embed.set_image(url="https://drive.google.com/uc?id=1ttZoP44xpkNt0LqW6uzVe_iyuZDVmEsc")
        embed.set_footer(
            text="Development by @kirashore since May 2025. 23",
            icon_url="https://drive.google.com/uc?id=1jik28uuy2m54_BYM2x31Dw0OmdFTEVGX"
        )

        await ctx.send(embed=embed)


    @commands.command()
    async def join(self, ctx, *, title_or_url=None):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            embed = Embed(title="🔊 Join to Voice", color=9786367)
            embed.description = f'In : {channel} Channel'
            await ctx.send(embed=embed)

            if title_or_url:
                await self.search_and_play(ctx, title_or_url)
            else:
                embed = Embed(color=9786367)
                embed.description = 'Using r!play (URL) or r!play (Music Title)'
                await ctx.send(embed=embed)
        else:
            embed = Embed(title="🔴Cannot Join", color=9786367)
            embed.description = 'Join to Voice Channel first.'
            await ctx.send(embed=embed)

    @commands.command()
    async def stop(self, ctx):
        self.queue = asyncio.Queue()
        self.is_autoplay = False
        if ctx.voice_client:
            ctx.voice_client.stop()
            embed = Embed(title="⏹️ Stopped", color=9786367)
            embed.description = "⏹️ Playback Hibernated, Autoplay Shutdown, and Queue deleted."
            await ctx.send(embed=embed)
        else:
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)

    @commands.command()
    async def play(self, ctx, *, title_or_url):
        vc = ctx.voice_client
        if not vc:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
                embed = Embed(title="🔊 Join to Voice", color=9786367)
                embed.description = f'In: {ctx.author.voice.channel} Voice'
                await ctx.send(embed=embed)
            else:
                embed = Embed(title="🔴Prefix Error", color=9786367)
                embed.description = "Join to Voice Channel first."
                await ctx.send(embed=embed)
                return

        await self.queue.put((ctx, title_or_url))
        embed = Embed(title="▶️ Arrayed to list", color=9786367)
        embed.description = f"`{title_or_url}`"
        await ctx.send(embed=embed)

        if not self.is_playing:
            await self.start_queue()

    async def search_and_play(self, ctx, title_or_url):
        try:
            title_or_url = normalize_youtube_url(title_or_url)
            ## logger.debug(f"🔍 Mencari: {title_or_url}")
            if is_youtube_url(title_or_url):
                data = ytdl.extract_info(title_or_url, download=False)
            else:
                data = ytdl.extract_info(f"ytsearch:{title_or_url}", download=False)
                entries = data.get('entries')
                if not entries:
                    embed = Embed(title="❌ Failed", color=9786367)
                    embed.description = f'Cannot finding : "{title_or_url}".'
                    await ctx.send(embed=embed)
                    return
                data = entries[0]

            logger.debug(f"🎵 Video ditemukan: {data['title']}")
            audio_url = data.get('url')
            if not audio_url:
                embed = Embed(title="🔴 URL Error", color=9786367)
                embed.set_author(name="🎶 Log")
                embed.description = "⚠️ URL Failed to fetch during process"
                await ctx.send(embed=embed)
                return

            self.last_video_info = data
            await self.play_audio(ctx, audio_url)

        except yt_dlp.utils.DownloadError as e:
            logger.exception("❌ Gagal ambil video:")
            embed = Embed(title="🔴 Error", color=9786367)
            embed.description = "❌ Failed fetching data"
            await ctx.send(embed=embed)
        except Exception as e:
            logger.exception("⚠️ Error saat cari/play lagu:")
            embed = Embed(title="🔴 Error", color=9786367)
            embed.description = f"⚠️ Error: {str(e)}"
            await ctx.send(embed=embed)

    async def start_queue(self):
        self.is_playing = True

        while not self.queue.empty():
            ctx, title_or_url = await self.queue.get()
            self.autoplay_ctx = ctx
            try:
                await self.search_and_play(ctx, title_or_url)
                while ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
                    await asyncio.sleep(3)
            except Exception as e:
                embed = Embed(title="🔴 Error ", color=9786367)
                embed.description = f"❌ Error during play : {e}"
                await ctx.send(embed=embed)
                continue

        self.is_playing = False

    async def play_audio(self, ctx, url):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            embed = Embed(title="🔴 Not Connected", color=9786367)
            embed.description = "⚠️ Bot isn't here, Join Voice First."
            await ctx.send(embed=embed)
            return

        def after_play(error):
            if error:
                logger.error(f"Player error: {error}")
            asyncio.run_coroutine_threadsafe(self.autoplay_next(), self.bot.loop)
        await asyncio.sleep(3)

        vc.play(
            discord.FFmpegPCMAudio(url, **ffmpeg_options),
            after=after_play
        )

        await self.send_now_playing(ctx, self.last_video_info["title"], self.last_video_info["thumbnail"])

    async def autoplay_next(self):
        if not self.is_autoplay:
            ## logger.info("🛑 Autoplay dimatikan.")
            return

        if not self.last_video_info or not self.autoplay_ctx:
            return

        related = self.last_video_info.get('related_videos')
        if related and len(related) > 0:
            for vid in related:
                next_id = vid.get("id")
                if not next_id:
                    continue
                next_url = f"https://www.youtube.com/watch?v={next_id}"
                ## logger.info(f"⏭ Autoplay next: {next_url}")
                try:
                    data = ytdl.extract_info(next_url, download=False)
                    audio_url = data.get('url')
                    if not audio_url:
                        continue
                    self.last_video_info = data
                    await self.play_audio(self.autoplay_ctx, audio_url)
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Gagal autoplay {next_url}: {e}")
                    continue
        else:
            ## logger.info("⚠️ Related videos kosong, fallback search next video berdasarkan judul")

            title = self.last_video_info.get('title', '')
            if title:
                search_results = ytdl.extract_info(f"ytsearch:{title}", download=False)
                entries = search_results.get('entries', []) if search_results else []
                for entry in entries:
                    if entry.get('id') != self.last_video_info.get('id'):
                        try:
                            next_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                            ## logger.info(f"⏭ Autoplay fallback next: {next_url}")
                            data = ytdl.extract_info(next_url, download=False)
                            audio_url = data.get('url')
                            if not audio_url:
                                continue
                            self.last_video_info = data
                            await self.play_audio(self.autoplay_ctx, audio_url)
                            return
                        except Exception as e:
                            logger.warning(f"⚠️ Gagal fallback autoplay {next_url}: {e}")
                            continue
            else:
                logger.warning("❌ Gagal fallback autoplay: judul lagu kosong")

    async def send_now_playing(self, ctx, music_title, youtube_thumbnail_url):
        embed = Embed(
            title=f"🎶 Playing: {music_title}",
            color=0x23F4C6
        )
        embed.set_thumbnail(url="https://i.imgur.com/XHhYdWw.png")
        embed.set_image(url=youtube_thumbnail_url)
        embed.set_footer(text="Rein Music 🎧")

        await ctx.send(embed=embed)
    
    async def send_not_connected(ctx):
        embed = Embed(title="🔴Prefix Error", color=9786367)
        embed.description = "Join to Voice Channel first."
        await ctx.send(embed=embed)

    @commands.command()
    async def stopautoplay(self, ctx):
        self.is_autoplay = False
        embed = Embed(title="🔴 Autoplay Shutdown.", color=9786367)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def info(self, ctx):
        embed = Embed(
            title="❔ Command Info",
            description=(
                "`r!join` : Join the voice channel.\n"
                "`r!leave` : Leave the voice channel.\n"
                "`r!play (URL) or (Music Title)` : Play a song.\n"
                "`r!pause` : Pause the currently playing song.\n"
                "`r!resume` : Resume the paused song.\n"
                "`r!stop` : Stop the music and clear the queue.\n"
                "`r!skip` : Skip the current song.\n"
            ),
            color=9786367
        )
        await ctx.send(embed=embed)


    @commands.command()
    async def autoplay(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)
            return

        if not self.last_video_info:
            embed = Embed(title="💠 There is no song playing, play the song first then it will autoplay.", color=9786367)
            await ctx.send(embed=embed)
            return

        self.is_autoplay = True
        self.autoplay_ctx = ctx
        embed = Embed(title="💠 Autoplay Active", color=9786367)
        await ctx.send(embed=embed)

        vc = ctx.voice_client
        if not vc.is_playing() and not vc.is_paused():
            await self.autoplay_next()

    @commands.command()
    async def pause(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)
            return
        
        vc = ctx.voice_client       
        if vc and vc.is_playing():
            vc.pause()
            embed = Embed(title="⏸ Paused", color=9786367)
            await ctx.send(embed=embed)

    @commands.command()
    async def resume(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)
            return
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            embed = Embed(title="▶️ Resume current", color=9786367)
            await ctx.send(embed=embed)

    @commands.command()
    async def skip(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)
            return
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            embed = Embed(title="⏭ Skipped", color=9786367)
            await ctx.send(embed=embed)

    @commands.command()
    async def leave(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            embed = Embed(title="🔴Prefix Error", color=9786367)
            embed.description = "Join to Voice Channel first."
            await ctx.send(embed=embed)
            return
        
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()
            for f in os.listdir('files'):
                os.remove(os.path.join('files', f))
            embed = Embed(title="🔚 Disconnected", color=9786367)
            await ctx.send(embed=embed)
        else:
            embed = Embed(title="🔴 Not Connected", color=9786367)
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))