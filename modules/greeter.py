from discord.ext import commands

class GreeterModule(commands.Cog, name ="Greeter module"):
    def __init__(self, bot) -> None:
        super().__init__()
        self.bot = bot
    
    @commands.command(name="hey")
    async def adhoc_play(self, ctx):
        await ctx.send(f"Hey {ctx.author.name}")