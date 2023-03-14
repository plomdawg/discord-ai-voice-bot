#!/usr/bin/env python3
# voice.py - Voice class for AI Voice Bots
import elevenlabslib
import pathlib

# Voice class for interacting with the ElevenLabs API.
class Voice:
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

    def generate_tts_mp3(self, text, voice, mp3_path: pathlib.Path):
        """ Generate a TTS clip and save it to a file """
        audio_bytes = self.voices[voice].generate_audio_bytes(text, stability=0.35)
        elevenlabslib.helpers.save_bytes_to_path(mp3_path, audio_bytes)
        return mp3_path

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
