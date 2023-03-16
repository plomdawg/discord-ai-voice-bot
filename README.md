# AI Voice bot

This bot plays AI voices from [ElevenLabs](https://beta.elevenlabs.io) using custom made voices from my friends.

Here's a demo of playing a TTS message in a voice channel. The 🔄 emoji is used to replay the cached `.mp3` file.

![Discord_QXzOSBmMNH](https://user-images.githubusercontent.com/6510862/224864185-ecce62ad-f27b-4634-a6e0-5a3205b7c630.gif)

## Usage

1. Get an ElevenLabs API key from the 'Profile' tab on https://beta.elevenlabs.io (create an account first, if needed)
1. Create a discord bot in the [Discord Developer Portal](https://discord.com/developers/applications)
1. Create a discord bot user for the bot and write down the secret token somewhere.
1. Enable the MESSAGE CONTENT and SERVER MEMBERS intents for the bot user.
    ![image](https://user-images.githubusercontent.com/6510862/224864847-cc9933ef-c417-42ca-8007-3962638e180d.png)
1. Install the dependencies.
    ```console
    pip install -r bot/requirements.txt
    ```
1. Launch the bot.
    ```console
    python bot/ai-voice-bot.py --token [your token here] --elevenlabs [your key here]
    ```


## Scraping the web for audio files

To generate audio files for a new voice, you can use the `scrape-audio-clips.py` script.

Run the scraper with the following command:

```console
python scrape-audio-clips.py --url https://dota2.fandom.com/wiki/Abaddon/Responses --voice abaddon
```

This will create, `abaddon.mp3`, which you can [upload to Elevenlabs](https://beta.elevenlabs.io/voice-lab) to create a custom voice model.
