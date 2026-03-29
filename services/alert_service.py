"""
alert_service.py – Background loop that sends respawn-warning messages.

Design:
  • Runs every ALERT_LOOP_INTERVAL seconds via discord.py tasks.loop.
  • Tracks which (boss_id, threshold) pairs have already been alerted to avoid
    spam.  The state resets after the boss has spawned (remain <= 0) so the
    next kill cycle gets fresh alerts.
  • alert_state dict key:  (boss_id, threshold_minutes)
    value:  True  – alert was sent for this cycle
            absent – not yet sent
"""
import logging
from typing import Optional

import discord
from discord.ext import tasks
from google.cloud.firestore_v1.async_client import AsyncClient

import database.firestore as db_layer
from config import Config
from services import boss_service
from services.time_service import calc_next_spawn, calc_remain

logger = logging.getLogger(__name__)

# ── In-memory alert state ─────────────────────────────────────────────────────
# {(boss_id, threshold_minutes): True}
alert_state: dict[tuple[str, int], bool] = {}


# ── Alert loop ────────────────────────────────────────────────────────────────

def create_alert_loop(bot: discord.Client, db: AsyncClient):
    """
    Factory that returns a tasks.Loop bound to *bot* and *db*.
    Call `.start()` on the returned loop inside `on_ready`.
    """

    @tasks.loop(seconds=Config.ALERT_LOOP_INTERVAL)
    async def alert_loop() -> None:
        channel = _get_alert_channel(bot)
        if channel is None:
            logger.warning(
                "Alert channel %s not found or bot lacks access.",
                Config.ALERT_CHANNEL_ID,
            )
            return

        bosses = await boss_service.get_bosses_cached(db)
        kill_records = await db_layer.get_all_kill_records(db)

        for boss in bosses:
            record = kill_records.get(boss.id)
            if record is None:
                continue  # no kill recorded yet – skip

            next_spawn = calc_next_spawn(record.last_kill_time, boss.cycle_minutes)
            remain = calc_remain(next_spawn)
            remain_minutes = remain.total_seconds() / 60

            # If the boss has already spawned, clear previous alert state so
            # the next kill cycle can trigger fresh alerts.
            if remain_minutes <= 0:
                _clear_alerts_for_boss(boss.id)
                continue

            # Check each threshold in descending order so we don't fire a
            # 5-minute alert before the 10-minute alert.
            for threshold in sorted(Config.ALERT_THRESHOLDS, reverse=True):
                key = (boss.id, threshold)
                if remain_minutes <= threshold and not alert_state.get(key):
                    await _send_alert(channel, boss.name, threshold)
                    alert_state[key] = True

    @alert_loop.before_loop
    async def before_alert_loop() -> None:
        await bot.wait_until_ready()
        logger.info("Alert loop ready.")

    return alert_loop


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_alert_channel(bot: discord.Client) -> Optional[discord.TextChannel]:
    channel = bot.get_channel(Config.ALERT_CHANNEL_ID)
    if isinstance(channel, discord.TextChannel):
        return channel
    return None


def _clear_alerts_for_boss(boss_id: str) -> None:
    """Remove all alert-state entries for a given boss."""
    keys_to_delete = [k for k in alert_state if k[0] == boss_id]
    for k in keys_to_delete:
        del alert_state[k]


async def _send_alert(
    channel: discord.TextChannel, boss_name: str, threshold: int
) -> None:
    embed = discord.Embed(
        title="⚠️  Respawn Alert!",
        color=discord.Color.orange(),
    )
    embed.add_field(name="Boss", value=boss_name, inline=False)
    embed.add_field(
        name="Spawns in", value=f"**{threshold} minutes!**", inline=False
    )
    try:
        await channel.send(embed=embed)
        logger.info("Alert sent: boss=%s threshold=%dm", boss_name, threshold)
    except discord.DiscordException as exc:
        logger.error(
            "Failed to send alert for %s (%dm): %s", boss_name, threshold, exc
        )
