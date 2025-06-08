import discord
import psycopg2
from discord.ext import commands, tasks
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
calender_TOKEN = os.getenv("calender_token")

# PostgreSQL 연결
conn = psycopg2.connect(
    host=os.getenv("PG_HOST"),
    database=os.getenv("PG_DATABASE"),
    user=os.getenv("PG_USER"),
    password=os.getenv("PG_PASSWORD"),
    port=os.getenv("PG_PORT"),
)
cursor = conn.cursor()

# Discord 봇 설정
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 일정 테이블 생성 (PostgreSQL 문법)
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    title VARCHAR(50) DEFAULT 'Birth',
    date DATE,
    writer TEXT,
    author_id TEXT
)
"""
)
conn.commit()

TARGET_CHANNEL_ID = 1380961745090379859


@bot.event
async def on_ready():
    print(f"✅ 봇 로그인됨: {bot.user}")


@tasks.loop(hours=9)
async def daily_birthday_check():
    await bot.wait_until_ready()
    today = datetime.now().strftime("%m-%d")

    cursor.execute("SELECT date, writer, author_id FROM schedule WHERE title = 'Birth'")
    rows = cursor.fetchall()

    birthday_list = []
    for date_obj, writer, author_id in rows:
        if date_obj.strftime("%m-%d") == today:
            birthday_list.append((writer, author_id))

    if birthday_list:
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        message = "🎉 오늘 생일인 분이 있습니다!\n"
        for writer, author_id in birthday_list:
            mention = f"<@{author_id}>"
            message += f"🎂 **{writer}** 님 ({mention}) 생일 축하합니다!\n"
        await channel.send(message)


@bot.command(name="생일확인")
async def get_next_schedule(ctx):
    today = datetime.now().date()
    today_md = today.strftime("%m-%d")

    cursor.execute("SELECT date, writer, author_id FROM schedule WHERE title = 'Birth'")
    rows = cursor.fetchall()
    upcoming_birthdays = []
    for date_obj, writer, author_id in rows:
        birthday_this_year = date_obj.replace(year=today.year)
        if birthday_this_year < today:
            birthday_next = birthday_this_year.replace(year=today.year + 1)
        else:
            birthday_next = birthday_this_year

        days_left = (birthday_next - today).days
        upcoming_birthdays.append((birthday_next, writer, author_id, days_left))
    if upcoming_birthdays:
        upcoming_birthdays.sort(key=lambda x: x[0])
        message = "🎂 **다가오는 생일자 목록 (최대 10명):**\n"

        for birthday, writer, author_id, days_left in upcoming_birthdays[:10]:
            mention = f"<@{author_id}>"
            message += f"\n🧑‍🎂 **{writer}** — `{birthday.strftime('%Y-%m-%d')}` (⏳ {days_left}일 남음, 등록자: {mention})"

        await ctx.send(message)
    else:
        await ctx.send("📭 예정된 생일 일정이 없습니다.")


@bot.command(name="내일정")
async def get_user_schedule(ctx):
    now = datetime.now().date()
    author_id = str(ctx.author.id)
    cursor.execute(
        "DELETE FROM schedule WHERE date < %s AND author_id = %s", (now, author_id)
    )
    conn.commit()

    cursor.execute(
        "SELECT title, date, writer FROM schedule WHERE date >= %s AND author_id = %s ORDER BY date LIMIT 5",
        (now, author_id),
    )
    rows = cursor.fetchall()

    if rows:
        message = f"📋 {ctx.author.mention}님의 예정된 일정 (최대 5개):\n"
        for title, date_obj, writer in rows:
            days_left = (date_obj - now).days
            d_day = "오늘" if days_left == 0 else f"{days_left}일 남음"
            message += (
                f"\n🔸 **{title}** — `{date_obj.strftime('%Y-%m-%d')}` (⏳ {d_day})"
            )
        await ctx.send(message)
    else:
        await ctx.send(f"{ctx.author.mention}님은 예정된 일정이 없습니다.")


@bot.command(name="자기소개")
async def add_birth(ctx, date: str, writer: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    author_id = str(ctx.author.id)

    cursor.execute(
        "SELECT * FROM schedule WHERE title = 'Birth' and author_id = %s", (author_id,)
    )
    row = cursor.fetchone()
    if row:
        writer = row[3]
        await ctx.send(
            f"{writer}님은 이미 등록 되어 있습니다. {writer}님 의 생일은 `{row[2]}`입니다. 🎂\n"
        )
        return
    cursor.execute(
        "INSERT INTO schedule (date, writer, author_id) VALUES (%s, %s, %s)",
        (date_obj, writer, author_id),
    )
    conn.commit()
    await ctx.send(
        f"✅ 자기소개 추가됨: **{writer}**님의 아이디는 {author_id}입니다. 🎂은 `{date}`입니다."
    )


@bot.command(name="일정추가")
async def add_schedule(ctx, title: str, date: str, writer: str):
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    author_id = str(ctx.author.id)

    cursor.execute(
        "SELECT * FROM schedule WHERE title = %s and date = %s  and author_id = %s",
        (title, date_obj, author_id),
    )
    row = cursor.fetchone()
    if row:
        writer = row[3]
        title = row[1]
        date_obj = row[2]
        await ctx.send(f"{writer}님의 {date_obj} {title} 일정은 이미 등록되었습니다. ")
        return
    cursor.execute(
        "INSERT INTO schedule (title, date, writer, author_id) VALUES (%s, %s, %s, %s)",
        (title, date_obj, writer, author_id),
    )
    conn.commit()
    await ctx.send(
        f"✅ 일정 추가됨: {writer}님의 **{title}** 일정이 `{date}`에 등록되었습니다. 작성자: <@{author_id}>"
    )


bot.run(calender_TOKEN)
