# voice.py - Voice class for AI Voice Bots
import elevenlabslib
import pathlib
import random
import logging
import time
import io

class TTS:
    def __init__(self, elevenlabs, text, tts_path, message_id):
        self.text = text
        self.elevenlabs = elevenlabs
        self.tts_path = pathlib.Path(tts_path)
        self.mp3_path = self.tts_path / pathlib.Path(f"{message_id}.mp3")

        # Set the voice for this message.
        # Use a random voice if not specified.
        self.random_voice = True
        self.voice = self.get_voice(seed=message_id)

        # Generate the sound clip later, if needed.
        self._bytes = None
        
        # Keep track of how long it takes to generate the clip.
        self.seconds = 0
        
        logging.debug(f"Creatied TTS object for message {message_id}")
        logging.debug(f" - Text: {text}")
        logging.debug(f" - MP3 path: {self.mp3_path}")
        logging.debug(f" - Voice: {self.voice}")

    @property
    def cost(text):
        """ Calculates the cost of a TTS message. """
        # Starter tier gives 40,000 characters per month for $5.
        #cost_per_character = 5 / 40000
        # Creator tier gives 140,000 characters per month for $22.
        # And you can buy 1000 additional characters for $0.30
        #cost_per_character = 22 / 140000
        # The estimated cost with additional characters is about 5000 characters per dollar.
        cost_per_character = 0.0002  # 1 / 5000
        cost = round(len(text) * cost_per_character, 8)
        return f"${cost}"

    @property
    def bytes(self):
        """ Generate a TTS clip and return it as bytes. """
        if self._bytes is None:
            logging.info(f"Generating TTS clip for text {self.text}")
            # Get the voice object for this message.
            voice = self.elevenlabs.voices[self.voice]
            # Time how long it takes to generate the audio bytes.
            start = time.time()
            # Set the stability to 0.35 to get a more natural sounding voice.
            self._bytes = voice.generate_audio_bytes(self.text, stability=0.35)
            # Calculate how long it took to generate the clip.
            self.seconds = round(time.time() - start, 2)
        logging.debug(f"Generated TTS clip for message in {self.seconds} seconds")
        return self._bytes

    @property
    def mp3(self):
        """ Generate a TTS clip and save it to a file. """
        if not self.mp3_path.exists():
            # Make sure the tts directory exists.
            self.tts_path.mkdir(parents=True, exist_ok=True)
            # Save the audio bytes to a file.
            elevenlabslib.helpers.save_bytes_to_path(self.mp3_path, self.bytes)
        return self.mp3_path

    def get_voice(self, seed):
        """ Get the voice for this message. """
        # Use a seed for the random voice so we can reproduce it later.
        voice = random.Random(seed).choice(list(self.elevenlabs.voices.keys()))

        # Check if the message starts with the name of a voice.
        for voice_name in self.elevenlabs.voices.keys():
            # The voice may be followed by a colon or semicolon.
            if self.text.startswith(f"{voice_name}:") or self.text.startswith(f"{voice_name};"):
                # Set the voice to the specified voice.
                self.voice = voice_name
                # Strip the name and colon from the message.
                self.text = self.text[len(voice_name)+1:].strip()
                # We are not using a random voice.
                self.random_voice = False
                # Stop looking for a voice in case there are multiple.
                break

        return voice


# Voice class for interacting with the ElevenLabs API.
class ElevenLabsVoice:
    def __init__(self, api_key):
        self.api_key = api_key
        self.user = elevenlabslib.ElevenLabsUser(api_key)

        # Grab all available voices and store them in a dictionary.
        self.voices = {}

        # Loop through all available voices.
        for available_voice in list(self.user.get_available_voices()):
            # Ignore built-in voices.
            if available_voice.category == "premade":
                continue
            # Store the name as lowercase for easier lookup.
            voice = available_voice.initialName.lower()
            self.voices[voice] = available_voice

    def get_tts(self, text, path, message_id):
        """ Get the TTS clip for a message.
        args:
            text: The message text.
            path: The path to the TTS clip directory.
            message_id: The message ID, used for the random number generator and the filename.
        returns:
            tts: The TTS clip.
        """
        return TTS(self, text, path, message_id)
