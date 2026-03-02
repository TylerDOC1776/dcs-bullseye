const { SlashCommandBuilder } = require('discord.js');
const play = require('play-dl');
const { getQueue, createQueue } = require('../music/MusicQueue');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('play')
    .setDescription('Search YouTube and play a track')
    .addStringOption(opt =>
      opt.setName('query')
        .setDescription('Song name or YouTube URL')
        .setRequired(true)
    ),

  async execute(interaction) {
    const voiceChannel = interaction.member.voice.channel;
    if (!voiceChannel) {
      return interaction.reply({ content: 'You need to be in a voice channel first.', ephemeral: true });
    }

    await interaction.deferReply();

    const query = interaction.options.getString('query');

    // Resolve URL or search
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
        if (!results.length) {
          return interaction.editReply('No results found for that query.');
        }
        videoUrl = results[0].url;
        title = results[0].title;
        duration = results[0].durationRaw;
      }
    } catch (err) {
      console.error('play-dl error:', err);
      return interaction.editReply('Failed to find or load that track. Try a different search.');
    }

    const track = {
      title,
      url: videoUrl,
      duration: duration || 'unknown',
      requestedBy: interaction.user.username,
    };

    const guildId = interaction.guildId;
    let queue = getQueue(guildId);

    if (!queue) {
      queue = createQueue(guildId, interaction.channel);
    }

    const wasEmpty = queue.tracks.length === 0;

    try {
      await queue.add(track, voiceChannel);
    } catch (err) {
      console.error('Queue add error:', err);
      return interaction.editReply(`Error: ${err.message}`);
    }

    if (wasEmpty) {
      interaction.editReply(`Playing **${title}** [${duration}]`);
    } else {
      interaction.editReply(`Added to queue: **${title}** [${duration}] — position ${queue.tracks.length}`);
    }
  },
};
