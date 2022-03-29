import dotenv
import discord
from discord.ext import commands
from discord.utils import find

import os
from modules.embed import COLOUR

from modules.player import MusicModule
from modules.errors import CommandErrHandler
from modules.betting import BettingModule
from modules.wallet import WalletManager, WalletModule

CHIMP_GREETING_TITLE = "Chimp-bot - for being a general ape."

CHIMP_GREETING_BODY = """
Chimpiticus 4:32.
    So an ape created Chimp-bot in his own image,
    in the image of Cakeybot he created it;
    chimp and bot he created it.
Popular commands to get started:
    - `$play <song>` to stream a song to your voice channel.
    - `$p-play <song>` to spend Chimp-coin and bypass the song queue.
    - `$bet <premise> - <outcome> or <outcome>` to start a betting room (Ex: `$bet He is going to feed - yes or no`).
"""

class ChimpBotClient(commands.Bot):
    
    async def on_ready(self):
        print(f"{self.user.name} has connected!")
    
    async def on_guild_join(self, guild):
        general = find(lambda x: x.name == "general", guild.text_channels)
        if general and general.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title=CHIMP_GREETING_TITLE,
                description=CHIMP_GREETING_BODY,
                color=COLOUR)
            await general.send(embed=embed)
    
def main():
    dotenv.load_dotenv()

    token = os.getenv("DISCORD_TOKEN")

    intents = discord.Intents.default()
    intents.members = True

    bot = ChimpBotClient(command_prefix="$", intents=intents)
    wallet = WalletManager()
    bot.add_cog(MusicModule(bot, wallet))
    bot.add_cog(BettingModule(bot, wallet))
    bot.add_cog(CommandErrHandler(bot))
    bot.add_cog(WalletModule(bot, wallet))
    bot.run(token)

if __name__ == "__main__":
    main()