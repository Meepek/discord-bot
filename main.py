import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import aiosqlite
from typing import Optional
import pytz
import re
import traceback

# --- PODSTAWOWA KONFIGURACJA ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

LOG_CHANNEL_ID = None
POLAND_TZ = pytz.timezone('Europe/Warsaw')
DB_PATH = '/data/bot_database.db'

# --- BRANDING & COLORS ---
LOGO_URL = "https://i.postimg.cc/0jY1crF6/moje-logo2.jpg"
FOOTER_TEXT = "© Aelios2.pl | Bot by Meep"
COLORS = {
    "main": 0xE67E22,
    "success": 0x2ECC71,
    "error": 0xE74C3C,
    "warn": 0x3498DB,
}

# --- KONFIGURACJA FUNKCJI ---
NOTIFICATION_CONFIG = {}
REMINDER_CONFIG = {
    "enabled": False,
    "delay_days": 3
}
SHOP_CONFIG = {
    "channel_id": None,
    "manual_reward_roles": ["Opiekun JB", "Zarząd", "Właściciel"]
}
SHOP_CATEGORIES = ["Specjalne role", "VIP", "Premium", "Fajki", "Oferty Dnia", "Inne"]

# --- TYPY REKRUTACJI (PUNKT 2 - nowe podania) ---
ADMIN_RECRUITMENT_TYPES = [
    "Podanie Admin JB",
    "Podanie Zaufany JB",
    "Podanie Admin DC",
    "Podanie Admin Supermoce",
    "Podanie Admin Surf + RPG",
    "Podanie Admin DR",
    "Podanie Admin Projekt RPG"
]
CREATIVE_RECRUITMENT_TYPES = [
    "Podanie Developer",
    "Podanie MapDeveloper",
    "Podanie Grafik",
    "Podanie Redaktor"
]
ALL_RECRUITMENT_TYPES = ADMIN_RECRUITMENT_TYPES + CREATIVE_RECRUITMENT_TYPES

# --- LISTA SERWERÓW (PUNKT 3 - propozycje i błędy) ---
SERVER_LIST = [
    "JailBreak",
    "Supermoce",
    "Surf + RPG",
    "DeathRun",
    "Projekt RPG",
    "Discord",
    "Inne"
]

# --- ZARZĄDZANIE UPRAWNIENIAMI ---
SETUP_ADMIN_ROLES = ["Właściciel", "Zarząd"]
SHOP_ADMIN_ROLES = ["Właściciel", "Zarząd"]
REPUTATION_ADMIN_ROLES = ["Właściciel", "Zarząd"]
RECRUITMENT_ADMIN_ROLES = ["Opiekun JB", "Zarząd", "Właściciel"]
CREATIVE_RECRUITMENT_ADMIN_ROLES = ["Właściciel", "Zarząd"]
ANNOUNCEMENT_ADMIN_ROLES = ["Właściciel", "Zarząd"]
REDAKCJA_ROLES = ["Właściciel", "Zarząd", "Redaktor"]
GENERAL_ADMIN_ROLES = ["Właściciel", "Zarząd", "Opiekun JB", "Opiekun Discord"]

# --- SZABLONY ODPOWIEDZI ---
RESPONSE_TEMPLATES = {
    "reject_suggestion": [
        "Pomysł był już proponowany w przeszłości.",
        "Niezgodne z wizją rozwoju serwera.",
        "Technicznie niemożliwe do zrealizowania.",
    ],
    "reject_bug": [
        "Nie udało się odtworzyć opisanego błędu.",
        "Opisane zachowanie jest zamierzone.",
    ],
    "reject_complaint": [
        "Niewystarczające dowody do podjęcia akcji.",
        "Zgłoszone zachowanie nie narusza regulaminu.",
    ],
    "reject_appeal": [
        "Kara została nałożona słusznie.",
        "Odwołanie nie zawiera wystarczającej skruchy.",
    ],
    "reject_application": [
        "Kandydat nie spełnia podstawowych wymagań.",
        "Podanie jest niekompletne lub napisane niestarannie.",
        "Obecnie nie poszukujemy nowych członków ekipy.",
    ]
}

# --- BAZA DANYCH (PUNKT 5 - aiosqlite) ---
async def init_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, username TEXT NOT NULL,
                category TEXT NOT NULL, description TEXT NOT NULL, reason TEXT NOT NULL,
                server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category TEXT NOT NULL,
                bug_type TEXT NOT NULL, description TEXT NOT NULL, evidence TEXT,
                server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'reported', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, complaint_type TEXT NOT NULL,
                target_user TEXT NOT NULL, data TEXT NOT NULL, thread_id TEXT,
                status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, appeal_type TEXT NOT NULL,
                data TEXT NOT NULL, thread_id TEXT, status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, username TEXT NOT NULL,
                application_type TEXT NOT NULL, data TEXT NOT NULL, thread_id TEXT,
                status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reputation_points (
                user_id TEXT PRIMARY KEY, points INTEGER DEFAULT 0
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                message_id INTEGER PRIMARY KEY, question TEXT NOT NULL, options TEXT NOT NULL,
                votes TEXT NOT NULL, author_id INTEGER NOT NULL
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, description TEXT, cost INTEGER NOT NULL,
                category TEXT NOT NULL, role_id INTEGER DEFAULT NULL, stock INTEGER DEFAULT NULL
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shop_purchases (
                user_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, item_id)
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS recruitment_status (
                position TEXT PRIMARY KEY, is_open INTEGER DEFAULT 1
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                message_id INTEGER PRIMARY KEY, author_id INTEGER NOT NULL, attendees TEXT NOT NULL
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS editorial_counters (
                type TEXT PRIMARY KEY, count INTEGER DEFAULT 0
            )''')

        # Dodaj kolumny reminder_sent jeśli nie istnieją
        tables_to_alter = {
            "suggestions": "reminder_sent INTEGER DEFAULT 0",
            "bug_reports": "reminder_sent INTEGER DEFAULT 0",
            "complaints": "reminder_sent INTEGER DEFAULT 0",
            "appeals": "reminder_sent INTEGER DEFAULT 0",
            "applications": "reminder_sent INTEGER DEFAULT 0"
        }
        for table, column_def in tables_to_alter.items():
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
            except Exception:
                pass

        # Dodaj kolumnę server jeśli nie istnieje
        for table in ["suggestions", "bug_reports"]:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN server TEXT DEFAULT 'Nieokreślony'")
            except Exception:
                pass

        await db.commit()

# --- FUNKCJE POMOCNICZE BAZY DANYCH (aiosqlite) ---
async def save_suggestion(user_id, username, category, description, reason, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO suggestions (user_id, username, category, description, reason, server, thread_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (user_id, username, category, description, reason, server, thread_id))
        await db.commit()

async def save_bug_report(user_id, category, bug_type, description, evidence, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO bug_reports (user_id, category, bug_type, description, evidence, server, thread_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (user_id, category, bug_type, description, evidence, server, thread_id))
        await db.commit()

async def save_complaint(user_id, complaint_type, target_user, data, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO complaints (user_id, complaint_type, target_user, data, thread_id) VALUES (?, ?, ?, ?, ?)',
                         (user_id, complaint_type, target_user, json.dumps(data), thread_id))
        await db.commit()

async def save_appeal(user_id, appeal_type, data, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO appeals (user_id, appeal_type, data, thread_id) VALUES (?, ?, ?, ?)',
                         (user_id, appeal_type, json.dumps(data), thread_id))
        await db.commit()

async def save_application(user_id, username, app_type, data, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO applications (user_id, username, application_type, data, thread_id) VALUES (?, ?, ?, ?, ?)',
                         (user_id, username, app_type, json.dumps(data), thread_id))
        await db.commit()

async def update_reputation(user_id: int, points: int, mode: str = 'add'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO reputation_points (user_id, points) VALUES (?, 0)", (str(user_id),))
        if mode == 'add':
            await db.execute("UPDATE reputation_points SET points = points + ? WHERE user_id = ?", (points, str(user_id)))
        elif mode == 'set':
            await db.execute("UPDATE reputation_points SET points = ? WHERE user_id = ?", (points, str(user_id)))
        await db.commit()
        async with db.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            return row[0]

# --- FUNKCJE POMOCNICZE ---
def is_authorized(interaction: discord.Interaction, required_roles: list) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    return any(role.name in required_roles for role in interaction.user.roles)

def has_permission_for_type(user: discord.Member, item_type: str) -> bool:
    if user.guild_permissions.administrator:
        return True
    item_lower = item_type.lower()
    if any(x in item_lower for x in ["jb", "supermoce", "surf", "dr", "projekt rpg", "deathrun"]):
        return any(role.name in ["Opiekun JB", "Zarząd", "Właściciel"] for role in user.roles)
    elif "discord" in item_lower or "dc" in item_lower:
        return any(role.name in ["Opiekun Discord", "Zarząd", "Właściciel"] for role in user.roles)
    return False

async def log_action(guild: discord.Guild, action: str, user: discord.Member, details: str = ""):
    if not LOG_CHANNEL_ID:
        return
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        return
    embed = discord.Embed(title="📋 Log Akcji", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    embed.add_field(name="👤 Użytkownik", value=user.mention, inline=True)
    embed.add_field(name="⚡ Akcja", value=action, inline=True)
    if details:
        embed.add_field(name="📝 Szczegóły", value=details, inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"ID: {user.id} | {FOOTER_TEXT}")
    try:
        await log_channel.send(embed=embed)
    except discord.HTTPException:
        pass

async def send_notification(guild: discord.Guild, post_type: str, thread_url: str, is_reminder: bool = False):
    config = NOTIFICATION_CONFIG.get(post_type)
    if not config:
        return
    channel = guild.get_channel(config['channel_id'])
    if not channel:
        return
    role_mention = f"<@&{config['role_id']}>" if config.get('role_id') else ""
    title = f"⏰ Przypomnienie: {post_type}" if is_reminder else f"📬 Nowe zgłoszenie: {post_type}"
    description = f"Zgłoszenie czeka na reakcję od ponad {REMINDER_CONFIG['delay_days']} dni.\n\n[Przejdź do posta]({thread_url})" if is_reminder else f"Nowy post czeka na Twoją uwagę.\n\n[Przejdź do posta]({thread_url})"

    color = COLORS["main"]
    if is_reminder:
        color = COLORS["warn"]
    elif post_type.startswith("Podanie"):
        color = COLORS["success"]

    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    try:
        await channel.send(content=role_mention, embed=embed)
    except discord.HTTPException:
        pass

# --- PUNKT 4: GLOBALNY ERROR HANDLER ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_id = datetime.now().strftime("%Y%m%d%H%M%S")

    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ Nie masz uprawnień do użycia tej komendy."
    elif isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏳ Poczekaj **{error.retry_after:.1f}s** przed ponownym użyciem."
    elif isinstance(error, app_commands.MissingRole):
        msg = "❌ Nie masz wymaganej roli."
    else:
        msg = f"❌ Wystąpił nieoczekiwany błąd. (ID: `{error_id}`)\nJeśli problem się powtarza, zgłoś to administracji."
        print(f"[ERROR {error_id}] Komenda: {interaction.command.name if interaction.command else 'unknown'}")
        print(f"[ERROR {error_id}] Użytkownik: {interaction.user} ({interaction.user.id})")
        print(f"[ERROR {error_id}] {traceback.format_exception(type(error), error, error.__traceback__)}")

    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass

# --- MODALE (PUNKT 3 - uproszczone propozycje i błędy z wyborem serwera) ---
class SuggestionModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowa Propozycja - {server}")
        self.server = server
        self.description = discord.ui.TextInput(label="Opis propozycji", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.reason = discord.ui.TextInput(label="Dlaczego ma zostać wprowadzona?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, f"Propozycja", "💡", server=self.server)

class BugReportModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowy Błąd - {server}")
        self.server = server
        self.description = discord.ui.TextInput(label="Opis błędu", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.evidence = discord.ui.TextInput(label="Dowody (linki do screenów, filmów)", required=False, max_length=1024)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, f"Błąd", "🐛", server=self.server)

class ComplaintModal(discord.ui.Modal):
    def __init__(self, complaint_type: str):
        super().__init__(title=f"Nowa {complaint_type}")
        self.target_nick = discord.ui.TextInput(label="Nick osoby, na którą składasz skargę", required=True)
        self.add_item(self.target_nick)
        self.reason = discord.ui.TextInput(label="Opis sytuacji i powód skargi", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)
        self.evidence = discord.ui.TextInput(label="Dowody (linki do screenów, filmów)", required=True, max_length=1024)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title.replace("Nowa ", ""), "⚠️")

class AppealModal(discord.ui.Modal):
    def __init__(self, appeal_type: str):
        super().__init__(title=f"Nowe {appeal_type}")
        self.ban_reason = discord.ui.TextInput(label="Powód otrzymanej kary", required=True, max_length=1024)
        self.add_item(self.ban_reason)
        self.admin_nick = discord.ui.TextInput(label="Nick admina, który nałożył karę", required=True)
        self.add_item(self.admin_nick)
        self.appeal_reason = discord.ui.TextInput(label="Dlaczego chcesz otrzymać unbana?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.appeal_reason)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title.replace("Nowe ", ""), "🔓")

# --- MODALE PODAŃ (PUNKT 2 - jeden wzór dla wszystkich adminów serwerowych) ---
class ServerAdminApplicationModal(discord.ui.Modal):
    """Uniwersalny modal dla wszystkich podań adminowskich na serwerach gier."""
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie i swoim doświadczeniu", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    def __init__(self, application_type: str):
        super().__init__(title=application_type)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title, "📋")

class TrustedApplicationModal(discord.ui.Modal, title="Podanie Zaufany JB"):
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Zaufany JB", "📋")

class DiscordAdminApplicationModal(discord.ui.Modal, title="Podanie Admin DC"):
    server_time = discord.ui.TextInput(label="Od kiedy jesteś na tym serwerze Discord?", required=True)
    experience = discord.ui.TextInput(label="Doświadczenie jako administrator", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    knowledge = discord.ui.TextInput(label="Znajomość Discorda (od 1 do 10)", required=True, max_length=2)
    availability = discord.ui.TextInput(label="Ile czasu dziennie mógłbyś poświęcić?", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Admin DC", "📋")

class DeveloperApplicationModal(discord.ui.Modal, title="Podanie Developer"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Developer", "💻")

class MapDeveloperApplicationModal(discord.ui.Modal, title="Podanie MapDeveloper"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie MapDeveloper", "🗺️")

class GraphicDesignerApplicationModal(discord.ui.Modal, title="Podanie Grafik"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Grafik", "🎨")

class EditorApplicationModal(discord.ui.Modal, title="Podanie Redaktor"):
    name = discord.ui.TextInput(label="Imię", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(label="Dlaczego chcesz zostać redaktorem?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    example = discord.ui.TextInput(label="Przykładowa treść", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Redaktor", "📝")

class DecisionReasonModal(discord.ui.Modal, title="Uzasadnienie decyzji"):
    reason_input = discord.ui.TextInput(label="Notatka (opcjonalnie)", style=discord.TextStyle.paragraph, required=False, max_length=1024)

    def __init__(self, original_interaction: discord.Interaction, action: str, post_type: str, author_id: int):
        super().__init__()
        self.original_interaction = original_interaction
        self.action = action
        self.post_type = post_type
        self.author_id = author_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await process_decision(interaction, self.original_interaction, self.action, self.post_type, self.author_id, self.reason_input.value)

class AnnouncementModal(discord.ui.Modal, title="Nowe ogłoszenie"):
    title_input = discord.ui.TextInput(label="Tytuł ogłoszenia", required=True, max_length=256)
    content_input = discord.ui.TextInput(label="Treść ogłoszenia", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.TextChannel, role: Optional[discord.Role]):
        super().__init__()
        self.channel = channel
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=self.title_input.value, description=self.content_input.value, color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Ogłoszenie dodane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        role_mention = self.role.mention if self.role else ""
        await self.channel.send(content=role_mention, embed=embed)
        await interaction.response.send_message("✅ Ogłoszenie zostało pomyślnie opublikowane.", ephemeral=True)

class EventModal(discord.ui.Modal, title="Nowe wydarzenie"):
    title_input = discord.ui.TextInput(label="Tytuł wydarzenia", required=True, max_length=256)
    datetime_input = discord.ui.TextInput(label="Data i godzina (DD.MM.RRRR HH:MM)", placeholder="np. 25.12.2025 18:00", required=True)
    rewards_input = discord.ui.TextInput(label="Nagrody", required=False, max_length=1024)
    content_input = discord.ui.TextInput(label="Opis wydarzenia", style=discord.TextStyle.paragraph, required=True, max_length=2000)

    def __init__(self, channel: discord.TextChannel, role: Optional[discord.Role]):
        super().__init__()
        self.channel = channel
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        try:
            dt_object = datetime.strptime(self.datetime_input.value, "%d.%m.%Y %H:%M")
            localized_dt = POLAND_TZ.localize(dt_object)
            timestamp = int(localized_dt.timestamp())
        except ValueError:
            await interaction.response.send_message("❌ Nieprawidłowy format daty! Użyj `DD.MM.RRRR HH:MM`.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🎉 Nowe wydarzenie: {self.title_input.value}", description=self.content_input.value, color=COLORS["success"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="📅 Kiedy?", value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", inline=False)
        if self.rewards_input.value:
            embed.add_field(name="🎁 Nagrody", value=self.rewards_input.value, inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Wydarzenie zorganizowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")

        role_mention = self.role.mention if self.role else ""
        message = await self.channel.send(content=role_mention, embed=embed, view=EventView(initial_count=0))

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT INTO events (message_id, author_id, attendees) VALUES (?, ?, ?)", (message.id, interaction.user.id, json.dumps([])))
            await db.commit()

        await interaction.response.send_message("✅ Wydarzenie zostało pomyślnie opublikowane.", ephemeral=True)

class QuickShotModal(discord.ui.Modal, title="Nowy Szybki Strzał"):
    title_input = discord.ui.TextInput(label="Tytuł (np. Szybkie strzały z @User)", required=True)
    interviewer = discord.ui.TextInput(label="Osoba przeprowadzająca", required=True)
    interviewee = discord.ui.TextInput(label="Osoba odpowiadająca", required=True)
    content = discord.ui.TextInput(label="Pytania i Odpowiedzi", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.ForumChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title=f"⚡ {self.title_input.value}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="🎙️ Przeprowadził/a", value=self.interviewer.value, inline=True)
        embed.add_field(name="🗣️ Odpowiadał/a", value=self.interviewee.value, inline=True)
        embed.add_field(name="📝 Treść", value=self.content.value, inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Opublikowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        await self.channel.create_thread(name=self.title_input.value, embed=embed)
        await interaction.followup.send("✅ Pomyślnie opublikowano Szybki Strzał.", ephemeral=True)

class InterviewModal(discord.ui.Modal, title="Nowy Wywiad"):
    title_input = discord.ui.TextInput(label="Tytuł wywiadu", required=True)
    interviewer = discord.ui.TextInput(label="Osoba przeprowadzająca", required=True)
    interviewee = discord.ui.TextInput(label="Gość wywiadu", required=True)
    content = discord.ui.TextInput(label="Treść wywiadu", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.ForumChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title=f"🎤 {self.title_input.value}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="🎙️ Przeprowadził/a", value=self.interviewer.value, inline=True)
        embed.add_field(name="🌟 Gość", value=self.interviewee.value, inline=True)
        embed.add_field(name="📝 Treść", value=self.content.value, inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Opublikowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        await self.channel.create_thread(name=self.title_input.value, embed=embed)
        await interaction.followup.send("✅ Pomyślnie opublikowano Wywiad.", ephemeral=True)

# --- WIDOK EVENTU ---
class EventView(discord.ui.View):
    def __init__(self, initial_count: int = 0):
        super().__init__(timeout=None)
        self.signup_button = discord.ui.Button(label=f"Zapisz się! ({initial_count})", style=discord.ButtonStyle.success, custom_id="event_signup_button", emoji="✋")
        self.signup_button.callback = self.signup_callback
        self.add_item(self.signup_button)

    async def signup_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT attendees FROM events WHERE message_id = ?", (interaction.message.id,)) as cursor:
                data = await cursor.fetchone()

            if not data:
                await interaction.followup.send("❌ Wystąpił błąd z tym wydarzeniem.", ephemeral=True)
                return

            attendees = json.loads(data[0])
            user_id = interaction.user.id

            if user_id in attendees:
                attendees.remove(user_id)
                await interaction.followup.send("❌ Zostałeś wypisany z wydarzenia.", ephemeral=True)
            else:
                attendees.append(user_id)
                await interaction.followup.send("✅ Zostałeś zapisany na wydarzenie!", ephemeral=True)

            await db.execute("UPDATE events SET attendees = ? WHERE message_id = ?", (json.dumps(attendees), interaction.message.id))
            await db.commit()

        self.signup_button.label = f"Zapisz się! ({len(attendees)})"
        await interaction.edit_original_response(view=self)

# --- LOGIKA DECYZJI ---
async def process_decision(interaction: discord.Interaction, original_interaction: discord.Interaction, action: str, post_type: str, author_id: int, reason_text: str):
    try:
        original_message = original_interaction.message
        original_embed = original_message.embeds[0]

        action_map = {
            "accept_suggestion": {"text": "Propozycja przyjęta", "color": COLORS["success"], "points": 5, "prefix": "[Zaakceptowane]", "final": True},
            "reject_suggestion": {"text": "Propozycja odrzucona", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
            "accept_bug": {"text": "W trakcie naprawy", "color": COLORS["warn"], "points": 0, "prefix": "[W trakcie]", "final": False},
            "resolve_bug": {"text": "Naprawiony", "color": COLORS["success"], "points": 3, "prefix": "[Naprawione]", "final": True},
            "reject_bug": {"text": "Zgłoszenie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
            "accept_complaint": {"text": "Skarga rozpatrzona pozytywnie", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
            "reject_complaint": {"text": "Skarga odrzucona", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
            "accept_appeal": {"text": "Odwołanie zaakceptowane", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
            "reject_appeal": {"text": "Odwołanie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
            "accept_application": {"text": "Podanie przyjęte", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
            "reject_application": {"text": "Podanie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
        }

        action_details = action_map.get(action)
        if not action_details:
            return

        original_embed.color = action_details["color"]
        for i, field in enumerate(original_embed.fields):
            if field.name == "📊 Status":
                original_embed.set_field_at(i, name="📊 Status", value=action_details["text"], inline=True)
                break

        decision_embed = discord.Embed(title="⚖️ Decyzja podjęta!", color=action_details["color"])
        decision_embed.add_field(name="Status", value=action_details["text"], inline=True)
        decision_embed.add_field(name="Rozpatrzył", value=interaction.user.mention, inline=True)
        if reason_text:
            decision_embed.add_field(name="Notatka od administracji", value=reason_text, inline=False)
        if LOGO_URL:
            decision_embed.set_thumbnail(url=LOGO_URL)
        decision_embed.set_footer(text=FOOTER_TEXT)

        if action_details["points"] > 0:
            await update_reputation(author_id, action_details["points"], mode='add')

        dm_message = ""
        if action == "accept_application":
            dm_message = f"✅ Gratulacje! Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało zaakceptowane!"
            member = interaction.guild.get_member(author_id)
            if member:
                try:
                    roles_map = {
                        "Podanie Admin JB": ["Junior Admin JB", "Administracja JB"],
                        "Podanie Zaufany JB": ["Zaufany JB", "Administracja JB"],
                        "Podanie Admin DC": ["Admin Discord"],
                        "Podanie Admin Supermoce": ["Admin Supermoce"],
                        "Podanie Admin Surf + RPG": ["Admin Surf + RPG"],
                        "Podanie Admin DR": ["Admin DR"],
                        "Podanie Admin Projekt RPG": ["Admin Projekt RPG"],
                    }
                    roles_to_add_names = roles_map.get(post_type, [])
                    roles_to_add = [discord.utils.get(interaction.guild.roles, name=name) for name in roles_to_add_names]
                    valid_roles = [r for r in roles_to_add if r]
                    if valid_roles:
                        await member.add_roles(*valid_roles, reason=f"Akceptacja podania: {post_type}")
                except discord.Forbidden:
                    await original_interaction.channel.send(f"⚠️ **Błąd uprawnień!** Nie udało się nadać roli {member.mention}.")
                except Exception as e:
                    print(f"Błąd podczas nadawania roli: {e}")
        elif action == "reject_application":
            dm_message = f"❌ Niestety, Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało odrzucone."

        new_view = None if action_details["final"] else ManagementView(post_type, author_id, is_in_progress=True)

        await original_message.edit(embed=original_embed, view=new_view)
        await original_interaction.channel.send(embed=decision_embed)

        if action_details["final"]:
            current_name = original_interaction.channel.name
            new_name = f"{action_details['prefix']} {current_name}"
            if len(new_name) > 100:
                new_name = new_name[:97] + "..."
            try:
                await original_interaction.channel.edit(name=new_name, locked=True, archived=True)
            except discord.HTTPException:
                pass

        if dm_message:
            try:
                member = interaction.guild.get_member(author_id)
                if member:
                    await member.send(dm_message)
            except discord.Forbidden:
                pass

        await log_action(interaction.guild, f"Zarządzano postem: {action_details['text']}", interaction.user, f"Post: {original_interaction.channel.mention}")

    except Exception as e:
        print(f"Błąd w process_decision: {e}")
        traceback.print_exc()

# --- FUNKCJE TWORZĄCE POSTY ---
async def create_generic_post(modal: discord.ui.Modal, interaction: discord.Interaction, post_type: str, emoji: str, server: str = None):
    await interaction.response.defer(ephemeral=True)
    try:
        full_type = f"{post_type} ({server})" if server else post_type
        embed = discord.Embed(title=f"{emoji} Nowe zgłoszenie: {full_type}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))

        if server:
            embed.add_field(name="🖥️ Serwer", value=server, inline=True)

        for item in modal.children:
            if item.value:
                embed.add_field(name=item.label, value=item.value, inline=False)

        embed.add_field(name="👤 Autor", value=interaction.user.mention, inline=False)
        embed.add_field(name="📊 Status", value="Oczekuje na decyzję", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=FOOTER_TEXT)

        forum_channel = interaction.channel.parent if isinstance(interaction.channel, discord.Thread) else interaction.channel

        # Szukaj tagu - najpierw pełny typ, potem sam post_type
        tag = discord.utils.get(forum_channel.available_tags, name=full_type)
        if not tag:
            tag = discord.utils.get(forum_channel.available_tags, name=post_type)
        if not tag:
            # Spróbuj znaleźć tag po części nazwy
            for available_tag in forum_channel.available_tags:
                if post_type.lower() in available_tag.name.lower():
                    tag = available_tag
                    break

        post_title = f"{full_type}: {interaction.user.display_name}"
        if len(post_title) > 100:
            post_title = post_title[:97] + "..."

        applied_tags = [tag] if tag else []
        thread_message = await forum_channel.create_thread(
            name=post_title,
            embed=embed,
            applied_tags=applied_tags,
            view=ManagementView(post_type, interaction.user.id)
        )

        # Zapis do bazy danych
        data = {item.label: item.value for item in modal.children if item.value}
        if post_type == "Propozycja":
            await save_suggestion(str(interaction.user.id), interaction.user.display_name, post_type, data.get('Opis propozycji', ''), data.get('Dlaczego ma zostać wprowadzona?', ''), server or 'Nieokreślony', str(thread_message.thread.id))
        elif post_type == "Błąd":
            await save_bug_report(str(interaction.user.id), post_type, "Nieokreślony", data.get('Opis błędu', ''), data.get('Dowody (linki do screenów, filmów)', ''), server or 'Nieokreślony', str(thread_message.thread.id))
        elif post_type.startswith("Skarga"):
            await save_complaint(str(interaction.user.id), post_type, data.get('Nick osoby, na którą składasz skargę', ''), data, str(thread_message.thread.id))
        elif post_type.startswith("Odwołanie"):
            await save_appeal(str(interaction.user.id), post_type, data, str(thread_message.thread.id))
        elif post_type.startswith("Podanie"):
            await save_application(str(interaction.user.id), interaction.user.display_name, post_type, data, str(thread_message.thread.id))

        await log_action(interaction.guild, f"Złożono: {full_type}", interaction.user, f"Post: {thread_message.thread.mention}")
        await send_notification(interaction.guild, post_type, thread_message.thread.jump_url)
        await interaction.followup.send(f"✅ Twoje zgłoszenie zostało opublikowane w poście {thread_message.thread.mention}!", ephemeral=True)

    except Exception as e:
        print(f"Błąd podczas tworzenia posta ({post_type}): {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send("❌ Wystąpił nieoczekiwany błąd. Spróbuj ponownie.", ephemeral=True)
        except discord.HTTPException:
            pass

# --- GŁÓWNE MENU WYBORU (PUNKT 3 - nowy system propozycji/błędów) ---
class ForumSelectionView(discord.ui.View):
    def __init__(self, view_type: str):
        super().__init__(timeout=None)
        self.add_item(ForumSelect(view_type=view_type, custom_id=f"persistent_forum_select_{view_type}"))

class ForumSelect(discord.ui.Select):
    def __init__(self, view_type: str, custom_id: str):
        options, placeholder = [], "Wybierz akcję..."

        if view_type == "proposals_bugs":
            placeholder = "Co chcesz zgłosić?"
            options = [
                discord.SelectOption(label="Propozycja", emoji="💡", value="propozycja", description="Zaproponuj zmianę na serwerze"),
                discord.SelectOption(label="Błąd", emoji="🐛", value="blad", description="Zgłoś błąd na serwerze"),
            ]
        elif view_type == "complaints_appeals":
            placeholder = "Wybierz akcję (skargi i odwołania)..."
            options = [
                discord.SelectOption(label="Skarga", emoji="⚠️", value="Skarga", description="Złóż skargę na gracza lub admina"),
                discord.SelectOption(label="Odwołanie", emoji="🔓", value="Odwołanie", description="Odwołaj się od kary"),
            ]
        elif view_type == "recruitment":
            placeholder = "Wybierz stanowisko, na które aplikujesz..."
            options = []
            for position in ADMIN_RECRUITMENT_TYPES:
                options.append(discord.SelectOption(label=position, value=position, emoji="📋"))
        elif view_type == "creative_recruitment":
            placeholder = "Wybierz stanowisko, na które aplikujesz..."
            options = []
            for position in CREATIVE_RECRUITMENT_TYPES:
                options.append(discord.SelectOption(label=position, value=position, emoji="🎨"))

        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=custom_id)
        self.view_type = view_type

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        # Propozycje i błędy - pokaż wybór serwera
        if choice in ["propozycja", "blad"]:
            view = ServerSelectionView(post_type=choice)
            embed = discord.Embed(
                title="🖥️ Wybierz serwer",
                description="Na którym serwerze chcesz zgłosić propozycję/błąd?",
                color=COLORS["main"]
            )
            if LOGO_URL:
                embed.set_thumbnail(url=LOGO_URL)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        # Skargi i odwołania
        if choice == "Skarga":
            await interaction.response.send_modal(ComplaintModal("Skarga"))
            return
        if choice == "Odwołanie":
            await interaction.response.send_modal(AppealModal("Odwołanie"))
            return

        # Rekrutacje - sprawdź czy otwarta
        if choice in ALL_RECRUITMENT_TYPES:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT is_open FROM recruitment_status WHERE position = ?", (choice,)) as cursor:
                    status = await cursor.fetchone()
            is_open = status[0] if status else 1

            if not is_open:
                await interaction.response.send_message("❌ Rekrutacja na to stanowisko jest obecnie zamknięta.", ephemeral=True)
                return

            # Mapa modali
            modal_map = {
                "Podanie Admin JB": lambda: ServerAdminApplicationModal("Podanie Admin JB"),
                "Podanie Zaufany JB": TrustedApplicationModal,
                "Podanie Admin DC": DiscordAdminApplicationModal,
                "Podanie Admin Supermoce": lambda: ServerAdminApplicationModal("Podanie Admin Supermoce"),
                "Podanie Admin Surf + RPG": lambda: ServerAdminApplicationModal("Podanie Admin Surf + RPG"),
                "Podanie Admin DR": lambda: ServerAdminApplicationModal("Podanie Admin DR"),
                "Podanie Admin Projekt RPG": lambda: ServerAdminApplicationModal("Podanie Admin Projekt RPG"),
                "Podanie Developer": DeveloperApplicationModal,
                "Podanie MapDeveloper": MapDeveloperApplicationModal,
                "Podanie Grafik": GraphicDesignerApplicationModal,
                "Podanie Redaktor": EditorApplicationModal
            }

            requirements_map = {
                "Podanie Admin JB": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
                "Podanie Zaufany JB": "• Minimum 14 lat\n• Aktywność na serwerze",
                "Podanie Admin DC": "• Doświadczenie z Discordem\n• Aktywność na serwerze Discord",
                "Podanie Admin Supermoce": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
                "Podanie Admin Surf + RPG": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
                "Podanie Admin DR": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
                "Podanie Admin Projekt RPG": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
                "Podanie Redaktor": "• Minimum 16 lat\n• Bardzo dobra znajomość języka polskiego\n• Kreatywność\n• Gotowość do regularnego tworzenia treści"
            }

            if choice in requirements_map:
                embed = discord.Embed(title=f"📋 Wymagania - {choice}", description=requirements_map.get(choice), color=COLORS["main"])
                if LOGO_URL:
                    embed.set_thumbnail(url=LOGO_URL)
                embed.set_footer(text=FOOTER_TEXT)
                await interaction.response.send_message(embed=embed, view=RequirementsView(choice), ephemeral=True)
            elif choice in modal_map:
                modal_class = modal_map[choice]
                modal = modal_class() if callable(modal_class) else modal_class
                await interaction.response.send_modal(modal)

# --- PUNKT 3: WYBÓR SERWERA ---
class ServerSelectionView(discord.ui.View):
    def __init__(self, post_type: str):
        super().__init__(timeout=180)
        self.add_item(ServerSelect(post_type=post_type))

class ServerSelect(discord.ui.Select):
    def __init__(self, post_type: str):
        self.post_type = post_type
        options = [discord.SelectOption(label=server, value=server, emoji="🖥️") for server in SERVER_LIST]
        super().__init__(placeholder="Wybierz serwer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        server = self.values[0]
        if self.post_type == "propozycja":
            await interaction.response.send_modal(SuggestionModal(server=server))
        elif self.post_type == "blad":
            await interaction.response.send_modal(BugReportModal(server=server))

class RequirementsView(discord.ui.View):
    def __init__(self, application_type: str):
        super().__init__(timeout=180)
        self.application_type = application_type

        continue_btn = discord.ui.Button(label="Akceptuję i chcę kontynuować", style=discord.ButtonStyle.success, emoji="✅")
        continue_btn.callback = self.continue_callback
        self.add_item(continue_btn)

        # Dodaj przycisk statystyk dla serwerów gier
        game_server_types = ["Podanie Admin JB", "Podanie Zaufany JB", "Podanie Admin Supermoce", "Podanie Admin Surf + RPG", "Podanie Admin DR", "Podanie Admin Projekt RPG"]
        if self.application_type in game_server_types:
            stats_btn = discord.ui.Button(label="Statystyki serwera", style=discord.ButtonStyle.link, url="https://tsarvar.com/pl/servers/counter-strike2/91.224.117.153:27015", emoji="📊")
            self.add_item(stats_btn)

    async def continue_callback(self, interaction: discord.Interaction):
        modal_map = {
            "Podanie Admin JB": lambda: ServerAdminApplicationModal("Podanie Admin JB"),
            "Podanie Zaufany JB": TrustedApplicationModal,
            "Podanie Admin DC": DiscordAdminApplicationModal,
            "Podanie Admin Supermoce": lambda: ServerAdminApplicationModal("Podanie Admin Supermoce"),
            "Podanie Admin Surf + RPG": lambda: ServerAdminApplicationModal("Podanie Admin Surf + RPG"),
            "Podanie Admin DR": lambda: ServerAdminApplicationModal("Podanie Admin DR"),
            "Podanie Admin Projekt RPG": lambda: ServerAdminApplicationModal("Podanie Admin Projekt RPG"),
            "Podanie Developer": DeveloperApplicationModal,
            "Podanie MapDeveloper": MapDeveloperApplicationModal,
            "Podanie Grafik": GraphicDesignerApplicationModal,
            "Podanie Redaktor": EditorApplicationModal
        }
        if self.application_type in modal_map:
            modal_class = modal_map[self.application_type]
            modal = modal_class() if callable(modal_class) else modal_class
            await interaction.response.send_modal(modal)
        self.stop()

# --- MENU ZARZĄDZANIA I SZABLONÓW ---
class ManagementView(discord.ui.View):
    def __init__(self, post_type: str, author_id: int, is_in_progress: bool = False):
        super().__init__(timeout=None)
        self.post_type, self.author_id = post_type, author_id
        self.add_item(ManagementSelect(post_type=post_type, custom_id=f"persistent_management_select_{post_type.replace(' ', '_')}", is_in_progress=is_in_progress))

class ManagementSelect(discord.ui.Select):
    def __init__(self, post_type: str, custom_id: str, is_in_progress: bool = False):
        self.post_type = post_type
        options = []
        if is_in_progress:
            options = [
                discord.SelectOption(label="Błąd naprawiony", value="resolve_bug", emoji="✅"),
                discord.SelectOption(label="Odrzuć zgłoszenie", value="reject_bug", emoji="❌")]
        else:
            options_map = {
                "Podanie": [
                    discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_application", emoji="✅"),
                    discord.SelectOption(label="Rozpatrz negatywnie", value="reject_application", emoji="❌")],
                "Propozycja": [
                    discord.SelectOption(label="Przyjmij propozycję", value="accept_suggestion", emoji="✅"),
                    discord.SelectOption(label="Odrzuć propozycję", value="reject_suggestion", emoji="❌")],
                "Błąd": [
                    discord.SelectOption(label="Błąd przyjęty do naprawy", value="accept_bug", emoji="🔧"),
                    discord.SelectOption(label="Odrzuć zgłoszenie", value="reject_bug", emoji="❌")],
                "Skarga": [
                    discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_complaint", emoji="✅"),
                    discord.SelectOption(label="Odrzuć skargę", value="reject_complaint", emoji="❌")],
                "Odwołanie": [
                    discord.SelectOption(label="Zaakceptuj odwołanie", value="accept_appeal", emoji="✅"),
                    discord.SelectOption(label="Odrzuć odwołanie", value="reject_appeal", emoji="❌")]}
            chosen_key = next((key for key in options_map if self.post_type.startswith(key)), None)
            options = options_map.get(chosen_key, [])

        super().__init__(placeholder="Wybierz akcję zarządczą...", min_values=1, max_values=1, options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        if not has_permission_for_type(interaction.user, self.post_type):
            await interaction.response.send_message("❌ Nie masz uprawnień!", ephemeral=True)
            return

        action = self.values[0]
        if action in RESPONSE_TEMPLATES:
            view = TemplateReasonView(original_interaction=interaction, action=action, post_type=self.post_type, author_id=self.view.author_id)
            await interaction.response.send_message("Wybierz szablon odpowiedzi lub wpisz własny powód.", view=view, ephemeral=True)
        else:
            await interaction.response.send_modal(DecisionReasonModal(original_interaction=interaction, action=action, post_type=self.post_type, author_id=self.view.author_id))

class TemplateReasonView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction, action: str, post_type: str, author_id: int):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.action = action
        self.post_type = post_type
        self.author_id = author_id

        templates = RESPONSE_TEMPLATES.get(action, [])
        options = [discord.SelectOption(label=t[:100]) for t in templates]

        self.select_menu = discord.ui.Select(placeholder="Wybierz gotowy szablon odpowiedzi...", options=options)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reason_text = self.select_menu.values[0]
        await process_decision(interaction, self.original_interaction, self.action, self.post_type, self.author_id, reason_text)
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(content="✅ Decyzja została podjęta.", view=self)

    @discord.ui.button(label="Inny powód (wpisz ręcznie)", style=discord.ButtonStyle.secondary)
    async def custom_reason_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DecisionReasonModal(original_interaction=self.original_interaction, action=self.action, post_type=self.post_type, author_id=self.author_id)
        await interaction.response.send_modal(modal)
        self.stop()

# --- SYSTEM ANKIET ---
class PollView(discord.ui.View):
    def __init__(self, options: list, message_id: int = 0):
        super().__init__(timeout=None)
        self.message_id = message_id
        for i, option_text in enumerate(options):
            self.add_item(PollButton(label=option_text, custom_id=f"poll_{message_id}_{i}"))

class PollButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message_id = int(self.custom_id.split('_')[1])
        button_index = int(self.custom_id.split('_')[2])

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT votes FROM polls WHERE message_id = ?", (message_id,)) as cursor:
                votes_json = await cursor.fetchone()
            if not votes_json:
                return

            votes = json.loads(votes_json[0])
            voter_id_str = str(interaction.user.id)

            for option_votes in votes.values():
                if voter_id_str in option_votes:
                    option_votes.remove(voter_id_str)

            votes[str(button_index)].append(voter_id_str)
            await db.execute("UPDATE polls SET votes = ? WHERE message_id = ?", (json.dumps(votes), message_id))
            await db.commit()

            async with db.execute("SELECT question, options, author_id FROM polls WHERE message_id = ?", (message_id,)) as cursor:
                poll_data = await cursor.fetchone()

        question, options, author_id = poll_data
        options = json.loads(options)
        author = interaction.guild.get_member(author_id) or await bot.fetch_user(author_id)

        new_embed = discord.Embed(title="📊 Ankieta", description=f"**{question}**", color=COLORS["main"])
        for i, option_text in enumerate(options):
            voter_ids = votes.get(str(i), [])
            voter_mentions = [f"<@{uid}>" for uid in voter_ids]
            value_text = "\n".join(voter_mentions) if voter_mentions else "Brak głosów"
            if len(value_text) > 1024:
                value_text = value_text[:1020] + "\n..."
            new_embed.add_field(name=f"{option_text} ({len(voter_ids)})", value=value_text, inline=False)
        new_embed.set_footer(text=f"Ankieta stworzona przez: {author.display_name} | {FOOTER_TEXT}")
        if LOGO_URL:
            new_embed.set_thumbnail(url=LOGO_URL)

        await interaction.edit_original_response(embed=new_embed)

# --- SYSTEM SKLEPU ---
async def create_shop_embed(category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, name, cost, description, stock FROM shop_items WHERE category = ? ORDER BY cost ASC", (category,)) as cursor:
            items = await cursor.fetchall()

    embed = discord.Embed(title=f"🛒 Sklep - Kategoria: {category}", color=COLORS["main"])
    if not items:
        embed.description = "Brak przedmiotów w tej kategorii."
    else:
        description = ""
        for item_id, name, cost, desc, stock in items:
            stock_info = ""
            if stock is not None:
                if stock > 0:
                    stock_info = f" (Pozostało: {stock} szt.)"
                else:
                    stock_info = " (Wyprzedane)"
            description += f"**ID: {item_id} | {name}{stock_info}** - `{cost} rep.`\n*_{desc}_*\n\n"
        embed.description = description
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    return embed

class ShopView(discord.ui.View):
    def __init__(self, initial_category: Optional[str] = None):
        super().__init__(timeout=None)
        self.add_item(ShopCategorySelect())
        if initial_category:
            self.add_item(ShopItemSelect(category=initial_category))

class ShopCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=cat, value=cat) for cat in SHOP_CATEGORIES]
        super().__init__(placeholder="Wybierz kategorię sklepu...", min_values=1, max_values=1, options=options, custom_id="shop_category_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_category = self.values[0]
        new_embed = await create_shop_embed(selected_category)
        new_view = ShopView(initial_category=selected_category)
        await interaction.edit_original_response(embed=new_embed, view=new_view)

class ShopItemSelect(discord.ui.Select):
    def __init__(self, category: str):
        super().__init__(placeholder="Wybierz przedmiot, który chcesz kupić...", min_values=1, max_values=1, custom_id="shop_item_select")
        self.category = category
        # Items will be loaded when callback is called
        self.options = [discord.SelectOption(label="Ładowanie...", value="loading")]

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "loading":
            await interaction.response.send_message("⏳ Proszę wybrać kategorię ponownie.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        item_id = int(self.values[0])

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name, cost, role_id, stock, category FROM shop_items WHERE id = ?", (item_id,)) as cursor:
                item = await cursor.fetchone()

            if not item:
                await interaction.followup.send("❌ Przedmiot nie znaleziony.", ephemeral=True)
                return

            item_name, item_cost, role_id, stock, category = item

            if stock is not None and stock <= 0:
                await interaction.followup.send("❌ Ten przedmiot jest już wyprzedany!", ephemeral=True)
                return

            if category == "Specjalne role":
                async with db.execute("SELECT 1 FROM shop_purchases WHERE user_id = ? AND item_id = ?", (interaction.user.id, item_id)) as cursor:
                    if await cursor.fetchone():
                        await interaction.followup.send("❌ Już posiadasz ten unikalny przedmiot!", ephemeral=True)
                        return

            async with db.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(interaction.user.id),)) as cursor:
                user_points_row = await cursor.fetchone()
            user_points = user_points_row[0] if user_points_row else 0

            if user_points < item_cost:
                await interaction.followup.send(f"❌ Nie masz wystarczającej reputacji! Potrzebujesz **{item_cost}**, a masz **{user_points}**.", ephemeral=True)
                return

            new_points = user_points - item_cost
            await db.execute("UPDATE reputation_points SET points = ? WHERE user_id = ?", (new_points, str(interaction.user.id)))

            if stock is not None:
                await db.execute("UPDATE shop_items SET stock = stock - 1 WHERE id = ?", (item_id,))

            if category == "Specjalne role":
                await db.execute("INSERT INTO shop_purchases (user_id, item_id) VALUES (?, ?)", (interaction.user.id, item_id))

            await db.commit()

        if role_id:
            try:
                role_to_add = interaction.guild.get_role(role_id)
                if role_to_add:
                    await interaction.user.add_roles(role_to_add, reason="Zakup w sklepie reputacji")
                    await interaction.followup.send(f"✅ Gratulacje! Kupiłeś i otrzymałeś rolę **{item_name}** za **{item_cost}** reputacji. Twoje saldo: **{new_points}** rep.", ephemeral=True)
                else:
                    raise ValueError("Rola nie znaleziona")
            except Exception as e:
                print(f"Błąd podczas nadawania roli ze sklepu: {e}")
                await interaction.followup.send(f"⚠️ Zakupiono **{item_name}**, ale wystąpił błąd przy nadawaniu roli. Administracja została powiadomiona.", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ Gratulacje! Kupiłeś **{item_name}** za **{item_cost}** reputacji. Twoje saldo: **{new_points}** rep.\nAdministracja została powiadomiona.", ephemeral=True)
            if SHOP_CONFIG.get("channel_id") and category in ["VIP", "Premium", "Fajki", "Oferty Dnia"]:
                notif_channel = bot.get_channel(SHOP_CONFIG["channel_id"])
                if notif_channel:
                    roles_to_mention = [discord.utils.get(interaction.guild.roles, name=r_name) for r_name in SHOP_CONFIG["manual_reward_roles"]]
                    role_mentions = " ".join([r.mention for r in roles_to_mention if r])
                    embed = discord.Embed(title="🛍️ Nowy zakup w sklepie!", color=COLORS["success"], timestamp=datetime.now(POLAND_TZ))
                    embed.add_field(name="Kupujący", value=interaction.user.mention, inline=False)
                    embed.add_field(name="Przedmiot", value=f"{item_name} (ID: {item_id})", inline=False)
                    embed.add_field(name="Koszt", value=f"{item_cost} reputacji", inline=False)
                    embed.set_footer(text=FOOTER_TEXT)
                    embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    await notif_channel.send(content=role_mentions, embed=embed)

        await log_action(interaction.guild, "Zakup w sklepie", interaction.user, f"Przedmiot: {item_name}, Koszt: {item_cost} rep.")

# --- GRUPA KOMEND SLASH ---
reputation_group = app_commands.Group(name="reputacja", description="Zarządzanie reputacją użytkowników.")
recruitment_group = app_commands.Group(name="rekrutacja", description="Zarządzanie statusami rekrutacji.")
announcement_group = app_commands.Group(name="ogloszenie", description="Zarządzanie ogłoszeniami i eventami.")
redakcja_group = app_commands.Group(name="redakcja", description="Komendy dla działu redakcji.")

# --- KOMENDY SLASH ---
@bot.tree.command(name="setup_logi", description="Konfiguruje kanał logów bota.")
async def setup_logi(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Kanał logów został ustawiony na {kanal.mention}.", ephemeral=True)
    await log_action(interaction.guild, "Skonfigurowano logi", interaction.user, f"Kanał: {kanal.mention}")

@bot.tree.command(name="setup_powiadomienia", description="Konfiguruje powiadomienia dla opiekunów.")
async def setup_powiadomienia(interaction: discord.Interaction, typ_zgloszenia: str, kanal: discord.TextChannel, rola: Optional[discord.Role] = None):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    NOTIFICATION_CONFIG[typ_zgloszenia] = {'channel_id': kanal.id, 'role_id': rola.id if rola else None}
    await interaction.response.send_message(f"✅ Ustawiono powiadomienia dla `{typ_zgloszenia}` na kanale {kanal.mention}" + (f" z rolą {rola.mention}." if rola else "."), ephemeral=True)

@bot.tree.command(name="setup_przypomnienia", description="Włącza lub wyłącza automatyczne przypomnienia.")
async def setup_przypomnienia(interaction: discord.Interaction, wlaczone: bool, dni: app_commands.Range[int, 1, 30] = 3):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    REMINDER_CONFIG["enabled"] = wlaczone
    REMINDER_CONFIG["delay_days"] = dni
    status = "włączone" if wlaczone else "wyłączone"
    await interaction.response.send_message(f"✅ Automatyczne przypomnienia zostały **{status}**. Czas oczekiwania: **{dni} dni**.", ephemeral=True)

@bot.tree.command(name="setup_forum_propozycje", description="Tworzy panel zgłaszania propozycji i błędów.")
async def setup_forum_propozycje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    embed = discord.Embed(title="💡 Propozycje i Błędy 🐛", description="Masz pomysł na ulepszenie serwera lub znalazłeś błąd?\nWybierz opcję z menu poniżej, a następnie wybierz serwer!", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Zgłoszeń - Propozycje i Błędy", embed=embed, view=ForumSelectionView("proposals_bugs"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="setup_forum_skargi", description="Tworzy panel składania skarg i odwołań.")
async def setup_forum_skargi(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    embed = discord.Embed(title="⚠️ Skargi i Odwołania 🔓", description="Chcesz złożyć skargę lub odwołać się od kary? Użyj menu poniżej.", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Zgłoszeń - Skargi i Odwołania", embed=embed, view=ForumSelectionView("complaints_appeals"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="setup_forum_rekrutacje", description="Tworzy panel rekrutacyjny dla ról admin.")
async def setup_forum_rekrutacje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    embed = discord.Embed(title="📋 Centrum Rekrutacji Administracji", description="Chcesz dołączyć do ekipy administracyjnej? Wybierz stanowisko z menu poniżej.", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Rekrutacyjny - Administracja", embed=embed, view=ForumSelectionView("recruitment"))
    await interaction.response.send_message(f"✅ Panel rekrutacyjny został utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="setup_forum_rekrutacje_kreatywne", description="Tworzy panel rekrutacyjny dla ról kreatywnych.")
async def setup_forum_rekrutacje_kreatywne(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, CREATIVE_RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    embed = discord.Embed(title="🎨 Centrum Rekrutacji Kreatywnej", description="Chcesz dołączyć do ekipy kreatywnej? Wybierz stanowisko z menu poniżej.", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Rekrutacyjny - Role Kreatywne", embed=embed, view=ForumSelectionView("creative_recruitment"))
    await interaction.response.send_message(f"✅ Panel rekrutacji kreatywnej został utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="info", description="Wyświetla informacje o aktywności użytkownika.")
async def info(interaction: discord.Interaction, uzytkownik: discord.Member):
    await interaction.response.defer(ephemeral=True)
    async with aiosqlite.connect(DB_PATH) as db:
        embed = discord.Embed(title=f"📋 Kartoteka: {uzytkownik.display_name}", color=uzytkownik.color, timestamp=datetime.now(POLAND_TZ))
        embed.set_thumbnail(url=uzytkownik.display_avatar.url)

        async with db.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(uzytkownik.id),)) as cursor:
            rep = await cursor.fetchone()
        embed.add_field(name="⭐ Reputacja", value=rep[0] if rep else "0", inline=False)

        tables = {"applications": "Podania", "suggestions": "Propozycje", "bug_reports": "Błędy", "complaints": "Skargi", "appeals": "Odwołania"}
        for table, name in tables.items():
            async with db.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (str(uzytkownik.id),)) as cursor:
                count_row = await cursor.fetchone()
                count = count_row[0]
            if count > 0:
                embed.add_field(name=name, value=str(count), inline=True)

    embed.set_footer(text=FOOTER_TEXT)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="moje_zgloszenia", description="Wyświetla listę Twoich zgłoszeń i ich status.")
async def moje_zgloszenia(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    async with aiosqlite.connect(DB_PATH) as db:
        embed = discord.Embed(title=f"📋 Twoje zgłoszenia", color=interaction.user.color, timestamp=datetime.now(POLAND_TZ))
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=FOOTER_TEXT)

        tables_map = {
            "Propozycje": ("suggestions", "category", "status"),
            "Błędy": ("bug_reports", "category", "status"),
            "Skargi": ("complaints", "complaint_type", "status"),
            "Odwołania": ("appeals", "appeal_type", "status"),
            "Podania": ("applications", "application_type", "status")
        }
        content = ""
        for name, (table, type_col, status_col) in tables_map.items():
            async with db.execute(f"SELECT {type_col}, {status_col}, thread_id FROM {table} WHERE user_id = ?", (str(interaction.user.id),)) as cursor:
                rows = await cursor.fetchall()
            if rows:
                content += f"**{name}**\n"
                for row in rows:
                    thread_link = f" ([Link](https://discord.com/channels/{interaction.guild.id}/{row[2]}))" if row[2] else ""
                    content += f"- `{row[0]}`: *{row[1]}*{thread_link}\n"
                content += "\n"

        embed.description = content if content else "Nie znaleziono żadnych Twoich zgłoszeń."
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ankieta", description="Tworzy ankietę z przyciskami.")
async def ankieta(interaction: discord.Interaction, pytanie: str, opcje: str):
    if not is_authorized(interaction, GENERAL_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    options_list = [opt.strip() for opt in opcje.split(';') if opt.strip()][:5]
    if len(options_list) < 2:
        await interaction.response.send_message("❌ Ankieta musi mieć co najmniej 2 opcje.", ephemeral=True)
        return

    embed = discord.Embed(title="📊 Ankieta", description=f"**{pytanie}**", color=COLORS["main"])
    for opt in options_list:
        embed.add_field(name=f"{opt} (0)", value="Brak głosów", inline=False)
    embed.set_footer(text=f"Ankieta stworzona przez: {interaction.user.display_name} | {FOOTER_TEXT}")
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)

    await interaction.response.send_message("Tworzenie ankiety...", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    view = PollView(options=options_list, message_id=message.id)
    await message.edit(view=view)

    async with aiosqlite.connect(DB_PATH) as db:
        initial_votes = json.dumps({str(i): [] for i in range(len(options_list))})
        await db.execute("INSERT INTO polls (message_id, question, options, votes, author_id) VALUES (?, ?, ?, ?, ?)",
                         (message.id, pytanie, json.dumps(options_list), initial_votes, interaction.user.id))
        await db.commit()

    await interaction.edit_original_response(content="✅ Ankieta została utworzona!")

# --- KOMENDY SKLEPU ---
@bot.tree.command(name="setup_powiadomienia_sklep", description="Konfiguruje kanał powiadomień o zakupach.")
async def setup_powiadomienia_sklep(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    SHOP_CONFIG["channel_id"] = kanal.id
    await interaction.response.send_message(f"✅ Skonfigurowano kanał powiadomień o zakupach na {kanal.mention}.", ephemeral=True)

@bot.tree.command(name="dodaj_przedmiot", description="Dodaje przedmiot do sklepu (ręczna nagroda).")
@app_commands.describe(kategoria="Kategoria przedmiotu", nazwa="Nazwa przedmiotu", koszt="Cena w reputacji", opis="Opis przedmiotu")
async def dodaj_przedmiot(interaction: discord.Interaction, kategoria: str, nazwa: str, koszt: app_commands.Range[int, 1], opis: str):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    if kategoria not in SHOP_CATEGORIES:
        await interaction.response.send_message(f"❌ Nieprawidłowa kategoria. Dostępne: {', '.join(SHOP_CATEGORIES)}", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?, ?, ?, ?, NULL, NULL)", (nazwa, koszt, opis, kategoria))
        await db.commit()
    await interaction.response.send_message(f"✅ Dodano przedmiot `{nazwa}` do kategorii `{kategoria}` za **{koszt}** reputacji.", ephemeral=True)

@bot.tree.command(name="dodaj_specjalna_role", description="Dodaje limitowaną rolę do sklepu (automatyczna).")
@app_commands.describe(nazwa="Nazwa przedmiotu", koszt="Cena w reputacji", rola="Rola do nadania", ilosc="Liczba dostępnych sztuk", opis="Opis przedmiotu")
async def dodaj_specjalna_role(interaction: discord.Interaction, nazwa: str, koszt: app_commands.Range[int, 1], rola: discord.Role, ilosc: app_commands.Range[int, 1], opis: str):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?, ?, ?, ?, ?, ?)", (nazwa, koszt, opis, "Specjalne role", rola.id, ilosc))
        await db.commit()
    await interaction.response.send_message(f"✅ Dodano rolę {rola.mention} jako `{nazwa}` ({ilosc} szt.) za **{koszt}** reputacji.", ephemeral=True)

@dodaj_przedmiot.autocomplete('kategoria')
async def dodaj_przedmiot_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=cat, value=cat) for cat in SHOP_CATEGORIES if current.lower() in cat.lower() and cat != "Specjalne role"]

@bot.tree.command(name="usun_przedmiot", description="Usuwa przedmiot ze sklepu.")
async def usun_przedmiot(interaction: discord.Interaction, id_przedmiotu: int):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM shop_items WHERE id = ?", (id_przedmiotu,))
        await db.commit()
        if cursor.rowcount > 0:
            await interaction.response.send_message(f"✅ Usunięto przedmiot o ID **{id_przedmiotu}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ Nie znaleziono przedmiotu o ID **{id_przedmiotu}**.", ephemeral=True)

@bot.tree.command(name="setup_sklep_panel", description="Tworzy interaktywny panel sklepu.")
async def setup_sklep_panel(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień do użycia tej komendy.", ephemeral=True)
        return
    embed = await create_shop_embed(SHOP_CATEGORIES[0])
    view = ShopView(initial_category=SHOP_CATEGORIES[0])
    await kanal.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Panel sklepu został utworzony na kanale {kanal.mention}.", ephemeral=True)

@bot.tree.command(name="ranking", description="Wyświetla ranking użytkowników z największą reputacją.")
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, points FROM reputation_points ORDER BY points DESC LIMIT 10") as cursor:
            top_users = await cursor.fetchall()

    embed = discord.Embed(title="🏆 Ranking Reputacji - Top 10", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)

    if not top_users:
        embed.description = "Ranking jest pusty."
    else:
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, points) in enumerate(top_users):
            user = interaction.guild.get_member(int(user_id))
            user_name = user.display_name if user else f"Użytkownik (ID: {user_id})"
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            description += f"{medal} {user_name} - `{points} rep.`\n"
        embed.description = description

    await interaction.followup.send(embed=embed)

# --- KOMENDY REPUTACJI ---
@reputation_group.command(name="dodaj", description="Dodaje reputację użytkownikowi.")
async def reputacja_dodaj(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 1]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='add')
    await interaction.response.send_message(f"✅ Dodano **{ilosc}** reputacji dla {uzytkownik.mention}. Nowe saldo: **{new_balance}** rep.", ephemeral=True)

@reputation_group.command(name="usun", description="Usuwa reputację użytkownikowi.")
async def reputacja_usun(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 1]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, -ilosc, mode='add')
    await interaction.response.send_message(f"✅ Usunięto **{ilosc}** reputacji {uzytkownik.mention}. Nowe saldo: **{new_balance}** rep.", ephemeral=True)

@reputation_group.command(name="ustaw", description="Ustawia reputację na konkretną wartość.")
async def reputacja_ustaw(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 0]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='set')
    await interaction.response.send_message(f"✅ Ustawiono reputację {uzytkownik.mention} na **{new_balance}** rep.", ephemeral=True)

# --- KOMENDY REKRUTACJI ---
@recruitment_group.command(name="otworz", description="Otwiera rekrutację na dane stanowisko.")
async def rekrutacja_otworz(interaction: discord.Interaction, stanowisko: str):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if stanowisko not in ALL_RECRUITMENT_TYPES:
        await interaction.response.send_message("❌ Nieprawidłowe stanowisko.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 1)", (stanowisko,))
        await db.commit()
    await interaction.response.send_message(f"✅ Rekrutacja na **{stanowisko}** została **otwarta**.", ephemeral=True)

@recruitment_group.command(name="zamknij", description="Zamyka rekrutację na dane stanowisko.")
async def rekrutacja_zamknij(interaction: discord.Interaction, stanowisko: str):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if stanowisko not in ALL_RECRUITMENT_TYPES:
        await interaction.response.send_message("❌ Nieprawidłowe stanowisko.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 0)", (stanowisko,))
        await db.commit()
    await interaction.response.send_message(f"✅ Rekrutacja na **{stanowisko}** została **zamknięta**.", ephemeral=True)

@rekrutacja_otworz.autocomplete('stanowisko')
@rekrutacja_zamknij.autocomplete('stanowisko')
async def rekrutacja_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=pos, value=pos) for pos in ALL_RECRUITMENT_TYPES if current.lower() in pos.lower()]

# --- KOMENDY REDAKCJI ---
@redakcja_group.command(name="pytanie_dnia", description="Publikuje nowe pytanie dnia.")
async def pytanie_dnia(interaction: discord.Interaction, kanal: discord.ForumChannel, pytanie: str):
    if not is_authorized(interaction, REDAKCJA_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO editorial_counters (type, count) VALUES ('pytanie_dnia', 0) ON CONFLICT(type) DO NOTHING")
        await db.execute("UPDATE editorial_counters SET count = count + 1 WHERE type = 'pytanie_dnia'")
        async with db.execute("SELECT count FROM editorial_counters WHERE type = 'pytanie_dnia'") as cursor:
            row = await cursor.fetchone()
            new_count = row[0]
        await db.commit()

    title = f"Pytanie dnia #{new_count}"
    embed = discord.Embed(title=f"❓ {title}", description=pytanie, color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=f"Opublikowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
    await kanal.create_thread(name=title, embed=embed)
    await interaction.followup.send("✅ Pomyślnie opublikowano pytanie dnia.", ephemeral=True)

@redakcja_group.command(name="szybki_strzal", description="Publikuje szybkie strzały.")
async def szybki_strzal(interaction: discord.Interaction, kanal: discord.ForumChannel):
    if not is_authorized(interaction, REDAKCJA_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.send_modal(QuickShotModal(channel=kanal))

@redakcja_group.command(name="wywiad", description="Publikuje wywiad.")
async def wywiad(interaction: discord.Interaction, kanal: discord.ForumChannel):
    if not is_authorized(interaction, REDAKCJA_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.send_modal(InterviewModal(channel=kanal))

@redakcja_group.command(name="qa", description="Rozpoczyna sesję Q&A.")
async def qa(interaction: discord.Interaction, kanal: discord.ForumChannel, tytul: str):
    if not is_authorized(interaction, REDAKCJA_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = discord.Embed(title=f"❓ {tytul}", description="Zapraszamy do zadawania pytań w odpowiedziach poniżej!", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=f"Sesja Q&A rozpoczęta przez: {interaction.user.display_name} | {FOOTER_TEXT}")
    await kanal.create_thread(name=tytul, embed=embed)
    await interaction.response.send_message("✅ Pomyślnie rozpoczęto sesję Q&A.", ephemeral=True)

# --- ZADANIA W TLE ---
@tasks.loop(hours=1)
async def check_for_old_posts():
    if not REMINDER_CONFIG["enabled"]:
        return

    async with aiosqlite.connect(DB_PATH) as db:
        delay = timedelta(days=REMINDER_CONFIG["delay_days"])
        time_threshold = datetime.now(POLAND_TZ) - delay

        tables_to_check = {
            "suggestions": "category", "bug_reports": "category", "complaints": "complaint_type",
            "appeals": "appeal_type", "applications": "application_type"
        }

        for table, type_col in tables_to_check.items():
            async with db.execute(f"SELECT thread_id, {type_col} FROM {table} WHERE status NOT LIKE '%odrzucon%' AND status NOT LIKE '%przyjęt%' AND status NOT LIKE '%naprawion%' AND reminder_sent = 0 AND created_at < ?", (time_threshold.strftime('%Y-%m-%d %H:%M:%S.%f'),)) as cursor:
                old_posts = await cursor.fetchall()

            for thread_id, post_type in old_posts:
                for guild in bot.guilds:
                    try:
                        thread = await guild.fetch_channel(int(thread_id))
                        if not thread.locked:
                            await send_notification(guild, post_type, thread.jump_url, is_reminder=True)
                            await db.execute(f"UPDATE {table} SET reminder_sent = 1 WHERE thread_id = ?", (thread_id,))
                            await db.commit()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        continue

# --- EVENTY BOTA ---
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}!')
    await init_database()

    bot.add_view(ForumSelectionView("proposals_bugs"))
    bot.add_view(ForumSelectionView("complaints_appeals"))
    bot.add_view(ForumSelectionView("recruitment"))
    bot.add_view(ForumSelectionView("creative_recruitment"))
    bot.add_view(ShopView())
    bot.add_view(EventView())

    post_types = ["Propozycja", "Błąd", "Skarga", "Odwołanie"] + ALL_RECRUITMENT_TYPES
    for post_type in post_types:
        bot.add_view(ManagementView(post_type, author_id=0))

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT message_id, options FROM polls") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                message_id, options_json = row
                options = json.loads(options_json)
                bot.add_view(PollView(options, message_id))

    bot.tree.add_command(reputation_group)
    bot.tree.add_command(recruitment_group)
    bot.tree.add_command(announcement_group)
    bot.tree.add_command(redakcja_group)
    check_for_old_posts.start()

    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

# --- URUCHOMIENIE BOTA ---
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! BRAK TOKENA! Ustaw zmienną DISCORD_BOT_TOKEN    !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
else:
    bot.run(TOKEN)
