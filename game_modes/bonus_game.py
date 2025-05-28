import asyncio
import discord
from models.player import Player
from helpers import get_bonus, check
from config import COLORS

class BonusGame:
    """Manages bonus quiz sessions."""
    
    def __init__(self, client, channel, categories, difficulties, player):
        self.client = client
        self.channel = channel
        self.categories = categories
        self.difficulties = difficulties
        self.player = player
        self.user_score = Player(player.name, player.id)
    
    async def start_game(self):
        """Start the bonus game session."""
        bonus_count = 0
        
        while True:
            bonus_data = get_bonus(self.categories, self.difficulties)['bonuses'][0]
            lead_in = bonus_data['leadin_sanitized']
            
            lead_in_embed = discord.Embed(
                title=bonus_data["set"]["name"],
                description=lead_in,
                color=COLORS['GREEN']
            )
            lead_in_embed.set_author(name=f"For {self.player.name}")
            await self.channel.send(embed=lead_in_embed)
            
            # Handle three bonus parts
            for part_num in range(3):
                bonus_part = bonus_data['parts_sanitized'][part_num]
                answer_part = bonus_data['answers_sanitized'][part_num]
                
                bonus_embed = discord.Embed(
                    title=f"Part {part_num + 1}",
                    description=bonus_part,
                    color=COLORS['BLUE']
                )
                await self.channel.send(embed=bonus_embed)
                
                answer_result = await self._get_bonus_answer(answer_part)
                
                if answer_result == 'accept':
                    correct_embed = discord.Embed(
                        title="Correct",
                        description=answer_part,
                        color=COLORS['BLUE']
                    )
                    correct_embed.set_author(name=self.player.name)
                    await self.channel.send(embed=correct_embed)
                    self.user_score.increase_points()
                
                elif answer_result == 'reject':
                    await self._handle_self_evaluation(answer_part)
                
                elif answer_result in ['end', 'skip']:
                    if answer_result == 'end':
                        await self._show_bonus_stats(bonus_count)
                        return
                    break  # Skip to next bonus
            
            bonus_count += 1
    
    async def _get_bonus_answer(self, correct_answer: str):
        """Get and evaluate a bonus answer."""
        try:
            answer_msg = await self.client.wait_for('message', timeout=3600)
            
            if answer_msg.author != self.player or answer_msg.channel != self.channel:
                return await self._get_bonus_answer(correct_answer)
            
            if answer_msg.content.startswith('_'):
                return await self._get_bonus_answer(correct_answer)
            
            if answer_msg.content == '=end':
                return 'end'
            
            if answer_msg.content == '=skip':
                return 'skip'
            
            result = check(correct_answer, answer_msg.content)
            
            if result['directive'] in ['accept', 'prompt']:
                return 'accept'
            else:
                return 'reject'
                
        except asyncio.TimeoutError:
            await self._show_bonus_stats(0)
            return 'end'
    
    async def _handle_self_evaluation(self, answer_part: str):
        """Handle self-evaluation for incorrect answers."""
        incorrect_embed = discord.Embed(
            title="Were you correct? [y/n]",
            description=answer_part,
            color=COLORS['RED']
        )
        incorrect_embed.set_author(name=self.player.name)
        await self.channel.send(embed=incorrect_embed)
        
        try:
            eval_msg = await self.client.wait_for('message', timeout=3600)
            
            if eval_msg.channel != self.channel or self.player != eval_msg.author:
                return await self._handle_self_evaluation(answer_part)
            
            if eval_msg.content.lower() == 'y':
                self.user_score.increase_points()
                
        except asyncio.TimeoutError:
            pass
    
    async def _show_bonus_stats(self, bonus_count: int):
        """Display final bonus statistics."""
        categories_display = ', '.join(self.categories) if self.categories else "All"
        difficulties_display = ', '.join(self.difficulties) if self.difficulties else "All"
        
        ppb = "N/A" if bonus_count == 0 else self.user_score.get_points() / bonus_count
        
        stats_embed = discord.Embed(
            title="Stats",
            description=f"requested by {self.player.name}",
            color=COLORS['RED']
        )
        stats_embed.add_field(name="Categories", value=categories_display)
        stats_embed.add_field(name="Difficulties", value=difficulties_display)
        stats_embed.add_field(name="Bonuses", value=bonus_count)
        stats_embed.add_field(name="Points", value=self.user_score.get_points())
        stats_embed.add_field(name="PPB", value=ppb)
        
        await self.channel.send(embed=stats_embed)
