import datetime
import logging
import openai
import json
import os
import discord
import tempfile
from gtts import gTTS
from discord import Intents
from discord.ext import commands
from discord.ext import commands
from dotenv import load_dotenv
from pycoingecko import CoinGeckoAPI

if not discord.opus.is_loaded():
    discord.opus.load_opus('/opt/homebrew/lib/libopus.0.dylib')

logging.basicConfig(level=logging.INFO)
load_dotenv()

DC_API_KEY = os.environ["DISCORD_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY
cg = CoinGeckoAPI()

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")


@bot.command(name="ask")
@commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
async def ask(ctx, *, question):
    print(f"{ctx.author.name} asked: {question}")
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"{question}\n\n",
        temperature=0.7,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    answer = response.choices[0].text.strip()
    nickname = ctx.author.display_name  # Get the user's nickname
    save_question_and_answer_to_file(nickname, question, answer)

    # Create an embed for the answer
    answer_embed = discord.Embed(
        title="Genie's Answer",
        description=answer,
        color=discord.Color.blue()
    )
    answer_embed.set_footer(text=f"Asked by: {nickname}")

    await ctx.send(embed=answer_embed)

    # Make the bot speak the answer
    await text_to_speech(ctx, f"{answer}")


@ask.error
async def ask_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining_time = int(error.retry_after)
        await ctx.send(f"Please wait {remaining_time} seconds before asking another question.")
    else:
        raise error


@bot.command(name="test")
async def test(ctx):
    await ctx.send("Test command received!")


@test.error
async def test_error(ctx, error):
    await ctx.send(f"An error occurred while processing the test command: {error}")


@bot.command(name="price")
async def price(ctx, *, coin_name: str):
    try:
        search_results = cg.search(coin_name)
        if search_results and search_results['coins']:
            coin_id = search_results['coins'][0]['id']
            coin_data = cg.get_coin_by_id(coin_id)
            symbol = coin_data['symbol'].upper()
            current_price = coin_data['market_data']['current_price']['usd']
            await ctx.send(f"The current price of {symbol} is ${current_price:.2f}.")
        else:
            await ctx.send(f"Could not find the cryptocurrency '{coin_name}'.")
    except Exception as e:
        print(e)
        await ctx.send("Error occurred while fetching the cryptocurrency price.")


@price.error
async def price_error(ctx, error):
    await ctx.send(f"An error occurred while processing the price command: {error}")


@bot.command(name="prediction")
async def prediction(ctx, *, coin_name: str):
    try:
        # Fetch coin ID
        search_results = cg.search(coin_name)
        if search_results and search_results['coins']:
            coin_id = search_results['coins'][0]['id']
            coin_data = cg.get_coin_by_id(coin_id)

            # Extract data to be used in the prompt
            symbol = coin_data['symbol'].upper()
            price_change_percentage_24h = coin_data['market_data']['price_change_percentage_24h']

            # Construct the prompt
            prompt = f"Based on the recent market trends, the price of {symbol} has changed by {price_change_percentage_24h:.2f}% in the last 24 hours. What is your prediction and analysis for the future of {symbol}?"

            # Generate a response from ChatGPT
            response = openai.Completion.create(
                engine="text-davinci-004",
                prompt=prompt,
                max_tokens=100,
                n=1,
                stop=None,
                temperature=0.5,
            )

            prediction_text = response.choices[0].text.strip()
            await ctx.send(prediction_text)
        else:
            await ctx.send(f"Could not find the cryptocurrency '{coin_name}'.")
    except Exception as e:
        print(e)
        await ctx.send("Error occurred while fetching the cryptocurrency prediction.")


@prediction.error
async def prediction_error(ctx, error):
    await ctx.send(f"An error occurred while processing the prediction command: {error}")

@bot.command(name="speak")
async def speak(ctx, *, text: str):
    """Converts text to speech and plays it in the user's voice channel."""
    if not ctx.author.voice:
        await ctx.send("You must be connected to a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()

    tts = gTTS(text=text, lang="en", slow=False)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        tts.save(fp.name)
        fp.seek(0)
        source = discord.FFmpegPCMAudio(executable="ffmpeg", source=fp.name)
        ctx.voice_client.play(source, after=lambda e: (print(f"Error playing audio: {e}") if e else None, os.remove(fp.name)))

    await ctx.send(f"Playing: {text}")

def save_question_and_answer_to_file(nickname, question, answer):
    data = {}
    try:
        with open("questions_and_answers.json", "r") as file:
            file_content = file.read().strip()
            if file_content:
                data = json.loads(file_content)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error reading questions_and_answers.json: {e}")

    entry = {
        "nickname": nickname,
        "question": question,
        "answer": answer,
        "timestamp": str(datetime.datetime.now())
    }

    if "entries" not in data:
        data["entries"] = []

    data["entries"].append(entry)

    with open("questions_and_answers.json", "w") as file:
        json.dump(data, file, indent=4)


async def text_to_speech(ctx, text: str):
    if not ctx.author.voice:
        await ctx.send("You must be connected to a voice channel to use this command.")
        return

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await voice_channel.connect()

    tts = gTTS(text=text, lang="en", slow=False)
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        tts.save(fp.name)
        fp.seek(0)
        source = discord.FFmpegPCMAudio(executable="ffmpeg", source=fp.name)
        ctx.voice_client.play(source, after=lambda e: (print(f"Error playing audio: {e}") if e else None, os.remove(fp.name)))

    await ctx.send(f"Playing: {text}")


@bot.command(name="stt")
async def stt(ctx):
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("You must be connected to a voice channel to use this command.")
        return

    # Connect to the voice channel
    voice_client = await voice_channel.connect()

    # Start listening to the voice channel
    voice_client.start_listening()
    await ctx.send("Listening...")

    # Transcribe the speech to text
    transcribed_text = transcribe_speech(voice_client)

    # Pass the transcribed text to the GPT model
    response = openai.Completion.create(
        engine="text-davinci-004",
        prompt=f"{transcribed_text}\n\n",
        temperature=0.7,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    answer = response.choices[0].text.strip()

    # Send the answer back to the chat channel
    await ctx.send(answer)

async def on_message(message):
    if message.content == "!stt":
        voice_channel = message.author.voice.channel
        if voice_channel is not None:
            # Join the user's voice channel
            vc = await voice_channel.connect()

            # Get the audio from the voice channel
            audio = vc.sources.get(discord.FFmpegPCMAudio)

            # Use the speech_recognition library to transcribe the audio
            r = sr.Recognizer()
            transcribed_text = r.recognize_google(audio)

            # Disconnect from the voice channel
            await vc.disconnect()

            # Send the transcribed text as a message
            await message.channel.send(transcribed_text)
        else:
            await message.channel.send("You must be in a voice channel to use this command.")

def transcribe_speech(voice_client):
    # Replace this with your own code to transcribe the speech to text
    transcribed_text = "Sample transcribed text"
    return transcribed_text

bot.run(DC_API_KEY)
