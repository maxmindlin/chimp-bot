import asyncio
from os.path import exists
import discord
from discord.ext import commands

from modules.errors import InvalidCommandUsage

from .embed import COLOUR

WALLET_FILE = "wallets.txt"

class InvalidBet(Exception):
    def __init__(self, msg) -> None:
        self.msg = msg

class Bet:
    def __init__(self, player,  outcome, amount) -> None:
        self.outcome = outcome
        self.amount = amount
        self.player = player

class BettingRoom:
    def __init__(self, title, outcomes, author) -> None:
        self.outcomes = outcomes
        self.title = title
        self.bets = []
        self.author = author
    
    def add_bet(self, bet):
        if bet.amount <= 0:
            raise InvalidBet("bet must be greater than 0")

        for b in self.bets:
            if bet.player == b.player:
                raise InvalidBet(f"{bet.player} has already placed a bet!")

        if bet.outcome not in self.outcomes:
            try:
                idx = int(bet.outcome)
                outcome = self.outcomes[idx - 1] # humans arent 0-indexed
                bet.outcome = outcome
            except:
                raise InvalidBet("bet must be an outcome or an index of an outcome")
        
        self.bets.append(bet)
    
    def winners(self, outcome):
        return filter(lambda b: b.outcome == outcome, self.bets)

class BettingModule(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        super().__init__()
        self.curr_bets = {}
        self.wallets = self.load_wallets()
        self.wallet_lock = asyncio.Lock()
    
    @staticmethod
    def load_wallets():
        if exists(WALLET_FILE):
            with open(WALLET_FILE) as f:
                entries = f.read().splitlines()
                out = {}
                for entry in entries:
                    [player, bal] = entry.split("=")
                    out[player] = int(bal)
                return out
        else:
            return {}
    
    @commands.command(name="bet")
    async def bet(self, ctx, *, msg):
        channel_id = ctx.channel.id
        if channel_id not in self.curr_bets:
            # <msg> - <op> or <op>
            try:
                [title, opts] = msg.split(" - ")
                [op1, op2] = opts.split(" or ")
            except:
                raise InvalidCommandUsage("New bet command must be in form `<msg> - <op> or <op>`")
            
            self.curr_bets[channel_id] = BettingRoom(title, [op1, op2], ctx.author.name)
            embed = discord.Embed(title="A new betting room is open!", color=COLOUR)
            embed.set_footer(text="Type `$bet <outcome> <amount>` to place a bet")
            await ctx.send(embed=embed)
        else:
            # bet on existing bet
            # <bet> <amount>
            try:
                [bet, str_amt] = msg.split(" ")
            except:
                raise InvalidCommandUsage("Bet command must be in form `<bet> <amount>`")

            try:
                amt = int(str_amt)     
            except:
                raise InvalidCommandUsage("Bet amount required and must be integer")

            player = ctx.author.name
            if player not in self.wallets:
                embed = discord.Embed(title=f"Cannot place bet: {player} does not have a Chimp-wallet yet!", color=COLOUR)
                embed.set_footer(text="Type `$new-chimp-wallet` to get a wallet with some welcome Chimp-coins")
                await ctx.send(embed=embed)
                return
            
            if amt > self.wallets[player]:
                embed = discord.Embed(title=f"Cannot accept bet from {player} - you do not have that much Chimp-coin", color=COLOUR)
                embed.set_footer(text="Type `$wallet-balance` to see how much you have")
                await ctx.send(embed=embed)
                return

            try:
                placed = Bet(player, bet, amt)
                self.curr_bets[channel_id].add_bet(placed)
                self.wallets[player] -= amt
                embed = discord.Embed(title=f"Bet placed by {placed.player}: {placed.outcome} for {placed.amount}", color=COLOUR)
                await ctx.send(embed=embed)
            except InvalidBet as e:
                embed = discord.Embed(title=f"Invalid bet: {e}", color=COLOUR)
                await ctx.send(embed=embed)
                return
            except Exception as e:
                embed = discord.Embed(title="Unexpected error taking bet", color=COLOUR)
                print(f"Error processing bet: {e}")
                await ctx.send(embed=embed)
                return
    
    @commands.command(name="bet-running")
    async def bet_running(self, ctx):
        channel_id = ctx.channel.id
        if channel_id not in self.curr_bets:
            embed = discord.Embed(title="No betting room is currently running", color=COLOUR)
            embed.set_footer(text="Type `$bet <msg> - <op> or <op>` to start a new bet")
            await ctx.send(embed=embed)
        else:
            curr = self.curr_bets[channel_id].title
            ops = self.curr_bets[channel_id].outcomes
            embed = discord.Embed(title=f"Current bet: {curr}", color=COLOUR)
            embed.set_footer(text=f"Bet options: {ops}")
            await ctx.send(embed=embed)
    
    @commands.command(name="bet-winner")
    async def bet_winner(self, ctx, *, msg):
        author = ctx.author.name
        channel_id = ctx.channel.id
        if channel_id not in self.curr_bets:
            raise InvalidCommandUsage("A betting room must be open to declare a winner")
        
        room = self.curr_bets[channel_id]
        if room.author != author:
            raise InvalidCommandUsage(f"Only the room creator {room.author} can declare a winner")
    
    @commands.command(name="new-chimp-wallet")
    async def new_chimp_wallet(self, ctx):
        player = ctx.author.name
        if player in self.wallets:
            raise InvalidCommandUsage(f"{player} already has a chimp-wallet!")
        
        self.wallets[player] = 500
        embed = discord.Embed(title=f"Welcome {player} to Chimp-betting!", color=COLOUR)
        embed.set_footer(text="Heres 500 Chimp-coins to get you started")
        await ctx.send(embed=embed)

    @commands.command(name="balance")
    async def wallet_balance(self, ctx):
        player = ctx.author.name
        if player not in self.wallets:
            embed = discord.Embed(title=f"{player} you dont have a Chimp-wallet yet!", color=COLOUR)
            embed.set_footer(text="Type `$new-chimp-wallet` to get a wallet with some welcome Chimp-coins")
            await ctx.send(embed=embed)
            return
        
        balance = self.wallets[player]
        embed = discord.Embed(title=f"{player} you have a balance of {balance} Chimp-coins", color=COLOUR)
        await ctx.send(embed=embed)
    
    @bet.after_invoke
    @bet_winner.after_invoke
    async def persist_wallets(self, ctx):
        await self.wallet_lock.acquire()
        f = open("wallets.txt", "w")
        out = ""
        for player, balance in self.wallets.items():
            out += f"{player}={balance}\n"
        f.write(out)
        f.close()
        self.wallet_lock.release()