"""
commands/list.py – Slash command /list

Displays all bosses with:
  • Cycle time
  • Remain until next spawn (realtime calculation)
  • Next spawn time (UTC+7)

Paginated 10 rows per page with Prev / Next buttons.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands
from google.cloud.firestore_v1.async_client import AsyncClient

import database.firestore as db_layer
from services import boss_service
from services.time_service import (
    calc_next_spawn,
    calc_remain,
    format_remain,
    format_time_ict,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


# ── Row data ──────────────────────────────────────────────────────────────────

@dataclass
class BossRow:
    name: str
    cycle_label: str   # e.g. "3h30m"
    remain_label: str  # e.g. "7h14m"  or "Unknown"
    next_spawn_label: str  # e.g. "01:18" or "Unknown"
    remain_seconds: float  # for sorting; float('inf') when unknown


# ── Command registration ──────────────────────────────────────────────────────

def register_list_command(tree: app_commands.CommandTree, db: AsyncClient) -> None:
    """Register the /list slash command onto *tree*."""

    @tree.command(name="list", description="Show all boss respawn timers.")
    async def list_bosses(interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        rows = await _build_rows(db)

        if not rows:
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Boss List",
                    description="No boss data found. Add bosses to the `dimboss` collection.",
                    color=discord.Color.blue(),
                )
            )
            return

        view = PaginationView(rows)
        embed = view.build_embed()
        await interaction.followup.send(embed=embed, view=view)


# ── Build sorted rows ─────────────────────────────────────────────────────────

async def _build_rows(db: AsyncClient) -> list[BossRow]:
    bosses = await boss_service.get_bosses_cached(db)
    kill_records = await db_layer.get_all_kill_records(db)

    rows: list[BossRow] = []
    for boss in bosses:
        record = kill_records.get(boss.id)

        # Format cycle (reuse format_remain logic on a timedelta)
        from datetime import timedelta
        cycle_td = timedelta(minutes=boss.cycle_minutes)
        cycle_label = _format_cycle(boss.cycle_minutes)

        if record is None:
            rows.append(
                BossRow(
                    name=boss.name,
                    cycle_label=cycle_label,
                    remain_label="Unknown",
                    next_spawn_label="Unknown",
                    remain_seconds=float("inf"),
                )
            )
            continue

        next_spawn = calc_next_spawn(record.last_kill_time, boss.cycle_minutes)
        remain = calc_remain(next_spawn)
        remain_secs = remain.total_seconds()

        rows.append(
            BossRow(
                name=boss.name,
                cycle_label=cycle_label,
                remain_label=format_remain(remain),
                next_spawn_label=format_time_ict(next_spawn),
                remain_seconds=remain_secs,
            )
        )

    # Sort: spawned bosses (negative remain) last, unknown last of all
    def sort_key(r: BossRow) -> float:
        if r.remain_seconds == float("inf"):
            return float("inf")
        if r.remain_seconds <= 0:
            return float("inf") - 1  # just before unknown
        return r.remain_seconds

    rows.sort(key=sort_key)
    return rows


def _format_cycle(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h > 0 and m > 0:
        return f"{h}h{m:02d}m"
    if h > 0:
        return f"{h}h"
    return f"{m}m"


# ── Pagination view ───────────────────────────────────────────────────────────

class PaginationView(discord.ui.View):
    def __init__(self, rows: list[BossRow]):
        super().__init__(timeout=120)  # buttons expire after 2 minutes
        self.rows = rows
        self.page = 0
        self.max_page = max(0, (len(rows) - 1) // PAGE_SIZE)
        self._update_buttons()

    # ── Embed builder ─────────────────────────────────────────────────────

    def build_embed(self) -> discord.Embed:
        start = self.page * PAGE_SIZE
        end = start + PAGE_SIZE
        page_rows = self.rows[start:end]

        embed = discord.Embed(
            title="📋  Boss Respawn List",
            color=discord.Color.blue(),
        )

        # Build a fixed-width table using code block
        header = f"{'Boss':<16} {'Next':>5}  {'Remain':>8}  {'Cycle':>6}"
        divider = "─" * len(header)
        lines = [header, divider]

        for row in page_rows:
            lines.append(
                f"{row.name:<16} {row.next_spawn_label:>5}  {row.remain_label:>8}  {row.cycle_label:>6}"
            )

        embed.description = f"```\n{chr(10).join(lines)}\n```"
        embed.set_footer(
            text=f"Page {self.page + 1} / {self.max_page + 1}  •  {len(self.rows)} bosses"
        )
        return embed

    # ── Button callbacks ──────────────────────────────────────────────────

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = max(0, self.page - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.page = min(self.max_page, self.page + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _update_buttons(self) -> None:
        self.prev_button.disabled = self.page == 0
        self.next_button.disabled = self.page == self.max_page

    async def on_timeout(self) -> None:
        """Disable buttons when the view times out."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True