const { SlashCommandBuilder } = require('discord.js');
const { getQueue } = require('../music/MusicQueue');
const { AudioPlayerStatus } = require('@discordjs/voice');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('pause')
    .setDescription('Pause playback'),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue || queue.tracks.length === 0) {
      return interaction.reply({ content: 'Nothing is playing.', ephemeral: true });
    }
    if (queue.status !== AudioPlayerStatus.Playing) {
      return interaction.reply({ content: 'Already paused.', ephemeral: true });
    }

    queue.pause();
    interaction.reply('Paused.');
  },
};
