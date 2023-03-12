# Dota Discord Voice Bot

This bot plays AI voices from [ElevenLabs](https://beta.elevenlabs.io) using custom made voices from my friends.


![ai bot demo](https://user-images.githubusercontent.com/6510862/224526407-8c490469-9a30-4d32-84dc-ca799b1aabef.gif)


I asked for a recording of at least a minute of everybody reading something they're interested in or telling a story. We wanted to provide a voice sample that didn't sound like they were reading a script for the first time.



## Scraping Dota Wiki for audio files


Run the scraper with the following command:

```console
cd audio
./generate-dota-voice-model.py --url https://dota2.fandom.com/wiki/Abaddon/Responses --voice abaddon
```

This will generate an audio file, `abaddon.mp3`, which you can [upload to Elevenlabs](https://beta.elevenlabs.io/voice-lab) to create a custom voice model.

