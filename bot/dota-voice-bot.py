#!/usr/bin/env python3
# Dota Voice Bot - A Discord bot that plays Dota 2 voice lines in voice channels.
# Usage: dota-voice-bot.py --token <discord bot token> --prefix <command prefix>
import discord
import argparse
import asyncio
import elevenlabslib
import pathlib


class Voice:
    def __init__(self, api_key):
        self.api_key = api_key
        self.user = elevenlabslib.ElevenLabsUser(api_key)

        # Grab all available voices and store them in a dictionary.
        self.voices = {}
        # Skip the first 9 voices, they are the built-in voices.
        for voice in list(self.user.get_available_voices())[9:]:
            print(voice.initialName)
            self.voices[voice.initialName.lower()] = voice

    def generate_tts_mp3(self, text, voice, mp3_path):
        """ Generate a TTS clip and save it to a file """
        elevenlabslib.helpers.save_bytes_to_path(
            mp3_path, self.voices[voice].generate_audio_bytes(text))
        return mp3_path


# Parse command line arguments.
parser = argparse.ArgumentParser(description='Dota Voice Bot')
parser.add_argument('--token', help='Discord bot token', required=True)
parser.add_argument('--elevenlabs', help='ElevenLabs API key', required=True)
parser.add_argument('--prefix', help='Command prefix', default=';')
args = parser.parse_args()

# Enable message content intent.
intents = discord.Intents.default()
intents.message_content = True

# Create the discord client.
client = discord.Client(intents=intents)

# Create the AI voice client.
ai_voice = Voice(args.elevenlabs)


async def handle_message_tts(message):
    """ Processes a TTS message. May be triggered by on_message() or on_reaction() """
    # Try to remove the check, it's okay if it doesn't exist.
    try:
        await message.remove_reaction("✅", client.user)
    except:
        pass
    # Add emoji hourglass to the message as a reaction.
    await message.add_reaction("⏳")
    # Remove the prefix from the message.
    text = message.content[len(args.prefix):]
    # Remove the mention from the message.
    text = text.replace(f"<@{client.user.id}>", '').strip()
    # Default to the mark voice.
    voice = "mark"
    # Check if the message starts with the name of a voice
    for voice_name in ai_voice.voices.keys():
        if text.startswith(f"{voice_name}: "):
            voice = voice_name
            # Strip the name and colon from the message
            text = text[len(voice_name)+2:].strip()

    # Let the user know if the message is too long.
    if len(text) > 420:
        return await message.channel.send("Message too long, please keep it under 420 characters.")
    
    # Make sure the tts directory exists.
    tts_path = pathlib.Path("tts")
    tts_path.mkdir(parents=True, exist_ok=True)
    
    # Generate mp3 file path using the message ID.
    mp3_path = tts_path / f"{message.id}.mp3"
    
    # Generate the TTS clip if it doesn't exist.
    if not mp3_path.exists():
        mp3_path = ai_voice.generate_tts_mp3(text, voice=voice, mp3_path=mp3_path)

    # Remove the hourglass reaction and react with a sound icon.
    await message.remove_reaction("⏳", client.user)
    await message.add_reaction("🔊")

    # Play the message in the user's voice channel.
    await play_tts_in_channel(message.author.voice.channel, mp3_path)

    # React with a checkmark once we're done.
    await message.remove_reaction("🔊", client.user)
    await message.add_reaction("✅")
    
    # React with a replay button.
    await message.add_reaction("🔄")
    


async def play_tts_in_channel(voice_channel, audio_path):
    """ Play an audio clip in a voice channel """
    # Connect to the voice channel.
    print(f"  - Connecting to voice channel {voice_channel.name}")
    vc = discord.utils.get(client.voice_clients, guild=voice_channel.guild)
    if not vc:
        vc = await voice_channel.connect()

    # Play the audio clip.
    print(f"  - Playing audio clip {audio_path}")
    vc.play(discord.FFmpegPCMAudio(audio_path))

    # Wait until the clip finishes playing.
    print("  - Waiting for clip to finish...")
    while vc.is_playing():
        await asyncio.sleep(1)
    print("  - Done playing clip.")


@client.event
async def on_ready():
    """ Called after the bot successfully connects to Discord servers """
    print(f"Connected as {client.user.name} ({client.user.id})")

    # Change presence to "Playing dota voices in _ guilds"
    text = f"for {args.prefix}help"
    activity = discord.Activity(name=text, type=discord.ActivityType.watching)
    await client.change_presence(activity=activity)

    # Print guild info
    print(f"Active in {len(client.guilds)} guilds.")

    # Print invite link.
    permissions = 690520124992
    print(f"Invite link: https://discordapp.com/oauth2/authorize?client_id={client.user.id}&scope=bot&permissions={permissions}")


@client.event
async def on_message(message):
    # Ignore messages from the bot itself.
    if message.author == client.user:
        return

    # Help message.
    if message.content.startswith(args.prefix + "help"):
        response = "**voices**: "
        for voice in ai_voice.voices.keys():
            response += f"`{voice}`, "
        response = response[:-2]
        response += "\n"
        response += "**usage**: `;[text]` or `;[voice]: [text]`"
        await message.channel.send(response)
        return

    # Play TTS messages that start with the prefix.
    if message.content.startswith(args.prefix):
        await handle_message_tts(message)


@client.event
async def on_reaction_add(reaction, user):
    # Ignore own reactions.
    if user == client.user:
        return

    # If the reaction emoji is a replay button, replay the message.
    if reaction.emoji == "🔄":
        # Remove the user's reaction.
        await reaction.remove(user)
        # Handle the message as a TTS message.
        await handle_message_tts(reaction.message)


def main():
    client.run(args.token)


if __name__ == '__main__':
    main()
