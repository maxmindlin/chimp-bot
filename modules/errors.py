import discord
import sys
import traceback
from discord.ext import commands

from modules.embed import COLOUR

class InvalidCommandUsage(Exception):
    def __init__(self, usage):
        self.usage = usage

class CommandErrHandler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('I do not know that command?!')
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, InvalidCommandUsage):
            embed = discord.Embed(title=f"Invalid command usage: {error.original.usage}", colour=COLOUR)
            await ctx.send(embed=embed)
        else:
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)