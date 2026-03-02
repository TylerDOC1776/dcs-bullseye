const play = require('play-dl');
const { getQueue, createQueue, deleteQueue } = require('../music/MusicQueue');

const PREFIX = '!';

module.exports = {
  name: 'messageCreate',
  async execute(message) {
    // Ignore bots and messages without the prefix
    if (message.author.bot) return;
    if (!message.content.startsWith(PREFIX)) return;

    const args = message.content.slice(PREFIX.length).trim().split(/\s+/);
    const commandName = args.shift().toLowerCase();

    const guildId = message.guildId;

    // ── !play ────────────────────────────────────────────────────────────────
    if (commandName === 'play') {
      const voiceChannel = message.member.voice.channel;
      if (!voiceChannel) {
        return message.reply('You need to be in a voice channel first.');
      }
      if (!args.length) {
        return message.reply('Usage: `!play <song name or URL>`');
      }

      const query = args.join(' ');
      let videoUrl, title, duration;

      try {
        const isUrl = query.startsWith('http://') || query.startsWith('https://');
        if (isUrl) {
          const info = await play.video_info(query);
          videoUrl = query;
          title = info.video_details.title;
          duration = info.video_details.durationRaw;
        } else {
          const results = await play.search(query, { limit: 1 });
          if (!results.length) return message.reply('No results found.');
          videoUrl = results[0].url;
          title = results[0].title;
          duration = results[0].durationRaw;
        }
      } catch (err) {
        console.error('play-dl error:', err);
        return message.reply('Failed to find or load that track. Try a different search.');
      }

      const track = {
        title,
        url: videoUrl,
        duration: duration || 'unknown',
        requestedBy: message.author.username,
      };

      let queue = getQueue(guildId);
      if (!queue) queue = createQueue(guildId, message.channel);

      const wasEmpty = queue.tracks.length === 0;

      try {
        await queue.add(track, voiceChannel);
      } catch (err) {
        return message.reply(`Error: ${err.message}`);
      }

      if (!wasEmpty) {
        message.reply(`Added to queue: **${title}** [${duration}] — position ${queue.tracks.length}`);
      }
      // "Now playing" message comes from MusicQueue itself
    }

    // ── !skip ────────────────────────────────────────────────────────────────
    else if (commandName === 'skip') {
      const queue = getQueue(guildId);
      if (!queue || !queue.tracks.length) return message.reply('Nothing is playing.');
      const skipped = queue.tracks[0].title;
      queue.skip();
      message.reply(`Skipped **${skipped}**.`);
    }

    // ── !stop ────────────────────────────────────────────────────────────────
    else if (commandName === 'stop') {
      const queue = getQueue(guildId);
      if (!queue) return message.reply('Nothing is playing.');
      queue.stop();
      deleteQueue(guildId);
      message.reply('Stopped and cleared the queue.');
    }

    // ── !pause ───────────────────────────────────────────────────────────────
    else if (commandName === 'pause') {
      const queue = getQueue(guildId);
      if (!queue || !queue.tracks.length) return message.reply('Nothing is playing.');
      queue.pause();
      message.reply('Paused.');
    }

    // ── !resume ──────────────────────────────────────────────────────────────
    else if (commandName === 'resume') {
      const queue = getQueue(guildId);
      if (!queue || !queue.tracks.length) return message.reply('Nothing is playing.');
      queue.resume();
      message.reply('Resumed.');
    }

    // ── !queue ───────────────────────────────────────────────────────────────
    else if (commandName === 'queue') {
      const queue = getQueue(guildId);
      if (!queue || !queue.tracks.length) return message.reply('The queue is empty.');
      const lines = queue.tracks.map((track, i) => {
        const prefix = i === 0 ? '▶️ Now:' : `${i}.`;
        return `${prefix} **${track.title}** [${track.duration}] — ${track.requestedBy}`;
      });
      message.reply(lines.join('\n'));
    }

    // ── !volume ──────────────────────────────────────────────────────────────
    else if (commandName === 'volume') {
      const queue = getQueue(guildId);
      if (!queue || !queue.tracks.length) return message.reply('Nothing is playing.');
      const level = parseInt(args[0]);
      if (isNaN(level) || level < 1 || level > 100) {
        return message.reply('Usage: `!volume <1-100>`');
      }
      queue.setVolume(level);
      message.reply(`Volume set to **${level}%**.`);
    }

    // ── !help ────────────────────────────────────────────────────────────────
    else if (commandName === 'help') {
      message.reply([
        '**Larabot commands** (also available as `/slash` commands)',
        '`!play <song or URL>` — play or enqueue a track',
        '`!skip` — skip the current track',
        '`!stop` — stop playback and clear the queue',
        '`!pause` — pause playback',
        '`!resume` — resume playback',
        '`!queue` — show the queue',
        '`!volume <1-100>` — set volume',
      ].join('\n'));
    }
  },
};
