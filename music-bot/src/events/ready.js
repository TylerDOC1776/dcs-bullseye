module.exports = {
  name: 'ready',
  once: true,
  execute(client) {
    console.log(`Larabot is online — logged in as ${client.user.tag}`);
  },
};
