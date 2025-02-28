import discord
from discord import app_commands
from discord.ext import commands


class PingCommand(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping",
                          description="Check if the bot is online")
    @app_commands.checks.cooldown(1, 1.0)  # 1 use every second
    async def ping(self, interaction: discord.Interaction):
        """Sends a ping response with bot latency."""
        try:
            if not hasattr(interaction, 'response'):
                return

            await interaction.response.defer(ephemeral=True)
            latency = round(self.bot.latency * 1000)  # Convert to ms
            status = "🟢" if latency < 1000 else "🟡" if latency < 3000 else "🔴"

            await interaction.followup.send(
                f"{status} Pong! Bot latency: `{latency}ms`")
            print(
                f"🏓 Ping command used by {interaction.user} (ID: {interaction.user.id}) - Latency: {latency}ms"
            )
        except Exception as e:
            print(f"Error in ping command: {e}")
            await interaction.followup.send(
                "An error occurred while processing the command.",
                ephemeral=True)


async def setup(bot):
    await bot.add_cog(PingCommand(bot))
