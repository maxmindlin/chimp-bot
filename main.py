import dotenv
import discord
from discord.ext import commands

import os

from modules.greeter import GreeterModule
from modules.player import MusicModule
from modules.errors import CommandErrHandler

class ChimpBotClient(commands.Bot):
    
    async def on_ready(self):
        print(f"{self.user.name} has connected!")

def main():
    dotenv.load_dotenv()

    token = os.getenv("DISCORD_TOKEN")

    intents = discord.Intents.default()
    intents.members = True

    bot = ChimpBotClient(command_prefix="$", intents=intents)
    bot.add_cog(GreeterModule(bot))
    bot.add_cog(MusicModule(bot))
    bot.add_cog(CommandErrHandler(bot))
    bot.run(token)

if __name__ == "__main__":
    main()