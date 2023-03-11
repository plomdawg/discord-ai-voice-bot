#!/usr/bin/env python3
# Dota Voice Bot - A Discord bot that plays Dota 2 voice lines in voice channels.
# Usage: dota-voice-bot.py --token <discord bot token> --prefix <command prefix>
import discord
import argparse
import asyncio
import elevenlabslib
import io


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

    def generate_tts_mp3(self, text, voice):
        """ Generate a TTS clip and save it to a file """
        mp3_path = "tts.mp3"
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

async def generate_tts(text, voice):
    """ Generate a TTS clip and return the path to the file """
    print(f"Generating audio clip in voice {voice} for: '{text}'")
    audio_path = ai_voice.generate_tts_mp3(text, voice=voice)
    return audio_path

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


@client.event
async def on_message(message):
    # Ignore messages from the bot itself.
    if message.author == client.user:
        return

    # Help message.
    if message.content.startswith(args.prefix + "help"):
        response = "**voices**:"
        for voice in ai_voice.voices.keys():
            response += f"`{voice}`, "
        response = response[:-2]
        response += "\n"
        response += "**usage**: `;[text]` or `;[voice]: [text]`"
        await message.channel.send(response)
        return

    # Play TTS messages that start with the prefix.
    if message.content.startswith(args.prefix):
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
        # Make sure the message isn't too loud, if it is, let the user know.
        if len(text) > 200:
            await message.channel.send("Message too long, please keep it under 200 characters.")
            return

        # Generate the TTS clip.
        audio_path = await generate_tts(text, voice=voice)
        audio_path = ai_voice.generate_tts_mp3(text, voice=voice)

        # Remove the hourglass reaction and react with a sound icon.
        await message.remove_reaction("⏳", client.user)
        await message.add_reaction("🔊")

        # Play the message in the user's voice channel.
        await play_tts_in_channel(message.author.voice.channel, audio_path)

        # React with a checkmark once we're done.
        await message.remove_reaction("🔊", client.user)
        await message.add_reaction("✅")


def main():
    client.run(args.token)


if __name__ == '__main__':
    main()
