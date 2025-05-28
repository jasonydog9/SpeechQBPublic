import asyncio
import discord
from typing import List
from models.player import Player
from helpers import get_question, check
from config import COLORS
from utils.helpers import player_in_list

class TossupGame:
    """Manages text-based tossup quiz sessions."""
    
    def __init__(self, client, channel, categories: List[str], difficulties: List[str]):
        self.client = client
        self.channel = channel
        self.categories = categories
        self.difficulties = difficulties
        self.player_list = []
        self.buzz_queue = []
        self.skip_list = []
        self.end_list = []
        self.clear_list = []
    
    async def start_game(self):
        """Start the tossup game session."""
        question_finished = False
        question_count = 1
        
        while True:
            time_remaining = 20
            new_question = get_question(self.categories, self.difficulties)
            question_text = new_question['tossups'][0]['question_sanitized']
            
            embed = discord.Embed(
                title=f'Tossup {question_count} - {new_question["tossups"][0]["set"]["name"]}',
                description="",
                color=COLORS['BLUE']
            )
            msg = await self.channel.send(embed=embed)
            
            words = question_text.split()
            displayed_text = ""
            
            await asyncio.sleep(0.7)
            
            while not question_finished:
                if len(words) < 6:
                    for _ in range(len(words)):
                        displayed_text += words.pop(0) + " "
                else:
                    for _ in range(6):
                        displayed_text += words.pop(0) + " "
                
                new_embed = discord.Embed(
                    title=f'Tossup {question_count} - {new_question["tossups"][0]["set"]["name"]}',
                    description=displayed_text,
                    color=COLORS['BLUE']
                )
                
                if time_remaining < 0:
                    dead_embed = discord.Embed(
                        title="Tossup dead",
                        description=f'Answer: {new_question["tossups"][0]["answer_sanitized"]}',
                        color=COLORS['RED']
                    )
                    await self.channel.send(embed=dead_embed)
                    question_finished = True
                    break
                
                await msg.edit(embed=new_embed)
                
                # Handle buzzes and game control
                await self._handle_game_events(new_question, words, displayed_text, question_count)
                
                if question_finished:
                    break
                
                # Check for end conditions
                if self._should_end_game():
                    return
                
                time_remaining -= 0.8
            
            # Handle continuation
            if not await self._handle_continuation(question_count):
                return
            
            question_count += 1
            question_finished = False
    
    async def _handle_game_events(self, question_data, words, displayed_text, question_count):
        """Handle buzzes, skips, and other game events."""
        # Handle buzzes
        while self.buzz_queue:
            user = self.buzz_queue[0]
            answer = await self._get_tossup_answer(
                question_data['tossups'][0]['answer_sanitized'],
                user,
                words
            )
            
            if answer == 'accept':
                self._award_points(user, words)
                self.buzz_queue.clear()
                return True
            elif answer == 'reject':
                self._deduct_points(user, words)
                self.buzz_queue.pop(0)
            else:
                self.buzz_queue.pop(0)
        
        # Handle skip requests
        if self.skip_list:
            await self._handle_skip(question_data)
            return True
        
        return False
    
    async def _get_tossup_answer(self, correct_answer: str, user, words: List[str]):
        """Get and evaluate a player's answer."""
        answer_embed = discord.Embed(
            title='',
            description=f'Answer (or wd) {user.mention}',
            color=COLORS['BLUE']
        )
        await self.channel.send(embed=answer_embed)
        
        try:
            answer_msg = await self.client.wait_for('message', timeout=20.0)
            
            if answer_msg.author != user or answer_msg.channel != self.channel:
                return 'timeout'
            
            if answer_msg.content.lower() in ['wd', 'withdraw']:
                return 'withdraw'
            
            result = check(correct_answer, answer_msg.content)
            
            if result['directive'] == 'accept':
                points = 15 if "(*)" in words else 10
                embed = discord.Embed(
                    title=f'Correct. {points} points',
                    description=f'Answer: {correct_answer}',
                    color=COLORS['GREEN']
                )
                await self.channel.send(embed=embed)
                return 'accept'
            
            elif result['directive'] == 'reject':
                points = -5 if words else 0
                embed = discord.Embed(
                    title="Incorrect!",
                    description=f'{points} points for {user.mention}',
                    color=COLORS['RED']
                )
                await self.channel.send(embed=embed)
                return 'reject'
            
            elif result['directive'] == 'prompt':
                embed = discord.Embed(title="PROMPT", color=COLORS['BLUE'])
                await self.channel.send(embed=embed)
                return 'prompt'
                
        except asyncio.TimeoutError:
            return 'timeout'
    
    def _award_points(self, user, words: List[str]):
        """Award points to a player."""
        for player in self.player_list:
            if player.get_id() == user.id:
                if "(*)" in words:
                    player.power()
                else:
                    player.increase_points()
                break
    
    def _deduct_points(self, user, words: List[str]):
        """Deduct points from a player."""
        for player in self.player_list:
            if player.get_id() == user.id:
                if words:  # Only neg if there are words left
                    player.neg()
                break
    
    async def _handle_skip(self, question_data):
        """Handle skip request."""
        self.skip_list.clear()
        embed = discord.Embed(
            title='Tossup skipped.',
            description=f'Answer: {question_data["tossups"][0]["answer_sanitized"]}',
            color=COLORS['RED']
        )
        await self.channel.send(embed=embed)
    
    async def _handle_continuation(self, question_count) -> bool:
        """Handle game continuation prompt."""
        continue_embed = discord.Embed(
            title="Do you want to continue? Answer Y/N",
            color=COLORS['BLUE']
        )
        await self.channel.send(embed=continue_embed)
        
        try:
            response = await self.client.wait_for('message', timeout=180.0)
            
            if response.channel != self.channel:
                return await self._handle_continuation(question_count)
            
            if response.content.lower() == 'y':
                return True
            elif response.content.lower() == 'n':
                await self._show_final_scores(question_count)
                return False
                
        except asyncio.TimeoutError:
            await self._handle_timeout(question_count)
            return False
    
    async def _show_final_scores(self, question_count):
        """Display final scores."""
        categories_display = ', '.join(self.categories) if self.categories else 'All'
        difficulties_display = ', '.join(sorted(self.difficulties)) if self.difficulties else 'All Diffs'
        
        score_text = ""
        for player in self.player_list:
            score_text += f"{player.get_name()}: {player.get_points()} {player.to_string()}\n"
        
        scores_embed = discord.Embed(
            title=f"Scores ({question_count} TU read) - {categories_display}, {difficulties_display}",
            description=score_text,
            color=COLORS['BLUE']
        )
        await self.channel.send(embed=scores_embed)
    
    def _should_end_game(self) -> bool:
        """Check if the game should end."""
        return bool(self.end_list or self.clear_list)
    
    def add_player_if_new(self, user):
        """Add a new player if they haven't joined yet."""
        if not player_in_list(user.id, self.player_list):
            self.player_list.append(Player(user.name, user.id))
    
    async def _handle_timeout(self, question_count):
        """Handle session timeout."""
        timeout_embed = discord.Embed(title="Session timed-out!", color=COLORS['RED'])
        await self.channel.send(embed=timeout_embed)
        await self._show_final_scores(question_count)
