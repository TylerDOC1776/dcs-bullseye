import discord
from discord import app_commands
from discord.ext import commands

from music_queue import Song
from playlist_manager import PlaylistManager


class Playlists(commands.Cog):
    def __init__(self, bot: commands.Bot, pm: PlaylistManager):
        self.bot = bot
        self.pm = pm

    @property
    def music(self):
        return self.bot.get_cog('Music')

    playlist = app_commands.Group(name='playlist', description='Manage your personal playlists')

    @playlist.command(name='create', description='Create a new playlist')
    @app_commands.describe(name='Name for the new playlist')
    async def create(self, interaction: discord.Interaction, name: str):
        if self.pm.create(interaction.user.id, name):
            await interaction.response.send_message(f'Created playlist **{name}**.')
        else:
            await interaction.response.send_message(
                f'You already have a playlist called **{name}**.', ephemeral=True
            )

    @playlist.command(name='delete', description='Delete one of your playlists')
    @app_commands.describe(name='Name of the playlist to delete')
    async def delete(self, interaction: discord.Interaction, name: str):
        if self.pm.delete(interaction.user.id, name):
            await interaction.response.send_message(f'Deleted playlist **{name}**.')
        else:
            await interaction.response.send_message(
                f'Playlist **{name}** not found.', ephemeral=True
            )

    @playlist.command(name='add', description='Add a song to one of your playlists')
    @app_commands.describe(name='Playlist name', query='Song name or YouTube URL')
    async def add(self, interaction: discord.Interaction, name: str, query: str):
        if self.pm.get(interaction.user.id, name) is None:
            await interaction.response.send_message(
                f'Playlist **{name}** not found.', ephemeral=True
            )
            return

        await interaction.response.defer()
        try:
            data = await self.music.fetch_metadata(query)
        except Exception as e:
            await interaction.followup.send(f'Could not find that song: {e}')
            return

        title = data.get('title', 'Unknown')
        webpage_url = data.get('webpage_url', query)
        self.pm.add_song(interaction.user.id, name, title, webpage_url)
        await interaction.followup.send(f'Added **{title}** to **{name}**.')

    @playlist.command(name='remove', description='Remove a song from a playlist by its position')
    @app_commands.describe(name='Playlist name', position='Song number shown in /playlist show')
    async def remove(self, interaction: discord.Interaction, name: str, position: int):
        if self.pm.remove_song(interaction.user.id, name, position - 1):
            await interaction.response.send_message(
                f'Removed song #{position} from **{name}**.'
            )
        else:
            await interaction.response.send_message(
                'Invalid playlist name or position.', ephemeral=True
            )

    @playlist.command(name='list', description='List all your playlists')
    async def list_cmd(self, interaction: discord.Interaction):
        playlists = self.pm.all_playlists(interaction.user.id)
        if not playlists:
            await interaction.response.send_message(
                'You have no playlists. Create one with `/playlist create`.', ephemeral=True
            )
            return
        lines = [
            f'`{name}` — {len(songs)} song{"s" if len(songs) != 1 else ""}'
            for name, songs in playlists.items()
        ]
        await interaction.response.send_message('**Your playlists:**\n' + '\n'.join(lines))

    @playlist.command(name='show', description='Show the songs in one of your playlists')
    @app_commands.describe(name='Playlist name')
    async def show(self, interaction: discord.Interaction, name: str):
        songs = self.pm.get(interaction.user.id, name)
        if songs is None:
            await interaction.response.send_message(
                f'Playlist **{name}** not found.', ephemeral=True
            )
            return
        if not songs:
            await interaction.response.send_message(f'**{name}** is empty.')
            return
        lines = [f'`{i + 1}.` {s["title"]}' for i, s in enumerate(songs)]
        await interaction.response.send_message(f'**{name}:**\n' + '\n'.join(lines))

    @playlist.command(name='play', description='Queue all songs from one of your playlists')
    @app_commands.describe(name='Playlist name')
    async def play(self, interaction: discord.Interaction, name: str):
        if not interaction.user.voice:
            await interaction.response.send_message(
                'You must be in a voice channel first.', ephemeral=True
            )
            return

        songs = self.pm.get(interaction.user.id, name)
        if songs is None:
            await interaction.response.send_message(
                f'Playlist **{name}** not found.', ephemeral=True
            )
            return
        if not songs:
            await interaction.response.send_message(f'**{name}** is empty.', ephemeral=True)
            return

        await interaction.response.defer()

        queue = self.music.get_queue(interaction.guild_id)
        if queue.voice_client is None or not queue.voice_client.is_connected():
            queue.voice_client = await interaction.user.voice.channel.connect()
        elif queue.voice_client.channel != interaction.user.voice.channel:
            await queue.voice_client.move_to(interaction.user.voice.channel)

        was_playing = queue.voice_client.is_playing() or queue.voice_client.is_paused()

        for s in songs:
            queue.add(Song(
                title=s['title'],
                webpage_url=s['webpage_url'],
                requested_by=interaction.user.display_name,
            ))

        if not was_playing:
            await self.music._play_next(interaction.guild_id)

        await interaction.followup.send(f'Queued **{len(songs)}** songs from **{name}**.')


async def setup(bot: commands.Bot):
    pm = PlaylistManager()
    await bot.add_cog(Playlists(bot, pm))
