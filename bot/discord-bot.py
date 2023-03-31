#!/usr/bin/env python3
# AI Voice Bot - A Discord bot that plays AI voice lines in voice channels.
# Usage: bot/discord-bot.py --token <discord bot token> --prefix <command prefix>
import discord
import argparse
import asyncio
import logging
import openai

import elevenlabs


# Parse command line arguments.
parser = argparse.ArgumentParser(description='Dota Voice Bot')
parser.add_argument('--token', help='Discord bot token', required=True)
parser.add_argument('--elevenlabs', help='ElevenLabs API key', required=True)
parser.add_argument('--openai', help='Open AI API key', required=True)
parser.add_argument('--prefix', help='Command prefix', default=';')
parser.add_argument('--debug', help='Enable debug mode', action='store_true')
args = parser.parse_args()

# Configure logging. Log messages with the date and time.
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
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
ai_voice = elevenlabs.ElevenLabsVoice(args.elevenlabs)
logging.info(f"Available voices: {', '.join(list(ai_voice.voices.keys()))}")

# Set the OpenAI key.
openai.api_key = args.openai

async def remove_reactions(message, emojis=["❌", "🔄"]):
    """ Remove reactions from a message without erroring if the reaction doesn't exist """
    for emoji in emojis:
        try:
            await message.remove_reaction(emoji, client.user)
        except discord.errors.NotFound:
            pass


def get_voice_channel(user, guild_id):
    # Find the user's voice channel.
    voice_channel = None

    # Check if the user is in a voice channel.
    # If not, let the user know they need to be in a voice channel.
    voice_channel = None
    try:
        voice_channel = user.voice.channel
    except AttributeError:
        for channel in client.get_guild(guild_id).voice_channels:
            for member in channel.members:
                if member.id == user.id:
                    voice_channel = channel
                    break
    return voice_channel

async def messages_to_prompt(messages, system_prompt) -> str:
    """ Convert a discord message to a prompt for the AI. """
    prompt = [{"role": "system", "content": system_prompt}]
    for message in messages:
        if message.author.bot:
            role = "assistant"
            content = message.content
        else:
            role = "user"
            content = f"{message.author.name}: {message.content}"
        prompt.append({"role": role, "content": content})
    return prompt

async def handle_message_chatgpt(message):
    """ Process a chat message in the #ask-chatgpt channel """
    await message.add_reaction("👀")
    
    # This is a top level message.
    if type(message.channel) == discord.TextChannel:
        # Create a thread that last 1 hour
        thread = await message.create_thread(name=message.content, auto_archive_duration=60)
        
        explanation = "Hello! Please provide a **system prompt**.\n\nIt helps establish the desired context, role, or behavior you expect from the AI while interacting with it. By providing a system message, you can guide the model to better understand the context of the conversation or task and generate more relevant and accurate responses.\n\nFor example, if you want to use GPT-4 as an assistant to provide recommendations on movies, you can start with a system message like:\n\n`'You are an AI assistant that specializes in providing movie recommendations.'`\n\nThis system message will set the context for the model, ensuring that it understands its role as a movie recommendation assistant during the conversation.\n\nYou can edit the message any time before the thread is closed."
        
        # Reply to the thread asking for a system prompt.
        embed = discord.Embed(
            description=explanation,
            color=0x808080
        )
        explanation_message = await thread.send(embed=embed)
        
        # Wait for a response. If we don't hear back in 5 minutes, close the thread.
        def check(m):
            if type(m.channel) == discord.Thread:
                if m.channel.id == thread.id:
                    return True
        try: 
            user_response = await client.wait_for('message', check=check, timeout=300)
            await user_response.add_reaction("🧠")
            system_prompt = user_response.content
        except asyncio.TimeoutError:
            await thread.send("No response. Closing thread.")
            await thread.edit(locked=True)
    
        # Edit the explaination message to include the system prompt.
        embed.description = f"System Prompt:"
        embed.color = 0x00ff00
        #await explanation_message.edit(embed=embed)
        
        # Send another message containing the system prompt.
        #embed.description = f"```{system_prompt}```"
        #await thread.send(embed=embed)

        # Remove the 👀 reaction.
        await remove_reactions(message, ["👀"])
        return
    
    # This is a reply to a thread.
    # Find the system prompt - it is the third message in the thread.
    # Fetch the thread and grab the third message.
    replies = await message.channel.history(limit=100).flatten()

    # Reverse the replies so the most recent is last.
    replies.reverse()

    # If there are only three messages, the third message is the system prompt.
    # We don't need to do anything here.
    if len(replies) == 3:
        return await replies[2].add_reaction("✅")
    
    # If there are more than three messages, the third message is the system prompt and the rest are replies.
    system_prompt = []
    system_prompt.append("Chat will be in the form: '[username]: [message]'.")
    system_prompt.append("Do not start the response with the username.")
    system_prompt.append(replies[2].content.strip())
    system_prompt = "\n".join(system_prompt)

    # Remove the first 3 messages.
    replies = replies[3:]

    # Generate the prompt.    
    prompt_messages = await messages_to_prompt(replies, system_prompt)
    print(prompt_messages)
    
    # Set the max response length.
    max_response_length = 800

    # Prepare the model.
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        max_tokens=max_response_length,
        messages=prompt_messages,
        temperature=0.7,  # lower temp = more consistent responses
    )
    
    # Return the content from the first choice.
    response = completion.choices[0]['message']['content']
    
    # Remove the bot's name from the response.
    response = response.replace("plombot AI: ", "")
    
    await message.channel.send(response)
    await remove_reactions(message, ["👀"])

async def handle_message_chatgpt_old(message):
    """ Process a chat message in the #ask-chatgpt channel """
    await message.add_reaction("👀")
    # Read the chat history for this channel
    messages = await message.channel.history(limit=11).flatten()
    messages.reverse()


    # Set the max response length.
    max_response_length = 800
    
    # Set the system prompt.
    #system_prompt = "I am a highly intelligent question answering bot. Start with your name, then ask a question. If you ask me a question that is rooted in truth, I will give you the answer. If you ask me a question that is nonsense, trickery, or has no clear answer, I will respond with \"Unknown\".\n\nQ: What is human life expectancy in the United States?\nA: Human life expectancy in the United States is 78 years.\n\nQ: Who was president of the United States in 1955?\nA: Dwight D. Eisenhower was president of the United States in 1955.\n\nQ: Which party did he belong to?\nA: He belonged to the Republican Party.\n\nQ: What is the square root of banana?\nA: Unknown\n\nQ: How does a telescope work?\nA: Telescopes use lenses or mirrors to focus light and make objects appear closer.\n\nQ: Where were the 1992 Olympics held?\nA: The 1992 Olympics were held in Barcelona, Spain.\n\nQ: How many squigs are in a bonk?\nA: Unknown\n\nQ: Where is the Valley of Kings?\nA:"
    #system_prompt = "I am a highly intelligent question answering bot. Start with your name, then ask a question. If I do not know the answer, I will make one up."
    system_prompt = []
    system_prompt.append("You are a highly intelligent question answering bot.")
    #system_prompt.append("You are a highly intelligent discord bot.")
    #system_prompt.append("You are a highly intelligent question answering discord bot that loves memes.")
    #system_prompt.append("You are a meme lord.")
    system_prompt.append("You are not a family-friendly bot. You can use swear words.")
    system_prompt.append("Reference memes whenever possible.")
    #system_prompt.append("Use discord emojis.")
    system_prompt.append("Use a lot of unicode emojis.")
    system_prompt.append("The chat history will be given for context before the message.")
    system_prompt.append("Chat will be in the form: '[username]: [message]'.")
    
    system_prompt.append("Read the sentiment of only the last message and respond with the same sentiment.")    
    system_prompt.append("Do not include a username in the response.")
    system_prompt.append("")
    
    
    
    #system_prompt.append("Only respond to the last question asked.")
    

    system_prompt = '\n'.join(system_prompt)
    
    prompt_messages = await messages_to_prompt(messages, system_prompt)

    print(system_prompt)
    
    # Prepare the model.
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        max_tokens=max_response_length,
        messages=prompt_messages,
        temperature=0.7,  # lower temp = more consistent responses
    )
    
    # Return the content from the first choice.
    response = completion.choices[0]['message']['content']
    
    # Remove the bot's name from the response.
    response = response.replace("plombot AI: ", "")
    
    await message.channel.send(response)
    await remove_reactions(message, ["👀"])
    await message.add_reaction("✅")
    

async def handle_message_tts(message, user):
    """ Processes a TTS message. May be triggered by on_message() or on_reaction() """
    # Remove any existing reactions.
    await remove_reactions(message)

    # Remove the prefix from the message.
    text = message.content[len(args.prefix):].strip()

    # Let the user know if the message is too long.
    if len(text) > 420:
        await message.add_reaction("❌")
        return await message.channel.send(f"{user.mention} Message too long, please keep it under 420 characters.")

    # Get the voice for this message.
    tts = ai_voice.get_tts(text=text, message_id=message.id, path="tts-discord")

    # Send a message to the channel that the message was sent in.
    # Keep track of the message ID so we can edit it later.
    # Start the color off as gray.
    embed = discord.Embed(
        description=tts.text,
        color=0x808080
    )

    # Add the voice to the message. Note if it's a random voice.
    footer = f"- {tts.voice} (random)" if tts.random_voice else f"- {tts.voice}"

    # Add the user that requested the message to the footer.
    footer += f" (by @{message.author.name})"

    # If this is a replay, add the replay requester.
    if user != message.author or tts.mp3_path.exists():
        footer += f" (🔄 by @{user.name})"

    # Calculate the cost and add it to the footer.
    if tts.mp3_path.exists():
        footer += f" cost: $0 (cached!)"
    else:
        footer += f" cost: {tts.cost}"

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

    # React with a replay button.
    await message.add_reaction("🔄")

    # Get the voice channel the user is in.
    voice_channel = get_voice_channel(user, message.guild.id)

    # Make sure we found a voice channel.
    if voice_channel is None:
        return await fail("You must be in a voice channel to play a message.")

    # Generate the TTS clip.
    mp3 = tts.mp3

    # Add the time it took to generate the clip to the footer.
    if tts.seconds > 0:
        footer += f" in {tts.seconds:.2f}s"
        embed.set_footer(text=footer)

    # Change the embed color to a light blue.
    embed.color = 0x007fcd
    await response.edit(embed=embed)

    # Play the message in the user's voice channel.
    try:
        await play_mp3_in_channel(voice_channel, mp3)
    except discord.errors.ClientException as error:
        logging.error(error)
        return await fail(error)

    # Edit the embed color to green.
    embed.color = 0x00ff00
    await response.edit(embed=embed)


async def play_mp3_in_channel(voice_channel, audio_path):
    """ Play an audio clip in a voice channel """
    logging.info(f"Playing clip {audio_path} in {voice_channel}")

    # Get the voice client for the guild.
    vc = discord.utils.get(client.voice_clients, guild=voice_channel.guild)

    # The voice client is already connected to a channel.
    if vc:
        # Check if the voice client is already playing a clip.
        logging.debug(f"  - Voice client is already connected to a channel: {vc.channel.name}")
        while vc.is_playing():
            logging.debug(
                "  - Voice client is already playing a clip, waiting...")
            await asyncio.sleep(1)

        # Make sure the voice client is connected to the correct channel.
        if vc.channel is not voice_channel:
            logging.debug(f"  - Moving to voice channel: {voice_channel.name}")
            await vc.move_to(voice_channel)

    # Connect to the voice channel.
    if not vc:
        logging.debug(f"  - Connecting to voice channel: {voice_channel.name}")
        vc = await voice_channel.connect()

    # Play the audio clip.
    logging.debug(f"  - Playing audio clip {audio_path}")
    vc.play(discord.FFmpegPCMAudio(audio_path))


@ client.event
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


@ client.event
async def on_message(message):
    # Ignore messages from the bot itself.
    if message.author == client.user:
        return

    # Messages sent to #ask-chatgpt or threads within #ask-chatgpt.
    if type(message.channel) == discord.TextChannel:
        if message.channel.id == 1091222348440551456:
            return await handle_message_chatgpt(message)
    else:
        if message.channel.parent is not None and message.channel.parent.id == 1091222348440551456:
            return await handle_message_chatgpt(message)

    # Help message.
    if message.content.startswith(args.prefix + "help"):
        logging.info(
            f"Help message requested by {message.author.name} ({message.author.id})")
        response = "**voices**: "
        for voice in ai_voice.voices.keys():
            response += f"`{voice}`, "
        response = response[:-2]
        response += "\n"
        response += "**usage**: `;[text]` or `;[voice] [text]`"
        await message.channel.send(response)
        return

    # Play TTS messages that start with the prefix.
    if message.content.startswith(args.prefix):
        await handle_message_tts(message, message.author)


@ client.event
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


@ client.event
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
    if any([not user.bot for user in voice_client.channel.members]):
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
