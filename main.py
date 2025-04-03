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
active_channels = {}
player_lists = {}
end_list = {}
skip_list = {}
clear_list = {}

TOKEN = 'INSERT YOUR TOKEN HERE'
client = discord.Client(intents=discord.Intents.all())


class Player:
    def __init__(self, name, id):
        self.name = name
        self.points = 0
        self.id = id
        self.powers = 0
        self.tens = 0
        self.negs = 0

    def increasePoints(self):
        self.tens += 1
        self.points += 10

    def power(self):
        self.powers += 1
        self.points += 15

    def neg(self):
        self.negs += 1
        self.points -= 5

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_points(self):
        return self.points

    def get_tens(self):
        return self.tens

    def get_powers(self):
        return self.powers

    def get_negs(self):
        return self.negs

    def toString(self):
        return "(" + str(self.get_powers()) + "/" + str(self.get_tens()) + "/" + str(self.get_negs()) + ")"


def player_in_list(id, list):
    for i in list:
        if i.get_id() == id:
            return True
    return False


@client.event
async def on_ready():
    print(f'{client.user} is running')
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name='=help'))


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
    buzzes = ["buzz", "bz", "buz"]
    if message.content.lower() in buzzes and message.channel.id in active_channels:
        active_channels[message.channel.id].append(message.author)
        if not player_in_list(message.author.id, player_lists[message.channel.id]) and message.author != client.user:
            player_lists[message.channel.id].append(Player(message.author.name, message.author.id))

    if message.content.lower() == "=skip" and message.channel.id in active_channels:
        skip_list[message.channel.id].append('skip')
    if message.content.lower() == "=end" and message.channel.id in active_channels:
        end_list[message.channel.id].append('end')
    if message.content.lower() == '=clear' and message.channel.id in active_channels:
        clear_list[message.channel.id].append('clear')
        del active_channels[message.channel.id]
        del player_lists[message.channel.id]
        del skip_list[message.channel.id]
        del end_list[message.channel.id]
        del clear_list[message.channel.id]
        embed = discord.Embed(title="Session Cleared!", color=0x00FF00)
        await message.channel.send(embed=embed)


    async def update_question(q):
        q = re.sub("\(.*?\)|\[.*?\]", "", q)
        return q

    async def play_audio(q, voice):
        audio = get_audio(q)
        source = FFmpegPCMAudio(audio)
        voice.play(source)
        return audio

    async def remove_audio(audiolist):
        for k in audiolist:
            os.remove(k)

    def finish_question(words, q):
        for k in range(len(words)):
            q = q + words[0] + " "
            del words[0]
        return q

    def increase(playerList, user, words):
        for m in playerList:
            if m.get_id() == user.id:
                if "(*)" in words:
                    m.power()
                else:
                    m.increasePoints()

    def decrease(playerList, user, words):
        for m in playerList:
            if m.get_id() == user.id:
                if (len(words) != 0):
                    m.neg()

    def isPower(words):
        if "(*)" in words:
            return 15
        return 10

    def isNeg(words):
        if len(words) > 0:
            return -5
        return 0

    async def ts(catList, diffList, channel, buzzQ):
        questionFin = False
        quesCount = 1
        player_list = player_lists[channel.id]
        while True:
            time = 20
            newQues = get_question(catList, diffList)
            question = newQues['tossups'][0]['question_sanitized']
            embed = discord.Embed(title='Tossup ' + str(quesCount) + ' - ' + newQues['tossups'][0]['set']['name'],
                                  description="",
                                  color=0x0000FF)
            msg = await channel.send(embed=embed)
            words = question.split()
            q = ""
            await asyncio.sleep(0.7)
            while not questionFin:

                if (len(words) < 6):
                    for i in range(len(words)):
                        q += words[0] + " "
                        del words[0]
                else:
                    for i in range(6):
                        q += words[0] + " "
                        del words[0]
                new_embed = discord.Embed(title='Tossup ' + str(quesCount) + ' - ' + newQues['tossups'][0]['set']['name'],
                                          description=q, color=0x0000FF)
                if time < 0:
                    dead = discord.Embed(title="Tossup dead", description = 'Answer: ' + newQues['tossups'][0]['answer_sanitized'], color=0xFF0000)
                    await channel.send(embed = dead)
                    questionFin = True
                    bembed = discord.Embed(title="Do you want to continue? Answer Y/N", color=0x0000FF)
                    await channel.send(embed=bembed)

                    break
                await msg.edit(embed=new_embed)
                for i in range(8):
                    await asyncio.sleep(0.1)
                    if len(words) == 0:
                        time -= 0.1
                    while len(buzzQ) > 0:
                        answer = await ts_answer(newQues['tossups'][0]['answer_sanitized'], buzzQ[0], channel, words)
                        if (answer == 'accept'):
                            increase(player_list, buzzQ[0], words)
                            buzzQ.clear()
                            questionFin = True
                            q = q + "<:15:1192708186621345863> "
                            bembed = discord.Embed(title="Do you want to continue? Answer Y/N", color=0x0000FF)
                            await channel.send(embed=bembed)
                            break
                        if answer == 'reject':
                            decrease(player_list, buzzQ[0], words)
                            del buzzQ[0]
                            q = q + "<:neg:1192707931242778696> "
                        if answer == 'prompt':
                            continue
                        if answer == 'wd':
                            del buzzQ[0]
                        if answer == 'end':
                            buzzQ.clear()
                            break
                        if answer == 'skip':
                            buzzQ.clear()
                            break
                    while len(skip_list[channel.id]) > 0:
                        skip_list[channel.id].clear()
                        end_list[channel.id].clear()
                        buzzQ.clear()
                        embed = discord.Embed(title='Tossup skipped.',
                                              description='Answer: ' + newQues['tossups'][0]['answer_sanitized'], color=0xFF0000)
                        await channel.send(embed=embed)
                        questionFin = True
                        bembed = discord.Embed(title="Do you want to continue? Answer Y/N", color=0x0000FF)
                        await channel.send(embed=bembed)
                        break
                    while len(end_list[channel.id]) > 0 or len(clear_list[channel.id]) > 0:
                        new_embed = discord.Embed(
                            title='Tossup ' + str(quesCount) + ' - ' + newQues['tossups'][0]['set']['name'],
                            description=finish_question(words, q),
                            color=0x0000FF)
                        await msg.edit(embed=new_embed)
                        c = ''
                        if (len(catList) == 0):
                            c = 'All'
                        else:
                            c = catList[0]
                            del catList[0]
                            for cat in catList:
                                c += ", " + cat
                        if (len(diffList) == 0):
                            c += ", All Diffs"
                        else:
                            for diff in sorted(diffList):
                                c += ", " + str(diff)
                        score = ""
                        for player in player_list:
                            score += player.get_name() + ": " + str(
                                player.get_points()) + " " + player.toString() + "\n"
                        scores = discord.Embed(title="Scores (" + str(quesCount) + " TU read) - " + c,
                                               description=score, color=0x0000FF)
                        await channel.send(embed=scores)
                        del active_channels[channel.id]
                        del player_lists[channel.id]
                        del skip_list[channel.id]
                        del end_list[channel.id]
                        del clear_list[channel.id]
                        return
                    if questionFin:
                        break
            while questionFin:
                new_embed = discord.Embed(
                    title='Tossup ' + str(quesCount) + ' - ' + newQues['tossups'][0]['set']['name'],
                    description=finish_question(words, q),
                    color=0x0000FF)
                await msg.edit(embed=new_embed)
                try:
                    next = await client.wait_for('message', timeout=180.0)
                    if next.channel != channel:
                        continue
                    if (next.content == 'y' or next.content == 'Y'):
                        questionFin = False
                        quesCount += 1
                        break
                    if (next.content == 'n' or next.content == 'N'):
                        c=''
                        if (len(catList) == 0):
                            c = 'All'
                        else:
                            c = catList[0]
                            del catList[0]
                            for cat in catList:
                                c += ", " + cat
                        if (len(diffList) == 0):
                            c += ", All Diffs"
                        else:
                            for diff in sorted(diffList):
                                c += ", " + str(diff)
                        score = ""
                        for player in player_list:
                            score += player.get_name() + ": " + str(player.get_points()) + " " +player.toString() + "\n"
                        scores = discord.Embed(title="Scores (" + str(quesCount) + " TU read) - " + c, description = score, color=0x0000FF)
                        await channel.send(embed=scores)
                        del active_channels[channel.id]
                        del player_lists[channel.id]
                        del skip_list[channel.id]
                        del end_list[channel.id]
                        return

                except asyncio.TimeoutError:
                    timeout = discord.Embed(title="Session timed-out!", color=0xFF0000)
                    await channel.send(embed=timeout)
                    c = catList[0]
                    del catList[0]
                    for cat in catList:
                        c += ", " + cat
                    for diff in diffList:
                        c += ", " + str(diff)
                    score = ""
                    for player in player_list:
                        score += player.get_name() + ": " + str(player.get_points()) + player.toString() + "\n"
                    scores = discord.Embed(title="Scores (" + str(quesCount) + " TU read) - " + c, description=score,
                                           color=0x0000FF)
                    await channel.send(embed=scores)
                    del active_channels[channel.id]
                    del player_lists[channel.id]
                    del skip_list[channel.id]
                    del end_list[channel.id]
                    return

    async def ts_answer(a, user, channel, words):
        answerEmbed = discord.Embed(title='', description='Answer (or wd)' + user.mention, color=0x0000FF)
        await channel.send(embed=answerEmbed)
        while True:
            try:
                answer = await client.wait_for('message', timeout=20.0)
                if user != answer.author or answer.channel != channel:
                    continue
                if answer.content.startswith("_"):
                    break
                if answer.content == '=skip':
                    embed = discord.Embed(title='Tossup skipped.',
                                          description='Answer: ' + a, color=0xFF0000)
                    await channel.send(embed=embed)
                    return 'skip'
                if answer.content == '=score':
                    return 'score'
                if answer.content == 'wd' or answer.content == 'Wd' or answer.content == 'WD':
                    return 'wd'
                if answer.content == '=end':
                    return 'end'
                if check(a, answer.content)['directive'] == 'accept':
                    embed = discord.Embed(title='Correct. ' + str(isPower(words)) + " points",
                                          description='Answer: ' + a, color=0x00FF00)
                    await channel.send(embed=embed)
                    return 'accept'
                elif check(a, answer.content)['directive'] == 'reject':
                    embed = discord.Embed(title="Incorrect!",
                                          description=str(isNeg(words)) + " points for " + user.mention, color=0xFF0000)
                    await channel.send(embed=embed)
                    return 'reject'
                elif check(a, answer.content)['directive'] == 'prompt':
                    embed = discord.Embed(title="PROMPT", color=0x0000FF)
                    await channel.send(embed=embed)
                    return 'prompt'

            except asyncio.TimeoutError:
                return 'reject'

    async def bonus(categories, difficulties, channel, player):
        user = Player(player.name, player.id)
        questionFin = False
        bonusNum = 0
        while True:
            partNum = 0
            bonus = get_bonus(categories, difficulties)['bonuses'][0]
            leadIn = bonus['leadin_sanitized']
            leadInEmbed = discord.Embed(title=bonus["set"]["name"], description=leadIn, color=0x00FF00)
            leadInEmbed.set_author(name="For " + player.name)
            await channel.send(embed=leadInEmbed)
            while (partNum < 3):
                bonusPart = bonus['parts_sanitized'][partNum]
                answerPart = bonus['answers_sanitized'][partNum]
                bonusEmbed = discord.Embed(title="Part " + str(partNum + 1), description = bonusPart, color =0x0000FF)
                await channel.send(embed=bonusEmbed)
                answer = await bonus_answer(answerPart, player, channel)
                if (answer == 'accept'):
                    correctEmbed = discord.Embed(title="Correct", description=answerPart, color = 0x0000FF)
                    correctEmbed.set_author(name=player.name)
                    await channel.send(embed=correctEmbed)
                    user.increasePoints()
                if (answer == 'reject'):
                    incorrectEmbed = discord.Embed(title="Were you correct? [y/n]", description=answerPart, color=0xFF0000)
                    incorrectEmbed.set_author(name=player.name)
                    await channel.send(embed=incorrectEmbed)
                    while True:
                        try:
                            ans = await client.wait_for('message', timeout=3600)
                            if ans.channel != channel or player != ans.author:
                                continue
                            if ans.content.lower() == "y" or ans.content.lower() == "n":
                                if ans.content.lower() == "y":
                                    user.increasePoints()
                                break

                        except asyncio.TimeoutError:
                            ppb = 0
                            if categories == []:
                                categories = "All"
                            if bonusNum == 0:
                                ppb = "N/A"
                            else:
                                ppb = user.get_points() / bonusNum
                            scoresEmbed = discord.Embed(title="Stats", description="requested by " + player.name, color=0xFF0000)
                            scoresEmbed.add_field(name="Categories", value=categories)
                            scoresEmbed.add_field(name="Bonuses", value=bonusNum)
                            scoresEmbed.add_field(name="Points", value=user.get_points())
                            scoresEmbed.add_field(name="PPB", value=ppb)
                            await channel.send(embed=scoresEmbed)
                            del active_channels[channel.id]
                            return
                if answer == "end":
                    ppb = 0
                    if categories == []:
                        categories = "All"
                    if bonusNum == 0:
                        ppb = "N/A"
                    else:
                        ppb = user.get_points() / bonusNum
                    if len(difficulties) == 0:
                        difficulties = "All"
                    scoresEmbed = discord.Embed(title="Stats", description="requested by " + player.name, color=0xFF0000)
                    scoresEmbed.add_field(name="Categories", value = categories)
                    scoresEmbed.add_field(name="Difficulties", value = difficulties)
                    scoresEmbed.add_field(name="Bonuses", value=bonusNum)
                    scoresEmbed.add_field(name="Points", value=user.get_points())
                    scoresEmbed.add_field(name="PPB", value=ppb)
                    await channel.send(embed=scoresEmbed)
                    del active_channels[channel.id]
                    return
                if answer == "skip":
                    break
                if not questionFin:
                    partNum += 1
            bonusNum += 1

    async def bonus_answer(answerLine, player, channel):
        while True:
            try:
                answer = await client.wait_for('message', timeout=3600)
                if answer.author != player or answer.channel != channel:
                    continue
                if answer.content.startswith('_'):
                    continue
                if answer.content == "=end":
                    return "end"
                if answer.content == "=skip":
                    return "skip"
                if check(answerLine, answer.content)['directive'] == 'accept' or check(answerLine, answer.content)[
                    'directive'] == 'prompt':
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
            question = wholeQues['tossups'][0]['question_sanitized']
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
                            del active_channels[channel.id]
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
                        del active_channels[channel.id]
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
                        while (len(buzzQ) > 0):
                            voice.pause()
                            answer = await get_answer(wholeQues['tossups'][0]['answer_sanitized'], question, buzzQ[0], msgChannel,
                                                      wholeQues['tossups'][0]['set']['name'], buzzQ)
                            if answer == 1:
                                voice.stop()
                                questionFin = True
                                await channel.send("Y to continue, N to stop")
                                break

                            if answer == '=end':
                                await channel.send("Finished")
                                scores = discord.Embed(title="SCORES", color=0xFFBF00)
                                for i in playerList:
                                    scores.add_field(name=i.get_name(), value=i.get_points())
                                await channel.send(embed=scores)
                                voice.stop()
                                voice.play(FFmpegPCMAudio('silence.mp3'))
                                await client.voice_clients[0].disconnect()
                                await remove_audio(audioList)
                                del active_channels[channel.id]
                                return
                            if answer == 0:
                                del buzzQ[0]
                                continue
                            if answer == 'prompt':
                                voice.pause()
                                continue
                            if answer == '=score':
                                scores = discord.Embed(title="SCORES", color=0xFFBF00)
                                for i in playerList:
                                    scores.add_field(name=i.get_name(), value=i.get_points())
                                await channel.send(embed=scores)
                            if answer == '=skip' or answer == '=next':
                                voice.stop()
                                embed = discord.Embed(title=wholeQues['tossups'][0]['set']['name'], description=question,
                                                      color=0x00FF00)
                                embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer_sanitized'])
                                await channel.send(embed=embed)
                                buzzQ.clear()
                                questionFin = True
                                await channel.send("Y to continue, N to stop")
                                break
                    elif buzz.content == '=end':
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
                        del active_channels[channel.id]
                        return
                    elif buzz.content == '=skip' or buzz.content == '=next':
                        voice.stop()
                        embed = discord.Embed(title=wholeQues['tossups'][0]['set']['name'], description=question,
                                              color=0x00FF00)
                        embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer_sanitized'])
                        await channel.send(embed=embed)
                        buzzQ.clear()
                        questionFin = True
                        await channel.send("Y to continue, N to stop")
                        break
                    elif buzz.content == '=score':
                        scores = discord.Embed(title="SCORES", color=0xFFBF00)
                        for i in playerList:
                            scores.add_field(name=i.get_name(), value=i.get_points())
                        await channel.send(embed=scores)
                    voice.resume()
                except asyncio.TimeoutError:
                    voice.stop()
                    embed = discord.Embed(title=wholeQues['tossups'][0]['set']['name'], description=question,
                                          color=0x00FF00)
                    embed.add_field(name='Answer', value=wholeQues['tossups'][0]['answer_sanitized'])
                    await channel.send(embed=embed)
                    await channel.send("Ran out of time")
                    questionFin = True
                    await channel.send("Y to continue, N to stop")
                    buzzQ.clear()
                    break

    async def get_answer(a, q, user, channel, setName, buzzQ):
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
                if (answer.content == '=skip' or answer.content == '=next'):
                    return '=skip'
                if (answer.content == '=score'):
                    return '=score'
                if (answer.content == 'wd' or answer.content == 'Wd' or answer.content == 'WD'):
                    embed = discord.Embed(title="Withdrew", color=0x738ADB)
                    await channel.send(embed=embed)
                    return 0
                if answer.content == '=end':
                    buzzQ.clear()
                    return '=end'
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
                    return 0
                elif check(a, answer.content)['directive'] == 'prompt':
                    embed = discord.Embed(title="PROMPT", color=0x0000FF)
                    await channel.send(embed=embed)
                    return 'prompt'

            except asyncio.TimeoutError:
                await channel.send("Out of time")
                buzzQ.remove(user)
                return 0

    if message.content.startswith('=play'):
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
            "Trash": "trash",
            "American Literature": "amlit",
            "British Literature": "britlit",
            "Classical Literature": "classicallit",
            "European Literature": "eurolit",
            "World Literature": "worldlit",
            "Other Literature": "otherlit",
            "American History": "amhist",
            "Ancient History": "ancienthist",
            "European History": "eurohist",
            "World History": "worldhist",
            "Other History": "otherhist",
            "Biology": "bio",
            "Chemistry": "chem",
            "Physics": "phys",
            "Other Science": "osci",
            "Visual Fine Arts": "vfa",
            "Auditory Fine Arts": "afa",
            "Other Fine Arts": "ofa",
            "Drama": "drama",
            "Long Fiction": "longfiction",
            "Poetry": "poetry",
            "Short Fiction": "shortfiction",
            "Misc Literature": "misclit",
            "Math": "math",
            "Astronomy": "astronomy",
            "Computer Science": "cs",
            "Earth Science": "earthscience",
            "Engineering": "eng",
            "Misc Science": "miscsci",
            "Architecture": "architecture",
            "Dance": "dance",
            "Film": "film",
            "Jazz": "jazz",
            "Opera": "opera",
            "Photography": "photography",
            "Misc Arts": "miscarts",
            "Anthropology": "anthropology",
            "Economics": "economics",
            "Linguistics": "linguistics",
            "Psychology": "psych",
            "Sociology": "sociology",
            "Other Social Science": "otherss"
        }

        catList = message.content
        catList = catList.replace(',', '')
        catList = catList.split();
        catList.remove('=play')
        diffList = []
        newCatList = []
        for i in catList:
            if i.isdigit() and 10 > int(i) > 0:
                diffList.append(i)
            elif i.isdigit():
                await message.channel.send("Enter a correct difficulty")
                return
            else:
                newCatList.append(i)
        catList = newCatList

        def get_key(val):

            for key, value in subs.items():
                if val == value:
                    return key

            return "key doesn't exist"

        for i in catList:
            if i in subs.values() and get_key(i) != "key doesn't exist":
                catList[catList.index(i)] = get_key(i)
            else:
                await message.channel.send("Enter Correct Categories")
                return  # removes element that is not in subs, could return idk in futur

        v_channel = message.author.voice
        channel = message.channel
        if v_channel is None:
            await message.channel.send('must be in voice channel')
            return
        elif channel.id in active_channels.keys():
            embed = discord.Embed(title='Session Active', color = 0xFF0000)
            await channel.send(embed = embed)
            return
        else:
            voice = await v_channel.channel.connect()
            voice_clients[voice.guild.id] = voice
            channel = message.channel
            channels[channel.id] = channel
            buzzQ = []
            active_channels[channel.id] = buzzQ
            await play(catList, diffList, voice_clients[voice.guild.id], channel, channels[message.channel.id], buzzQ)

    if message.content.startswith('=ts'):
        cats = {
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
            "Trash": "trash",
            "American Literature": "amlit",
            "British Literature": "britlit",
            "Classical Literature": "classicallit",
            "European Literature": "eurolit",
            "World Literature": "worldlit",
            "Other Literature": "otherlit",
            "American History": "amhist",
            "Ancient History": "ancienthist",
            "European History": "eurohist",
            "World History": "worldhist",
            "Other History": "otherhist",
            "Biology": "bio",
            "Chemistry": "chem",
            "Physics": "phys",
            "Other Science": "osci",
            "Visual Fine Arts": "vfa",
            "Auditory Fine Arts": "afa",
            "Other Fine Arts": "ofa",
            "Drama": "drama",
            "Long Fiction": "longfiction",
            "Poetry": "poetry",
            "Short Fiction": "shortfiction",
            "Misc Literature": "misclit",
            "Math": "math",
            "Astronomy": "astronomy",
            "Computer Science": "cs",
            "Earth Science": "earthscience",
            "Engineering": "eng",
            "Misc Science": "miscsci",
            "Architecture": "architecture",
            "Dance": "dance",
            "Film": "film",
            "Jazz": "jazz",
            "Opera": "opera",
            "Photography": "photography",
            "Misc Arts": "miscarts",
            "Anthropology": "anthropology",
            "Economics": "economics",
            "Linguistics": "linguistics",
            "Psychology": "psych",
            "Sociology": "sociology",
            "Other Social Science": "otherss"
        }
        catList= message.content
        catList = catList.replace(',', '')
        catList = catList.split();
        catList.remove('=ts')
        diffList = []
        newCatList = []
        for i in catList:
            if i.isdigit() and 10 > int(i) > 0:
                diffList.append(i)
            elif i.isdigit():
                embed = discord.Embed(title="Enter a correct difficulty", color = 0xFF0000)
                await message.channel.send(embed=embed)
                return
            else:
                newCatList.append(i)
        catList = newCatList


        def get_key(val):

            for key, value in cats.items():
                if val == value:
                    return key

            return "key doesn't exist"
        for i in catList:
            if i in cats.values() and get_key(i) != "key doesn't exist":
                catList[catList.index(i)] = get_key(i)
            else:
                await message.channel.send("Enter Correct Categories")
                return # removes element that is not in subs, could return idk in futur

        channel = message.channel
        buzzQ = []
        player_list = []
        if (channel.id not in active_channels.keys()):
            active_channels[channel.id] = buzzQ
            player_lists[channel.id] = player_list
            skip_list[channel.id] = []
            end_list[channel.id] = []
            clear_list[channel.id] = []
            await ts(catList, diffList, channel, active_channels[channel.id]);
        else:
            embed = discord.Embed(title='Session Active', color = 0xFF0000)
            await channel.send(embed = embed)



    if message.content.startswith('=bonus'):
        cats = {
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
            "Trash": "trash",
            "American Literature": "amlit",
            "British Literature": "britlit",
            "Classical Literature": "classicallit",
            "European Literature": "eurolit",
            "World Literature": "worldlit",
            "Other Literature": "otherlit",
            "American History": "amhist",
            "Ancient History": "ancienthist",
            "European History": "eurohist",
            "World History": "worldhist",
            "Other History": "otherhist",
            "Biology": "bio",
            "Chemistry": "chem",
            "Physics": "phys",
            "Other Science": "osci",
            "Visual Fine Arts": "vfa",
            "Auditory Fine Arts": "afa",
            "Other Fine Arts": "ofa",
            "Drama": "drama",
            "Long Fiction": "longfiction",
            "Poetry": "poetry",
            "Short Fiction": "shortfiction",
            "Misc Literature": "misclit",
            "Math": "math",
            "Astronomy": "astronomy",
            "Computer Science": "cs",
            "Earth Science": "earthscience",
            "Engineering": "eng",
            "Misc Science": "miscsci",
            "Architecture": "architecture",
            "Dance": "dance",
            "Film": "film",
            "Jazz": "jazz",
            "Opera": "opera",
            "Photography": "photography",
            "Misc Arts": "miscarts",
            "Anthropology": "anthropology",
            "Economics": "economics",
            "Linguistics": "linguistics",
            "Psychology": "psych",
            "Sociology": "sociology",
            "Other Social Science": "otherss"
        }

        catList = message.content
        catList = catList.replace(',', '')
        catList = catList.split();
        catList.remove('=bonus')
        diffList = []
        newCatList = []
        for i in catList:
            if i.isdigit() and 10 > int(i) > 0:
                diffList.append(i)
            elif i.isdigit():
                embed = discord.Embed(title="Enter a correct difficulty", color=0xFF0000)
                await message.channel.send(embed=embed)
                return
            else:
                newCatList.append(i)
        catList = newCatList

        def get_key(val):

            for key, value in cats.items():
                if val == value:
                    return key

            return "key doesn't exist"

        for i in catList:
            if i in cats.values() and get_key(i) != "key doesn't exist":
                catList[catList.index(i)] = get_key(i)
            else:
                await message.channel.send("Enter Correct Categories")
                return  # removes element that is not in subs, could return idk in futur

        channel = message.channel
        user = message.author
        buzzQ = []
        if (channel.id not in active_channels.keys()):
            active_channels[channel.id] = buzzQ
            skip_list[channel.id] = []
            end_list[channel.id] = []
            clear_list[channel.id] = []
            await bonus(catList, diffList, channel, user)
        else:
            embed = discord.Embed(title='Session Active', color=0xFF0000)
            await channel.send(embed=embed)

    if message.content == '=help':
        embed = discord.Embed(title="SpeechQB Help", color=0x3776AB)
        embed.add_field(name="=ts",
                              value = "=ts [cats] [diffs]. i. e  =ts geo 2, this is a text based version",
                              inline=False)
        embed.add_field(name="=play",
                        value="=play [cats] [diffs]. i. e   -play geo 2 (must be in voice channel), this mode will use AI reader in voice channel to read you questions",
                        inline=False)
        embed.add_field(name="How to buzz in",
                        value="To buzz in an answer type bz or buzz then type your answer within 20 seconds",
                        inline=False)
        embed.add_field(name="How to Withdraw",
                        value="To withdraw after buzzing type wd within 20 seconds",
                        inline=False)
        embed.add_field(name="=skip or =next", value="skips current question", inline=False)
        embed.add_field(name="=end",
                        value="Once in the game and you wish to end, type =end",
                        inline=False)
        embed.add_field(name='=bonus',
                        value="type =bonus [cats] [diffs] to play bonuses",
                        inline=False)
        embed.add_field(name="=score",
                        value="Gives the scores of every person who has buzzed in",
                        inline=False)
        embed.add_field(name="DM dogeking0 for any bugs",
                        value="Version 0.4.0",
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
