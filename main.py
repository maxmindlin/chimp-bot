import dotenv
import discord
from discord.ext import commands

import os

from modules.greeter import GreeterModule
from modules.player import MusicModule
from modules.errors import CommandErrHandler
from modules.betting import Bet, BettingModule
from modules.wallet import WalletManager, WalletModule

class ChimpBotClient(commands.Bot):
    
    async def on_ready(self):
        print(f"{self.user.name} has connected!")

def main():
    dotenv.load_dotenv()

    token = os.getenv("DISCORD_TOKEN")

    intents = discord.Intents.default()
    intents.members = True

    bot = ChimpBotClient(command_prefix="$", intents=intents)
    wallet = WalletManager()
    bot.add_cog(GreeterModule(bot))
    bot.add_cog(MusicModule(bot, wallet))
    bot.add_cog(BettingModule(bot, wallet))
    bot.add_cog(CommandErrHandler(bot))
    bot.add_cog(WalletModule(bot, wallet))
    bot.run(token)

if __name__ == "__main__":
    main()