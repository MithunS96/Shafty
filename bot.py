import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz
import uuid
from typing import Optional

# ────── LOAD ENV ──────
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")

# ────── TIMEZONE ──────
IST = pytz.timezone("Asia/Kolkata")

# ────── BOT SETUP ──────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone=IST)

# ────── STORAGE (in-memory) ──────
meetings = {}

# ────── READY ──────
@bot.event
async def on_ready():
    await bot.tree.sync()
    scheduler.start()
    print(f"✅ Bot online as {bot.user}")

# ────── INSTAGRAM ANNOUNCEMENT (WITH ROLE PING) ──────
@bot.tree.command(name="insta", description="Announce a new Instagram post")
async def insta(
    interaction: discord.Interaction,
    link: str,
    role: Optional[discord.Role] = None
):
    role_ping = role.mention if role else ""

    await interaction.response.send_message(
        f"📸 **New Instagram Post!**\n"
        f"{role_ping}\n"
        f"Check it out 👉 {link}"
    )

# ────── MEETING COMMAND ──────
@bot.tree.command(
    name="meeting",
    description="Schedule a meeting with 24h & 1h reminders"
)
async def meeting(
    interaction: discord.Interaction,
    date: str,      # YYYY-MM-DD
    time: str,      # HH:MM (24hr)
    message: str,
    role: Optional[discord.Role] = None
):
    try:
        meeting_time = datetime.strptime(
            f"{date} {time}", "%Y-%m-%d %H:%M"
        )
        meeting_time = IST.localize(meeting_time)

        meeting_id = str(uuid.uuid4())[:8]
        channel_id = interaction.channel_id
        role_ping = role.mention if role else ""

        # Store meeting
        meetings[meeting_id] = {
            "time": meeting_time,
            "message": message,
            "channel_id": channel_id,
            "role": role_ping
        }

        # 24h reminder
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=meeting_time - timedelta(hours=24),
            args=[meeting_id, "⏰ 24-hour reminder"]
        )

        # 1h reminder
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=meeting_time - timedelta(hours=1),
            args=[meeting_id, "⏰ 1-hour reminder"]
        )

        await interaction.response.send_message(
            f"📅 **Meeting Scheduled**\n"
            f"🆔 ID: `{meeting_id}`\n"
            f"🕒 {meeting_time.strftime('%d %b %Y, %I:%M %p IST')}\n"
            f"🔔 Reminders: 24h & 1h before\n"
            f"{role_ping}"
        )

    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid format.\nUse `YYYY-MM-DD` and `HH:MM` (24-hour)",
            ephemeral=True
        )

# ────── SEND REMINDER ──────
async def send_reminder(meeting_id, prefix):
    meeting = meetings.get(meeting_id)
    if not meeting:
        return

    channel = bot.get_channel(meeting["channel_id"])
    if channel:
        await channel.send(
            f"{prefix}\n"
            f"{meeting['role']}\n"
            f"📌 **Meeting:** {meeting['message']}"
        )

# ────── LIST MEETINGS ──────
@bot.tree.command(name="meetings", description="List upcoming meetings")
async def list_meetings(interaction: discord.Interaction):
    if not meetings:
        await interaction.response.send_message("No upcoming meetings.")
        return

    msg = "**📅 Upcoming Meetings:**\n"
    for mid, m in meetings.items():
        msg += (
            f"\n🆔 `{mid}` | "
            f"{m['time'].strftime('%d %b %I:%M %p IST')} — "
            f"{m['message']}"
        )

    await interaction.response.send_message(msg)

# ────── CANCEL MEETING ──────
@bot.tree.command(name="cancel", description="Cancel a meeting by ID")
async def cancel(interaction: discord.Interaction, meeting_id: str):
    if meeting_id not in meetings:
        await interaction.response.send_message(
            "❌ Meeting ID not found.", ephemeral=True
        )
        return

    meetings.pop(meeting_id)
    scheduler.remove_all_jobs()

    # Re-schedule remaining meetings
    for mid, m in meetings.items():
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=m["time"] - timedelta(hours=24),
            args=[mid, "⏰ 24-hour reminder"]
        )
        scheduler.add_job(
            send_reminder,
            "date",
            run_date=m["time"] - timedelta(hours=1),
            args=[mid, "⏰ 1-hour reminder"]
        )

    await interaction.response.send_message(
        f"🗑️ Meeting `{meeting_id}` cancelled."
    )

# ────── RUN BOT ──────
bot.run(TOKEN)
