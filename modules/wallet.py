import asyncio
import discord
from os.path import exists
from discord.ext import commands

from modules.errors import InvalidCommandUsage

from .embed import COLOUR

WALLET_FILE = "wallets.txt"

class WalletTransactionError(Exception):
    def __init__(self, msg):
        self.msg = msg
    
    def __repr__(self) -> str:
        return f"Error in wallet transaction: {self.msg}"

class InsufficientFundsError(Exception):
    def __repr__(self) -> str:
        return "Player has insufficient funds for that transaction"

class NoWalletError(Exception):
    def __repr__(self) -> str:
        return "Player has no wallet"

class WalletManager():
    """
    Manages the balances for all players.

    TODO: there might be some async conflicts here.
    Make sure the lock is used properly if these appear.
    """
    def __init__(self):
        self.balances = self.load_balances()
        self.lock = asyncio.Lock()

    def balance(self, player):
        if player in self.balances:
            return self.balances[player]
        else:
            return None

    def withdraw(self, player, amt):
        if player not in self.balances:
            raise NoWalletError()
        
        if self.balances[player] < amt:  
            raise InsufficientFundsError()
        
        self.balances[player] -= amt
    
    def deposit(self, player, amt):
        if player not in self.balances:
            raise NoWalletError()
        
        self.balances[player] += amt
    
    def new_wallet(self, player):
        self.balances[player] = 0

    @staticmethod
    def load_balances():
        if exists(WALLET_FILE):
            with open(WALLET_FILE) as f:
                entries = f.read().splitlines()
                out = {}
                for entry in entries:
                    [player, bal] = entry.split("=")
                    out[int(player)] = int(bal)
                return out
        else:
            return {}
    
    async def persist(self, *args, **kwargs):
        await self.lock.acquire()
        with open(WALLET_FILE, "w") as f:
            out = ""
            for player, bal in self.balances.items():
                out += f"{player}={bal}\n"
            f.write(out)
        self.lock.release()

class WalletModule(commands.Cog):
    """
    Module for handling commands related to player wallets,
    such as spending and checking balances.
    """
    def __init__(self, bot, wallet):
        self.bot = bot
        super().__init__()
        self.wallet = wallet
    
    @commands.command(name="balance")
    async def balance(self, ctx):
        player = ctx.author.id
        name = ctx.author.name
        balance = self.wallet.balance(player)
        if balance is None:
            embed = discord.Embed(title=f"{name} you dont have a Chimp-wallet yet!", color=COLOUR)
            embed.set_footer(text="Type `$new-wallet` to get a wallet with some welcome Chimp-coins")
            await ctx.send(embed=embed)
            return
        
        dm = self.bot.get_user(player) or await self.bot.fetch_user(player)
        embed = discord.Embed(title=f"{name} you have a balance of {balance} Chimp-coins", color=COLOUR)
        await dm.send(embed=embed)
    
    @commands.command(name="new-wallet")
    async def new_wallet(self, ctx):
        player = ctx.author.id
        name = ctx.author.name
        if self.wallet.balance(player) is not None:
            raise InvalidCommandUsage(f"{name} already has a Chimp-wallet!")
        
        self.wallet.new_wallet(player)
        self.wallet.deposit(player, 500)
        embed = discord.Embed(title=f"Welcome {name} to Chimp-betting!", color=COLOUR)
        embed.set_footer(text="Heres 500 Chimp-coins to get you started")
        await ctx.send(embed=embed)
    
    @new_wallet.after_invoke
    async def persist_changes(self, ctx):
        await self.wallet.persist()