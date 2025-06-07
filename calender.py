import discord
import sqlite3
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
calender_TOKEN = os.getenv("calender_token")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# SQLite 연결
conn = sqlite3.connect("schedule.db")
cursor = conn.cursor()

# 테이블 예시: schedule(id INTEGER PRIMARY KEY, title TEXT, date TEXT)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT default 'Birth',
    date TEXT,
    writer TEXT,
    author_id TEXT

)
"""
)
conn.commit()

TARGET_CHANNEL_ID = 1380858273506529361


@bot.event
async def on_ready():
    print(f"봇 로그인됨: {bot.user}")


@tasks.loop(hours=9)
async def daily_birthday_check():
    await bot.wait_until_ready()  # 봇이 완전히 실행된 뒤 시작
    today = datetime.datetime.now().strftime("%m-%d")

    cursor.execute("SELECT date, writer, author_id FROM schedule WHERE title = 'Birth'")
    rows = cursor.fetchall()

    birthday_list = []
    for date_str, writer, author_id in rows:
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            if date_obj.strftime("%m-%d") == today:
                birthday_list.append((writer, author_id))
        except:
            continue

    if birthday_list:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        message = f"🎉 오늘 생일인 분이 있습니다!\n"
        for writer, author_id in birthday_list:
            mention = f"<@{author_id}>"
            message += f"🎂 **{writer}** 님 ({mention}) 생일 축하합니다!\n"
        await channel.send(message)


@bot.command(name="생일확인")
async def get_next_schedule(ctx):
    today = datetime.now()
    today_md = today.strftime("%m-%d")

    cursor.execute("SELECT date, writer, author_id FROM schedule WHERE title = 'Birth'")
    rows = cursor.fetchall()
    upcoming_birthdays = []
    for date_str, writer, author_id in rows:
        try:
            original_date = datetime.strptime(date_str, "%Y-%m-%d")
            birthday_this_year = original_date.replace(year=today.year)
            if birthday_this_year.strftime("%m-%d") >= today_md:
                upcoming_birthdays.append((birthday_this_year, writer, author_id))
        except:
            continue

    if upcoming_birthdays:
        upcoming_birthdays.sort(key=lambda x: x[0])
        message = "🎂 **다가오는 생일자 목록 (최대 5명):**\n"

        for birthday, writer, author_id in upcoming_birthdays[:5]:
            days_left = (birthday - today).days
            mention = f"<@{author_id}>"
            message += (
                f"\n🧑‍🎂 **{writer}** — `{birthday.strftime('%Y-%m-%d')}`"
                f" (⏳ {days_left}일 남음, 등록자: {mention})"
            )

        await ctx.send(message)
    else:
        await ctx.send("📭 예정된 생일 일정이 없습니다.")


@bot.command(name="내일정")
async def get_user_schedule(ctx):
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d")
    author_id = str(ctx.author.id)

    cursor.execute(
        "SELECT title, date, writer FROM schedule WHERE date >= ? AND author_id = ? ORDER BY date LIMIT 1",
        (now_str, author_id),
    )
    result = cursor.fetchone()

    if result:
        title, date_str, writer = result
        schedule_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_left = (schedule_date - now).days
        await ctx.send(
            f"👤 {ctx.author.mention}님의 다음 일정:\n"
            f"📅 **{title}**\n🕒 `{date_str}`\n⏳ **{days_left}일** 남았습니다."
        )
    else:
        await ctx.send(f"{ctx.author.mention}님은 예정된 일정이 없습니다.")


@bot.command(name="자기소개")
async def add_birth(ctx, date: str, writer: str):
    datetime.strptime(date, "%Y-%m-%d")
    author_id = str(ctx.author.id)
    cursor.execute(
        "INSERT INTO schedule (date, writer, author_id) VALUES (?, ?, ?)",
        (date, writer, author_id),
    )
    conn.commit()
    await ctx.send(
        f"✅ 자기소개정보 추가됨: **{writer}**님의 아이디는{author_id}입니다. 🎂은 `{date}` 입니다."
    )


@bot.command(name="일정추가")
async def add_schedule(ctx, title: str, date: str, writer: str):
    datetime.strptime(date, "%Y-%m-%d")
    author_id = str(ctx.author.id)
    cursor.execute(
        "INSERT INTO schedule (title, date, writer, author_id) VALUES (?, ?, ?, ?)",
        (title, date, writer, author_id),
    )
    conn.commit()
    await ctx.send(
        f"✅ 일정 추가됨:{writer}님의  **{title}**에 일정이 `{date}`에 추가되었습니다. 작성자: <@{author_id}>"
    )


bot.run(calender_TOKEN)
