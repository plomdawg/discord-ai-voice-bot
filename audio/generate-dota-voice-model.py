#!/usr/bin/env python3
# This script downloads all audio files from a given webpage.
# It then combines them into a single audio file.
# Usage: python generate-dota-voice-model.py --url <url> --voice <voice name>
# Example: python generate-dota-voice-model.py --url https://dota2.fandom.com/wiki/Crystal_Maiden/Responses --voice crystal_maiden

import requests
import argparse
import pathlib
from bs4 import BeautifulSoup
import pydub

# Parse command line arguments.
parser = argparse.ArgumentParser(description='Generate Dota Voice Model')
parser.add_argument('--url', help='URL to download audio files from', required=True)
parser.add_argument('--download', help='Only download the audio files', action='store_true')
parser.add_argument('--combine', help='Only combine the audio files', action='store_true')
parser.add_argument('--voice', help='Voice name', required=True)
args = parser.parse_args()

# Store audio files under files/[voice] directory.
audio_directory = pathlib.Path(f"files/{args.voice}")

def download_mp3s():
    # Download the webpage.
    print(f"Downloading webpage {args.url}")
    webpage = requests.get(args.url).text
    soup = BeautifulSoup(webpage, 'html.parser')

    # Find all audio links that contain .mp3
    links = soup.find_all('a', href=lambda href: href and ".mp3" in href)

    # Make sure the audio directory exists.
    if not audio_directory.exists():
        audio_directory.mkdir(parents=True)

    # Download each audio file.
    for i, link in enumerate(links):
        # Get the audio file name.
        audio_file_name = f"{args.voice} {i}.mp3"
        audio_file_path = audio_directory / audio_file_name

        # Download the audio file.
        print(f"Downloading audio file {audio_file_name} ({i} / {len(links)})")
        audio_file = requests.get(link['href'])

        # Save the audio file.
        with open(audio_file_path, 'wb') as f:
            f.write(audio_file.content)


def combine_mp3s():
    # Combine all audio files into a single audio file.
    sound = pydub.AudioSegment.empty()
    files = list(audio_directory.glob("*.mp3"))
    for i, audio_file in enumerate(files):
        print(f"Adding: {audio_file} ({i} / {len(files)})")
        sound += pydub.AudioSegment.from_file(audio_file, format="mp3")
        # Add 300ms of silence.
        sound += pydub.AudioSegment.silent(duration=300)
    
    # Save the combined audio file.
    output_path = audio_directory / f"{args.voice}.mp3"
    sound.export(output_path, format="mp3")
    print(f"Combined audio file saved to: {output_path}")
    
if __name__ == "__main__":
    # Download and combine the audio files.
    # If --download is specified, only download the audio files.
    # If --combine is specified, only combine the audio files.
    if args.download:
        download_mp3s()
    elif args.combine:
        combine_mp3s()
    else:
        download_mp3s()
        combine_mp3s()
