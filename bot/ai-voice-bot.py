#!/usr/bin/env python3
# AI Voice Bot - A Discord bot that plays AI voice lines in voice channels.
# Usage: ai-voice-bot.py --token <discord bot token> --prefix <command prefix>
import discord
import argparse
import asyncio
import elevenlabslib
import pathlib
import logging
import random


class Voice:
    def __init__(self, api_key):
        self.api_key = api_key
        self.user = elevenlabslib.ElevenLabsUser(api_key)

        # Grab all available voices and store them in a dictionary.
        self.voices = {}
        # Skip the first 9 voices, they are the built-in voices.
        for available_voice in list(self.user.get_available_voices())[9:]:
            # Store the name as lowercase for easier lookup.
            voice = available_voice.initialName.lower()
            self.voices[voice] = available_voice

        logging.info(
            f"Available voices: {', '.join(list(self.voices.keys()))}")

    def generate_tts_mp3(self, text, voice, mp3_path):
        """ Generate a TTS clip and save it to a file """
        elevenlabslib.helpers.save_bytes_to_path(
            mp3_path, self.voices[voice].generate_audio_bytes(text, stability=0.35))
        return mp3_path


# Parse command line arguments.
parser = argparse.ArgumentParser(description='Dota Voice Bot')
parser.add_argument('--token', help='Discord bot token', required=True)
parser.add_argument('--elevenlabs', help='ElevenLabs API key', required=True)
parser.add_argument('--prefix', help='Command prefix', default=';')
parser.add_argument('--debug', help='Enable debug mode', action='store_true')
args = parser.parse_args()

# Configure logging.
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,  # Set the log level.
    filename='ai-voice-bot.log',  # Log to a file.
    filemode='a',  # Append to the log file.
    # Set the log format.
    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p'
)
# Set the discord logger to only log warnings and above.
logging.getLogger("discord").setLevel(logging.WARNING)

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
    try:
        await message.remove_reaction("❌", client.user)
    except:
        pass
    # Add emoji hourglass to the message as a reaction.
    await message.add_reaction("⏳")
    # Remove the prefix from the message.
    text = message.content[len(args.prefix):].strip()

    # Default to a random voice.
    random_voice = True
    voice = random.choice(list(ai_voice.voices.keys()))

    # Check if the message starts with the name of a voice
    for voice_name in ai_voice.voices.keys():
        if text.startswith(f"{voice_name}:") or text.startswith(f"{voice_name};"):
            voice = voice_name
            # Strip the name and colon from the message
            text = text[len(voice_name)+1:].strip()
            random_voice = False
            break
        elif text.startswith(f"{voice_name}"):
            voice = voice_name
            text = text[len(voice_name):].strip()
            random_voice = False
            break

    # Let the user know if the message is too long.
    if len(text) > 420:
        await message.remove_reaction("⏳", client.user)
        await message.add_reaction("❌")
        return await message.channel.send(f"{message.author.mention} Message too long, please keep it under 420 characters.")

    # Make sure the tts directory exists.
    tts_path = pathlib.Path("tts")
    tts_path.mkdir(parents=True, exist_ok=True)

    # React with a replay button.
    await message.add_reaction("🔄")

    # Generate mp3 file path using the message ID.
    mp3_path = tts_path / f"{message.id}.mp3"

    # Generate the TTS clip if it doesn't exist.
    if not mp3_path.exists():
        mp3_path = ai_voice.generate_tts_mp3(
            text, voice=voice, mp3_path=mp3_path)

    # Find the user's voice channel.
    voice_channel = None

    # Check if the user is in a voice channel.
    # If not, let the user know they need to be in a voice channel.
    voice_channel = None
    try:
        voice_channel = message.author.voice.channel
    except AttributeError:
        pass
        
    # Make sure we found a voice channel.
    if voice_channel is None:
        await message.remove_reaction("⏳", client.user)
        await message.add_reaction("❌")
        await message.reply(f"{message.author.mention} You must be in a voice channel to play a message.")

    # Remove the hourglass reaction and react with a sound icon.
    await message.remove_reaction("⏳", client.user)
    await message.add_reaction("🔊")

    # Play the message in the user's voice channel.
    try:
        await play_tts_in_channel(voice_channel, mp3_path)
    except discord.errors.ClientException as error:
        logging.error(error)
        # Remove the sound icon reaction and react with a cross.
        await message.remove_reaction("🔊", client.user)
        await message.add_reaction("❌")
        return

    # React with a checkmark once we're done.
    await message.remove_reaction("🔊", client.user)
    await message.add_reaction("✅")


async def play_tts_in_channel(voice_channel, audio_path):
    """ Play an audio clip in a voice channel """
    logging.info(
        f"Playing clip {audio_path} in voice channel {voice_channel}")

    # Get the voice client for the guild.
    vc = discord.utils.get(client.voice_clients, guild=voice_channel.guild)

    # If the voice client is already connected, check if it's playing a clip.
    if vc:
        logging.debug("  - Voice client is already connected to a channel")
        while vc.is_playing():
            logging.debug(
                "  - Voice client is already playing a clip, waiting...")
            await asyncio.sleep(1)

    # Connect to the voice channel.
    if not vc:
        logging.debug(f"  - Connecting to voice channel {voice_channel.name}")
        vc = await voice_channel.connect()

    # Play the audio clip.
    logging.debug(f"  - Playing audio clip {audio_path}")
    vc.play(discord.FFmpegPCMAudio(audio_path))


@client.event
async def on_ready():
    """ Called after the bot successfully connects to Discord servers """
    logging.info(
        f"Connected to {len(client.guilds)} guilds as {client.user.name} ({client.user.id})")

    # Change presence to "Playing AI voices | ;help"
    await client.change_presence(
        activity=discord.Activity(
            name=f"AI voices | {args.prefix}help",
            type=discord.ActivityType.playing
        ))

    # Print the invite link.
    logging.info(
        f"Invite: https://discordapp.com/oauth2/authorize?client_id={client.user.id}&scope=bot&permissions=690520124992")


@client.event
async def on_message(message):
    # Ignore messages from the bot itself.
    if message.author == client.user:
        return

    # Help message.
    if message.content.startswith(args.prefix + "help"):
        logging.info(
            f"Help message requested by {message.author.name} ({message.author.id})")
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
async def on_raw_reaction_add(payload):
    # Only handle reactions on messages in a guild.
    if payload.guild_id is None:
        return

    # Ignore bot reactions.
    if payload.member.bot:
        return

    # Find the user from the payload.
    user = await client.fetch_user(payload.user_id)

    # Find the message that was reacted to using the message ID
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)

    # If the reaction emoji is a replay button, replay the message.
    if payload.emoji.name == "🔄":
        # Remove the user's reaction.
        await message.remove_reaction(emoji=payload.emoji, member=payload.member)
        # Handle the message as a TTS message.
        await handle_message_tts(message)


def main():
    client.run(args.token)


if __name__ == '__main__':
    main()
