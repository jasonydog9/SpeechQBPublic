import asyncio
import discord
from discord.ext import commands
from config import TOKEN
from bot_client import QuizBot

def main():
    """Main entry point for the Discord bot."""
    intents = discord.Intents.all()
    bot = QuizBot(intents=intents)
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
