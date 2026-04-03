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

# --- LISTA SERWERÓW ---
SERVER_LIST = [
    "JailBreak",
    "Supermoce",
    "Surf + RPG",
    "DeathRun",
    "Projekt RPG",
    "Discord",
    "Inne"
]

# --- TYPY REKRUTACJI ---
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

# --- MAPOWANIE TAGÓW (PUNKT 2 - automatyczne tagi) ---
TAG_MAPPING = {
    # Propozycje
    "Propozycja JailBreak":      "Propozycja JailBreak",
    "Propozycja Supermoce":      "Propozycja Supermoce",
    "Propozycja Surf + RPG":     "Propozycja Surf + RPG",
    "Propozycja DeathRun":       "Propozycja DeathRun",
    "Propozycja Projekt RPG":    "Propozycja Projekt RPG",
    "Propozycja Discord":        "Propozycja Discord",
    "Propozycja Inne":           "Propozycja Inne",
    # Błędy
    "Błąd JailBreak":            "Błąd JailBreak",
    "Błąd Supermoce":            "Błąd Supermoce",
    "Błąd Surf + RPG":           "Błąd Surf + RPG",
    "Błąd DeathRun":             "Błąd DeathRun",
    "Błąd Projekt RPG":          "Błąd Projekt RPG",
    "Błąd Discord":              "Błąd Discord",
    "Błąd Inne":                 "Błąd Inne",
    # Skargi
    "Skarga JailBreak":          "Skarga JailBreak",
    "Skarga Supermoce":          "Skarga Supermoce",
    "Skarga Surf + RPG":         "Skarga Surf + RPG",
    "Skarga DeathRun":           "Skarga DeathRun",
    "Skarga Projekt RPG":        "Skarga Projekt RPG",
    "Skarga Discord":            "Skarga Discord",
    "Skarga Inne":               "Skarga Inne",
    # Odwołania
    "Odwołanie JailBreak":       "Odwołanie JailBreak",
    "Odwołanie Supermoce":       "Odwołanie Supermoce",
    "Odwołanie Surf + RPG":      "Odwołanie Surf + RPG",
    "Odwołanie DeathRun":        "Odwołanie DeathRun",
    "Odwołanie Projekt RPG":     "Odwołanie Projekt RPG",
    "Odwołanie Discord":         "Odwołanie Discord",
    "Odwołanie Inne":            "Odwołanie Inne",
    # Podania Admin
    "Podanie Admin JB":          "Podanie Admin JB",
    "Podanie Admin Supermoce":   "Podanie Admin Supermoce",
    "Podanie Admin Surf + RPG":  "Podanie Admin Surf + RPG",
    "Podanie Admin DR":          "Podanie Admin DR",
    "Podanie Admin Projekt RPG": "Podanie Admin Projekt RPG",
    "Podanie Admin DC":          "Podanie Admin DC",
    # Podania Zaufany
    "Podanie Zaufany JB":        "Podanie Zaufany JB",
    # Podania kreatywne
    "Podanie Developer":         "Podanie Developer",
    "Podanie MapDeveloper":      "Podanie MapDeveloper",
    "Podanie Grafik":            "Podanie Grafik",
    "Podanie Redaktor":          "Podanie Redaktor",
}

# Tagi statusu (punkt 4)
STATUS_TAG_NAMES = {
    "pending":      "Oczekuje",
    "in_progress":  "W trakcie",
    "closed":       "Zamknięte",
}

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

# =========================================================
# --- BAZA DANYCH ---
# =========================================================
async def init_database():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, username TEXT NOT NULL,
                category TEXT NOT NULL, description TEXT NOT NULL,
                reason TEXT NOT NULL, server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, category TEXT NOT NULL,
                bug_type TEXT NOT NULL, description TEXT NOT NULL,
                evidence TEXT, server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'reported',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, complaint_type TEXT NOT NULL,
                target_user TEXT NOT NULL, data TEXT NOT NULL,
                server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, appeal_type TEXT NOT NULL,
                data TEXT NOT NULL, server TEXT DEFAULT 'Nieokreślony',
                thread_id TEXT, status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL, username TEXT NOT NULL,
                application_type TEXT NOT NULL, data TEXT NOT NULL,
                thread_id TEXT, status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reputation_points (
                user_id TEXT PRIMARY KEY, points INTEGER DEFAULT 0
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS polls (
                message_id INTEGER PRIMARY KEY, question TEXT NOT NULL,
                options TEXT NOT NULL, votes TEXT NOT NULL, author_id INTEGER NOT NULL
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS shop_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, description TEXT,
                cost INTEGER NOT NULL, category TEXT NOT NULL,
                role_id INTEGER DEFAULT NULL, stock INTEGER DEFAULT NULL
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
                message_id INTEGER PRIMARY KEY,
                author_id INTEGER NOT NULL, attendees TEXT NOT NULL
            )''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS editorial_counters (
                type TEXT PRIMARY KEY, count INTEGER DEFAULT 0
            )''')

        # --- PUNKT 1: Tabela cooldownów na podania ---
        await db.execute('''
            CREATE TABLE IF NOT EXISTS application_cooldowns (
                user_id TEXT NOT NULL,
                application_type TEXT NOT NULL,
                rejected_at TIMESTAMP NOT NULL,
                PRIMARY KEY (user_id, application_type)
            )''')

        # --- PUNKT 2: Tabela paneli rekrutacji do odświeżania ---
        await db.execute('''
            CREATE TABLE IF NOT EXISTS recruitment_panels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                panel_type TEXT NOT NULL
            )''')

        # Dodaj kolumny jeśli nie istnieją (migracja)
        migrations = [
            ("suggestions",  "reminder_sent INTEGER DEFAULT 0"),
            ("bug_reports",  "reminder_sent INTEGER DEFAULT 0"),
            ("complaints",   "reminder_sent INTEGER DEFAULT 0"),
            ("appeals",      "reminder_sent INTEGER DEFAULT 0"),
            ("applications", "reminder_sent INTEGER DEFAULT 0"),
            ("suggestions",  "server TEXT DEFAULT 'Nieokreślony'"),
            ("bug_reports",  "server TEXT DEFAULT 'Nieokreślony'"),
            ("complaints",   "server TEXT DEFAULT 'Nieokreślony'"),
            ("appeals",      "server TEXT DEFAULT 'Nieokreślony'"),
        ]
        for table, col_def in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            except Exception:
                pass

        await db.commit()

# =========================================================
# --- FUNKCJE POMOCNICZE BAZY DANYCH ---
# =========================================================
async def save_suggestion(user_id, username, category, description, reason, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO suggestions (user_id,username,category,description,reason,server,thread_id) VALUES (?,?,?,?,?,?,?)',
            (user_id, username, category, description, reason, server, thread_id))
        await db.commit()

async def save_bug_report(user_id, category, bug_type, description, evidence, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO bug_reports (user_id,category,bug_type,description,evidence,server,thread_id) VALUES (?,?,?,?,?,?,?)',
            (user_id, category, bug_type, description, evidence, server, thread_id))
        await db.commit()

async def save_complaint(user_id, complaint_type, target_user, data, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO complaints (user_id,complaint_type,target_user,data,server,thread_id) VALUES (?,?,?,?,?,?)',
            (user_id, complaint_type, target_user, json.dumps(data), server, thread_id))
        await db.commit()

async def save_appeal(user_id, appeal_type, data, server, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO appeals (user_id,appeal_type,data,server,thread_id) VALUES (?,?,?,?,?)',
            (user_id, appeal_type, json.dumps(data), server, thread_id))
        await db.commit()

async def save_application(user_id, username, app_type, data, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO applications (user_id,username,application_type,data,thread_id) VALUES (?,?,?,?,?)',
            (user_id, username, app_type, json.dumps(data), thread_id))
        await db.commit()

async def update_reputation(user_id: int, points: int, mode: str = 'add'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO reputation_points (user_id, points) VALUES (?, 0)", (str(user_id),))
        if mode == 'add':
            await db.execute(
                "UPDATE reputation_points SET points = points + ? WHERE user_id = ?", (points, str(user_id)))
        elif mode == 'set':
            await db.execute(
                "UPDATE reputation_points SET points = ? WHERE user_id = ?", (points, str(user_id)))
        await db.commit()
        async with db.execute(
            "SELECT points FROM reputation_points WHERE user_id = ?", (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            return row[0]

# =========================================================
# --- PUNKT 1: COOLDOWN NA PODANIA ---
# =========================================================
COOLDOWN_DAYS = 7

async def check_application_cooldown(user_id: str, app_type: str) -> Optional[datetime]:
    """
    Zwraca datę końca cooldownu jeśli aktywny, None jeśli brak.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT rejected_at FROM application_cooldowns WHERE user_id = ? AND application_type = ?",
            (user_id, app_type)) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    rejected_at = datetime.fromisoformat(row[0])
    if rejected_at.tzinfo is None:
        rejected_at = POLAND_TZ.localize(rejected_at)
    cooldown_end = rejected_at + timedelta(days=COOLDOWN_DAYS)
    now = datetime.now(POLAND_TZ)
    if now < cooldown_end:
        return cooldown_end
    # Cooldown minął - usuń wpis
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM application_cooldowns WHERE user_id = ? AND application_type = ?",
            (user_id, app_type))
        await db.commit()
    return None

async def set_application_cooldown(user_id: str, app_type: str):
    """Ustawia cooldown po odrzuceniu podania."""
    now = datetime.now(POLAND_TZ).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO application_cooldowns (user_id, application_type, rejected_at) VALUES (?,?,?)",
            (user_id, app_type, now))
        await db.commit()

async def remove_application_cooldown(user_id: str, app_type: str):
    """Zdejmuje cooldown z użytkownika."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM application_cooldowns WHERE user_id = ? AND application_type = ?",
            (user_id, app_type))
        await db.commit()

# =========================================================
# --- PUNKT 3: ANTYSPAM PODAŃ ---
# =========================================================
async def check_active_application(user_id: str, app_type: str) -> bool:
    """
    Zwraca True jeśli użytkownik ma już aktywne (nierozpatrzone) podanie tego typu.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM applications WHERE user_id = ? AND application_type = ? AND status = 'pending'",
            (user_id, app_type)) as cursor:
            row = await cursor.fetchone()
    return row is not None

# =========================================================
# --- FUNKCJE POMOCNICZE ---
# =========================================================
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
    elif any(x in item_lower for x in ["skarga", "odwołanie", "propozycja", "błąd"]):
        return any(role.name in ["Opiekun JB", "Opiekun Discord", "Zarząd", "Właściciel"] for role in user.roles)
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
    title = f"⏰ Przypomnienie: {post_type}" if is_reminder else f"🔔 Nowe zgłoszenie: {post_type}"
    description = (
        f"Zgłoszenie czeka na reakcję od ponad {REMINDER_CONFIG['delay_days']} dni.\n\n[Przejdź do posta]({thread_url})"
        if is_reminder else
        f"Nowy post czeka na Twoją uwagę.\n\n[Przejdź do posta]({thread_url})"
    )
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

# =========================================================
# --- PUNKT 2: TAGI - FUNKCJE POMOCNICZE ---
# =========================================================
def find_tag(forum_channel, tag_name: str) -> Optional[discord.ForumTag]:
    tag = discord.utils.get(forum_channel.available_tags, name=tag_name)
    if tag:
        return tag
    for available_tag in forum_channel.available_tags:
        if tag_name.lower() in available_tag.name.lower() or available_tag.name.lower() in tag_name.lower():
            return available_tag
    return None

def get_tag_name_for_post(post_type: str, server: str = None) -> str:
    if server and server != "Nieokreślony":
        full_tag = f"{post_type} {server}"
        if full_tag in TAG_MAPPING:
            return TAG_MAPPING[full_tag]
        server_map = {"JailBreak": "JB", "DeathRun": "DR"}
        short_server = server_map.get(server, server)
        full_tag_short = f"{post_type} {short_server}"
        if full_tag_short in TAG_MAPPING:
            return TAG_MAPPING[full_tag_short]
        return full_tag
    else:
        return TAG_MAPPING.get(post_type, post_type)

# =========================================================
# --- PUNKT 4: ZARZĄDZANIE TAGAMI STATUSU ---
# =========================================================
async def update_thread_status_tag(thread: discord.Thread, new_status: str):
    """
    Aktualizuje tag statusu wątku (Oczekuje/W trakcie/Zamknięte).
    new_status: 'pending' | 'in_progress' | 'closed'
    """
    try:
        forum = thread.parent
        if not isinstance(forum, discord.ForumChannel):
            return

        status_tag_name = STATUS_TAG_NAMES.get(new_status)
        if not status_tag_name:
            return

        new_status_tag = find_tag(forum, status_tag_name)

        # Usuń stare tagi statusu, zachowaj tagi typów
        status_tag_names_all = set(STATUS_TAG_NAMES.values())
        current_tags = [t for t in thread.applied_tags if t.name not in status_tag_names_all]

        if new_status_tag:
            current_tags.append(new_status_tag)

        # Discord limit: max 5 tagów
        current_tags = current_tags[:5]

        await thread.edit(applied_tags=current_tags)
    except Exception as e:
        print(f"Błąd podczas aktualizacji tagu statusu: {e}")

# =========================================================
# --- PUNKT 2: BUDOWANIE EMBEDU PANELU REKRUTACJI ---
# =========================================================
async def build_recruitment_embed(panel_type: str) -> discord.Embed:
    """
    Buduje embed panelu rekrutacji z aktualnym statusem stanowisk.
    panel_type: 'recruitment' | 'creative_recruitment'
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT position, is_open FROM recruitment_status") as cursor:
            rows = await cursor.fetchall()
    status_map = {row[0]: row[1] for row in rows}

    if panel_type == "recruitment":
        title = "🛡️ Centrum Rekrutacji Administracji"
        description_lines = [
            "Chcesz dołączyć do ekipy administracyjnej?\n",
            "**Podanie Admin** → wybierz serwer po kliknięciu",
            "**Podanie Zaufany JB** → tylko dla JailBreak\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "**Status stanowisk:**\n",
        ]
        positions = ADMIN_RECRUITMENT_TYPES
    else:
        title = "🎨 Centrum Rekrutacji Kreatywnej"
        description_lines = [
            "Chcesz dołączyć do ekipy kreatywnej?\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "**Status stanowisk:**\n",
        ]
        positions = CREATIVE_RECRUITMENT_TYPES

    for pos in positions:
        is_open = status_map.get(pos, 1)
        # Emoji zamiast koloru (Discord nie wspiera kolorowych tagów w embedzie)
        status_emoji = "🟢" if is_open else "🔴"
        status_text = "Otwarta" if is_open else "Zamknięta"
        description_lines.append(f"{status_emoji} **{pos}** — {status_text}")

    embed = discord.Embed(
        title=title,
        description="\n".join(description_lines),
        color=COLORS["main"],
        timestamp=datetime.now(POLAND_TZ)
    )
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=f"Ostatnia aktualizacja | {FOOTER_TEXT}")
    return embed

# =========================================================
# --- ERROR HANDLER ---
# =========================================================
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

# =========================================================
# --- MODALE ---
# =========================================================
class SuggestionModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowa Propozycja - {server}")
        self.server = server
        self.description = discord.ui.TextInput(
            label="Opis propozycji", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.reason = discord.ui.TextInput(
            label="Dlaczego ma zostać wprowadzona?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Propozycja", "💡", server=self.server)


class BugReportModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowy Błąd - {server}")
        self.server = server
        self.description = discord.ui.TextInput(
            label="Opis błędu", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.evidence = discord.ui.TextInput(
            label="Dowody (linki do screenów, filmów)", required=False, max_length=1024)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Błąd", "🐛", server=self.server)


class ComplaintModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowa Skarga - {server}")
        self.server = server
        self.target_nick = discord.ui.TextInput(label="Nick osoby, na którą składasz skargę", required=True)
        self.add_item(self.target_nick)
        self.reason = discord.ui.TextInput(
            label="Opis sytuacji i powód skargi", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)
        self.evidence = discord.ui.TextInput(
            label="Dowody (linki do screenów, filmów)", required=True, max_length=1024)
        self.add_item(self.evidence)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Skarga", "⚠️", server=self.server)


class AppealModal(discord.ui.Modal):
    def __init__(self, server: str):
        super().__init__(title=f"Nowe Odwołanie - {server}")
        self.server = server
        self.ban_reason = discord.ui.TextInput(label="Powód otrzymanej kary", required=True, max_length=1024)
        self.add_item(self.ban_reason)
        self.admin_nick = discord.ui.TextInput(label="Nick admina, który nałożył karę", required=True)
        self.add_item(self.admin_nick)
        self.appeal_reason = discord.ui.TextInput(
            label="Dlaczego chcesz otrzymać unbana?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.appeal_reason)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Odwołanie", "📋", server=self.server)


class ServerAdminApplicationModal(discord.ui.Modal):
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(
        label="Napisz coś o sobie i swoim doświadczeniu",
        style=discord.TextStyle.paragraph, required=True, max_length=1024)

    def __init__(self, application_type: str):
        super().__init__(title=application_type)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title, "📝")


class TrustedApplicationModal(discord.ui.Modal, title="Podanie Zaufany JB"):
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(
        label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Zaufany JB", "📝")


class DiscordAdminApplicationModal(discord.ui.Modal, title="Podanie Admin DC"):
    server_time = discord.ui.TextInput(label="Od kiedy jesteś na tym serwerze Discord?", required=True)
    experience = discord.ui.TextInput(
        label="Doświadczenie jako administrator", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    knowledge = discord.ui.TextInput(label="Znajomość Discorda (od 1 do 10)", required=True, max_length=2)
    availability = discord.ui.TextInput(label="Ile czasu dziennie mógłbyś poświęcić?", required=True)
    about = discord.ui.TextInput(
        label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Admin DC", "📝")


class DeveloperApplicationModal(discord.ui.Modal, title="Podanie Developer"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(
        label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(
        label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Developer", "📝")


class MapDeveloperApplicationModal(discord.ui.Modal, title="Podanie MapDeveloper"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(
        label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(
        label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie MapDeveloper", "📝")


class GraphicDesignerApplicationModal(discord.ui.Modal, title="Podanie Grafik"):
    nick = discord.ui.TextInput(label="Nick", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(
        label="Dlaczego chcesz do nas dołączyć?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(
        label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Grafik", "📝")


class EditorApplicationModal(discord.ui.Modal, title="Podanie Redaktor"):
    name = discord.ui.TextInput(label="Imię", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    why = discord.ui.TextInput(
        label="Dlaczego chcesz zostać redaktorem?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    experience = discord.ui.TextInput(
        label="Doświadczenie", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    example = discord.ui.TextInput(
        label="Przykładowa treść", style=discord.TextStyle.paragraph, required=True, max_length=1024)

    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Redaktor", "📝")


class DecisionReasonModal(discord.ui.Modal, title="Uzasadnienie decyzji"):
    reason_input = discord.ui.TextInput(
        label="Notatka (opcjonalnie)", style=discord.TextStyle.paragraph, required=False, max_length=1024)

    def __init__(self, original_interaction: discord.Interaction, action: str, post_type: str, author_id: int):
        super().__init__()
        self.original_interaction = original_interaction
        self.action = action
        self.post_type = post_type
        self.author_id = author_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await process_decision(
            interaction, self.original_interaction, self.action,
            self.post_type, self.author_id, self.reason_input.value)


class AnnouncementModal(discord.ui.Modal, title="Nowe ogłoszenie"):
    title_input = discord.ui.TextInput(label="Tytuł ogłoszenia", required=True, max_length=256)
    content_input = discord.ui.TextInput(
        label="Treść ogłoszenia", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.TextChannel, role: Optional[discord.Role]):
        super().__init__()
        self.channel = channel
        self.role = role

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=self.title_input.value, description=self.content_input.value,
            color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Ogłoszenie dodane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        role_mention = self.role.mention if self.role else ""
        await self.channel.send(content=role_mention, embed=embed)
        await interaction.response.send_message("✅ Ogłoszenie zostało pomyślnie opublikowane.", ephemeral=True)


class EventModal(discord.ui.Modal, title="Nowe wydarzenie"):
    title_input = discord.ui.TextInput(label="Tytuł wydarzenia", required=True, max_length=256)
    datetime_input = discord.ui.TextInput(
        label="Data i godzina (DD.MM.RRRR HH:MM)", placeholder="np. 25.12.2025 18:00", required=True)
    rewards_input = discord.ui.TextInput(label="Nagrody", required=False, max_length=1024)
    content_input = discord.ui.TextInput(
        label="Opis wydarzenia", style=discord.TextStyle.paragraph, required=True, max_length=2000)

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
            await interaction.response.send_message(
                "❌ Nieprawidłowy format daty! Użyj 'DD.MM.RRRR HH:MM'.", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"🎉 Nowe wydarzenie: {self.title_input.value}",
            description=self.content_input.value,
            color=COLORS["success"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="📅 Kiedy?", value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)", inline=False)
        if self.rewards_input.value:
            embed.add_field(name="🎁 Nagrody", value=self.rewards_input.value, inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Wydarzenie zorganizowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        role_mention = self.role.mention if self.role else ""
        message = await self.channel.send(content=role_mention, embed=embed, view=EventView(initial_count=0))
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO events (message_id, author_id, attendees) VALUES (?, ?, ?)",
                (message.id, interaction.user.id, json.dumps([])))
            await db.commit()
        await interaction.response.send_message("✅ Wydarzenie zostało pomyślnie opublikowane.", ephemeral=True)


class QuickShotModal(discord.ui.Modal, title="Nowy Szybki Strzał"):
    title_input = discord.ui.TextInput(label="Tytuł (np. Szybkie strzały z @User)", required=True)
    interviewer = discord.ui.TextInput(label="Osoba przeprowadzająca", required=True)
    interviewee = discord.ui.TextInput(label="Osoba odpowiadająca", required=True)
    content = discord.ui.TextInput(
        label="Pytania i Odpowiedzi", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.ForumChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title=f"⚡ {self.title_input.value}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="🎤 Przeprowadził/a", value=self.interviewer.value, inline=True)
        embed.add_field(name="🗣️ Odpowiadał/a",   value=self.interviewee.value, inline=True)
        embed.add_field(name="📝 Treść",           value=self.content.value,     inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Opublikowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        await self.channel.create_thread(name=self.title_input.value, embed=embed)
        await interaction.followup.send("✅ Pomyślnie opublikowano Szybki Strzał.", ephemeral=True)


class InterviewModal(discord.ui.Modal, title="Nowy Wywiad"):
    title_input = discord.ui.TextInput(label="Tytuł wywiadu", required=True)
    interviewer = discord.ui.TextInput(label="Osoba przeprowadzająca", required=True)
    interviewee = discord.ui.TextInput(label="Gość wywiadu", required=True)
    content = discord.ui.TextInput(
        label="Treść wywiadu", style=discord.TextStyle.paragraph, required=True, max_length=4000)

    def __init__(self, channel: discord.ForumChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(
            title=f"🎙️ {self.title_input.value}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
        embed.add_field(name="🎤 Przeprowadził/a", value=self.interviewer.value, inline=True)
        embed.add_field(name="🌟 Gość",            value=self.interviewee.value, inline=True)
        embed.add_field(name="📝 Treść",           value=self.content.value,     inline=False)
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=f"Opublikowane przez: {interaction.user.display_name} | {FOOTER_TEXT}")
        await self.channel.create_thread(name=self.title_input.value, embed=embed)
        await interaction.followup.send("✅ Pomyślnie opublikowano Wywiad.", ephemeral=True)


# --- PUNKT 6: MODAL EDYCJI PRZEDMIOTU ---
class EditItemModal(discord.ui.Modal, title="Edytuj przedmiot w sklepie"):
    new_name = discord.ui.TextInput(label="Nowa nazwa (zostaw puste = bez zmiany)", required=False, max_length=100)
    new_cost = discord.ui.TextInput(label="Nowa cena w reputacji (liczba)", required=False, max_length=10)
    new_desc = discord.ui.TextInput(
        label="Nowy opis (zostaw puste = bez zmiany)",
        style=discord.TextStyle.paragraph, required=False, max_length=512)
    new_stock = discord.ui.TextInput(
        label="Nowy stan magazynowy (-1 = nielimitowany)", required=False, max_length=10)

    def __init__(self, item_id: int):
        super().__init__()
        self.item_id = item_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT name, cost, description, stock FROM shop_items WHERE id = ?",
                (self.item_id,)) as cursor:
                item = await cursor.fetchone()
            if not item:
                await interaction.followup.send("❌ Przedmiot nie istnieje.", ephemeral=True)
                return

            old_name, old_cost, old_desc, old_stock = item
            new_name_val  = self.new_name.value.strip()  or old_name
            new_desc_val  = self.new_desc.value.strip()  or old_desc

            try:
                new_cost_val = int(self.new_cost.value.strip()) if self.new_cost.value.strip() else old_cost
                if new_cost_val < 1:
                    raise ValueError
            except ValueError:
                await interaction.followup.send("❌ Cena musi być liczbą całkowitą większą od 0.", ephemeral=True)
                return

            new_stock_val = old_stock
            if self.new_stock.value.strip():
                try:
                    v = int(self.new_stock.value.strip())
                    new_stock_val = None if v == -1 else v
                except ValueError:
                    await interaction.followup.send("❌ Stan magazynowy musi być liczbą (-1 = brak limitu).", ephemeral=True)
                    return

            await db.execute(
                "UPDATE shop_items SET name=?, cost=?, description=?, stock=? WHERE id=?",
                (new_name_val, new_cost_val, new_desc_val, new_stock_val, self.item_id))
            await db.commit()

        stock_display = "nielimitowany" if new_stock_val is None else str(new_stock_val)
        await interaction.followup.send(
            f"✅ Zaktualizowano przedmiot ID **{self.item_id}**:\n"
            f"• Nazwa: **{new_name_val}**\n"
            f"• Cena: **{new_cost_val}** rep.\n"
            f"• Opis: *{new_desc_val}*\n"
            f"• Magazyn: **{stock_display}**",
            ephemeral=True)

# =========================================================
# --- WIDOK EVENTU ---
# =========================================================
class EventView(discord.ui.View):
    def __init__(self, initial_count: int = 0):
        super().__init__(timeout=None)
        self.signup_button = discord.ui.Button(
            label=f"Zapisz się! ({initial_count})",
            style=discord.ButtonStyle.success,
            custom_id="event_signup_button",
            emoji="✅")
        self.signup_button.callback = self.signup_callback
        self.add_item(self.signup_button)

    async def signup_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT attendees FROM events WHERE message_id = ?", (interaction.message.id,)) as cursor:
                data = await cursor.fetchone()
            if not data:
                await interaction.followup.send("❌ Wystąpił błąd z tym wydarzeniem.", ephemeral=True)
                return
            attendees = json.loads(data[0])
            user_id = interaction.user.id
            if user_id in attendees:
                attendees.remove(user_id)
                await interaction.followup.send("✅ Zostałeś wypisany z wydarzenia.", ephemeral=True)
            else:
                attendees.append(user_id)
                await interaction.followup.send("✅ Zostałeś zapisany na wydarzenie!", ephemeral=True)
            await db.execute(
                "UPDATE events SET attendees = ? WHERE message_id = ?",
                (json.dumps(attendees), interaction.message.id))
            await db.commit()
        self.signup_button.label = f"Zapisz się! ({len(attendees)})"
        await interaction.edit_original_response(view=self)

# =========================================================
# --- LOGIKA DECYZJI ---
# =========================================================
async def process_decision(interaction: discord.Interaction, original_interaction: discord.Interaction,
                            action: str, post_type: str, author_id: int, reason_text: str):
    try:
        original_message = original_interaction.message
        original_embed   = original_message.embeds[0]

        action_map = {
            "accept_suggestion":  {"text": "Propozycja przyjęta",           "color": COLORS["success"], "points": 5, "prefix": "[Zaakceptowane]", "final": True,  "status_tag": "closed"},
            "reject_suggestion":  {"text": "Propozycja odrzucona",          "color": COLORS["error"],   "points": 0, "prefix": "[Odrzucone]",     "final": True,  "status_tag": "closed"},
            "accept_bug":         {"text": "W trakcie naprawy",             "color": COLORS["warn"],    "points": 0, "prefix": "[W trakcie]",     "final": False, "status_tag": "in_progress"},
            "resolve_bug":        {"text": "Naprawiony",                    "color": COLORS["success"], "points": 3, "prefix": "[Naprawione]",    "final": True,  "status_tag": "closed"},
            "reject_bug":         {"text": "Zgłoszenie odrzucone",          "color": COLORS["error"],   "points": 0, "prefix": "[Odrzucone]",     "final": True,  "status_tag": "closed"},
            "accept_complaint":   {"text": "Skarga rozpatrzona pozytywnie", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True,  "status_tag": "closed"},
            "reject_complaint":   {"text": "Skarga odrzucona",              "color": COLORS["error"],   "points": 0, "prefix": "[Odrzucone]",     "final": True,  "status_tag": "closed"},
            "accept_appeal":      {"text": "Odwołanie zaakceptowane",       "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True,  "status_tag": "closed"},
            "reject_appeal":      {"text": "Odwołanie odrzucone",           "color": COLORS["error"],   "points": 0, "prefix": "[Odrzucone]",     "final": True,  "status_tag": "closed"},
            "accept_application": {"text": "Podanie przyjęte",              "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True,  "status_tag": "closed"},
            "reject_application": {"text": "Podanie odrzucone",             "color": COLORS["error"],   "points": 0, "prefix": "[Odrzucone]",     "final": True,  "status_tag": "closed"},
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
        decision_embed.add_field(name="Status",     value=action_details["text"],    inline=True)
        decision_embed.add_field(name="Rozpatrzył", value=interaction.user.mention, inline=True)
        if reason_text:
            decision_embed.add_field(name="Notatka od administracji", value=reason_text, inline=False)
        if LOGO_URL:
            decision_embed.set_thumbnail(url=LOGO_URL)
        decision_embed.set_footer(text=FOOTER_TEXT)

        if action_details["points"] > 0:
            await update_reputation(author_id, action_details["points"], mode='add')

        dm_message = ""

        # --- PUNKT 1: Cooldown przy odrzuceniu podania ---
        if action == "reject_application":
            dm_message = f"❌ Niestety, Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało odrzucone.\n⏳ Możesz złożyć nowe podanie za **{COOLDOWN_DAYS} dni**."
            await set_application_cooldown(str(author_id), post_type)

        elif action == "accept_application":
            dm_message = f"🎉 Gratulacje! Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało zaakceptowane!"
            member = interaction.guild.get_member(author_id)
            if member:
                try:
                    roles_map = {
                        "Podanie Admin JB":          ["Junior Admin JB", "Administracja JB"],
                        "Podanie Zaufany JB":         ["Zaufany JB", "Administracja JB"],
                        "Podanie Admin DC":           ["Admin Discord"],
                        "Podanie Admin Supermoce":    ["Admin Supermoce"],
                        "Podanie Admin Surf + RPG":   ["Admin Surf + RPG"],
                        "Podanie Admin DR":           ["Admin DR"],
                        "Podanie Admin Projekt RPG":  ["Admin Projekt RPG"],
                    }
                    roles_to_add_names = roles_map.get(post_type, [])
                    roles_to_add = [discord.utils.get(interaction.guild.roles, name=n) for n in roles_to_add_names]
                    valid_roles = [r for r in roles_to_add if r]
                    if valid_roles:
                        await member.add_roles(*valid_roles, reason=f"Akceptacja podania: {post_type}")
                except discord.Forbidden:
                    await original_interaction.channel.send(
                        f"⚠️ **Błąd uprawnień!** Nie udało się nadać roli {member.mention}.")
                except Exception as e:
                    print(f"Błąd podczas nadawania roli: {e}")

        new_view = None if action_details["final"] else ManagementView(post_type, author_id, is_in_progress=True)
        await original_message.edit(embed=original_embed, view=new_view)
        await original_interaction.channel.send(embed=decision_embed)

        # --- PUNKT 4: Aktualizacja tagu statusu ---
        await update_thread_status_tag(original_interaction.channel, action_details["status_tag"])

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

        await log_action(
            interaction.guild, f"Zarządzano postem: {action_details['text']}",
            interaction.user, f"Post: {original_interaction.channel.mention}")

    except Exception as e:
        print(f"Błąd w process_decision: {e}")
        traceback.print_exc()

# =========================================================
# --- FUNKCJA TWORZĄCA POSTY ---
# =========================================================
async def create_generic_post(modal: discord.ui.Modal, interaction: discord.Interaction,
                               post_type: str, emoji: str, server: str = None):
    await interaction.response.defer(ephemeral=True)
    try:
        # --- PUNKT 1 & 3: Sprawdzenie cooldownu i antyspamu TYLKO dla podań ---
        if post_type.startswith("Podanie"):
            user_id_str = str(interaction.user.id)

            # Cooldown (po odrzuceniu)
            cooldown_end = await check_application_cooldown(user_id_str, post_type)
            if cooldown_end:
                ts = int(cooldown_end.timestamp())
                await interaction.followup.send(
                    f"⏳ Twoje poprzednie podanie na **{post_type}** zostało odrzucone.\n"
                    f"Możesz złożyć nowe dopiero <t:{ts}:R> (<t:{ts}:F>).",
                    ephemeral=True)
                return

            # Antyspam (aktywne podanie)
            has_active = await check_active_application(user_id_str, post_type)
            if has_active:
                await interaction.followup.send(
                    f"❌ Masz już aktywne podanie na **{post_type}**, które czeka na rozpatrzenie.\n"
                    f"Nie możesz złożyć kolejnego przed jego rozpatrzeniem.",
                    ephemeral=True)
                return

        full_type = f"{post_type} ({server})" if server else post_type

        embed = discord.Embed(
            title=f"{emoji} Nowe zgłoszenie: {full_type}",
            color=COLORS["main"],
            timestamp=datetime.now(POLAND_TZ))

        if server:
            embed.add_field(name="🌐 Serwer", value=server, inline=True)

        for item in modal.children:
            if item.value:
                embed.add_field(name=item.label, value=item.value, inline=False)

        embed.add_field(name="👤 Autor",    value=interaction.user.mention,  inline=False)
        embed.add_field(name="📊 Status",   value="Oczekuje na decyzję",     inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.set_footer(text=FOOTER_TEXT)

        forum_channel = (
            interaction.channel.parent
            if isinstance(interaction.channel, discord.Thread)
            else interaction.channel
        )

        # --- PUNKT 2 & 4: Tagi typu + tag statusu "Oczekuje" ---
        tag_name = get_tag_name_for_post(post_type, server)
        type_tag = find_tag(forum_channel, tag_name)
        if not type_tag and server:
            type_tag = find_tag(forum_channel, post_type)

        status_tag = find_tag(forum_channel, STATUS_TAG_NAMES["pending"])

        applied_tags = []
        if type_tag:
            applied_tags.append(type_tag)
        if status_tag and status_tag not in applied_tags:
            applied_tags.append(status_tag)
        applied_tags = applied_tags[:5]

        post_title = f"{full_type}: {interaction.user.display_name}"
        if len(post_title) > 100:
            post_title = post_title[:97] + "..."

        thread_message = await forum_channel.create_thread(
            name=post_title,
            embed=embed,
            applied_tags=applied_tags,
            view=ManagementView(post_type, interaction.user.id)
        )

        # Zapis do bazy danych
        data = {item.label: item.value for item in modal.children if item.value}

        if post_type == "Propozycja":
            await save_suggestion(
                str(interaction.user.id), interaction.user.display_name, post_type,
                data.get('Opis propozycji', ''),
                data.get('Dlaczego ma zostać wprowadzona?', ''),
                server or 'Nieokreślony',
                str(thread_message.thread.id))
        elif post_type == "Błąd":
            await save_bug_report(
                str(interaction.user.id), post_type, "Nieokreślony",
                data.get('Opis błędu', ''),
                data.get('Dowody (linki do screenów, filmów)', ''),
                server or 'Nieokreślony',
                str(thread_message.thread.id))
        elif post_type == "Skarga":
            await save_complaint(
                str(interaction.user.id), post_type,
                data.get('Nick osoby, na którą składasz skargę', ''),
                data, server or 'Nieokreślony',
                str(thread_message.thread.id))
        elif post_type == "Odwołanie":
            await save_appeal(
                str(interaction.user.id), post_type,
                data, server or 'Nieokreślony',
                str(thread_message.thread.id))
        elif post_type.startswith("Podanie"):
            await save_application(
                str(interaction.user.id), interaction.user.display_name, post_type,
                data, str(thread_message.thread.id))

        await log_action(interaction.guild, f"Złożono: {full_type}", interaction.user,
                         f"Post: {thread_message.thread.mention}")
        await send_notification(interaction.guild, post_type, thread_message.thread.jump_url)
        await interaction.followup.send(
            f"✅ Twoje zgłoszenie zostało opublikowane w poście {thread_message.thread.mention}!",
            ephemeral=True)

    except Exception as e:
        print(f"Błąd podczas tworzenia posta ({post_type}): {e}")
        traceback.print_exc()
        try:
            await interaction.followup.send("❌ Wystąpił nieoczekiwany błąd. Spróbuj ponownie.", ephemeral=True)
        except discord.HTTPException:
            pass

# =========================================================
# --- WIDOKI WYBORU ---
# =========================================================
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
                discord.SelectOption(label="Propozycja", emoji="💡", value="propozycja",
                                     description="Zaproponuj zmianę na serwerze"),
                discord.SelectOption(label="Błąd", emoji="🐛", value="blad",
                                     description="Zgłoś błąd na serwerze"),
            ]
        elif view_type == "complaints_appeals":
            placeholder = "Wybierz akcję (skargi i odwołania)..."
            options = [
                discord.SelectOption(label="Skarga",    emoji="⚠️", value="skarga",
                                     description="Złóż skargę na gracza lub admina"),
                discord.SelectOption(label="Odwołanie", emoji="📋", value="odwolanie",
                                     description="Odwołaj się od kary"),
            ]
        elif view_type == "recruitment":
            placeholder = "Wybierz typ podania..."
            options = [
                discord.SelectOption(label="Podanie Admin",      emoji="🛡️", value="podanie_admin",
                                     description="Złóż podanie na admina (wybór serwera)"),
                discord.SelectOption(label="Podanie Zaufany JB", emoji="⭐", value="Podanie Zaufany JB",
                                     description="Złóż podanie na Zaufanego JB"),
            ]
        elif view_type == "creative_recruitment":
            placeholder = "Wybierz stanowisko, na które aplikujesz..."
            options = []
            for position in CREATIVE_RECRUITMENT_TYPES:
                options.append(discord.SelectOption(label=position, value=position, emoji="🎨"))

        super().__init__(placeholder=placeholder, min_values=1, max_values=1,
                         options=options, custom_id=custom_id)
        self.view_type = view_type

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice in ["propozycja", "blad"]:
            view = ServerSelectionView(post_type=choice)
            embed = discord.Embed(title="🌐 Wybierz serwer",
                                  description="Na którym serwerze chcesz zgłosić propozycję/błąd?",
                                  color=COLORS["main"])
            if LOGO_URL:
                embed.set_thumbnail(url=LOGO_URL)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        if choice in ["skarga", "odwolanie"]:
            view = ServerSelectionView(post_type=choice)
            embed = discord.Embed(title="🌐 Wybierz serwer",
                                  description="Którego serwera dotyczy Twoje zgłoszenie?",
                                  color=COLORS["main"])
            if LOGO_URL:
                embed.set_thumbnail(url=LOGO_URL)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        if choice == "podanie_admin":
            view = AdminApplicationServerView()
            embed = discord.Embed(title="🛡️ Wybierz serwer",
                                  description="Na który serwer chcesz złożyć podanie na admina?",
                                  color=COLORS["main"])
            if LOGO_URL:
                embed.set_thumbnail(url=LOGO_URL)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        if choice == "Podanie Zaufany JB":
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT is_open FROM recruitment_status WHERE position = ?", (choice,)) as cursor:
                    status = await cursor.fetchone()
                    is_open = status[0] if status else 1
            if not is_open:
                await interaction.response.send_message(
                    "❌ Rekrutacja na to stanowisko jest obecnie zamknięta.", ephemeral=True)
                return
            embed = discord.Embed(
                title=f"📋 Wymagania - {choice}",
                description="• Minimum 14 lat\n• Aktywność na serwerze",
                color=COLORS["main"])
            if LOGO_URL:
                embed.set_thumbnail(url=LOGO_URL)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.response.send_message(embed=embed, view=RequirementsView(choice), ephemeral=True)
            return

        if choice in CREATIVE_RECRUITMENT_TYPES:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute(
                    "SELECT is_open FROM recruitment_status WHERE position = ?", (choice,)) as cursor:
                    status = await cursor.fetchone()
                    is_open = status[0] if status else 1
            if not is_open:
                await interaction.response.send_message(
                    "❌ Rekrutacja na to stanowisko jest obecnie zamknięta.", ephemeral=True)
                return
            modal_map = {
                "Podanie Developer":    DeveloperApplicationModal,
                "Podanie MapDeveloper": MapDeveloperApplicationModal,
                "Podanie Grafik":       GraphicDesignerApplicationModal,
                "Podanie Redaktor":     EditorApplicationModal,
            }
            if choice in modal_map:
                modal_class = modal_map[choice]
                modal = modal_class() if callable(modal_class) else modal_class
                await interaction.response.send_modal(modal)


class AdminApplicationServerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(AdminApplicationServerSelect())


class AdminApplicationServerSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="JailBreak",   value="Podanie Admin JB",          emoji="🎮"),
            discord.SelectOption(label="Supermoce",   value="Podanie Admin Supermoce",   emoji="🎮"),
            discord.SelectOption(label="Surf + RPG",  value="Podanie Admin Surf + RPG",  emoji="🎮"),
            discord.SelectOption(label="DeathRun",    value="Podanie Admin DR",          emoji="🎮"),
            discord.SelectOption(label="Projekt RPG", value="Podanie Admin Projekt RPG", emoji="🎮"),
            discord.SelectOption(label="Discord",     value="Podanie Admin DC",          emoji="💬"),
        ]
        super().__init__(placeholder="Wybierz serwer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT is_open FROM recruitment_status WHERE position = ?", (choice,)) as cursor:
                status = await cursor.fetchone()
                is_open = status[0] if status else 1
        if not is_open:
            await interaction.response.send_message(
                "❌ Rekrutacja na to stanowisko jest obecnie zamknięta.", ephemeral=True)
            return

        requirements_map = {
            "Podanie Admin JB":          "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
            "Podanie Admin DC":          "• Doświadczenie z Discordem\n• Aktywność na serwerze Discord",
            "Podanie Admin Supermoce":   "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
            "Podanie Admin Surf + RPG":  "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
            "Podanie Admin DR":          "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
            "Podanie Admin Projekt RPG": "• Minimum 16 lat\n• Aktywność na serwerze\n• Znajomość regulaminu",
        }
        embed = discord.Embed(
            title=f"📋 Wymagania - {choice}",
            description=requirements_map.get(choice, ""),
            color=COLORS["main"])
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=FOOTER_TEXT)
        await interaction.response.send_message(embed=embed, view=RequirementsView(choice), ephemeral=True)


class ServerSelectionView(discord.ui.View):
    def __init__(self, post_type: str):
        super().__init__(timeout=180)
        self.add_item(ServerSelect(post_type=post_type))


class ServerSelect(discord.ui.Select):
    def __init__(self, post_type: str):
        self.post_type = post_type
        options = [discord.SelectOption(label=s, value=s, emoji="🌐") for s in SERVER_LIST]
        super().__init__(placeholder="Wybierz serwer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        server = self.values[0]
        if self.post_type == "propozycja":
            await interaction.response.send_modal(SuggestionModal(server=server))
        elif self.post_type == "blad":
            await interaction.response.send_modal(BugReportModal(server=server))
        elif self.post_type == "skarga":
            await interaction.response.send_modal(ComplaintModal(server=server))
        elif self.post_type == "odwolanie":
            await interaction.response.send_modal(AppealModal(server=server))


class RequirementsView(discord.ui.View):
    def __init__(self, application_type: str):
        super().__init__(timeout=180)
        self.application_type = application_type

        continue_btn = discord.ui.Button(
            label="Akceptuję i chcę kontynuować",
            style=discord.ButtonStyle.success, emoji="✅")
        continue_btn.callback = self.continue_callback
        self.add_item(continue_btn)

        game_types = [
            "Podanie Admin JB", "Podanie Zaufany JB",
            "Podanie Admin Supermoce", "Podanie Admin Surf + RPG",
            "Podanie Admin DR", "Podanie Admin Projekt RPG"
        ]
        if self.application_type in game_types:
            stats_btn = discord.ui.Button(
                label="Statystyki serwera", style=discord.ButtonStyle.link,
                url="https://tsarvar.com/pl/servers/counter-strike2/91.224.117.153:27015", emoji="📊")
            self.add_item(stats_btn)

    async def continue_callback(self, interaction: discord.Interaction):
        modal_map = {
            "Podanie Admin JB":          lambda: ServerAdminApplicationModal("Podanie Admin JB"),
            "Podanie Zaufany JB":         TrustedApplicationModal,
            "Podanie Admin DC":           DiscordAdminApplicationModal,
            "Podanie Admin Supermoce":    lambda: ServerAdminApplicationModal("Podanie Admin Supermoce"),
            "Podanie Admin Surf + RPG":   lambda: ServerAdminApplicationModal("Podanie Admin Surf + RPG"),
            "Podanie Admin DR":           lambda: ServerAdminApplicationModal("Podanie Admin DR"),
            "Podanie Admin Projekt RPG":  lambda: ServerAdminApplicationModal("Podanie Admin Projekt RPG"),
            "Podanie Developer":          DeveloperApplicationModal,
            "Podanie MapDeveloper":        MapDeveloperApplicationModal,
            "Podanie Grafik":             GraphicDesignerApplicationModal,
            "Podanie Redaktor":           EditorApplicationModal,
        }
        if self.application_type in modal_map:
            modal_class = modal_map[self.application_type]
            modal = modal_class() if callable(modal_class) else modal_class
            await interaction.response.send_modal(modal)
        self.stop()


# =========================================================
# --- MENU ZARZĄDZANIA ---
# =========================================================
class ManagementView(discord.ui.View):
    def __init__(self, post_type: str, author_id: int, is_in_progress: bool = False):
        super().__init__(timeout=None)
        self.post_type  = post_type
        self.author_id  = author_id
        self.add_item(ManagementSelect(
            post_type=post_type,
            custom_id=f"persistent_management_select_{post_type.replace(' ', '_')}",
            is_in_progress=is_in_progress))


class ManagementSelect(discord.ui.Select):
    def __init__(self, post_type: str, custom_id: str, is_in_progress: bool = False):
        self.post_type = post_type
        options = []

        if is_in_progress:
            options = [
                discord.SelectOption(label="Błąd naprawiony",   value="resolve_bug", emoji="✅"),
                discord.SelectOption(label="Odrzuć zgłoszenie", value="reject_bug",  emoji="❌")]
        else:
            options_map = {
                "Podanie": [
                    discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_application", emoji="✅"),
                    discord.SelectOption(label="Rozpatrz negatywnie", value="reject_application", emoji="❌")],
                "Propozycja": [
                    discord.SelectOption(label="Przyjmij propozycję", value="accept_suggestion", emoji="✅"),
                    discord.SelectOption(label="Odrzuć propozycję",   value="reject_suggestion", emoji="❌")],
                "Błąd": [
                    discord.SelectOption(label="Błąd przyjęty do naprawy", value="accept_bug",  emoji="🔧"),
                    discord.SelectOption(label="Odrzuć zgłoszenie",        value="reject_bug",  emoji="❌")],
                "Skarga": [
                    discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_complaint", emoji="✅"),
                    discord.SelectOption(label="Odrzuć skargę",       value="reject_complaint", emoji="❌")],
                "Odwołanie": [
                    discord.SelectOption(label="Zaakceptuj odwołanie", value="accept_appeal", emoji="✅"),
                    discord.SelectOption(label="Odrzuć odwołanie",     value="reject_appeal", emoji="❌")],
            }
            chosen_key = next((k for k in options_map if self.post_type.startswith(k)), None)
            options = options_map.get(chosen_key, [])

        super().__init__(
            placeholder="Wybierz akcję zarządczą...",
            min_values=1, max_values=1,
            options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        if not has_permission_for_type(interaction.user, self.post_type):
            await interaction.response.send_message("❌ Nie masz uprawnień!", ephemeral=True)
            return
        action = self.values[0]
        if action in RESPONSE_TEMPLATES:
            view = TemplateReasonView(
                original_interaction=interaction, action=action,
                post_type=self.post_type, author_id=self.view.author_id)
            await interaction.response.send_message(
                "Wybierz szablon odpowiedzi lub wpisz własny powód.", view=view, ephemeral=True)
        else:
            await interaction.response.send_modal(
                DecisionReasonModal(
                    original_interaction=interaction, action=action,
                    post_type=self.post_type, author_id=self.view.author_id))


class TemplateReasonView(discord.ui.View):
    def __init__(self, original_interaction: discord.Interaction,
                 action: str, post_type: str, author_id: int):
        super().__init__(timeout=180)
        self.original_interaction = original_interaction
        self.action    = action
        self.post_type = post_type
        self.author_id = author_id

        templates = RESPONSE_TEMPLATES.get(action, [])
        options   = [discord.SelectOption(label=t[:100]) for t in templates]
        self.select_menu = discord.ui.Select(
            placeholder="Wybierz gotowy szablon odpowiedzi...", options=options)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        reason_text = self.select_menu.values[0]
        await process_decision(interaction, self.original_interaction, self.action,
                               self.post_type, self.author_id, reason_text)
        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(content="✅ Decyzja została podjęta.", view=self)

    @discord.ui.button(label="Inny powód (wpisz ręcznie)", style=discord.ButtonStyle.secondary)
    async def custom_reason_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DecisionReasonModal(
            original_interaction=self.original_interaction, action=self.action,
            post_type=self.post_type, author_id=self.author_id)
        await interaction.response.send_modal(modal)
        self.stop()

# =========================================================
# --- SYSTEM ANKIET ---
# =========================================================
class PollView(discord.ui.View):
    def __init__(self, options: list, message_id: int = 0):
        super().__init__(timeout=None)
        self.message_id = message_id
        for i, option_text in enumerate(options):
            self.add_item(PollButton(label=option_text, custom_id=f"poll_{message_id}_{i}"))


class PollButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        message_id   = int(self.custom_id.split('_')[1])
        button_index = int(self.custom_id.split('_')[2])

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT votes FROM polls WHERE message_id = ?", (message_id,)) as cursor:
                votes_json = await cursor.fetchone()
            if not votes_json:
                return
            votes = json.loads(votes_json[0])
            voter_id_str = str(interaction.user.id)
            for option_votes in votes.values():
                if voter_id_str in option_votes:
                    option_votes.remove(voter_id_str)
            votes[str(button_index)].append(voter_id_str)
            await db.execute(
                "UPDATE polls SET votes = ? WHERE message_id = ?", (json.dumps(votes), message_id))
            await db.commit()

            async with db.execute(
                "SELECT question, options, author_id FROM polls WHERE message_id = ?", (message_id,)) as cursor:
                poll_data = await cursor.fetchone()

        question, options, author_id = poll_data
        options = json.loads(options)
        author  = interaction.guild.get_member(author_id) or await bot.fetch_user(author_id)

        new_embed = discord.Embed(
            title="📊 Ankieta", description=f"**{question}**", color=COLORS["main"])
        for i, option_text in enumerate(options):
            voter_ids     = votes.get(str(i), [])
            voter_mentions= [f"<@{uid}>" for uid in voter_ids]
            value_text    = "\n".join(voter_mentions) if voter_mentions else "Brak głosów"
            if len(value_text) > 1024:
                value_text = value_text[:1020] + "\n..."
            new_embed.add_field(name=f"{option_text} ({len(voter_ids)})", value=value_text, inline=False)
        new_embed.set_footer(text=f"Ankieta stworzona przez: {author.display_name} | {FOOTER_TEXT}")
        if LOGO_URL:
            new_embed.set_thumbnail(url=LOGO_URL)
        await interaction.edit_original_response(embed=new_embed)

# =========================================================
# --- SYSTEM SKLEPU ---
# =========================================================
async def create_shop_embed(category: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, name, cost, description, stock FROM shop_items WHERE category = ? ORDER BY cost ASC",
            (category,)) as cursor:
            items = await cursor.fetchall()
    embed = discord.Embed(title=f"🛒 Sklep - Kategoria: {category}", color=COLORS["main"])
    if not items:
        embed.description = "Brak przedmiotów w tej kategorii."
    else:
        description = ""
        for item_id, name, cost, desc, stock in items:
            stock_info = ""
            if stock is not None:
                stock_info = f" (Pozostało: {stock} szt.)" if stock > 0 else " (Wyprzedane)"
            description += f"**ID: {item_id} | {name}{stock_info}** — `{cost} rep.`\n*_{desc}_*\n\n"
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
        super().__init__(placeholder="Wybierz kategorię sklepu...", min_values=1, max_values=1,
                         options=options, custom_id="shop_category_select")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        selected_category = self.values[0]
        new_embed = await create_shop_embed(selected_category)
        new_view  = ShopView(initial_category=selected_category)
        await interaction.edit_original_response(embed=new_embed, view=new_view)


class ShopItemSelect(discord.ui.Select):
    def __init__(self, category: str):
        super().__init__(placeholder="Wybierz przedmiot, który chcesz kupić...",
                         min_values=1, max_values=1, custom_id="shop_item_select")
        self.category = category
        self.options  = [discord.SelectOption(label="Ładowanie...", value="loading")]

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "loading":
            await interaction.response.send_message("⏳ Proszę wybrać kategorię ponownie.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        item_id = int(self.values[0])

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT name, cost, role_id, stock, category FROM shop_items WHERE id = ?",
                (item_id,)) as cursor:
                item = await cursor.fetchone()
            if not item:
                await interaction.followup.send("❌ Przedmiot nie znaleziony.", ephemeral=True)
                return

            item_name, item_cost, role_id, stock, category = item

            if stock is not None and stock <= 0:
                await interaction.followup.send("❌ Ten przedmiot jest już wyprzedany!", ephemeral=True)
                return

            if category == "Specjalne role":
                async with db.execute(
                    "SELECT 1 FROM shop_purchases WHERE user_id = ? AND item_id = ?",
                    (interaction.user.id, item_id)) as cursor:
                    if await cursor.fetchone():
                        await interaction.followup.send("❌ Już posiadasz ten unikalny przedmiot!", ephemeral=True)
                        return

            async with db.execute(
                "SELECT points FROM reputation_points WHERE user_id = ?",
                (str(interaction.user.id),)) as cursor:
                user_points_row = await cursor.fetchone()
            user_points = user_points_row[0] if user_points_row else 0

            if user_points < item_cost:
                await interaction.followup.send(
                    f"❌ Nie masz wystarczającej reputacji! Potrzebujesz **{item_cost}**, a masz **{user_points}**.",
                    ephemeral=True)
                return

            new_points = user_points - item_cost
            await db.execute(
                "UPDATE reputation_points SET points = ? WHERE user_id = ?",
                (new_points, str(interaction.user.id)))
            if stock is not None:
                await db.execute("UPDATE shop_items SET stock = stock - 1 WHERE id = ?", (item_id,))
            if category == "Specjalne role":
                await db.execute(
                    "INSERT INTO shop_purchases (user_id, item_id) VALUES (?, ?)",
                    (interaction.user.id, item_id))
            await db.commit()

        if role_id:
            try:
                role_to_add = interaction.guild.get_role(role_id)
                if role_to_add:
                    await interaction.user.add_roles(role_to_add, reason="Zakup w sklepie reputacji")
                    await interaction.followup.send(
                        f"✅ Gratulacje! Kupiłeś i otrzymałeś rolę **{item_name}** za **{item_cost}** reputacji. "
                        f"Twoje saldo: **{new_points}** rep.", ephemeral=True)
                else:
                    raise ValueError("Rola nie znaleziona")
            except Exception as e:
                print(f"Błąd podczas nadawania roli ze sklepu: {e}")
                await interaction.followup.send(
                    f"✅ Zakupiono **{item_name}**, ale wystąpił błąd przy nadawaniu roli. "
                    f"Administracja została powiadomiona.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"✅ Gratulacje! Kupiłeś **{item_name}** za **{item_cost}** reputacji. "
                f"Twoje saldo: **{new_points}** rep.\nAdministracja została powiadomiona.", ephemeral=True)

        if SHOP_CONFIG.get("channel_id") and category in ["VIP", "Premium", "Fajki", "Oferty Dnia"]:
            notif_channel = bot.get_channel(SHOP_CONFIG["channel_id"])
            if notif_channel:
                roles_to_mention = [
                    discord.utils.get(interaction.guild.roles, name=r_name)
                    for r_name in SHOP_CONFIG["manual_reward_roles"]]
                role_mentions = " ".join([r.mention for r in roles_to_mention if r])
                embed = discord.Embed(title="🛒 Nowy zakup w sklepie!",
                                      color=COLORS["success"], timestamp=datetime.now(POLAND_TZ))
                embed.add_field(name="Kupujący", value=interaction.user.mention, inline=False)
                embed.add_field(name="Przedmiot", value=f"{item_name} (ID: {item_id})", inline=False)
                embed.add_field(name="Koszt", value=f"{item_cost} reputacji", inline=False)
                embed.set_footer(text=FOOTER_TEXT)
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                await notif_channel.send(content=role_mentions, embed=embed)

        await log_action(interaction.guild, "Zakup w sklepie", interaction.user,
                         f"Przedmiot: {item_name}, Koszt: {item_cost} rep.")

# =========================================================
# --- GRUPY KOMEND ---
# =========================================================
reputation_group   = app_commands.Group(name="reputacja",   description="Zarządzanie reputacją użytkowników.")
recruitment_group  = app_commands.Group(name="rekrutacja",  description="Zarządzanie statusami rekrutacji.")
announcement_group = app_commands.Group(name="ogloszenie",  description="Zarządzanie ogłoszeniami i eventami.")
redakcja_group     = app_commands.Group(name="redakcja",    description="Komendy dla działu redakcji.")
podania_group      = app_commands.Group(name="podania",     description="Zarządzanie podaniami i cooldownami.")

# =========================================================
# --- KOMENDY SLASH ---
# =========================================================
@bot.tree.command(name="setup_logi", description="Konfiguruje kanał logów bota.")
async def setup_logi(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Kanał logów: {kanal.mention}.", ephemeral=True)
    await log_action(interaction.guild, "Skonfigurowano logi", interaction.user, f"Kanał: {kanal.mention}")


@bot.tree.command(name="setup_powiadomienia", description="Konfiguruje powiadomienia dla opiekunów.")
async def setup_powiadomienia(interaction: discord.Interaction, typ_zgloszenia: str,
                               kanal: discord.TextChannel, rola: Optional[discord.Role] = None):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    NOTIFICATION_CONFIG[typ_zgloszenia] = {'channel_id': kanal.id, 'role_id': rola.id if rola else None}
    await interaction.response.send_message(
        f"✅ Ustawiono powiadomienia dla `{typ_zgloszenia}` na kanale {kanal.mention}" +
        (f" z rolą {rola.mention}." if rola else "."), ephemeral=True)


@bot.tree.command(name="setup_przypomnienia", description="Włącza lub wyłącza automatyczne przypomnienia.")
async def setup_przypomnienia(interaction: discord.Interaction, wlaczone: bool,
                               dni: app_commands.Range[int, 1, 30] = 3):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    REMINDER_CONFIG["enabled"]    = wlaczone
    REMINDER_CONFIG["delay_days"] = dni
    status = "włączone" if wlaczone else "wyłączone"
    await interaction.response.send_message(
        f"✅ Przypomnienia **{status}**. Czas oczekiwania: **{dni} dni**.", ephemeral=True)


@bot.tree.command(name="setup_forum_propozycje", description="Tworzy panel zgłaszania propozycji i błędów.")
async def setup_forum_propozycje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = discord.Embed(
        title="💡 Propozycje i Błędy 🐛",
        description="Masz pomysł na ulepszenie serwera lub znalazłeś błąd?\nWybierz opcję z menu poniżej, a następnie wybierz serwer!",
        color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(
        name="Panel Zgłoszeń - Propozycje i Błędy", embed=embed,
        view=ForumSelectionView("proposals_bugs"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)


@bot.tree.command(name="setup_forum_skargi", description="Tworzy panel składania skarg i odwołań.")
async def setup_forum_skargi(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = discord.Embed(
        title="⚠️ Skargi i Odwołania 📋",
        description="Chcesz złożyć skargę lub odwołać się od kary?\nWybierz opcję z menu poniżej, a następnie wybierz serwer!",
        color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(
        name="Panel Zgłoszeń - Skargi i Odwołania", embed=embed,
        view=ForumSelectionView("complaints_appeals"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)


# --- PUNKT 2: SETUP REKRUTACJI Z ZAPISEM PANELU ---
@bot.tree.command(name="setup_forum_rekrutacje", description="Tworzy panel rekrutacyjny (Admin + Zaufany).")
async def setup_forum_rekrutacje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = await build_recruitment_embed("recruitment")
    thread_msg = await kanal_forum.create_thread(
        name="Panel Rekrutacyjny - Administracja", embed=embed,
        view=ForumSelectionView("recruitment"))
    # Zapisz panel do bazy danych
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO recruitment_panels (guild_id, channel_id, thread_id, message_id, panel_type) VALUES (?,?,?,?,?)",
            (str(interaction.guild.id), str(kanal_forum.id),
             str(thread_msg.thread.id), str(thread_msg.message.id), "recruitment"))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Panel rekrutacyjny utworzony na {kanal_forum.mention}!", ephemeral=True)


@bot.tree.command(name="setup_forum_rekrutacje_kreatywne",
                  description="Tworzy panel rekrutacyjny dla ról kreatywnych.")
async def setup_forum_rekrutacje_kreatywne(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    if not is_authorized(interaction, CREATIVE_RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = await build_recruitment_embed("creative_recruitment")
    thread_msg = await kanal_forum.create_thread(
        name="Panel Rekrutacyjny - Role Kreatywne", embed=embed,
        view=ForumSelectionView("creative_recruitment"))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO recruitment_panels (guild_id, channel_id, thread_id, message_id, panel_type) VALUES (?,?,?,?,?)",
            (str(interaction.guild.id), str(kanal_forum.id),
             str(thread_msg.thread.id), str(thread_msg.message.id), "creative_recruitment"))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Panel rekrutacji kreatywnej utworzony na {kanal_forum.mention}!", ephemeral=True)


# --- PUNKT 2: KOMENDA ODŚWIEŻANIA PANELU ---
@bot.tree.command(name="odswiez_rekrutacje",
                  description="Odświeża embed panelu rekrutacji (aktualizuje statusy stanowisk).")
async def odswiez_rekrutacje(interaction: discord.Interaction):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT thread_id, message_id, panel_type FROM recruitment_panels WHERE guild_id = ?",
            (str(interaction.guild.id),)) as cursor:
            panels = await cursor.fetchall()

    if not panels:
        await interaction.followup.send(
            "❌ Nie znaleziono żadnych paneli rekrutacji. Użyj najpierw `/setup_forum_rekrutacje`.",
            ephemeral=True)
        return

    updated = 0
    errors  = 0
    for thread_id, message_id, panel_type in panels:
        try:
            thread  = await interaction.guild.fetch_channel(int(thread_id))
            message = await thread.fetch_message(int(message_id))
            new_embed = await build_recruitment_embed(panel_type)
            await message.edit(embed=new_embed)
            updated += 1
        except Exception as e:
            print(f"Błąd odświeżania panelu (thread {thread_id}): {e}")
            errors += 1

    result_msg = f"✅ Odświeżono **{updated}** panel(i) rekrutacji."
    if errors:
        result_msg += f"\n⚠️ Nie udało się odświeżyć **{errors}** paneli (panel mógł zostać usunięty)."
    await interaction.followup.send(result_msg, ephemeral=True)


@bot.tree.command(name="info", description="Wyświetla informacje o aktywności użytkownika.")
async def info(interaction: discord.Interaction, uzytkownik: discord.Member):
    await interaction.response.defer(ephemeral=True)
    async with aiosqlite.connect(DB_PATH) as db:
        embed = discord.Embed(
            title=f"📋 Kartoteka: {uzytkownik.display_name}",
            color=uzytkownik.color, timestamp=datetime.now(POLAND_TZ))
        embed.set_thumbnail(url=uzytkownik.display_avatar.url)

        async with db.execute(
            "SELECT points FROM reputation_points WHERE user_id = ?", (str(uzytkownik.id),)) as cursor:
            rep = await cursor.fetchone()
        embed.add_field(name="⭐ Reputacja", value=rep[0] if rep else "0", inline=False)

        tables = {
            "applications": "Podania",
            "suggestions":  "Propozycje",
            "bug_reports":  "Błędy",
            "complaints":   "Skargi",
            "appeals":      "Odwołania"
        }
        for table, name in tables.items():
            async with db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (str(uzytkownik.id),)) as cursor:
                count_row = await cursor.fetchone()
            count = count_row[0]
            if count > 0:
                embed.add_field(name=name, value=str(count), inline=True)

        # Aktywne cooldowny
        async with db.execute(
            "SELECT application_type, rejected_at FROM application_cooldowns WHERE user_id = ?",
            (str(uzytkownik.id),)) as cursor:
            cooldowns = await cursor.fetchall()
        if cooldowns:
            cd_lines = []
            now = datetime.now(POLAND_TZ)
            for app_type, rejected_at in cooldowns:
                rejected_dt = datetime.fromisoformat(rejected_at)
                if rejected_dt.tzinfo is None:
                    rejected_dt = POLAND_TZ.localize(rejected_dt)
                cd_end = rejected_dt + timedelta(days=COOLDOWN_DAYS)
                if cd_end > now:
                    ts = int(cd_end.timestamp())
                    cd_lines.append(f"• {app_type}: <t:{ts}:R>")
            if cd_lines:
                embed.add_field(name="⏳ Aktywne cooldowny", value="\n".join(cd_lines), inline=False)

        embed.set_footer(text=FOOTER_TEXT)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="moje_zgloszenia", description="Wyświetla listę Twoich zgłoszeń i ich status.")
async def moje_zgloszenia(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    async with aiosqlite.connect(DB_PATH) as db:
        embed = discord.Embed(
            title="📋 Twoje zgłoszenia",
            color=interaction.user.color, timestamp=datetime.now(POLAND_TZ))
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text=FOOTER_TEXT)

        tables_map = {
            "Propozycje": ("suggestions",  "category",         "status"),
            "Błędy":      ("bug_reports",  "category",         "status"),
            "Skargi":     ("complaints",   "complaint_type",   "status"),
            "Odwołania":  ("appeals",      "appeal_type",      "status"),
            "Podania":    ("applications", "application_type", "status"),
        }
        content = ""
        for name, (table, type_col, status_col) in tables_map.items():
            async with db.execute(
                f"SELECT {type_col}, {status_col}, thread_id FROM {table} WHERE user_id = ?",
                (str(interaction.user.id),)) as cursor:
                rows = await cursor.fetchall()
            if rows:
                content += f"**{name}**\n"
                for row in rows:
                    thread_link = (
                        f" ([Link](https://discord.com/channels/{interaction.guild.id}/{row[2]}))"
                        if row[2] else ""
                    )
                    content += f"- `{row[0]}`: *{row[1]}*{thread_link}\n"
                content += "\n"
        embed.description = content if content else "Nie znaleziono żadnych Twoich zgłoszeń."
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="ankieta", description="Tworzy ankietę z przyciskami.")
async def ankieta(interaction: discord.Interaction, pytanie: str, opcje: str):
    if not is_authorized(interaction, GENERAL_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
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
        await db.execute(
            "INSERT INTO polls (message_id, question, options, votes, author_id) VALUES (?,?,?,?,?)",
            (message.id, pytanie, json.dumps(options_list), initial_votes, interaction.user.id))
        await db.commit()
    await interaction.edit_original_response(content="✅ Ankieta została utworzona!")


# =========================================================
# --- PUNKT 1: KOMENDY COOLDOWNÓW ---
# =========================================================
@podania_group.command(name="zdejmij_cooldown",
                       description="Zdejmuje cooldown na podanie z danego użytkownika.")
@app_commands.describe(
    uzytkownik="Użytkownik, któremu zdejmujesz cooldown",
    stanowisko="Stanowisko (np. Podanie Admin JB)")
async def zdejmij_cooldown(interaction: discord.Interaction,
                            uzytkownik: discord.Member, stanowisko: str):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if stanowisko not in ALL_RECRUITMENT_TYPES:
        await interaction.response.send_message(
            f"❌ Nieprawidłowe stanowisko. Dostępne:\n" + "\n".join(f"• {t}" for t in ALL_RECRUITMENT_TYPES),
            ephemeral=True)
        return
    await remove_application_cooldown(str(uzytkownik.id), stanowisko)
    await interaction.response.send_message(
        f"✅ Zdjęto cooldown na **{stanowisko}** dla {uzytkownik.mention}.", ephemeral=True)
    await log_action(interaction.guild, "Zdjęto cooldown na podanie", interaction.user,
                     f"Użytkownik: {uzytkownik.mention}, Stanowisko: {stanowisko}")


@podania_group.command(name="sprawdz_cooldown",
                       description="Sprawdza aktywne cooldowny użytkownika na podania.")
async def sprawdz_cooldown(interaction: discord.Interaction, uzytkownik: discord.Member):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT application_type, rejected_at FROM application_cooldowns WHERE user_id = ?",
            (str(uzytkownik.id),)) as cursor:
            cooldowns = await cursor.fetchall()

    embed = discord.Embed(
        title=f"⏳ Cooldowny na podania — {uzytkownik.display_name}",
        color=COLORS["warn"])
    if not cooldowns:
        embed.description = "Brak aktywnych cooldownów."
    else:
        now   = datetime.now(POLAND_TZ)
        lines = []
        for app_type, rejected_at in cooldowns:
            rejected_dt = datetime.fromisoformat(rejected_at)
            if rejected_dt.tzinfo is None:
                rejected_dt = POLAND_TZ.localize(rejected_dt)
            cd_end = rejected_dt + timedelta(days=COOLDOWN_DAYS)
            if cd_end > now:
                ts = int(cd_end.timestamp())
                lines.append(f"• **{app_type}** — wygasa <t:{ts}:R>")
            else:
                lines.append(f"• **{app_type}** — ✅ wygasł")
        embed.description = "\n".join(lines) if lines else "Brak aktywnych cooldownów."
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@zdejmij_cooldown.autocomplete('stanowisko')
async def cooldown_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=pos, value=pos)
        for pos in ALL_RECRUITMENT_TYPES if current.lower() in pos.lower()
    ]


# =========================================================
# --- KOMENDY SKLEPU ---
# =========================================================
@bot.tree.command(name="setup_powiadomienia_sklep",
                  description="Konfiguruje kanał powiadomień o zakupach.")
async def setup_powiadomienia_sklep(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    SHOP_CONFIG["channel_id"] = kanal.id
    await interaction.response.send_message(
        f"✅ Kanał powiadomień o zakupach: {kanal.mention}.", ephemeral=True)


@bot.tree.command(name="dodaj_przedmiot", description="Dodaje przedmiot do sklepu (ręczna nagroda).")
@app_commands.describe(kategoria="Kategoria przedmiotu", nazwa="Nazwa przedmiotu",
                       koszt="Cena w reputacji", opis="Opis przedmiotu")
async def dodaj_przedmiot(interaction: discord.Interaction, kategoria: str, nazwa: str,
                           koszt: app_commands.Range[int, 1], opis: str):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if kategoria not in SHOP_CATEGORIES:
        await interaction.response.send_message(
            f"❌ Nieprawidłowa kategoria. Dostępne: {', '.join(SHOP_CATEGORIES)}", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?,?,?,?,NULL,NULL)",
            (nazwa, koszt, opis, kategoria))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Dodano `{nazwa}` do kategorii `{kategoria}` za **{koszt}** rep.", ephemeral=True)


@bot.tree.command(name="dodaj_specjalna_role",
                  description="Dodaje limitowaną rolę do sklepu (automatyczna).")
@app_commands.describe(nazwa="Nazwa przedmiotu", koszt="Cena w reputacji",
                       rola="Rola do nadania", ilosc="Liczba dostępnych sztuk", opis="Opis przedmiotu")
async def dodaj_specjalna_role(interaction: discord.Interaction, nazwa: str,
                                koszt: app_commands.Range[int, 1], rola: discord.Role,
                                ilosc: app_commands.Range[int, 1], opis: str):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?,?,?,?,?,?)",
            (nazwa, koszt, opis, "Specjalne role", rola.id, ilosc))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Dodano rolę {rola.mention} jako `{nazwa}` ({ilosc} szt.) za **{koszt}** rep.", ephemeral=True)


# --- PUNKT 6: EDYCJA PRZEDMIOTU ---
@bot.tree.command(name="edytuj_przedmiot", description="Edytuje istniejący przedmiot w sklepie.")
@app_commands.describe(id_przedmiotu="ID przedmiotu do edycji (widoczne w sklepie)")
async def edytuj_przedmiot(interaction: discord.Interaction, id_przedmiotu: int):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT name FROM shop_items WHERE id = ?", (id_przedmiotu,)) as cursor:
            item = await cursor.fetchone()
    if not item:
        await interaction.response.send_message(
            f"❌ Nie znaleziono przedmiotu o ID **{id_przedmiotu}**.", ephemeral=True)
        return
    await interaction.response.send_modal(EditItemModal(item_id=id_przedmiotu))


@dodaj_przedmiot.autocomplete('kategoria')
async def dodaj_przedmiot_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=cat, value=cat)
        for cat in SHOP_CATEGORIES if current.lower() in cat.lower() and cat != "Specjalne role"
    ]


@bot.tree.command(name="usun_przedmiot", description="Usuwa przedmiot ze sklepu.")
async def usun_przedmiot(interaction: discord.Interaction, id_przedmiotu: int):
    if not is_authorized(interaction, SHOP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM shop_items WHERE id = ?", (id_przedmiotu,))
        await db.commit()
    if cursor.rowcount > 0:
        await interaction.response.send_message(
            f"✅ Usunięto przedmiot ID **{id_przedmiotu}**.", ephemeral=True)
    else:
        await interaction.response.send_message(
            f"❌ Nie znaleziono przedmiotu ID **{id_przedmiotu}**.", ephemeral=True)


@bot.tree.command(name="setup_sklep_panel", description="Tworzy interaktywny panel sklepu.")
async def setup_sklep_panel(interaction: discord.Interaction, kanal: discord.TextChannel):
    if not is_authorized(interaction, SETUP_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    embed = await create_shop_embed(SHOP_CATEGORIES[0])
    view  = ShopView(initial_category=SHOP_CATEGORIES[0])
    await kanal.send(embed=embed, view=view)
    await interaction.response.send_message(
        f"✅ Panel sklepu utworzony na {kanal.mention}.", ephemeral=True)


@bot.tree.command(name="ranking", description="Wyświetla ranking użytkowników z największą reputacją.")
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, points FROM reputation_points ORDER BY points DESC LIMIT 10") as cursor:
            top_users = await cursor.fetchall()
    embed = discord.Embed(title="🏆 Ranking Reputacji - Top 10", color=COLORS["main"])
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    if not top_users:
        embed.description = "Ranking jest pusty."
    else:
        medals      = ["🥇", "🥈", "🥉"]
        description = ""
        for i, (user_id, points) in enumerate(top_users):
            user      = interaction.guild.get_member(int(user_id))
            user_name = user.display_name if user else f"Użytkownik (ID: {user_id})"
            medal     = medals[i] if i < 3 else f"**{i+1}.**"
            description += f"{medal} {user_name} — `{points} rep.`\n"
        embed.description = description
    await interaction.followup.send(embed=embed)


# =========================================================
# --- PUNKT 5: KOMENDA STATYSTYKI ---
# =========================================================
@bot.tree.command(name="statystyki", description="Wyświetla statystyki zgłoszeń i rekrutacji.")
async def statystyki(interaction: discord.Interaction):
    if not is_authorized(interaction, GENERAL_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    async with aiosqlite.connect(DB_PATH) as db:
        embed = discord.Embed(
            title="📊 Statystyki serwera",
            color=COLORS["main"],
            timestamp=datetime.now(POLAND_TZ))
        if LOGO_URL:
            embed.set_thumbnail(url=LOGO_URL)

        # --- Otwarte zgłoszenia ---
        open_counts = {}
        open_queries = {
            "Propozycje":  ("suggestions",  "status = 'pending'"),
            "Błędy":       ("bug_reports",  "status = 'reported'"),
            "Skargi":      ("complaints",   "status = 'open'"),
            "Odwołania":   ("appeals",      "status = 'pending'"),
            "Podania":     ("applications", "status = 'pending'"),
        }
        open_lines = []
        for label, (table, where) in open_queries.items():
            async with db.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}") as cursor:
                row = await cursor.fetchone()
            count = row[0]
            open_counts[label] = count
            emoji = "🟡" if count > 0 else "🟢"
            open_lines.append(f"{emoji} **{label}:** {count} oczekujących")
        embed.add_field(
            name="📂 Oczekujące zgłoszenia",
            value="\n".join(open_lines),
            inline=False)

        # --- Statystyki ostatnich 7 dni ---
        week_ago = (datetime.now(POLAND_TZ) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        week_lines = []
        for label, (table, _) in open_queries.items():
            async with db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE created_at >= ?", (week_ago,)) as cursor:
                row = await cursor.fetchone()
            week_lines.append(f"• **{label}:** {row[0]}")
        embed.add_field(name="📅 Złożone w ciągu 7 dni", value="\n".join(week_lines), inline=True)

        # --- Statystyki ostatnich 30 dni ---
        month_ago = (datetime.now(POLAND_TZ) - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        month_lines = []
        for label, (table, _) in open_queries.items():
            async with db.execute(
                f"SELECT COUNT(*) FROM {table} WHERE created_at >= ?", (month_ago,)) as cursor:
                row = await cursor.fetchone()
            month_lines.append(f"• **{label}:** {row[0]}")
        embed.add_field(name="📅 Złożone w ciągu 30 dni", value="\n".join(month_lines), inline=True)

        # --- Status rekrutacji ---
        async with db.execute("SELECT position, is_open FROM recruitment_status") as cursor:
            rec_rows = await cursor.fetchall()
        if rec_rows:
            rec_lines = []
            for pos, is_open in rec_rows:
                emoji = "🟢" if is_open else "🔴"
                rec_lines.append(f"{emoji} {pos}")
            embed.add_field(
                name="🛡️ Status rekrutacji",
                value="\n".join(rec_lines),
                inline=False)

        # --- Aktywne cooldowny ---
        async with db.execute("SELECT COUNT(*) FROM application_cooldowns") as cursor:
            row = await cursor.fetchone()
        cd_count = row[0]
        embed.add_field(name="⏳ Aktywne cooldowny na podania", value=str(cd_count), inline=True)

        # --- Top reputacja ---
        async with db.execute(
            "SELECT user_id, points FROM reputation_points ORDER BY points DESC LIMIT 3") as cursor:
            top3 = await cursor.fetchall()
        if top3:
            medals   = ["🥇", "🥈", "🥉"]
            top_lines= []
            for i, (uid, pts) in enumerate(top3):
                member = interaction.guild.get_member(int(uid))
                name   = member.display_name if member else f"ID:{uid}"
                top_lines.append(f"{medals[i]} {name} — `{pts} rep.`")
            embed.add_field(name="🏆 Top 3 reputacja", value="\n".join(top_lines), inline=True)

        embed.set_footer(text=FOOTER_TEXT)
    await interaction.followup.send(embed=embed)


# =========================================================
# --- KOMENDY REPUTACJI ---
# =========================================================
@reputation_group.command(name="dodaj", description="Dodaje reputację użytkownikowi.")
async def reputacja_dodaj(interaction: discord.Interaction, uzytkownik: discord.Member,
                           ilosc: app_commands.Range[int, 1]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='add')
    await interaction.response.send_message(
        f"✅ Dodano **{ilosc}** rep dla {uzytkownik.mention}. Saldo: **{new_balance}** rep.", ephemeral=True)


@reputation_group.command(name="usun", description="Usuwa reputację użytkownikowi.")
async def reputacja_usun(interaction: discord.Interaction, uzytkownik: discord.Member,
                          ilosc: app_commands.Range[int, 1]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, -ilosc, mode='add')
    await interaction.response.send_message(
        f"✅ Usunięto **{ilosc}** rep od {uzytkownik.mention}. Saldo: **{new_balance}** rep.", ephemeral=True)


@reputation_group.command(name="ustaw", description="Ustawia reputację na konkretną wartość.")
async def reputacja_ustaw(interaction: discord.Interaction, uzytkownik: discord.Member,
                           ilosc: app_commands.Range[int, 0]):
    if not is_authorized(interaction, REPUTATION_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='set')
    await interaction.response.send_message(
        f"✅ Ustawiono reputację {uzytkownik.mention} na **{new_balance}** rep.", ephemeral=True)


# =========================================================
# --- KOMENDY REKRUTACJI ---
# =========================================================
@recruitment_group.command(name="otworz", description="Otwiera rekrutację na dane stanowisko.")
async def rekrutacja_otworz(interaction: discord.Interaction, stanowisko: str):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if stanowisko not in ALL_RECRUITMENT_TYPES:
        await interaction.response.send_message("❌ Nieprawidłowe stanowisko.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 1)", (stanowisko,))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Rekrutacja na **{stanowisko}** jest teraz **otwarta**.\n"
        f"💡 Użyj `/odswiez_rekrutacje` aby zaktualizować panel.", ephemeral=True)


@recruitment_group.command(name="zamknij", description="Zamyka rekrutację na dane stanowisko.")
async def rekrutacja_zamknij(interaction: discord.Interaction, stanowisko: str):
    if not is_authorized(interaction, RECRUITMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    if stanowisko not in ALL_RECRUITMENT_TYPES:
        await interaction.response.send_message("❌ Nieprawidłowe stanowisko.", ephemeral=True)
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 0)", (stanowisko,))
        await db.commit()
    await interaction.response.send_message(
        f"✅ Rekrutacja na **{stanowisko}** jest teraz **zamknięta**.\n"
        f"💡 Użyj `/odswiez_rekrutacje` aby zaktualizować panel.", ephemeral=True)


@rekrutacja_otworz.autocomplete('stanowisko')
@rekrutacja_zamknij.autocomplete('stanowisko')
async def rekrutacja_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=pos, value=pos)
        for pos in ALL_RECRUITMENT_TYPES if current.lower() in pos.lower()
    ]


# =========================================================
# --- KOMENDY OGŁOSZEŃ ---
# =========================================================
@announcement_group.command(name="wyslij", description="Wysyła ogłoszenie na wybrany kanał.")
async def ogloszenie_wyslij(interaction: discord.Interaction, kanal: discord.TextChannel,
                             rola: Optional[discord.Role] = None):
    if not is_authorized(interaction, ANNOUNCEMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.send_modal(AnnouncementModal(channel=kanal, role=rola))


@announcement_group.command(name="event", description="Tworzy wydarzenie z przyciskiem zapisu.")
async def ogloszenie_event(interaction: discord.Interaction, kanal: discord.TextChannel,
                            rola: Optional[discord.Role] = None):
    if not is_authorized(interaction, ANNOUNCEMENT_ADMIN_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.send_modal(EventModal(channel=kanal, role=rola))


# =========================================================
# --- KOMENDY REDAKCJI ---
# =========================================================
@redakcja_group.command(name="pytanie_dnia", description="Publikuje nowe pytanie dnia.")
async def pytanie_dnia(interaction: discord.Interaction, kanal: discord.ForumChannel, pytanie: str):
    if not is_authorized(interaction, REDAKCJA_ROLES):
        await interaction.response.send_message("❌ Nie masz uprawnień.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO editorial_counters (type, count) VALUES ('pytanie_dnia', 0) ON CONFLICT(type) DO NOTHING")
        await db.execute("UPDATE editorial_counters SET count = count + 1 WHERE type = 'pytanie_dnia'")
        async with db.execute(
            "SELECT count FROM editorial_counters WHERE type = 'pytanie_dnia'") as cursor:
            row = await cursor.fetchone()
        new_count = row[0]
        await db.commit()
    title = f"Pytanie dnia #{new_count}"
    embed = discord.Embed(
        title=f"❓ {title}", description=pytanie,
        color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
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
    embed = discord.Embed(
        title=f"❓ {tytul}",
        description="Zapraszamy do zadawania pytań w odpowiedziach poniżej!",
        color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=f"Sesja Q&A przez: {interaction.user.display_name} | {FOOTER_TEXT}")
    await kanal.create_thread(name=tytul, embed=embed)
    await interaction.response.send_message("✅ Pomyślnie rozpoczęto sesję Q&A.", ephemeral=True)


# =========================================================
# --- ZADANIA W TLE ---
# =========================================================
@tasks.loop(hours=1)
async def check_for_old_posts():
    if not REMINDER_CONFIG["enabled"]:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        delay          = timedelta(days=REMINDER_CONFIG["delay_days"])
        time_threshold = datetime.now(POLAND_TZ) - delay
        tables_to_check = {
            "suggestions":  "category",
            "bug_reports":  "category",
            "complaints":   "complaint_type",
            "appeals":      "appeal_type",
            "applications": "application_type",
        }
        for table, type_col in tables_to_check.items():
            async with db.execute(
                f"SELECT thread_id, {type_col} FROM {table} "
                f"WHERE status NOT LIKE '%odrzucon%' AND status NOT LIKE '%przyjęt%' "
                f"AND status NOT LIKE '%naprawion%' AND reminder_sent = 0 AND created_at < ?",
                (time_threshold.strftime('%Y-%m-%d %H:%M:%S.%f'),)) as cursor:
                old_posts = await cursor.fetchall()

            for thread_id, post_type in old_posts:
                for guild in bot.guilds:
                    try:
                        thread = await guild.fetch_channel(int(thread_id))
                        if not thread.locked:
                            await send_notification(guild, post_type, thread.jump_url, is_reminder=True)
                        await db.execute(
                            f"UPDATE {table} SET reminder_sent = 1 WHERE thread_id = ?", (thread_id,))
                        await db.commit()
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        continue


# =========================================================
# --- EVENTY BOTA ---
# =========================================================
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
    bot.add_view(AdminApplicationServerView())

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
    bot.tree.add_command(podania_group)

    check_for_old_posts.start()

    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")


# =========================================================
# --- URUCHOMIENIE BOTA ---
# =========================================================
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if not TOKEN:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! BRAK TOKENA! Ustaw zmienną DISCORD_BOT_TOKEN !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
else:
    bot.run(TOKEN)
