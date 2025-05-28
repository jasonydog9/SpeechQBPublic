import asyncio
import discord
from discord.ext import commands
from game_modes.text_mode import TextMode
from game_modes.voice_mode import VoiceMode
from game_modes.bonus_mode import BonusMode
from utils.player import Player
from utils.constants import CATEGORIES

class QuizBot:
    def __init__(self, token):
        self.token = token
        self.client = discord.Client(intents=discord.Intents.all())
        self.voice_clients = {}
        self.channels = {}
        self.questions = {}
        self.active_channels = {}
        self.player_lists = {}
        self.end_list = {}
        self.skip_list = {}
        self.clear_list = {}
        
        # Initialize game modes
        self.text_mode = TextMode(self)
        self.voice_mode = VoiceMode(self)
        self.bonus_mode = BonusMode(self)
        
        self.setup_events()
    
    def setup_events(self):
        @self.client.event
        async def on_ready():
            print(f'{self.client.user} is running')
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, 
                    name='=help'
                )
            )

        @self.client.event
        async def on_raw_reaction_add(payload):
            message_id = payload.message_id
            if message_id == 1163669112036282502:
                print('yes')
                guild_id = payload.guild_id
                guild = discord.utils.find(lambda g: g.id == guild_id, self.client.guilds)
                print(payload.emoji.name)
                role = discord.utils.get(guild.roles, id=1051732399723122760)
                member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
                if member is not None:
                    await member.remove_roles(role)

        @self.client.event
        async def on_message(message):
            await self.handle_message(message)

    async def handle_message(self, message):
        if message.author == self.client.user:
            return

        # Handle buzz inputs
        buzzes = ["buzz", "bz", "buz"]
        if message.content.lower() in buzzes and message.channel.id in self.active_channels:
            self.active_channels[message.channel.id].append(message.author)
            if not self.player_in_list(message.author.id, self.player_lists[message.channel.id]):
                self.player_lists[message.channel.id].append(
                    Player(message.author.name, message.author.id)
                )

        # Handle game control commands
        if message.content.lower() == "=skip" and message.channel.id in self.active_channels:
            self.skip_list[message.channel.id].append('skip')

        if message.content.lower() == "=end" and message.channel.id in self.active_channels:
            self.end_list[message.channel.id].append('end')

        if message.content.lower() == '=clear' and message.channel.id in self.active_channels:
            await self.clear_session(message.channel)

        # Handle game mode commands
        if message.content.startswith('=play'):
            await self.voice_mode.start_game(message)
        
        elif message.content.startswith('=ts'):
            await self.text_mode.start_game(message)
        
        elif message.content.startswith('=bonus'):
            await self.bonus_mode.start_game(message)
        
        elif message.content == '=help':
            await self.send_help(message.channel)
        
        # Easter eggs
        elif message.content == '-vikram':
            await self.send_vikram_embed(message.channel)
        elif message.content == '-jackie':
            await message.channel.send('Government Coup!!!!')
        elif message.content == '-akshath':
            await self.send_akshath_embed(message.channel)
        elif message.content == '-jason':
            await message.channel.send('where were you during the taiping rebellion')
        elif message.content == '-varma':
            await message.channel.send('I am adult medium 😠')

    def player_in_list(self, user_id, player_list):
        for player in player_list:
            if player.get_id() == user_id:
                return True
        return False

    async def clear_session(self, channel):
        self.clear_list[channel.id].append('clear')
        del self.active_channels[channel.id]
        del self.player_lists[channel.id]
        del self.skip_list[channel.id]
        del self.end_list[channel.id]
        del self.clear_list[channel.id]
        
        embed = discord.Embed(title="Session Cleared!", color=0x00FF00)
        await channel.send(embed=embed)

    def parse_categories_and_difficulties(self, content, command):
        """Parse categories and difficulties from command content"""
        cat_list = content.replace(',', '').split()
        cat_list.remove(command)
        
        diff_list = []
        new_cat_list = []
        
        for item in cat_list:
            if item.isdigit() and 0 < int(item) < 10:
                diff_list.append(item)
            elif item.isdigit():
                return None, None, "Enter a correct difficulty"
            else:
                new_cat_list.append(item)
        
        cat_list = new_cat_list
        
        # Convert abbreviations to full names
        for i, cat in enumerate(cat_list):
            if cat in CATEGORIES.values():
                for key, value in CATEGORIES.items():
                    if value == cat:
                        cat_list[i] = key
                        break
            elif cat not in CATEGORIES.keys():
                return None, None, "Enter Correct Categories"
        
        return cat_list, diff_list, None

    async def send_help(self, channel):
        embed = discord.Embed(title="SpeechQB Help", color=0x3776AB)
        embed.add_field(
            name="=ts",
            value="=ts [cats] [diffs]. i.e =ts geo 2, this is a text based version",
            inline=False
        )
        embed.add_field(
            name="=play",
            value="=play [cats] [diffs]. i.e -play geo 2 (must be in voice channel), this mode will use AI reader in voice channel to read you questions",
            inline=False
        )
        embed.add_field(
            name="How to buzz in",
            value="To buzz in an answer type bz or buzz then type your answer within 20 seconds",
            inline=False
        )
        embed.add_field(
            name="How to Withdraw",
            value="To withdraw after buzzing type wd within 20 seconds",
            inline=False
        )
        embed.add_field(name="=skip or =next", value="skips current question", inline=False)
        embed.add_field(
            name="=end",
            value="Once in the game and you wish to end, type =end",
            inline=False
        )
        embed.add_field(
            name='=bonus',
            value="type =bonus [cats] [diffs] to play bonuses",
            inline=False
        )
        embed.add_field(
            name="=score",
            value="Gives the scores of every person who has buzzed in",
            inline=False
        )
        embed.add_field(
            name="DM dogeking0 for any bugs",
            value="Version 0.4.0",
            inline=False
        )
        await channel.send(embed=embed)

    async def send_vikram_embed(self, channel):
        embed = discord.Embed(title="Veeekram", color=0x3776AB)
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/1029560549903700099/1166187556405252218/IMG_2491.jpg?ex=654993cc&is=65371ecc&hm=9b3f28fb13d33c5f52af344a0ab980c3684843f8207d477fa61d3eef5e4895f2&'
        )
        await channel.send(embed=embed)

    async def send_akshath_embed(self, channel):
        embed = discord.Embed(title="dyuude", color=0x3776AB)
        embed.set_image(
            url='https://cdn.discordapp.com/attachments/1029560549903700099/1170171115574923264/image.png?ex=655811c6&is=65459cc6&hm=71eb7cbfc3f11a2a1e3b55a241ebe0d7f9e1aac891be95d5bb7550c36c6d76e2&'
        )
        await channel.send(embed=embed)

    def run(self):
        self.client.run(self.token)
