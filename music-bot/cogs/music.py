import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
import threading

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

from music_queue import MusicQueue, Song

log = logging.getLogger('larabot')


class _YtdlLogger:
    """Routes yt-dlp output through Python's logging system."""
    def debug(self, msg):
        pass
    def info(self, msg):
        pass
    def warning(self, msg):
        log.warning('yt-dlp: %s', msg)
    def error(self, msg):
        log.error('yt-dlp: %s', msg)


YTDL_OPTIONS = {
    'noplaylist': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'cookiefile': r'C:\Musicbot\cookies.txt',
    'js_runtimes': {'node': {}},
    'remote_components': {'ejs:github'},
    'extractor_args': {'youtube': {'player_client': ['web']}},
    'logger': _YtdlLogger(),
}

SEARCH_OPTIONS = {
    **YTDL_OPTIONS,
    'extract_flat': 'in_playlist',
}

# Options for stream URL extraction — iOS client tried first (no n-challenge needed),
# falls back to web.  Python API respects explicit player_client even with cookies present.
PLAY_OPTIONS = {
    **YTDL_OPTIONS,
    'format': 'bestaudio/best',
    'extractor_args': {'youtube': {'player_client': ['ios', 'web']}},
}


class _PipedAudio(discord.AudioSource):
    """Audio source: FFmpeg reads a local temp file → PCM → discord."""

    FRAME_SIZE = 3840  # 48 000 Hz × 2 ch × 20 ms × 2 bytes

    def __init__(self, ffmpeg_proc: subprocess.Popen, tmpdir: str | None = None):
        self._ffmpeg = ffmpeg_proc
        self._out = ffmpeg_proc.stdout
        self._tmpdir = tmpdir

    def read(self) -> bytes:
        data = self._out.read(self.FRAME_SIZE)
        return data if len(data) == self.FRAME_SIZE else b''

    def is_opus(self) -> bool:
        return False

    def cleanup(self) -> None:
        try:
            self._ffmpeg.kill()
        except Exception:
            pass
        try:
            self._ffmpeg.wait(timeout=3)
        except Exception:
            pass
        for pipe in (self._ffmpeg.stdout, self._ffmpeg.stderr):
            try:
                if pipe:
                    pipe.close()
            except Exception:
                pass
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)


def is_url(query: str) -> bool:
    return query.startswith(('http://', 'https://'))


class SearchView(discord.ui.View):
    def __init__(self, results: list[dict], cog, guild_id: int, user_name: str):
        super().__init__(timeout=30)
        self.cog = cog
        self.guild_id = guild_id
        self.user_name = user_name
        self.results = results
        self.message: discord.Message | None = None

        options = []
        for i, r in enumerate(results):
            title = (r.get('title') or 'Unknown')[:100]
            dur = r.get('duration_string') or _fmt_duration(r.get('duration'))
            options.append(discord.SelectOption(
                label=title,
                description=f'Duration: {dur}' if dur else None,
                value=str(i),
            ))

        select = discord.ui.Select(placeholder='Choose a song...', options=options)
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: discord.Interaction):
        # Acknowledge immediately — yt-dlp extraction can take several seconds
        await interaction.response.defer()

        idx = int(interaction.data['values'][0])
        result = self.results[idx]

        video_id = result.get('id', '')
        webpage_url = (
            result.get('webpage_url')
            or result.get('url')
            or f'https://www.youtube.com/watch?v={video_id}'
        )

        song = Song(
            title=result.get('title', 'Unknown'),
            webpage_url=webpage_url,
            requested_by=self.user_name,
        )

        queue = self.cog.get_queue(self.guild_id)
        queue.add(song)

        if not queue.voice_client.is_playing() and not queue.voice_client.is_paused():
            await self.cog._play_next(self.guild_id)
            await interaction.edit_original_response(
                content=f'Now playing: **{song.title}**', view=None
            )
        else:
            await interaction.edit_original_response(
                content=f'Added to queue (position {queue.size}): **{song.title}**', view=None
            )
        self.stop()

    async def on_timeout(self):
        if self.message:
            await self.message.edit(content='Search timed out.', view=None)


def _fmt_duration(seconds) -> str:
    if not seconds:
        return ''
    seconds = int(seconds)
    return f'{seconds // 60}:{seconds % 60:02d}'


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queues: dict[int, MusicQueue] = {}

    def get_queue(self, guild_id: int) -> MusicQueue:
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    def _spawn_piped_audio(self, webpage_url: str) -> _PipedAudio:
        """Download audio via yt-dlp Python API to a temp file, then decode with FFmpeg."""
        tmpdir = tempfile.mkdtemp(prefix='larabot_')
        try:
            opts = {
                **PLAY_OPTIONS,
                'outtmpl': os.path.join(tmpdir, '%(id)s.%(ext)s'),
            }
            log.info('Downloading: %s', webpage_url)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info(webpage_url, download=True)

            # Find the downloaded file (skip any .part leftovers)
            files = [f for f in os.listdir(tmpdir) if not f.endswith('.part')]
            if not files:
                raise RuntimeError('yt-dlp produced no output file')
            filename = os.path.join(tmpdir, files[0])
            log.info('Downloaded: %s', filename)

            ffmpeg_proc = subprocess.Popen(
                ['ffmpeg', '-hide_banner', '-nostats',
                 '-i', filename, '-vn', '-f', 's16le', '-ar', '48000', '-ac', '2', 'pipe:1'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            def _drain_stderr():
                try:
                    for raw in ffmpeg_proc.stderr:
                        line = raw.decode('utf-8', errors='replace').rstrip()
                        if line:
                            log.warning('ffmpeg: %s', line)
                except (ValueError, OSError):
                    pass  # pipe closed during cleanup

            threading.Thread(target=_drain_stderr, daemon=True).start()
            return _PipedAudio(ffmpeg_proc, tmpdir)
        except Exception:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise

    async def fetch_metadata(self, query: str) -> dict:
        """Fetch title/webpage_url without resolving stream URLs."""
        loop = asyncio.get_event_loop()
        if is_url(query):
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                data = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(query, download=False, process=False)
                )
            return data
        else:
            results = await self.search_songs(query, count=1)
            if not results:
                raise ValueError('No results found')
            r = results[0]
            video_id = r.get('id', '')
            return {
                'title': r.get('title', 'Unknown'),
                'webpage_url': (
                    r.get('webpage_url')
                    or r.get('url')
                    or f'https://www.youtube.com/watch?v={video_id}'
                ),
            }

    async def search_songs(self, query: str, count: int = 5) -> list[dict]:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(SEARCH_OPTIONS) as ydl:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f'ytsearch{count}:{query}', download=False)
            )
        return (data.get('entries') or [])[:count]

    async def _play_next(self, guild_id: int):
        queue = self.get_queue(guild_id)
        song = queue.next()
        if song is None or queue.voice_client is None:
            log.info('_play_next: nothing to play (song=%s, vc=%s)', song, queue.voice_client)
            return

        log.info('_play_next: starting "%s" (%s)', song.title, song.webpage_url)
        loop = asyncio.get_event_loop()
        try:
            source = await loop.run_in_executor(
                None, lambda: self._spawn_piped_audio(song.webpage_url)
            )
        except Exception as e:
            log.error(f'Failed to start stream for "{song.title}" ({song.webpage_url}): {e}')
            await self._play_next(guild_id)
            return

        source = discord.PCMVolumeTransformer(source, volume=queue.volume)

        def after_playing(error):
            if error:
                log.error(f'Player error for "{song.title}": {error}')
            asyncio.run_coroutine_threadsafe(self._play_next(guild_id), self.bot.loop)

        queue.voice_client.play(source, after=after_playing)

    # --- Commands ---

    @app_commands.command(name='play', description='Play a song from YouTube')
    @app_commands.describe(query='Song name or YouTube URL')
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message(
                'You must be in a voice channel first.', ephemeral=True
            )
            return

        await interaction.response.defer()

        queue = self.get_queue(interaction.guild_id)

        if queue.voice_client is None or not queue.voice_client.is_connected():
            queue.voice_client = await interaction.user.voice.channel.connect()
        elif queue.voice_client.channel != interaction.user.voice.channel:
            await queue.voice_client.move_to(interaction.user.voice.channel)

        if is_url(query):
            # Direct URL — fetch metadata then queue for pipe-based playback
            try:
                data = await self.fetch_metadata(query)
            except Exception as e:
                await interaction.followup.send(f'Could not load that URL: {e}')
                return

            song = Song(
                title=data.get('title', 'Unknown'),
                webpage_url=data.get('webpage_url') or query,
                requested_by=interaction.user.display_name,
            )
            queue.add(song)

            if not queue.voice_client.is_playing() and not queue.voice_client.is_paused():
                await self._play_next(interaction.guild_id)
                await interaction.followup.send(f'Now playing: **{song.title}**')
            else:
                await interaction.followup.send(
                    f'Added to queue (position {queue.size}): **{song.title}**'
                )
        else:
            # Search — show selection menu
            try:
                results = await self.search_songs(query)
            except Exception as e:
                await interaction.followup.send(f'Search failed: {e}')
                return

            if not results:
                await interaction.followup.send('No results found.')
                return

            view = SearchView(results, self, interaction.guild_id, interaction.user.display_name)
            msg = await interaction.followup.send('Select a song:', view=view)
            view.message = msg

    @app_commands.command(name='leave', description='Disconnect the bot from the voice channel')
    async def leave(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if queue.voice_client and queue.voice_client.is_connected():
            queue.clear()
            queue.voice_client.stop()
            await queue.voice_client.disconnect()
            queue.voice_client = None
            await interaction.response.send_message('Disconnected.')
        else:
            await interaction.response.send_message('Not in a voice channel.', ephemeral=True)

    @app_commands.command(name='skip', description='Skip the current song')
    async def skip(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if queue.voice_client and queue.voice_client.is_playing():
            queue.voice_client.stop()
            await interaction.response.send_message('Skipped.')
        else:
            await interaction.response.send_message('Nothing is playing.', ephemeral=True)

    @app_commands.command(name='stop', description='Stop playback and clear the queue')
    async def stop(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        queue.clear()
        if queue.voice_client:
            queue.voice_client.stop()
            await queue.voice_client.disconnect()
            queue.voice_client = None
        await interaction.response.send_message('Stopped and disconnected.')

    @app_commands.command(name='pause', description='Pause playback')
    async def pause(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if queue.voice_client and queue.voice_client.is_playing():
            queue.voice_client.pause()
            await interaction.response.send_message('Paused.')
        else:
            await interaction.response.send_message('Nothing is playing.', ephemeral=True)

    @app_commands.command(name='resume', description='Resume playback')
    async def resume(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if queue.voice_client and queue.voice_client.is_paused():
            queue.voice_client.resume()
            await interaction.response.send_message('Resumed.')
        else:
            await interaction.response.send_message('Not paused.', ephemeral=True)

    @app_commands.command(name='queue', description='Show the current queue')
    async def queue_cmd(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild_id)
        if queue.current is None and queue.is_empty():
            await interaction.response.send_message('The queue is empty.')
            return

        lines = []
        if queue.current:
            lines.append(f'**Now playing:** {queue.current.title}')
        for i, song in enumerate(queue.queue, 1):
            lines.append(f'`{i}.` {song.title} — requested by {song.requested_by}')
        await interaction.response.send_message('\n'.join(lines))

    @app_commands.command(name='volume', description='Set the volume (0–100)')
    @app_commands.describe(level='Volume level between 0 and 100')
    async def volume(self, interaction: discord.Interaction, level: int):
        if not 0 <= level <= 100:
            await interaction.response.send_message(
                'Volume must be between 0 and 100.', ephemeral=True
            )
            return

        queue = self.get_queue(interaction.guild_id)
        queue.volume = level / 100
        if queue.voice_client and isinstance(queue.voice_client.source, discord.PCMVolumeTransformer):
            queue.voice_client.source.volume = queue.volume
        await interaction.response.send_message(f'Volume set to {level}%.')

    @app_commands.command(name='clear', description='Delete bot messages in this channel (mods only)')
    @app_commands.checks.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction):
        await interaction.response.send_message('Clearing...', ephemeral=True)
        deleted = await interaction.channel.purge(
            limit=200,
            check=lambda m: m.author == interaction.guild.me,
        )
        await interaction.edit_original_response(content=f'Deleted {len(deleted)} bot message(s).')

    @clear.error
    async def clear_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                'You need the **Manage Messages** permission to use this.', ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
