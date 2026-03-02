const { SlashCommandBuilder } = require('discord.js');
const { getQueue, deleteQueue } = require('../music/MusicQueue');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('stop')
    .setDescription('Stop playback and clear the queue'),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue) {
      return interaction.reply({ content: 'Nothing is playing.', ephemeral: true });
    }

    queue.stop();
    deleteQueue(interaction.guildId);
    interaction.reply('Stopped and cleared the queue.');
  },
};
