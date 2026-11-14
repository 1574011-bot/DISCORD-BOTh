# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   UND — All In One                                               ║
# ║                                                                  ║
# ║                                                                  ║
# ║   © 2026 KURAPIKA — All Rights Reserved                          ║
# ║   Built & owned by Kurapika                                      ║
# ╚══════════════════════════════════════════════════════════════════╝

"""Slash bridge: makes every text command reachable through `/cmd`.

Discord only allows 100 top-level slash commands per application, so the
text-only commands (and their subcommands) cannot all be registered as
top-level slash commands. `/cmd <name> <args>` resolves any command or
subcommand by name/alias and runs it exactly like a prefixed invocation
(same checks, converters, cooldowns and error handler).
"""

from discord import app_commands
from discord.ext import commands
from discord.ext.commands.view import StringView

PREFIX_CHARS = ("!", "/", ">", "?", ".")


class SlashBridge(commands.Cog):
    """Universal `/cmd` entry point for every UND command."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _normalize(raw: str) -> str:
        text = (raw or "").strip()
        while text and text[0] in PREFIX_CHARS:
            text = text[1:].lstrip()
        return text.lower()

    def resolve(self, raw: str):
        """Return the command matching a name, alias or qualified name."""
        wanted = self._normalize(raw)
        if not wanted:
            return None

        commands_list = list(self.bot.walk_commands())

        for command in commands_list:
            if command.qualified_name.lower() == wanted:
                return command

        for command in commands_list:
            if command.name.lower() == wanted:
                return command

        for command in commands_list:
            if wanted in {alias.lower() for alias in command.aliases}:
                return command

        return self.bot.get_command(wanted)

    async def name_autocomplete(self, interaction, current: str):
        wanted = self._normalize(current)
        choices = []
        seen = set()

        for command in self.bot.walk_commands():
            if command.hidden:
                continue
            qualified = command.qualified_name
            if qualified in seen:
                continue
            if wanted and wanted not in qualified.lower():
                continue
            seen.add(qualified)
            choices.append(app_commands.Choice(name=qualified[:100], value=qualified[:100]))
            if len(choices) >= 25:
                break

        return choices

    @app_commands.command(
        name="cmd",
        description="Run any UND command from slash — same as using the prefix (e.g. /cmd ban @user spam)",
    )
    @app_commands.describe(
        name="Command name — start typing to search every command",
        args="Arguments exactly like the prefixed version, e.g. @user 10m spamming",
    )
    @app_commands.autocomplete(name=name_autocomplete)
    async def cmd(self, interaction, name: str, args: str = ""):
        command = self.resolve(name)
        if command is None:
            await interaction.response.send_message(
                f"❌ No command named `{name}`. Start typing in the **name** field to search all commands "
                "(560 commands, subcommands and aliases included).",
                ephemeral=True,
            )
            return

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)

        ctx = await self.bot.get_context(interaction)
        if not ctx.prefix or ctx.prefix == "/":
            ctx.prefix = "!"
        ctx.command = command
        ctx.invoked_with = command.name
        ctx.view = StringView(args or "")

        try:
            await self.bot.invoke(ctx)
        except Exception as error:
            await interaction.followup.send(f"❌ {self._explain(error)}", ephemeral=True)

    @staticmethod
    def _explain(error: Exception) -> str:
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.CommandNotFound):
            return "This command does not exist anymore."
        if isinstance(error, commands.MissingRequiredArgument):
            return f"Missing argument `{error.param.name}`. Usage: `{error.param}` must be filled in the **args** field."
        if isinstance(error, commands.MissingPermissions):
            return "You need the following permissions: " + ", ".join(error.missing_permissions)
        if isinstance(error, commands.BotMissingPermissions):
            return "I need the following permissions: " + ", ".join(error.missing_permissions)
        if isinstance(error, commands.CheckFailure):
            return str(error) or "You cannot use this command here."
        if isinstance(error, commands.CommandOnCooldown):
            return f"On cooldown, try again in {error.retry_after:.1f}s."
        if isinstance(error, commands.BadArgument):
            return str(error)
        return f"{type(error).__name__}: {error}"


async def setup(bot):
    await bot.add_cog(SlashBridge(bot))
