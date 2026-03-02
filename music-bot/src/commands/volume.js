const { SlashCommandBuilder } = require('discord.js');
const { getQueue } = require('../music/MusicQueue');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('volume')
    .setDescription('Set playback volume (1–100)')
    .addIntegerOption(opt =>
      opt.setName('level')
        .setDescription('Volume level (1–100)')
        .setMinValue(1)
        .setMaxValue(100)
        .setRequired(true)
    ),

  async execute(interaction) {
    const queue = getQueue(interaction.guildId);
    if (!queue || queue.tracks.length === 0) {
      return interaction.reply({ content: 'Nothing is playing.', ephemeral: true });
    }

    const level = interaction.options.getInteger('level');
    queue.setVolume(level);
    interaction.reply(`Volume set to **${level}%**.`);
  },
};
