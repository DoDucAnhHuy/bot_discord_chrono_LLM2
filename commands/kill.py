"""
commands/kill.py – Slash command /kill với autocomplete tên boss.
"""
import logging
from typing import Any

import discord
from discord import app_commands

import database.firestore as db_layer
from models.kill import KillRecord
from services import boss_service
from services.time_service import (
    calc_next_spawn, calc_remain,
    format_datetime_ict, format_time_ict,
    format_remain, parse_kill_time,
)

logger = logging.getLogger(__name__)


def register_kill_command(tree: app_commands.CommandTree, db: Any) -> None:

    # ── Autocomplete callback ─────────────────────────────────────────────
    async def boss_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """
        Gợi ý tên boss khi người dùng gõ vào parameter boss.
        Lọc theo chuỗi đang gõ (case-insensitive), trả về tối đa 25 gợi ý.
        """
        bosses = await boss_service.get_bosses_cached(db)
        current_lower = current.lower()

        matches = [
            app_commands.Choice(name=boss.name, value=boss.name)
            for boss in bosses
            if current_lower in boss.name.lower()
        ]

        # Discord giới hạn tối đa 25 choices
        return matches[:25]

    # ── Slash command ─────────────────────────────────────────────────────
    @tree.command(name="kill", description="Ghi nhận thời gian kill boss.")
    @app_commands.describe(
        boss="Tên boss (gõ để tìm kiếm)",
        time='Thời gian kill theo UTC+7: "now" hoặc "HH:mm" (mặc định: now)',
    )
    @app_commands.autocomplete(boss=boss_autocomplete)
    async def kill(
        interaction: discord.Interaction,
        boss: str,
        time: str = "now",
    ) -> None:
        await interaction.response.defer()

        # 1. Tìm boss (vẫn giữ fuzzy search phòng trường hợp gõ tay)
        boss_obj = await boss_service.find_boss(db, boss)
        if boss_obj is None:
            await interaction.followup.send(embed=_error_embed(
                f"Boss `{boss}` không tìm thấy. Dùng `/list` để xem danh sách."
            ))
            return

        # 2. Parse thời gian
        try:
            kill_time_utc = parse_kill_time(time)
        except ValueError as exc:
            await interaction.followup.send(embed=_error_embed(str(exc)))
            return

        # 3. Lưu vào Firestore
        record = KillRecord(
            boss_id=boss_obj.id,
            last_kill_time=kill_time_utc,
            updated_by=str(interaction.user.id),
        )
        try:
            await db_layer.upsert_kill_record(db, record)
        except Exception:
            logger.exception("Firestore upsert failed for boss %s", boss_obj.id)
            await interaction.followup.send(embed=_error_embed(
                "Lỗi database — không thể lưu kill record."
            ))
            return

        # 4. Tính next spawn & remain
        next_spawn = calc_next_spawn(kill_time_utc, boss_obj.cycle_minutes)
        remain = calc_remain(next_spawn)

        # 5. Trả về embed
        embed = discord.Embed(
            title=f"⚔️  {boss_obj.name.upper()} KILLED",
            color=discord.Color.red(),
        )
        embed.add_field(name="Time Killed",  value=format_datetime_ict(kill_time_utc), inline=False)
        embed.add_field(name="Next Spawn",   value=format_time_ict(next_spawn),        inline=True)
        embed.add_field(name="Remain",       value=format_remain(remain),              inline=True)
        embed.set_footer(text=f"Recorded by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(title="❌  Error", description=message, color=discord.Color.red())