# AI Voice bot

This bot plays AI voices from [ElevenLabs](https://beta.elevenlabs.io) using custom made voices from my friends.

Here's a demo of playing a TTS message in a voice channel. The 🔄 emoji is used to replay the cached `.mp3` file.

![Discord_QXzOSBmMNH](https://user-images.githubusercontent.com/6510862/224864185-ecce62ad-f27b-4634-a6e0-5a3205b7c630.gif)


## Scraping Dota Wiki for audio files


Run the scraper with the following command:

```console
cd audio
./generate-dota-voice-model.py --url https://dota2.fandom.com/wiki/Abaddon/Responses --voice abaddon
```

This will generate an audio file, `abaddon.mp3`, which you can [upload to Elevenlabs](https://beta.elevenlabs.io/voice-lab) to create a custom voice model.

