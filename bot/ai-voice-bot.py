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
intents.members = True

# Create the discord client.
client = discord.Client(intents=intents)

# Create the AI voice client.
ai_voice = Voice(args.elevenlabs)


def calculate_cost(text):
    """ Calculates the cost of a TTS message """
    # Starter tier gives 40,000 characters per month for $5.
    #cost_per_character = 5 / 40000
    # Creator tier gives 140,000 characters per month for $22.
    # And you can buy 1000 additional characters for $0.30
    #cost_per_character = 22 / 140000
    # The estimated cost with additional characters is about 5000 characters per dollar.
    cost_per_character = 0.0002  # 1 / 5000
    cost = round(len(text) * cost_per_character, 8)
    return f"${cost}"


async def remove_reactions(message, emojis=["❌", "🔄"]):
    """ Remove reactions from a message without erroring if the reaction doesn't exist """
    for emoji in emojis:
        try:
            await message.remove_reaction(emoji, client.user)
        except discord.errors.NotFound:
            pass


async def handle_message_tts(message, user):
    """ Processes a TTS message. May be triggered by on_message() or on_reaction() """
    # Remove any existing reactions.
    await remove_reactions(message)

    # Remove the prefix from the message.
    text = message.content[len(args.prefix):].strip()

    # Default to a random voice.
    # Use the message ID as the seed for the random voice so we can reproduce it later.
    random_voice = True
    voice = random.Random(message.id).choice(list(ai_voice.voices.keys()))

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
        await message.add_reaction("❌")
        return await message.channel.send(f"{user.mention} Message too long, please keep it under 420 characters.")

    # Use message ID as the file name.
    tts_path = pathlib.Path("tts")
    mp3_path = tts_path / f"{message.id}.mp3"

    # Send a message to the channel that the message was sent in.
    # Keep track of the message ID so we can edit it later.
    # Start the color off as gray.
    embed = discord.Embed(
        title=text,
        color=0x808080
    )

    # Add the voice to the message. Note if it's a random voice.
    footer = f"- {voice} (random)" if random_voice else f"- {voice}"

    # Add the user that requested the message to the footer.
    footer += f" (requested by @{message.author.name})"

    # If this is a replay, add the replay requester.
    if user != message.author or mp3_path.exists():
        footer += f" (replayed by @{user.name})"

    # Calculate the cost and add it to the footer.
    if mp3_path.exists():
        footer += f" cost: $0 (cached!)"
    else:
        footer += f" cost: {calculate_cost(text)}"

    # Set the footer and send the message.
    embed.set_footer(text=footer)
    response = await message.channel.send(embed=embed)

    # Edit the response message if anything goes wrong.
    async def fail(reason):
        # Set the embed color to red.
        embed.color = 0xff0000
        
        # Set the embed description to the error message.
        embed.description = f"Failed! {reason}"
        await response.edit(embed=embed)
        
        # Respond with the error message.
        await message.channel.send(f"{user.mention} {reason}")

    # Make sure the tts directory exists.
    tts_path.mkdir(parents=True, exist_ok=True)

    # React with a replay button.
    await message.add_reaction("🔄")

    # Find the user's voice channel.
    voice_channel = None

    # Check if the user is in a voice channel.
    # If not, let the user know they need to be in a voice channel.
    voice_channel = None
    try:
        voice_channel = user.voice.channel
    except AttributeError:
        for channel in client.get_guild(message.guild.id).voice_channels:
            for member in channel.members:
                if member.id == user.id:
                    voice_channel = channel
                    break

    # Make sure we found a voice channel.
    if voice_channel is None:
        return await fail("You must be in a voice channel to play a message.")

    # Generate the TTS clip if the mp3 file doesn't exist.
    if not mp3_path.exists():
        ai_voice.generate_tts_mp3(text, voice=voice, mp3_path=mp3_path)

    # Change the embed color to a light blue.
    embed.color = 0x007fcd
    await response.edit(embed=embed)

    # Play the message in the user's voice channel.
    try:
        await play_tts_in_channel(voice_channel, mp3_path)
    except discord.errors.ClientException as error:
        logging.error(error)
        return await fail(error)

    # Edit the embed color to green.
    embed.color = 0x00ff00
    await response.edit(embed=embed)


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
        await handle_message_tts(message, message.author)


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
        await handle_message_tts(message, user)


@client.event
async def on_voice_state_update(member, before, after):
    """ Called when a user changes their voice state

    Args:
        member - The Member whose voice states changed.
        before - The VoiceState prior to the changes.
        after  - The VoiceState after to the changes.

    Leaves and clears the queue if the bot is left alone for 3 minutes
    """
    # Try to find the voice client for this guild.
    voice_client = None
    for vc in client.voice_clients:
        if vc.guild == member.guild:
            voice_client = vc
            break
    
    # Nothing to do if the bot is not in a voice channel.
    if voice_client is None:
        return
    
    # If there are any non-bots in the channel, do nothing.
    for user in voice_client.channel.members:
        if not user.bot:
            return

    # Save the bot's current channel.
    bot_channel = voice_client.channel

    # If the bot is alone in the channel, start the timer.
    # Loop until somebody comes back, or the timer runs out.
    timeout = 60  # seconds before disconnecting
    step = 15  # seconds between checks
    for _ in range(0, int(timeout/step)):
        await asyncio.sleep(step)
        
        # Check if a non-bot has joined the channel.
        if any([not user.bot for user in voice_client.channel.members]):
            return
        
        # Check if the bot has been disconnected.
        if voice_client is None or not voice_client.is_connected():
            return

        # Check if the bot has been moved to a different channel.
        if voice_client.channel is not bot_channel:
            return

    # If the bot is still alone, disconnect.
    await voice_client.disconnect()

def main():
    client.run(args.token)


if __name__ == '__main__':
    main()
