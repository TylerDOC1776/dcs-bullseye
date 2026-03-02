const {
  createAudioPlayer,
  createAudioResource,
  AudioPlayerStatus,
  VoiceConnectionStatus,
  entersState,
  joinVoiceChannel,
} = require('@discordjs/voice');
const play = require('play-dl');

// Map of guildId -> MusicQueue instance
const queues = new Map();

class MusicQueue {
  constructor(textChannel) {
    this.textChannel = textChannel;
    this.tracks = [];          // { title, url, duration, requestedBy }
    this.volume = 0.5;         // 0.0 – 1.0
    this.connection = null;
    this.currentResource = null;

    this.player = createAudioPlayer();

    this.player.on(AudioPlayerStatus.Idle, () => {
      this.tracks.shift();
      if (this.tracks.length > 0) {
        this._playTrack(this.tracks[0]);
      } else {
        this.textChannel.send('Queue finished. Disconnecting.');
        this._cleanup();
      }
    });

    this.player.on('error', err => {
      console.error('Audio player error:', err.message);
      this.textChannel.send(`Playback error: ${err.message} — skipping.`);
      this.tracks.shift();
      if (this.tracks.length > 0) {
        this._playTrack(this.tracks[0]);
      } else {
        this._cleanup();
      }
    });
  }

  // Connect to a voice channel
  async connect(voiceChannel) {
    this.connection = joinVoiceChannel({
      channelId: voiceChannel.id,
      guildId: voiceChannel.guild.id,
      adapterCreator: voiceChannel.guild.voiceAdapterCreator,
    });

    this.connection.subscribe(this.player);

    // Clean up if the connection is destroyed externally (e.g. bot kicked)
    this.connection.on(VoiceConnectionStatus.Destroyed, () => {
      this._cleanup(false);
    });

    // Wait for connection to be ready
    try {
      await entersState(this.connection, VoiceConnectionStatus.Ready, 10_000);
    } catch {
      this.connection.destroy();
      throw new Error('Could not connect to voice channel in time.');
    }
  }

  // Add a track to the queue; start playback if this is the first track
  async add(track, voiceChannel) {
    const wasEmpty = this.tracks.length === 0;
    this.tracks.push(track);

    if (wasEmpty) {
      if (!this.connection) {
        await this.connect(voiceChannel);
      }
      await this._playTrack(this.tracks[0]);
    }
  }

  async _playTrack(track) {
    const stream = await play.stream(track.url);
    this.currentResource = createAudioResource(stream.stream, {
      inputType: stream.type,
      inlineVolume: true,
    });
    this.currentResource.volume.setVolume(this.volume);
    this.player.play(this.currentResource);
    this.textChannel.send(`Now playing: **${track.title}** (requested by ${track.requestedBy})`);
  }

  skip() {
    this.player.stop(true); // triggers Idle → plays next
  }

  stop() {
    this.tracks = [];
    this.player.stop(true);
    this._cleanup();
  }

  pause() {
    return this.player.pause();
  }

  resume() {
    return this.player.unpause();
  }

  setVolume(percent) {
    this.volume = percent / 100;
    this.currentResource?.volume?.setVolume(this.volume);
  }

  get status() {
    return this.player.state.status;
  }

  _cleanup(destroyConnection = true) {
    if (destroyConnection && this.connection) {
      this.connection.destroy();
    }
    this.connection = null;
    this.currentResource = null;
  }
}

function getQueue(guildId) {
  return queues.get(guildId) || null;
}

function createQueue(guildId, textChannel) {
  const queue = new MusicQueue(textChannel);
  queues.set(guildId, queue);
  return queue;
}

function deleteQueue(guildId) {
  queues.delete(guildId);
}

module.exports = { getQueue, createQueue, deleteQueue };
