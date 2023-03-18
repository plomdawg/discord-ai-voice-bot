#!/usr/bin/env python3
# This script downloads all audio files from a given webpage into a single mp3.
# Usage: python scrape-audio-clips.py --url <url> --voice <voice name>
# Example: python scrape-audio-clips.py --url https://dota2.fandom.com/wiki/Crystal_Maiden/Responses --voice crystal_maiden

import requests
import argparse
import pathlib
from bs4 import BeautifulSoup
import pydub
import io

# Parse command line arguments.
parser = argparse.ArgumentParser(description='Download and combine audio files from a webpage')
parser.add_argument('--url', help='URL to download audio files from', required=True)
parser.add_argument('--download', help='Only download the audio files', action='store_true')
parser.add_argument('--combine', help='Only combine the audio files', action='store_true')
parser.add_argument('--voice', help='Voice name', required=True)
args = parser.parse_args()

print(f"Downloading audio files from: {args.url}")

# Store audio files under files/[voice] directory.
audio_directory = pathlib.Path("files")
audio_directory.mkdir(parents=True, exist_ok=True)
output_mp3_path = audio_directory / f"{args.voice}.mp3"

# Create an empty audio file.
audio = pydub.AudioSegment.empty()

# Download the webpage.
webpage = requests.get(args.url).text
soup = BeautifulSoup(webpage, 'html.parser')

# Find all .mp3 links on the webpage. 
links = soup.find_all('a', href=lambda href: href and ".mp3" in href)
for i, link in enumerate(links):
    # Download the audio file.
    print(f"Downloading mp3 {i} / {len(links)}")
    response = requests.get(link['href'])
    
    # Append the sound and a 400ms silence.
    audio += pydub.AudioSegment.from_mp3(io.BytesIO(response.content))
    audio += pydub.AudioSegment.silent(duration=400)

# Save the combined audio file.
audio.export(output_mp3_path, format="mp3")
print(f"Combined audio file saved to: {output_mp3_path}")
