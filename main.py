"""
main.py – Bot entrypoint.

Wires together:
  • Firebase / Firestore client
  • Slash commands  (/kill, /list)
  • Background alert loop
"""
import asyncio
import logging
import sys

import discord
from discord import app_commands

from config import Config
from database.firestore import init_firebase
from commands.kill import register_kill_command
from commands.list import register_list_command
from services.alert_service import create_alert_loop

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Bot setup ─────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready() -> None:
    logger.info("Logged in as %s (ID: %s)", client.user, client.user.id)

    # ── 1. Initialise Firestore ───────────────────────────────────────────
    db = init_firebase()

    # ── 2. Register slash commands ────────────────────────────────────────
    register_kill_command(tree, db)
    register_list_command(tree, db)

    # ── 3. Sync command tree ──────────────────────────────────────────────
    if Config.GUILD_ID:
        guild = discord.Object(id=Config.GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        logger.info("Commands synced to guild %s (instant)", Config.GUILD_ID)
    else:
        await tree.sync()
        logger.info("Commands synced globally (may take up to 1 hour)")

    # ── 4. Start background alert loop ───────────────────────────────────
    alert_loop = create_alert_loop(client, db)
    alert_loop.start()
    logger.info(
        "Alert loop started (interval: %ds, thresholds: %s min)",
        Config.ALERT_LOOP_INTERVAL,
        Config.ALERT_THRESHOLDS,
    )


@client.event
async def on_error(event: str, *args, **kwargs) -> None:
    logger.exception("Unhandled error in event '%s'", event)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client.run(Config.DISCORD_TOKEN, log_handler=None)
