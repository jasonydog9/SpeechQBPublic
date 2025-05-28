import asyncio
import os
import re
import discord
from discord import FFmpegPCMAudio
from helpers import get_question, check, get_audio
from utils.player import Player

class VoiceMode:
    def __init__(self, bot):
        self.bot = bot
        self.FFMPEG_OPTIONS = {'options': '-vn'}

    async def start_game(self, message):
        """Start a voice-based quiz game"""
        # Parse categories and difficulties
        cat_list, diff_list, error = self.bot.parse_categories_and_difficulties(
            message.content, '=play'
        )
        
        if error:
            await message.channel.send(error)
            return

        # Check if user is in voice channel
        v_channel = message.author.voice
        if v_channel is None:
            await message.channel.send('Must be in voice channel')
            return

        # Check if session is already active
        channel = message.channel
        if channel.id in self.bot.active_channels.keys():
            embed = discord.Embed(title='Session Active', color=0xFF0000)
            await channel.send(embed=embed)
            return

        # Connect to voice channel and start game
        voice = await v_channel.channel.connect()
        self.bot.voice_clients[voice.guild.id] = voice
        self.bot.channels[channel.id] = channel
        
        buzz_queue = []
        self.bot.active_channels[channel.id] = buzz_queue
        
        await self.play_game(cat_list, diff_list, voice, channel, buzz_queue)

    async def play_game(self, cat_list, diff_list, voice, channel, buzz_queue):
        """Main game loop for voice mode"""
        audio_list = []
        question_finished = False
        player_list = []

        while True:
            # Get new question
            new_question = get_question(cat_list, diff_list)
            self.bot.questions[channel.id] = new_question
            whole_question = self.bot.questions[channel.id]
            question = whole_question['tossups'][0]['question_sanitized']

            if not question_finished:
                cleaned_question = await self.update_question(question)
                audio_name = await self.play_audio(cleaned_question, voice)
                audio_list.append(audio_name)

            # Game loop
            while True:
                # Handle question continuation
                while question_finished:
                    try:
                        next_msg = await self.bot.client.wait_for('message', timeout=180.0)
                        if next_msg.channel != channel:
                            continue

                        if next_msg.content.lower() in ['y', 'yes']:
                            question_finished = False
                            await channel.send("Going on")
                            break
                        
                        if next_msg.content.lower() in ['n', 'no']:
                            await self.end_game(channel, voice, player_list, audio_list)
                            return

                    except asyncio.TimeoutError:
                        await self.timeout_end_game(channel, voice, player_list, audio_list)
                        return

                if question_finished:
                    question_finished = False
                    break

                # Wait for buzz or timeout
                try:
                    buzz = await self.bot.client.wait_for('message', timeout=60.0)
                    if buzz.channel != channel:
                        continue

                    # Add new players
                    if (buzz.channel == channel and 
                        not self.bot.player_in_list(buzz.author.id, player_list) and 
                        buzz.author != self.bot.client.user):
                        player_list.append(Player(buzz.author.name, buzz.author.id))

                    # Handle buzz
                    if self.is_buzz_command(buzz.content):
                        voice.pause()
                        buzz_queue.append(buzz.author)
                        
                        while len(buzz_queue) > 0:
                            answer = await self.get_answer(
                                whole_question['tossups'][0]['answer_sanitized'],
                                question,
                                buzz_queue[0],
                                channel,
                                whole_question['tossups'][0]['set']['name'],
                                buzz_queue,
                                player_list
                            )
                            
                            if answer == 1:  # Correct answer
                                voice.stop()
                                question_finished = True
                                await channel.send("Y to continue, N to stop")
                                break
                            elif answer == '=end':
                                await self.end_game(channel, voice, player_list, audio_list)
                                return
                            elif answer == 0:  # Wrong answer
                                del buzz_queue[0]
                                continue
                            elif answer == 'prompt':
                                voice.pause()
                                continue
                            elif answer == '=score':
                                await self.show_scores(channel, player_list)
                            elif answer in ['=skip', '=next']:
                                await self.skip_question(channel, voice, whole_question, question, buzz_queue)
                                question_finished = True
                                break

                    # Handle other commands
                    elif buzz.content == '=end':
                        await self.end_game(channel, voice, player_list, audio_list)
                        return
                    elif buzz.content in ['=skip', '=next']:
                        await self.skip_question(channel, voice, whole_question, question, buzz_queue)
                        question_finished = True
                        break
                    elif buzz.content == '=score':
                        await self.show_scores(channel, player_list)

                    voice.resume()

                except asyncio.TimeoutError:
                    await self.timeout_question(channel, voice, whole_question, question, buzz_queue)
                    question_finished = True
                    break

    async def update_question(self, question):
        """Clean up question text"""
        return re.sub(r"\(.?\)|\[.?\]", "", question)

    async def play_audio(self, question, voice):
        """Play audio for the question"""
        audio = get_audio(question)
        source = FFmpegPCMAudio(audio)
        voice.play(source)
        return audio

    async def remove_audio(self, audio_list):
        """Remove temporary audio files"""
        for audio_file in audio_list:
            try:
                os.remove(audio_file)
            except FileNotFoundError:
                pass

    def is_buzz_command(self, content):
        """Check if message is a buzz command"""
        return content.lower() in ['bz', 'buzz', 'Bz', 'Buzz']

    async def get_answer(self, correct_answer, question, user, channel, set_name, buzz_queue, player_list):
        """Handle user's answer attempt"""
        await channel.send(f"Answer for {user.mention}?")

        while True:
            try:
                answer = await self.bot.client.wait_for('message', timeout=20.0)
                
                # Handle new buzzes while waiting for answer
                if (answer.channel == channel and 
                    self.is_buzz_command(answer.content) and 
                    answer.author != user):
                    buzz_queue.append(answer.author)

                if user != answer.author or answer.channel != channel:
                    continue

                if answer.content.startswith("_"):
                    break

                # Handle commands
                if answer.content in ['=skip', '=next']:
                    return '=skip'
                if answer.content == '=score':
                    return '=score'
                if answer.content.lower() in ['wd', 'Wd', 'WD']:
                    embed = discord.Embed(title="Withdrew", color=0x738ADB)
                    await channel.send(embed=embed)
                    return 0
                if answer.content == '=end':
                    buzz_queue.clear()
                    return '=end'

                # Check answer
                result = check(correct_answer, answer.content)
                
                if result['directive'] == 'accept':
                    await channel.send("Correct!")
                    for player in player_list:
                        if player.get_id() == answer.author.id:
                            player.increasePoints()
                    
                    embed = discord.Embed(title=set_name, description=question, color=0x00FF00)
                    embed.add_field(name='Answer', value=correct_answer)
                    await channel.send(embed=embed)
                    buzz_queue.clear()
                    return 1
                
                elif result['directive'] == 'reject':
                    embed = discord.Embed(title="WRONG", color=0xFF0000)
                    await channel.send(embed=embed)
                    return 0
                
                elif result['directive'] == 'prompt':
                    embed = discord.Embed(title="PROMPT", color=0x0000FF)
                    await channel.send(embed=embed)
                    return 'prompt'

            except asyncio.TimeoutError:
                await channel.send("Out of time")
                if user in buzz_queue:
                    buzz_queue.remove(user)
                return 0

    async def show_scores(self, channel, player_list):
        """Display current scores"""
        scores = discord.Embed(title="SCORES", color=0xFFBF00)
        for player in player_list:
            scores.add_field(name=player.get_name(), value=player.get_points())
        await channel.send(embed=scores)

    async def skip_question(self, channel, voice, whole_question, question, buzz_queue):
        """Skip current question"""
        voice.stop()
        embed = discord.Embed(
            title=whole_question['tossups'][0]['set']['name'],
            description=question,
            color=0x00FF00
        )
        embed.add_field(name='Answer', value=whole_question['tossups'][0]['answer_sanitized'])
        await channel.send(embed=embed)
        buzz_queue.clear()
        await channel.send("Y to continue, N to stop")

    async def timeout_question(self, channel, voice, whole_question, question, buzz_queue):
        """Handle question timeout"""
        voice.stop()
        embed = discord.Embed(
            title=whole_question['tossups'][0]['set']['name'],
            description=question,
            color=0x00FF00
        )
        embed.add_field(name='Answer', value=whole_question['tossups'][0]['answer_sanitized'])
        await channel.send(embed=embed)
        await channel.send("Ran out of time")
        await channel.send("Y to continue, N to stop")
        buzz_queue.clear()

    async def end_game(self, channel, voice, player_list, audio_list):
        """End the game normally"""
        await channel.send("Finished")
        await self.show_scores(channel, player_list)
        
        voice.stop()
        voice.play(FFmpegPCMAudio('silence.mp3'))
        await self.bot.client.voice_clients[0].disconnect()
        await self.remove_audio(audio_list)
        
        if channel.id in self.bot.active_channels:
            del self.bot.active_channels[channel.id]

    async def timeout_end_game(self, channel, voice, player_list, audio_list):
        """End the game due to timeout"""
        await channel.send("Session Ending")
        await self.show_scores(channel, player_list)
        
        voice.play(FFmpegPCMAudio('silence.mp3'))
        await self.bot.client.voice_clients[0].disconnect()
        await self.remove_audio(audio_list)
        
        if channel.id in self.bot.active_channels:
            del self.bot.active_channels[channel.id]
