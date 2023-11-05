import discord
import os
import time
import requests
# from saucenao_api import SauceNao
from discord import app_commands
from discord.ext import tasks
from discord.components import Component, Button, ButtonStyle

from src import responses
from src import log
from src.dalle import Dalle
from src.jisho import Jisho

logger = log.setup_logger(__name__)

isPrivate = False
isReplyAll = False
alarms = {}
# MASTER = os.getenv("MASTER")
# SAUCENAO_KEY = os.getenv("SAUCENAO")
# MASTER_PROMPT = "\nThe master is talking to you"
MASTER_PROMPT = ""

class aclient(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.activity = discord.Activity(type=discord.ActivityType.watching, name="/chat | /help")


async def send_message(interaction:discord.Integration, user_message, thread = 1):
    global isReplyAll#, MASTER
    if not isReplyAll:
        author = interaction.user.id
        await interaction.response.defer(ephemeral=isPrivate)
    else:
        author = interaction.author.id
    try:
        response = '> **' + user_message + '** - <@' + \
            str(author) + '> \n\n'
        # if str(author) == MASTER:
        #     user_message += MASTER_PROMPT
        # print(user_message)
        response = f"{response}{await responses.handle_response(user_message, userid = thread)}"
        # if str(message.user.id) == MASTER:
        #     response = response + " What else do you want to know, my master?"
        if len(response) > 1900:
            # Split the response into smaller chunks of no more than 1900 characters each(Discord limit is 2000 per chunk)
            if "```" in response:
                # Split the response if the code block exists
                parts = response.split("```")
                # Send the first message
                if isReplyAll:
                    await interaction.channel.send(parts[0])
                else:
                    await interaction.followup.send(parts[0])
                # Send the code block in a seperate message
                code_block = parts[1].split("\n")
                formatted_code_block = ""
                for line in code_block:
                    while len(line) > 1900:
                        # Split the line at the 50th character
                        formatted_code_block += line[:1900] + "\n"
                        line = line[1900:]
                    formatted_code_block += line + "\n"  # Add the line and seperate with new line

                # Send the code block in a separate message
                if (len(formatted_code_block) > 2000):
                    code_block_chunks = [formatted_code_block[i:i+1900]
                                         for i in range(0, len(formatted_code_block), 1900)]
                    for chunk in code_block_chunks:
                        if isReplyAll:
                            await interaction.channel.send("```" + chunk + "```")
                        else:
                            await interaction.followup.send("```" + chunk + "```")
                else:
                    if isReplyAll:
                        await interaction.channel.send("```" + formatted_code_block + "```")
                    else:
                        await interaction.followup.send("```" + formatted_code_block + "```")
                # Send the remaining of the response in another message

                if len(parts) >= 3:
                    if isReplyAll:
                        await interaction.channel.send(parts[2])
                    else:
                        await interaction.followup.send(parts[2])
            else:
                response_chunks = [response[i:i+1900]
                                   for i in range(0, len(response), 1900)]
                for chunk in response_chunks:
                    if isReplyAll:
                        await interaction.channel.send(chunk)
                    else:
                        await interaction.followup.send(chunk)
                        
        else:
            if isReplyAll:
                await interaction.channel.send(response)
            else:
                await interaction.followup.send(response)
    except Exception as e:
        if isReplyAll:
            await interaction.channel.send("> **Error: Something went wrong, please try again later!**")
        else:
            await interaction.followup.send("> **Error: Something went wrong, please try again later!**")
        logger.exception(f"Error while sending message: {e}")

async def send_notification(client):
    import os.path

    config_dir = os.path.abspath(__file__ + "/../../")
    prompt_name = 'starting-notification.txt'
    prompt_path = os.path.join(config_dir, prompt_name)
    discord_channel_id = os.getenv("DISCORD_CHANNEL_ID")
    try:
        if os.path.isfile(prompt_path) and os.path.getsize(prompt_path) > 0:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt = f.read()
                if (discord_channel_id):
                    logger.info(f"Sending notification with size {len(prompt)}")
                    channel = client.get_channel(int(discord_channel_id))
                    await channel.send(prompt)
                else:
                    logger.info("No Channel selected. Skip sending starting notification.")
        else:
            logger.info(f"No {prompt_name}. Skip sending starting notification.")
    except Exception as e:
        logger.exception(f"Error while sending starting notification: {e}")

async def starting_prompt(client):
    import os.path

    config_dir = os.path.abspath(__file__ + "/../../")
    prompt_name = 'starting-prompt.txt'
    prompt_path = os.path.join(config_dir, prompt_name)
    try:
        if os.path.isfile(prompt_path) and os.path.getsize(prompt_path) > 0:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompts = f.readlines()
                for p in prompts:
                    logger.info(f"Sending prompt with size {len(p)}")
                    responseMessage = await responses.handle_response(p, "system")
                    logger.info(responseMessage)
        else:
            logger.info(f"No {prompt_name}. Skip sending starting prompt.")
    except Exception as e:
        logger.exception(f"Error while sending starting prompt: {e}")

async def send_one_message(interaction, prompt):
    responseMessage = await responses.handle_response(prompt, thread=0xFFFFFFFF)
    await interaction.channel.send(responseMessage)
    return responseMessage


# BtnLeftArrow = Button(style=ButtonStyle.blue, label="←")
# BtnRightArrow = Button(style=ButtonStyle.blue, label="→")
# NovelActionRow = discord.ui.ActionRow(BtnLeftArrow, BtnRightArrow)

def run_discord_bot():

    client = aclient()

    dalle = Dalle("./dalle_tokens.json")
    # sauceNao = SauceNao(SAUCENAO_KEY)
    jisho = Jisho('./JA-ZHdict.dat', './JA-ZHdictindex.dat', './JA-ZHdictpronindex.dat')

    @tasks.loop(seconds=1.0)
    async def tic():
        for t in alarms.keys():
            interaction = alarms[t][0]
            msg = alarms[t][1]
            if (time.time() > t):
                response = "{} {}".format(interaction.user.mention, msg)
                del alarms[t]
                await interaction.channel.send(response)

    @client.event
    async def on_ready():
        tic.start()
        await send_notification(client)
        await starting_prompt(client)
        await client.tree.sync()

        logger.info(f'{client.user} is now running!')

    
    
    @client.tree.command(name="about", description="Self introduction")
    async def introduce(interaction: discord.Interaction):
        await interaction.response.send_message("Hi! I am an AI servant. You can chat with me, ask me to generate an image, ask me to set an alarm, search for the source of a screenshot.")
    
    @client.tree.command(name="photo", description="Display a random photo")
    async def illust(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        r = requests.get('https://picsum.photos/536/354', allow_redirects=False)
        if (r.status_code != 302):
            await interaction.followup.send("An error occured.", ephemeral=True)
        else:
            await interaction.followup.send(r.headers['Location'], ephemeral=False)

    @client.tree.command(name="illust", description="Display a random illustration")
    async def illust(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        r = requests.get('https://www.loliapi.com/acg/pc/?type=&id=', allow_redirects=False)
        if (r.status_code != 302):
            await interaction.followup.send("An error occured.", ephemeral=True)
        else:
            await interaction.followup.send(r.headers['Location'], ephemeral=False)

    @client.tree.command(name="jisho", description="Japanese dictionary")
    async def jpnDict(interaction: discord.Interaction, *, word: str):
        author = interaction.user.id
        responseHead = '> **' + word + '** - <@' + \
            str(author) + '> \n'
        try:
            result = jisho.lookUp(word)
            response = f"{responseHead}{result}"
            await interaction.response.send_message(response)
        except Exception as err:
            await interaction.response.send_message(f"{responseHead} {str(err)}", ephemeral=True)

    # @client.tree.command(name="source", description="Find the source of a screenshot from an anime.")
    # async def findSource(interaction: discord.Interaction, *, url: str):
    #     author = interaction.user.id
    #     responseHead = '> **' + url + '** - <@' + \
    #         str(author) + '> \n'
    #     try:
    #         results = sauceNao.from_url(url)
    #         response = f"{responseHead}The title is: {results[0].title}\nThe author of this image is {results[0].author}.\nThe sources of this image are {results[0].urls}\nConfidence: {results[0].similarity}"
    #         await interaction.response.send_message(response)
    #     except Exception as err:
    #         await interaction.response.send_message(f"{responseHead} {str(err)}", ephemeral=True)

    @client.tree.command(name="alarm", description="Add an alarm")
    async def addAlarm(interaction: discord.Interaction, *, message: str, minute: int, second:int):
        alarms[time.time() + minute * 60 + second] = [interaction, message]
        await interaction.response.send_message('Alarm added.')

    @client.tree.command(name="dalle-token", description="Add your Dalle·E's token. The token should start with \"sess\".")
    async def addToken(interaction: discord.Interaction, *, token: str):
        response = ''
        if not token.startswith('sess'):
            response = 'Error! The token should start with "sess".'
        else:
            dalle.addToken(str(interaction.user.id), token)
            dalle.saveTokens("./dalle_tokens.json")
            response = 'Token has added.'
            logger.info(f"{interaction.user.id} added a token {token}")
        await interaction.response.send_message(response, ephemeral=True)

    @client.tree.command(name="gen-image", description="Generate a image with Dalle·E")
    async def genImage(interaction: discord.Interaction, *, prompt: str):
        author = interaction.user.id
        responseHead = '> **' + prompt + '** - <@' + \
            str(author) + '> \n'
        response = f"{responseHead}I am generating an image for you. This may take some time to finish."
        
        await interaction.response.send_message(response, ephemeral=True)
        try:
            result = await dalle.generate(interaction.user.id, prompt)
            await interaction.channel.send(f"{responseHead} Here is your image:\n{result[0]['generation']['image_path']}")

        except Exception as err:
           await interaction.followup.send(f"{responseHead} {str(err)}", ephemeral=True)

    @client.tree.command(name="self-chat", description="Make ChatGPT talk to itself")
    async def selfChat(interaction: discord.Interaction, *, message: str, iterations: int):
        if iterations > 0:
            author = interaction.user.id
            response = '> **' + message + '** - <@' + \
                str(author) + '> \n'
            response = f"{response}I will be talking to myself for {iterations} times.\n"
            
            await interaction.response.send_message(response, ephemeral=True)
            for _ in range(iterations):
                message = await send_one_message(interaction, message)

    @client.tree.command(name="chat", description="Have a chat with ChatGPT")
    async def chat(interaction: discord.Interaction, *, message: str, thread: int = 1):
        global isReplyAll
        if isReplyAll:
            await interaction.response.defer(ephemeral=False)
            await interaction.followup.send(
                "> **Warn: You already on replyAll mode. If you want to use slash command, switch to normal mode, use `/replyall` again**")
            logger.warning("\x1b[31mYou already on replyAll mode, can't use slash command!\x1b[0m")
            return
        if interaction.user == client.user:
            return
        username = str(interaction.user)
        user_message = message
        channel = str(interaction.channel)
        logger.info(
            f"\x1b[31m{username}\x1b[0m : '{user_message}' ({channel})")
        await send_message(interaction, user_message, thread)

    @client.tree.command(name="private", description="Toggle private access")
    async def private(interaction: discord.Interaction):
        if str(interaction.user.id) != MASTER:
            await interaction.response.send_message("This command is reserved for my master.", ephemeral=True)
            return
        global isPrivate
        await interaction.response.defer(ephemeral=False)
        if not isPrivate:
            isPrivate = not isPrivate
            logger.warning("\x1b[31mSwitch to private mode\x1b[0m")
            await interaction.followup.send(
                "> **Info: Next, the response will be sent via private message. If you want to switch back to public mode, use `/public`**")
        else:
            logger.info("You already on private mode!")
            await interaction.followup.send(
                "> **Warn: You already on private mode. If you want to switch to public mode, use `/public`**")

    @client.tree.command(name="public", description="Toggle public access")
    async def public(interaction: discord.Interaction):
        if str(interaction.user.id) != MASTER:
            await interaction.response.send_message("This command is reserved for my master.", ephemeral=True)
            return
        global isPrivate
        await interaction.response.defer(ephemeral=False)
        if isPrivate:
            isPrivate = not isPrivate
            await interaction.followup.send(
                "> **Info: Next, the response will be sent to the channel directly. If you want to switch back to private mode, use `/private`**")
            logger.warning("\x1b[31mSwitch to public mode\x1b[0m")
        else:
            await interaction.followup.send(
                "> **Warn: You already on public mode. If you want to switch to private mode, use `/private`**")
            logger.info("You already on public mode!")

    @client.tree.command(name="replyall", description="Toggle replyAll access")
    async def replyall(interaction: discord.Interaction):
        if str(interaction.user.id) != MASTER:
            await interaction.response.send_message("This command is reserved for my master.", ephemeral=True)
            return
        global isReplyAll
        await interaction.response.defer(ephemeral=False)
        if isReplyAll:
            await interaction.followup.send(
                "> **Info: The bot will only response to the slash command `/chat` next. If you want to switch back to replyAll mode, use `/replyAll` again.**")
            logger.warning("\x1b[31mSwitch to normal mode\x1b[0m")
        else:
            await interaction.followup.send(
                "> **Info: Next, the bot will response to all message in the server. If you want to switch back to normal mode, use `/replyAll` again.**")
            logger.warning("\x1b[31mSwitch to replyAll mode\x1b[0m")
        isReplyAll = not isReplyAll
            
    @client.tree.command(name="reset", description="Complete reset ChatGPT conversation history")
    async def reset(interaction: discord.Interaction):
        if str(interaction.user.id) != MASTER:
            await interaction.response.send_message("This command is reserved for my master.", ephemeral=True)
            return
        responses.contexts = {}
        await interaction.response.defer(ephemeral=False)
        await interaction.followup.send("> **Info: I have forgotten everything.**")
        logger.warning(
            "\x1b[31mChatGPT bot has been successfully reset\x1b[0m")
        await starting_prompt(client)
        
    @client.tree.command(name="help", description="Show help for the bot")
    async def help(interaction: discord.Interaction):
        if str(interaction.user.id) != MASTER:
            await interaction.response.send_message("This command is reserved for my master.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=False)
        await interaction.followup.send(""":star:**BASIC COMMANDS** \n
        - `/about` Self introduction
        - `/photo` Display a random photo
        - `/illust` Display a random illustration
        - `/jisho [word]` Japanese dictionary
        - `/source [url]` Find the source of a screenshot from an anime
        - `/alarm [message] [minute] [second]` Set an alarm
        - `/gen-image [prompt]` Generate an image with Dalle·E!
        - `/dalle-token [token]` Add your Dalle·E's token. The token should start with "sess"
        - `/chat [message]` Chat with ChatGPT!
        - `/self-chat` Let ChatGPT talk to itself""")
        logger.info(
            "\x1b[31mSomeone need help!\x1b[0m")

    @client.event
    async def on_message(message):
        if isReplyAll:
            if message.author == client.user:
                return
            username = str(message.author)
            user_message = str(message.content)
            channel = str(message.channel)
            logger.info(f"\x1b[31m{username}\x1b[0m : '{user_message}' ({channel})")
            await send_message(message, user_message)
    
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    client.run(TOKEN)