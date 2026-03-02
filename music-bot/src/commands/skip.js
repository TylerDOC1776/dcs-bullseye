const { SlashCommandBuilder } = require('discord.js');
const { getQueue } = require('../music/MusicQueue');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('skip')
    .setDescription('Skip the current track'),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue || queue.tracks.length === 0) {
      return interaction.reply({ content: 'Nothing is playing.', ephemeral: true });
    }

    const skipped = queue.tracks[0].title;
    queue.skip();
    interaction.reply(`Skipped **${skipped}**.`);
  },
};
