import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import aiosqlite

TOKEN = ''
GUILD_ID = 1347917916687044780  # آیدی سرور

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'✅ Bot is ready as {bot.user}')
    await setup_db()
    check_expired_roles.start()

async def setup_db():
    async with aiosqlite.connect("roles.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS timed_roles (
                user_id INTEGER,
                role_id INTEGER,
                expire_at TEXT,
                PRIMARY KEY (user_id, role_id)
            )
        """)
        await db.commit()

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member, role: discord.Role, days: int):
    expire_time = datetime.now() + timedelta(days=days)
    await member.add_roles(role)
    async with aiosqlite.connect("roles.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO timed_roles (user_id, role_id, expire_at) VALUES (?, ?, ?)",
            (member.id, role.id, expire_time.isoformat())
        )
        await db.commit()
    await ctx.send(f"✅ رول **{role.name}** به {member.mention} داده شد تا {days} روز.")

    # ارسال پیام خصوصی به کاربر
    try:
        await member.send(
            f"🎉 سلام! رول **{role.name}** به مدت **{days} روز** به شما در سرور **{ctx.guild.name}** داده شد."
        )
    except discord.Forbidden:
        await ctx.send(f"⚠️ نتونستم به {member.mention} پیام خصوصی بفرستم (احتمالا پیام‌های خصوصی رو بسته).")

@tasks.loop(minutes=60)
async def check_expired_roles():
    now = datetime.utcnow()
    async with aiosqlite.connect("roles.db") as db:
        async with db.execute("SELECT user_id, role_id, expire_at FROM timed_roles") as cursor:
            rows = await cursor.fetchall()
            for user_id, role_id, expire_at in rows:
                expire_time = datetime.fromisoformat(expire_at)
                if now >= expire_time:
                    guild = bot.get_guild(GUILD_ID)
                    member = guild.get_member(user_id)
                    role = guild.get_role(role_id)
                    if member and role:
                        await member.remove_roles(role)
                        print(f"❌ رول {role.name} از {member.name} برداشته شد.")
                    await db.execute(
                        "DELETE FROM timed_roles WHERE user_id = ? AND role_id = ?",
                        (user_id, role_id)
                    )
        await db.commit()

bot.run(TOKEN)
