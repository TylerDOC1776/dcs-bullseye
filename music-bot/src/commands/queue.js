const { SlashCommandBuilder } = require('discord.js');
const { getQueue } = require('../music/MusicQueue');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('queue')
    .setDescription('Show the current queue'),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue || queue.tracks.length === 0) {
      return interaction.reply({ content: 'The queue is empty.', ephemeral: true });
    }

    const lines = queue.tracks.map((track, i) => {
      const prefix = i === 0 ? '▶️ Now:' : `${i}.`;
      return `${prefix} **${track.title}** [${track.duration}] — ${track.requestedBy}`;
    });

    interaction.reply(lines.join('\n'));
  },
};
