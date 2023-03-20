#!/usr/bin/env python
# Twitch AI Voice Bot
# Usage: bot/twitch-bot.py --token <token> --user_token <user_token> --client_id <client_id> --channel <channel> --elevenlabs <elevenlabs api key> --prefix <prefix> --debug
# Plays a TTS sound clip when a user tips bits.
import argparse
import elevenlabs
import coloredlogs, logging

from twitchio.ext import commands, sounds, pubsub


# Parse command line arguments.
parser = argparse.ArgumentParser(description='Twitch AI Voice Bot')
parser.add_argument('--token', help='Twitch access token', required=True)
parser.add_argument(
    '--user_token', help='Twitch user OAUTH token', required=True)
parser.add_argument(
    '--client_id', help='Twitch token generator client ID', required=True)
parser.add_argument('--channel', help='Twitch channel name', required=True)
parser.add_argument('--elevenlabs', help='ElevenLabs API key', required=True)
parser.add_argument('--prefix', help='Command prefix', default=';')
parser.add_argument('--debug', help='Enable debug mode', action='store_true')
args = parser.parse_args()

# Configure logging to print the date and time, in color.
coloredlogs.install(fmt='%(asctime)s %(levelname)s: %(message)s', level='DEBUG' if args.debug else 'INFO')

class Bot(commands.Bot):

    def __init__(self):
        # Initialize the bot.
        super().__init__(token=args.token, prefix=';',
                         initial_channels=[args.channel])

        # Create the audio player.
        self.player = sounds.AudioPlayer(callback=self.player_done)

        # Create the AI voice client.
        self.elevenlabs = elevenlabs.ElevenLabsVoice(args.elevenlabs)

        # Keep track of number of bits donated and tts cost.
        self.bits = 0
        self.cost = 0

    async def event_ready(self):
        """ Called once when the bot goes online. """
        logging.info(f"Available voices:")
        logging.info(f" - {', '.join(list(self.elevenlabs.voices.keys()))}")

    async def event_message(self, message):
        logging.debug(f"event_message(): {message.raw_data}")
        """ Called when a message is sent in chat. """

        # Check if there are bits in the message.
        # if not ";bits=" in message.raw_data.split('PRIVMSG')[0]:
        #    return

        # Figure out how many bits were donated.
        # message.raw_data is a string like:
        # @badge-info=;badges=bits-leader/1;color=#FFADD6;display-name=plomdawg;emotes=;first-msg=0;flags=;id=05393199-f0c8-4f03-8185-6d70294f6034;mod=0;returning-chatter=0;room-id=57150492;subscriber=0;tmi-sent-ts=1679108362962;turbo=0;user-id=120300474;user-type= :plomdawg!plomdawg@plomdawg.tmi.twitch.tv PRIVMSG #waqasu :p
        bits = 0
        tokens = message.raw_data.split(";")
        for token in tokens:
            if token.startswith("bits="):
                bits = int(token.split("=")[1])
                logging.info(f"{message.author.name} donated {bits} bits!")
                break

        # Only play tts for 100 bits or more.
        if bits < 100 and message.author.name != "plomdawg":
            return

        # Remove "CheerX" from the message.
        text = message.content.replace(f"Cheer{bits}", "").strip()

        # Generate the TTS clip.
        tts = self.elevenlabs.get_tts(
            text=text, message_id=message.id, path="tts-twitch")
        sound = sounds.Sound(str(tts.mp3))
        logging.debug(f"sound: {sound}")

        # Play the TTS clip.
        logging.info(f"Playing TTS clip: {tts.mp3} in {tts.voice}'s voice!")
        self.player.play(sound)

        # Print a summary of the number of bits donated so far.
        self.bits += bits
        self.cost += tts.cost
        logging.info(f"Total bits donated: {self.bits} (${self.bits / 100})")
        logging.info(f"Total cost: ${self.cost}")
        logging.info(f"Profit: ${self.bits / 100 - self.cost}")

    async def event_raw_usernotice(self, channel, tags):
        """ https://dev.twitch.tv/docs/irc/tags/#usernotice-tags """
        logging.debug(f"event_raw_usernotice: {tags.get('msg-id')}")
        logging.debug(tags)

        if tags.bits:
            logging.info(f"Bits donated!")

        if tags.bits:
            logging.info(f"Bits donated!")

    async def player_done(self):
        """ Called when a sound is done playing. """
        logging.debug("Sound done playing")
        pass

    @commands.command()
    async def say(self, ctx: commands.Context):
        # Remove the prefix and command from the message.
        text = ctx.message.content[len(
            ctx.prefix)+len(ctx.command.name):].strip()

        # Generate the TTS clip.
        tts = self.elevenlabs.get_tts(
            text=text, message_id=ctx.message.id, path="tts-twitch")
        sound = sounds.Sound(tts.mp3)

        await ctx.send(f"playing '{tts.text}' in {tts.voice}'s voice!")

        # Play the TTS clip.
        self.player.play(sound)

    @commands.command()
    async def voices(self, ctx: commands.Context):
        """ List available voices. """
        await ctx.send(f"Available voices: {', '.join(list(self.elevenlabs.voices.keys()))}")

    @commands.command()
    async def test(self, ctx: commands.Context):
        """ Test the bot. """
        tts = self.elevenlabs.get_tts(
            text="p p poo poo", message_id="173eac12-f06e-4545-9dc6-7791340ea1e9", path="tts-twitch")

        # Generate the TTS clip.
        sound = sounds.Sound(str(tts.mp3))

        # await ctx.send(f"Playing '{tts.text}' in {tts.voice}'s voice!")

        # Play the TTS clip.
        self.player.play(sound)


bot = Bot()
bot.run()
