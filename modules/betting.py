import asyncio
from os.path import exists
import discord
from discord.ext import commands

from modules.wallet import InsufficientFundsError, NoWalletError

from .errors import InvalidCommandUsage
from .embed import COLOUR

WALLET_FILE = "wallets.txt"

class InvalidBet(Exception):
    def __init__(self, msg) -> None:
        self.msg = msg

class Bet:
    def __init__(self, player, player_name, outcome, amount) -> None:
        self.outcome = outcome
        self.amount = amount
        self.player = player
        self.player_name = player_name

class BettingRoom:
    def __init__(self, title, outcomes, author, author_name) -> None:
        self.outcomes = outcomes
        self.title = title
        self.bets = []
        self.author = author
        self.author_name = author_name
    
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
        return list(filter(lambda b: b.outcome == outcome, self.bets))

class BettingModule(commands.Cog):
    def __init__(self, bot, wallet) -> None:
        self.bot = bot
        self.wallet = wallet
        super().__init__()
        self.curr_bets = {}
    
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
        player = ctx.author.id
        player_name = ctx.author.name
        if channel_id not in self.curr_bets:
            # <msg> - <op> or <op>
            try:
                [title, opts] = msg.split(" - ")
                opts = opts.split(" or ")
            except:
                raise InvalidCommandUsage("New bet command must be in form `<outcome> - <op> or <op>`")
            
            self.curr_bets[channel_id] = BettingRoom(title, opts, player, player_name)
            embed = discord.Embed(title="A new betting room is open!", color=COLOUR)
            embed.set_footer(text="Type `$bet <outcome> <amount>` to place a bet")
            await ctx.send(embed=embed)
        else:
            # bet on existing bet
            # <outcome> <amount>
            try:
                [outcome, str_amt] = msg.split(" ")
            except:
                raise InvalidCommandUsage("Bet command must be in form `<outcome> <amount>`")

            try:
                amt = int(str_amt)     
            except:
                raise InvalidCommandUsage("Bet amount required and must be integer")

            try:
                bet = Bet(player, player_name, outcome, amt)
                self.wallet.withdraw(player, amt)
                self.curr_bets[channel_id].add_bet(bet)
                embed = discord.Embed(title=f"Bet placed by {player_name}: {bet.outcome} for {bet.amount}", color=COLOUR)
                await ctx.send(embed=embed)
            except InvalidBet as e:
                embed = discord.Embed(title=f"Invalid bet: {e}", color=COLOUR)
                await ctx.send(embed=embed)
                return
            except NoWalletError:
                embed = discord.Embed(title=f"Cannot place bet: {player_name} does not have a Chimp-wallet yet!", color=COLOUR)
                embed.set_footer(text="Type `$new-chimp-wallet` to get a wallet with some welcome Chimp-coins")
                await ctx.send(embed=embed)
                return
            except InsufficientFundsError:
                embed = discord.Embed(title=f"Cannot accept bet from {player_name} - you do not have that much Chimp-coin", color=COLOUR)
                embed.set_footer(text="Type `$wallet-balance` to see how much you have")
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
        author = ctx.author.id
        channel_id = ctx.channel.id
        if channel_id not in self.curr_bets:
            raise InvalidCommandUsage("A betting room must be open to declare a winner")
        
        room = self.curr_bets[channel_id]
        if room.author != author:
            raise InvalidCommandUsage(f"Only the room creator {room.author_name} can declare a winner")
        
        winning_outcome = msg
        if msg not in room.outcomes:
            try:
                idx = int(msg)
                winning_outcome = room.outcomes[idx - 1]
            except:
                raise InvalidCommandUsage("Winning outcome must be one of the possible outcomes")
        
        total_bets = len(room.bets)
        winners = room.winners(winning_outcome)
        total_winners = len(winners)
        ratio = 1
        if total_bets != 0:
            ratio -= total_winners / total_bets
        
        winners_list = ""
        for win in winners:
            amt = win.amount + win.amount * ratio
            amt = int(round(amt))
            self.wallet.deposit(win.player, amt)
            winners_list += f"• {win.player_name} ({amt})\n"
        
        embed = discord.Embed(title=f"{winning_outcome} wins!")
        embed.add_field(name="Winners", value=winners_list)

        del self.curr_bets[channel_id]
        await ctx.send(embed=embed)
    
    @bet.after_invoke
    @bet_winner.after_invoke
    async def persist_wallets(self, ctx):
        await self.wallet.persist()