const { SlashCommandBuilder } = require('discord.js');
const { getQueue } = require('../music/MusicQueue');
const { AudioPlayerStatus } = require('@discordjs/voice');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('resume')
    .setDescription('Resume playback'),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue || queue.tracks.length === 0) {
      return interaction.reply({ content: 'Nothing is playing.', ephemeral: true });
    }
    if (queue.status !== AudioPlayerStatus.Paused) {
      return interaction.reply({ content: 'Not currently paused.', ephemeral: true });
    }

    queue.resume();
    interaction.reply('Resumed.');
  },
};
