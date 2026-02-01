import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import pytz

# ────── LOAD ENV ──────
load_dotenv()
TOKEN = os.getenv("TOKEN")

# ────── TIMEZONE (IST) ──────
IST = pytz.timezone("Asia/Kolkata")

# ────── BOT SETUP ──────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
scheduler = AsyncIOScheduler(timezone=IST)

# ────── READY ──────
@bot.event
async def on_ready():
    await bot.tree.sync()
    scheduler.start()
    print(f"✅ Bot online as {bot.user}")

# ────── INSTAGRAM ANNOUNCEMENT ──────
@bot.tree.command(name="insta", description="Announce a new Instagram post")
async def insta(interaction: discord.Interaction, link: str):
    await interaction.response.send_message(
        f"📸 **New Instagram Post!**\n"
        f"Check it out 👉 {link}"
    )

# ────── MEETING WITH AUTO 1-HOUR REMINDER ──────
@bot.tree.command(
    name="meeting",
    description="Schedule a meeting with automatic 1-hour reminder"
)
async def meeting(
    interaction: discord.Interaction,
    date: str,   # YYYY-MM-DD
    time: str,   # HH:MM (24hr)
    message: str
):
    try:
        meeting_time = datetime.strptime(
            f"{date} {time}", "%Y-%m-%d %H:%M"
        )
        meeting_time = IST.localize(meeting_time)

        reminder_time = meeting_time - timedelta(hours=1)

        scheduler.add_job(
            send_reminder,
            "date",
            run_date=reminder_time,
            args=[interaction.channel_id, message]
        )

        await interaction.response.send_message(
            f"📅 **Meeting Scheduled**\n"
            f"🕒 {meeting_time.strftime('%d %b %Y, %I:%M %p IST')}\n"
            f"⏰ Reminder will be sent 1 hour before"
        )

    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid date/time format.\n"
            "Use: `YYYY-MM-DD` and `HH:MM (24-hour)`",
            ephemeral=True
        )

# ────── REMINDER SENDER ──────
async def send_reminder(channel_id, message):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(
            f"⏰ **Meeting Reminder (1 hour to go!)**\n{message}"
        )

# ────── RUN BOT ──────
bot.run(TOKEN)
