UX flow

In Discord text (or slash command):

/music listen (or !listen)

Bot joins (or is already in) the voice channel and says (TTS):

“Listening.”

Bot listens for one utterance (or max N seconds), runs STT, parses a command.

Bot confirms with TTS:

“Skipping.” / “Volume 20.” / “Playing lo-fi.”

Bot stops listening immediately.

Optional: if it can’t understand:

“Didn’t catch that. Try again.” (then stop anyway)

Core endpoints / components
Discord Bot (UI + voice capture + TTS)

Text command arms a “listening session”

Captures audio from that voice channel (only while armed)

Sends audio to STT

Sends parsed intent to orchestrator/music player

TTS confirmation

Orchestrator (policy + logging)

Validates permissions

Applies rate limits

Routes to music bot playback controls

Emits events (job + command + result)

Music playback (the actual player)

Already your bot can play music

It just needs a control interface (internal function calls or REST)

Listening session rules (what makes it reliable)

Max listen window: 4–8 seconds

Stop when:

first recognized command is parsed successfully, OR

silence timeout hits (e.g., 1.2s of silence after speech), OR

overall window expires

One command per arm (exactly what you asked)

Allow-list who can arm it (role or specific users)

Cool-down on arming (e.g., 10 seconds per channel)

Command grammar (keep it tight at first)

Start with these; they transcribe well:

skip / next

pause / resume

volume 0-100 (or “volume twenty”)

stop music

play <keyword> (this is hardest; you can add later)

If you do “play …”, consider requiring a second step:

voice: “play lo-fi”

bot: “Searching lo-fi. Say ‘confirm’ to queue, or ‘cancel’.”
(Still stops after one command? If you want strict one-command, keep play as text-only initially.)

What to store in state (per guild/channel)

A “listening session” object:

guildId

voiceChannelId

armedByUserId

startedAt

expiresAt

status: armed | capturing | transcribing | executing | done

audioBuffer (short)

attempts (usually 1)

This can be in-memory; if the bot restarts mid-session, it just dies gracefully.

Security / spam protection (minimum viable)

Only users with role DCS Operator can /music listen

Channel-level cooldown: 1 listen per 10 seconds

User-level cooldown: 1 listen per 20 seconds

Command allow-list for voice mode: skip/pause/resume/volume/stop

Hard cap on session length (8s)

TTS choices

Fast + simple: local TTS (Windows SAPI / edge-tts) if bot runs on Windows

Higher quality: cloud TTS

Keep responses short (“Listening.” “Skipping.” “Volume 20.”)

Tip: Don’t TTS the recognized text unless you want privacy issues; just confirm action.

Implementation note (important): Discord voice receiving

Playback is easy; receiving audio for STT depends on your bot stack.

Node (discord.js): doable; you’ll pipe PCM frames into STT.

Python (discord.py): voice receive is trickier; often you use forks or external tooling.

Lavalink: great playback; not designed for ingesting user audio for STT.

If you tell me your stack, I’ll point to the cleanest “voice receive” approach.

Suggested REST endpoints (if you want the orchestrator to own it)

You can keep it internal, but for consistency with your system:

POST /api/v1/discord/guilds/{guildId}/voice/listen

body: { "voiceChannelId": "...", "mode": "one-shot", "timeoutSeconds": 6 }

returns: { "jobId": "...", "status": "queued" }

And the result event includes:

transcript (optional, maybe store hashed/short)

parsed intent

executed action + success/failure