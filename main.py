import asyncio
import os
from time import sleep
import re

import discord
import requests
from discord import FFmpegPCMAudio, Permissions
from helpers import get_question, check, get_audio, get_bonus
from discord.ext import commands

FFMPEG_OPTIONS = {'options': '-vn'}
voice_clients = {}
channels = {}
questions = {}
list = []
new = {}

TOKEN = 'MTEwNDIyOTc0OTk2ODA4OTEwOA.GRp7KR.YFHle0fHoqd4Rft1C3KKNI-q-GdUoatGCwNGzA'
client = discord.Client(intents=discord.Intents.all())


class Player:
    def __init__(self, name, id):
        self.name = name
        self.points = 0
        self.id = id

    def increasePoints(self):
        self.points += 10

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_points(self):
        return self.points





def player_in_list(id, list):
    for i in list:
        if i.get_id() == id:
            return True
    return False


@client.event
async def on_ready():
    print(f'{client.user} is running')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='-help'))


@client.event
async def on_raw_reaction_add(payload):
    message_id = payload.message_id
    if message_id == 1163669112036282502:
        print('yes')
        guild_id = payload.guild_id
        guild = discord.utils.find(lambda g: g.id == guild_id, client.guilds)
        print(payload.emoji.name)
        role = discord.utils.get(guild.roles, id=1051732399723122760)
        member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
        if member is not None:
            await member.remove_roles(role)


@client.event
async def on_message(message):
    playerList = []
    if message.author == client.user:
        return
    async def update_question(q):
        q = re.sub("\(.*?\)|\[.*?\]", "", q)
        return q

    async def play_audio(q, voice):
        audio = get_audio(q)
        source = FFmpegPCMAudio(audio)
        voice.play(source)
        return audio

    async def remove_audio(list):
        for i in list:
            os.remove(i)

    async def bonus(categories, difficulties, voice, channel, player):
        audioList = []
        user = Player(player.name, player.id)
        questionFin = False
        while True:
            partNum = 0
            bonus = get_bonus(categories, difficulties)
            leadIn = bonus[0]['leadin']
            leadAudio = await play_audio(leadIn, voice)
            audioList.append(leadAudio)
            while (partNum > 3):
                while voice.is_playing(): #waits until first part is done reading
                    continue
                bonusPart = bonus[0]['parts'][partNum]
                answerPart = bonus[0]['answers'][partNum]
                audio_name = await play_audio(bonusPart, voice)
                audioList.append(audio_name)

                answer = await bonus_answer(answerPart, player, channel)
                voice.stop()
                if (answer == 'reread'):
                    break
                if (answer == 'accept'):
                    user.increasePoints()
                if (answer == 'reject'):
                    continue
                while not questionFin:






                partNum += 1

    async def bonus_answer(answerLine, player, channel):
        while True:
            try:
                answer = await client.wait_for('message', timeout=180.0)
                if answer.author != player or answer.channel != channel:
                    break
                if answer.content.startswith('_'):
                    break
                if answer.content == '-reread':
                    return 'reread'
                if check(answerLine, answer.content)['directive'] == 'accept' or check(answerLine, answer.content)['directive'] == 'prompt':
                    return 'accept'
                elif check(answerLine, answer.content)['directive'] == 'reject':
                    return 'reject'
            except asyncio.TimeoutError:
                return 'reject'




    async def play(catList, diffList, voice, channel, msgChannel, buzzQ):
        audioList = []

        questionFin = False
        while True:
            newQues = get_question(catList, diffList)
            questions[msgChannel] = newQues
            wholeQues = questions[msgChannel]
            question = wholeQues['tossups'][0]['question']
            if not questionFin:
                newQuestion = await update_question(question)
                new[msgChannel] = newQuestion
                audio_name = await play_audio(new[msgChannel], voice)
                audioList.append(audio_name)
            while True:

                while questionFin:
                    try:
                        next = await client.wait_for('message', timeout=180.0)
                        if next.channel != msgChannel:
                            continue
                        if (next.content == 'y' or next.content == 'Y'):
                            questionFin = True
                            await message.channel.send("Going on")
                            break
                        if (next.content == 'n' or next.content == 'N'):
                            await message.channel.send("Finished")
                            scores = discord.Embed(title="SCORES", color=0xFFBF00)
                            for i in playerList:
                                scores.add_field(name=i.get_name(), value=i.get_points())
                            await message.channel.send(embed=scores)
                            voice.stop()
                            voice.play(FFmpegPCMAudio('silence.mp3'))
                            await client.voice_clients[0].disconnect()
                            await remove_audio(audioList)
                            return

                    except asyncio.TimeoutError:
                        await message.channel.send("Session Ending")
                        scores = discord.Embed(title="SCORES", color=0xFFBF00)
                        for i in playerList:
                            scores.add_field(name=i.get_name(), value=i.get_points())
                        await channel.send(embed=scores)
                        voice.play(FFmpegPCMAudio('silence.mp3'))
                        await client.voice_clients[0].disconnect()
                        await remove_audio(audioList)
                        return
                if (questionFin):
                    questionFin = False
                    break

                try:
                    buzz = await client.wait_for('message', timeout=60.0)
                    if buzz.channel != msgChannel:
                        continue
                    if buzz.channel == channel and not player_in_list(buzz.author.id,
                                                                      playerList) and buzz.author != client.user:
                        playerList.append(Player(buzz.author.name, buzz.author.id))

                    if buzz.channel == channel and buzz.content == 'bz' or buzz.content == 'buzz' or buzz.content == 'Bz' or buzz.content == 'Buzz':
                        voice.pause()
                        buzzQ.append(buzz.author)
                        while (len(buzzQ) > 0):
                            voice.pause()
                            answer = await get_answer(wholeQues['tossups'][0]['answer'], question, buzzQ[0], msgChannel,
                                                      wholeQues['tossups'][0]['setName'])
                            if answer == 1:
                                voice.stop()
                                questionFin = True
                                await channel.send("Y to continue, N to stop")
                                break

                            if answer == '-end':
                                await channel.send("Finished")
                                scores = discord.Embed(title="SCORES", color=0xFFBF00)
                                for i in playerList:
                                    scores.add_field(name=i.get_name(), value=i.get_points())
                                await channel.send(embed=scores)
                                voice.stop()
                                voice.play(FFmpegPCMAudio('silence.mp3'))
                                await client.voice_clients[0].disconnect()
                                await remove_audio(audioList)
                                return
                            if answer == 0:
                                continue
                            if answer == 'prompt':
                                voice.pause()
                                continue
                            if answer == '-score':
                                scores = discord.Embed(title="SCORES", color=0xFFBF00)
                                for i in playerList:
                                    scores.add_field(name=i.get_name(), value=i.get_points())
                                await channel.send(embed=scores)
                            if answer == '-skip' or answer == '-next':
                                voice.stop()
                                embed = discord.Embed(title=wholeQues['tossups'][0]['setName'], description=question,
                                                      color=0x00FF00)
                                embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer'])
                                await channel.send(embed=embed)
                                buzzQ.clear()
                                questionFin = True
                                await channel.send("Y to continue, N to stop")
                                break
                    elif buzz.content == '-end':
                        await channel.send("Finished")
                        scores = discord.Embed(title="SCORES", color=0xFFBF00)
                        for i in playerList:
                            scores.add_field(name=i.get_name(), value=i.get_points())
                        await channel.send(embed=scores)
                        voice.stop()
                        voice.play(FFmpegPCMAudio('silence.mp3'))
                        await client.voice_clients[0].disconnect()
                        buzzQ.clear()
                        await remove_audio(audioList)
                        return
                    elif buzz.content == '-skip' or buzz.content == '-next':
                        voice.stop()
                        embed = discord.Embed(title=wholeQues['tossups'][0]['setName'], description=question,
                                              color=0x00FF00)
                        embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer'])
                        await channel.send(embed=embed)
                        buzzQ.clear()
                        questionFin = True
                        await channel.send("Y to continue, N to stop")
                        break
                    elif buzz.content == '-score':
                        scores = discord.Embed(title="SCORES", color=0xFFBF00)
                        for i in playerList:
                            scores.add_field(name=i.get_name(), value=i.get_points())
                        await channel.send(embed=scores)
                    voice.resume()
                except asyncio.TimeoutError:
                    voice.stop()
                    embed = discord.Embed(title=wholeQues['tossups'][0]['setName'], description=question,
                                          color=0x00FF00)
                    embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer'])
                    await channel.send(embed=embed)
                    await channel.send("Ran out of time")
                    questionFin = True
                    await channel.send("Y to continue, N to stop")
                    buzzQ.clear()
                    break

    async def get_answer(a, q, user, channel, setName):
        await channel.send("Answer for " + user.mention + "?")
        while True:
            try:
                answer = await client.wait_for('message', timeout=20.0)
                if answer.channel == channel and answer.content == 'bz' or answer.content == 'buzz' or answer.content == 'Bz' or answer.content == 'Buzz' and answer.author != user:
                    buzzQ.append(answer.author)
                if user != answer.author or answer.channel != channel:
                    continue
                if answer.content.startswith("_"):
                    break
                if (answer.content == '-skip' or answer.content == '-next'):
                    return '-skip'
                if (answer.content == '-score'):
                    return '-score'
                if (answer.content == 'wd' or answer.content == 'Wd' or answer.content == 'WD'):
                    embed = discord.Embed(title="Withdrew", color=0x738ADB)
                    await channel.send(embed=embed)
                    buzzQ.remove(user)
                    return 0
                if answer.content == '-end':
                    buzzQ.clear()
                    return '-end'
                if check(a, answer.content)['directive'] == 'accept':
                    await channel.send("Correct!")
                    for i in playerList:
                        if i.get_id() == answer.author.id:
                            i.increasePoints()
                    embed = discord.Embed(title=setName, description=q, color=0x00FF00)
                    embed.add_field(name='Answer', value=a)
                    await channel.send(embed=embed)
                    buzzQ.clear()
                    return 1
                elif check(a, answer.content)['directive'] == 'reject':
                    embed = discord.Embed(title="WRONG", color=0xFF0000)
                    await channel.send(embed=embed)
                    buzzQ.remove(user)
                    return 0
                elif check(a, answer.content)['directive'] == 'prompt':
                    embed = discord.Embed(title="PROMPT", color=0x0000FF)
                    await channel.send(embed=embed)
                    return 'prompt'

            except asyncio.TimeoutError:
                await channel.send("Out of time")
                buzzQ.remove(user)
                return 0

    if message.content.startswith('-play'):
        subs = {
            "Literature": "lit",
            "Science": "sci",
            "History": "hist",
            "Fine Arts": "fa",
            "Religion": "religion",
            "Mythology": "myth",
            "Philosophy": "philo",
            "Social Science": "ss",
            "Current Events": "ce",
            "Geography": "geo",
            "Trash": "trash"
        }

        catList = message.content.split()
        catList.remove('-play')
        diffList = []
        for i in catList:
            if i.isdigit() and 10 > int(i) > 0:
                diffList.append(i)
                catList.remove(i)
            elif i.isdigit():
                await message.channel.send("Enter a correct difficulty")
                return

        def get_key(val):

            for key, value in subs.items():
                if val == value:
                    return key

            return "key doesn't exist"

        for i in catList:
            if i in subs.values() and get_key(i) != "key doesn't exist":
                catList[catList.index(i)] = get_key(i)
            else:
                catList.remove(i)  # removes element that is not in subs, could return idk in futur

        channel = message.author.voice
        if channel is None:
            await message.channel.send('must be in voice channel')
            return

        voice = await channel.channel.connect()
        voice_clients[voice.guild.id] = voice
        channel = message.channel
        channels[message.channel.id] = channel
        buzzQ = []
        await play(catList, diffList, voice_clients[voice.guild.id], channel, channels[message.channel.id], buzzQ)

    if message.content.startswith('-bonus'):
        subs = {
            "Literature": "lit",
            "Science": "sci",
            "History": "hist",
            "Fine Arts": "fa",
            "Religion": "religion",
            "Mythology": "myth",
            "Philosophy": "philo",
            "Social Science": "ss",
            "Current Events": "ce",
            "Geography": "geo",
            "Trash": "trash"
        }

        catList = message.content.split()
        catList.remove('-bonus')
        diffList = []
        for i in catList:
            if i.isdigit() and 10 > int(i) > 0:
                diffList.append(i)
                catList.remove(i)
            elif i.isdigit():
                await message.channel.send("Enter a correct difficulty")
                return

        def get_key(val):

            for key, value in subs.items():
                if val == value:
                    return key

            return "key doesn't exist"

        for i in catList:
            if i in subs.values() and get_key(i) != "key doesn't exist":
                catList[catList.index(i)] = get_key(i)
            else:
                catList.remove(i)  # removes element that is not in subs, could return idk in futur

        channel = message.author.voice
        if channel is None:
            await message.channel.send('must be in voice channel')
            return

        voice = await channel.channel.connect()
        voice_clients[voice.guild.id] = voice
        channel = message.channel
        channels[message.channel.id] = channel
        player = message.author
        await bonus(catList, diffList, voice_clients[voice.guild.id], channels[message.channel.id], player)



    if message.content == '-help':
        embed = discord.Embed(title="SpeechQB Help", color=0x3776AB)
        embed.add_field(name="-play",
                        value="-play [cats] [diffs]. i. e   -play geo 2 (must be in voice channel)",
                        inline=False)
        embed.add_field(name="How to buzz in",
                        value="To buzz in an answer type bz or buzz then type your answer within 20 seconds",
                        inline=False)
        embed.add_field(name="How to Withdraw",
                        value="To withdraw after buzzing type wd within 20 seconds",
                        inline=False)
        embed.add_field(name="-skip or -next", value="skips current question", inline=False)
        embed.add_field(name="-end",
                        value="Once in the game and you wish to end, type -end",
                        inline=False)
        embed.add_field(name='-bonus',
                        value="type -bonus [cats] [diffs] to play bonuses",
                        inline=False)
        embed.add_field(name="-score",
                        value="Gives the scores of every person who has buzzed in",
                        inline=False)
        embed.add_field(name="DM dogeking0 for any bugs",
                        value="Version 0.2.0",
                        inline=False)
        await message.channel.send(embed=embed)

    if message.content == '-vikram':
        embed = discord.Embed(title="Veeekram", color=0x3776AB)
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/1029560549903700099/1166187556405252218/IMG_2491.jpg?ex=654993cc&is=65371ecc&hm=9b3f28fb13d33c5f52af344a0ab980c3684843f8207d477fa61d3eef5e4895f2&')
        await message.channel.send(embed=embed)
    if message.content == '-jackie':
        await message.channel.send('Government Coup!!!!')
    if message.content == '-akshath':
        embed = discord.Embed(title="dyuude", color=0x3776AB)
        embed.set_image(
            url=(
                'https://cdn.discordapp.com/attachments/1029560549903700099/1170171115574923264/image.png?ex=655811c6&is=65459cc6&hm=71eb7cbfc3f11a2a1e3b55a241ebe0d7f9e1aac891be95d5bb7550c36c6d76e2&'))
        await message.channel.send(embed=embed)
    if message.content == '-jason':
        await message.channel.send('where were you during the taiping rebellion')
    if message.content == '-varma':
        await message.channel.send('I am adult medium 😠')


client.run(TOKEN)
