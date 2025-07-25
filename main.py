import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime, timedelta
import sqlite3
from typing import Optional
import pytz

# --- PODSTAWOWA KONFIGURACJA ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
LOG_CHANNEL_ID = None
POLAND_TZ = pytz.timezone('Europe/Warsaw')

# --- BRANDING & COLORS ---
LOGO_URL = "https://i.postimg.cc/0jY1crF6/moje-logo2.jpg" 
FOOTER_TEXT = "© Aelios2.pl | Bot by Meep"
COLORS = {
    "main": 0xE67E22,      # Pomarańczowy
    "success": 0x2ECC71,   # Zielony
    "error": 0xE74C3C,     # Czerwony
    "warn": 0x3498DB,      # Jasnoniebieski (dla przypomnień)
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
RECRUITMENT_TYPES = ["Podanie Admin JB", "Podanie Zaufany JB", "Podanie Admin DC"]

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


# --- BAZA DANYCH ---
def init_database():
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()

    # Tworzymy wszystkie tabele, jeśli nie istnieją.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, username TEXT NOT NULL,
            category TEXT NOT NULL, description TEXT NOT NULL, reason TEXT NOT NULL,
            thread_id TEXT, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bug_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category TEXT NOT NULL,
            bug_type TEXT NOT NULL, description TEXT NOT NULL, evidence TEXT,
            thread_id TEXT, status TEXT DEFAULT 'reported', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, complaint_type TEXT NOT NULL,
            target_user TEXT NOT NULL, data TEXT NOT NULL, thread_id TEXT,
            status TEXT DEFAULT 'open', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, appeal_type TEXT NOT NULL,
            data TEXT NOT NULL, thread_id TEXT, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, username TEXT NOT NULL,
            application_type TEXT NOT NULL, data TEXT NOT NULL, thread_id TEXT,
            status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reputation_points (
            user_id TEXT PRIMARY KEY, points INTEGER DEFAULT 0
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS polls (
            message_id INTEGER PRIMARY KEY, question TEXT NOT NULL, options TEXT NOT NULL,
            votes TEXT NOT NULL, author_id INTEGER NOT NULL
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            cost INTEGER NOT NULL,
            category TEXT NOT NULL,
            role_id INTEGER DEFAULT NULL,
            stock INTEGER DEFAULT NULL 
        )''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_purchases (
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, item_id)
        )''')
    # NOWA TABELA: Status rekrutacji
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recruitment_status (
            position TEXT PRIMARY KEY,
            is_open INTEGER DEFAULT 1
        )''')
    
    tables_to_alter = {
        "suggestions": "reminder_sent INTEGER DEFAULT 0",
        "bug_reports": "reminder_sent INTEGER DEFAULT 0",
        "complaints": "reminder_sent INTEGER DEFAULT 0",
        "appeals": "reminder_sent INTEGER DEFAULT 0",
        "applications": "reminder_sent INTEGER DEFAULT 0"
    }

    for table, column_def in tables_to_alter.items():
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                raise

    conn.commit()
    conn.close()

# --- FUNKCJE POMOCNICZE BAZY DANYCH ---
def save_suggestion(user_id, username, category, description, reason, thread_id):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO suggestions (user_id, username, category, description, reason, thread_id) VALUES (?, ?, ?, ?, ?, ?)',(user_id, username, category, description, reason, thread_id))
    conn.commit()
    conn.close()

def save_bug_report(user_id, category, bug_type, description, evidence, thread_id):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bug_reports (user_id, category, bug_type, description, evidence, thread_id) VALUES (?, ?, ?, ?, ?, ?)',(user_id, category, bug_type, description, evidence, thread_id))
    conn.commit()
    conn.close()

def save_complaint(user_id, complaint_type, target_user, data, thread_id):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO complaints (user_id, complaint_type, target_user, data, thread_id) VALUES (?, ?, ?, ?, ?)',(user_id, complaint_type, target_user, json.dumps(data), thread_id))
    conn.commit()
    conn.close()

def save_appeal(user_id, appeal_type, data, thread_id):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO appeals (user_id, appeal_type, data, thread_id) VALUES (?, ?, ?, ?)',(user_id, appeal_type, json.dumps(data), thread_id))
    conn.commit()
    conn.close()

def save_application(user_id, username, app_type, data, thread_id):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO applications (user_id, username, application_type, data, thread_id) VALUES (?, ?, ?, ?, ?)',(user_id, username, app_type, json.dumps(data), thread_id))
    conn.commit()
    conn.close()

async def update_reputation(user_id: int, points: int, mode: str = 'add'):
    """Zarządza reputacją użytkownika (dodaje, usuwa, ustawia)."""
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO reputation_points (user_id, points) VALUES (?, 0)", (str(user_id),))
    if mode == 'add':
        cursor.execute("UPDATE reputation_points SET points = points + ? WHERE user_id = ?", (points, str(user_id)))
    elif mode == 'set':
        cursor.execute("UPDATE reputation_points SET points = ? WHERE user_id = ?", (points, str(user_id)))
    conn.commit()
    cursor.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(user_id),))
    new_balance = cursor.fetchone()[0]
    conn.close()
    return new_balance

# --- FUNKCJE POMOCNICZE ---
def has_jb_permissions(user: discord.Member) -> bool:
    return any(role.name == "Opiekun JB" for role in user.roles) or user.guild_permissions.administrator

def has_discord_permissions(user: discord.Member) -> bool:
    return any(role.name == "Opiekun Discord" for role in user.roles) or user.guild_permissions.administrator

def has_permission_for_type(user: discord.Member, item_type: str) -> bool:
    if "jb" in item_type.lower(): return has_jb_permissions(user)
    elif "discord" in item_type.lower() or "dc" in item_type.lower(): return has_discord_permissions(user)
    return user.guild_permissions.administrator

async def log_action(guild: discord.Guild, action: str, user: discord.Member, details: str = ""):
    if not LOG_CHANNEL_ID: return
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel: return
    embed = discord.Embed(title="📋 Log Akcji", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    embed.add_field(name="👤 Użytkownik", value=user.mention, inline=True)
    embed.add_field(name="🔧 Akcja", value=action, inline=True)
    if details: embed.add_field(name="📝 Szczegóły", value=details, inline=False)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text=f"ID: {user.id} | {FOOTER_TEXT}")
    try: await log_channel.send(embed=embed)
    except discord.HTTPException: pass

async def send_notification(guild: discord.Guild, post_type: str, thread_url: str, is_reminder: bool = False):
    config = NOTIFICATION_CONFIG.get(post_type)
    if not config: return
    channel = guild.get_channel(config['channel_id'])
    if not channel: return
    role_mention = f"<@&{config['role_id']}>" if config.get('role_id') else ""
    title = f"⏰ Przypomnienie: {post_type}" if is_reminder else f"🔔 Nowe zgłoszenie: {post_type}"
    description = f"Zgłoszenie czeka na reakcję od ponad {REMINDER_CONFIG['delay_days']} dni.\n\n[Przejdź do posta]({thread_url})" if is_reminder else f"Nowy post czeka na Twoją uwagę.\n\n[Przejdź do posta]({thread_url})"
    
    color = COLORS["main"]
    if is_reminder:
        color = COLORS["warn"]
    elif post_type.startswith("Podanie"):
        color = COLORS["success"]

    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    try: await channel.send(content=role_mention, embed=embed)
    except discord.HTTPException: pass

# --- MODALE ---
class SuggestionModal(discord.ui.Modal):
    def __init__(self, suggestion_type: str):
        super().__init__(title=f"Nowa {suggestion_type}")
        self.description = discord.ui.TextInput(label="Opis propozycji", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.reason = discord.ui.TextInput(label="Dlaczego ma zostać wprowadzona?", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)
    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title.replace("Nowa ", ""), "💡")

class BugReportModal(discord.ui.Modal):
    def __init__(self, bug_type: str):
        super().__init__(title=f"Nowy {bug_type}")
        self.description = discord.ui.TextInput(label="Opis błędu", style=discord.TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.description)
        self.evidence = discord.ui.TextInput(label="Dowody (linki do screenów, filmów)", required=False, max_length=1024)
        self.add_item(self.evidence)
    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, self.title.replace("Nowy ", ""), "🐛")

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

class AdminApplicationModal(discord.ui.Modal, title="Podanie Admin JB"):
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie i swoim doświadczeniu", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Admin JB", "📄")

class TrustedApplicationModal(discord.ui.Modal, title="Podanie Zaufany JB"):
    nick = discord.ui.TextInput(label="Nick z serwera", required=True)
    age = discord.ui.TextInput(label="Wiek", required=True, max_length=3)
    tsarvar = discord.ui.TextInput(label="Link do TSARVAR i profilu Steam", required=True)
    steam_id = discord.ui.TextInput(label="SteamID64", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Zaufany JB", "📄")

class DiscordAdminApplicationModal(discord.ui.Modal, title="Podanie Admin DC"):
    server_time = discord.ui.TextInput(label="Od kiedy jesteś na tym serwerze Discord?", required=True)
    experience = discord.ui.TextInput(label="Doświadczenie jako administrator", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    knowledge = discord.ui.TextInput(label="Znajomość Discorda (od 1 do 10)", required=True, max_length=2)
    availability = discord.ui.TextInput(label="Ile czasu dziennie mógłbyś poświęcić?", required=True)
    about = discord.ui.TextInput(label="Napisz coś o sobie", style=discord.TextStyle.paragraph, required=True, max_length=1024)
    async def on_submit(self, interaction: discord.Interaction):
        await create_generic_post(self, interaction, "Podanie Admin DC", "📄")

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

# --- LOGIKA DECYZJI ---
async def process_decision(interaction: discord.Interaction, original_interaction: discord.Interaction, action: str, post_type: str, author_id: int, reason_text: str):
    original_message = original_interaction.message
    original_embed = original_message.embeds[0]
    
    action_map = {
        "accept_suggestion": {"text": "Propozycja przyjęta", "color": COLORS["success"], "points": 5, "prefix": "[Zaakceptowane]", "final": True},
        "reject_suggestion": {"text": "Propozycja odrzucona", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
        "accept_bug":        {"text": "W trakcie naprawy", "color": COLORS["warn"], "points": 0, "prefix": "[W trakcie]", "final": False},
        "resolve_bug":       {"text": "Naprawiony", "color": COLORS["success"], "points": 3, "prefix": "[Naprawione]", "final": True},
        "reject_bug":        {"text": "Zgłoszenie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
        "accept_complaint":  {"text": "Skarga rozpatrzona pozytywnie", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
        "reject_complaint":  {"text": "Skarga odrzucona", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
        "accept_appeal":     {"text": "Odwołanie zaakceptowane", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
        "reject_appeal":     {"text": "Odwołanie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
        "accept_application": {"text": "Podanie przyjęte", "color": COLORS["success"], "points": 0, "prefix": "[Zaakceptowane]", "final": True},
        "reject_application": {"text": "Podanie odrzucone", "color": COLORS["error"], "points": 0, "prefix": "[Odrzucone]", "final": True},
    }
    
    action_details = action_map.get(action)
    if not action_details: return

    original_embed.color = action_details["color"]
    for i, field in enumerate(original_embed.fields):
        if field.name == "📊 Status":
            original_embed.set_field_at(i, name="📊 Status", value=action_details["text"], inline=True)
            break
    
    decision_embed = discord.Embed(title="✅ Decyzja podjęta!", color=action_details["color"])
    decision_embed.add_field(name="Status", value=action_details["text"], inline=True)
    decision_embed.add_field(name="Rozpatrzył", value=interaction.user.mention, inline=True)
    if reason_text:
        decision_embed.add_field(name="Notatka od administracji", value=reason_text, inline=False)
    if LOGO_URL: decision_embed.set_thumbnail(url=LOGO_URL)
    decision_embed.set_footer(text=FOOTER_TEXT)

    if action_details["points"] > 0: await update_reputation(author_id, action_details["points"], mode='add')

    dm_message = ""
    if action == "accept_application":
        dm_message = f"🎉 Gratulacje! Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało zaakceptowane!"
        member = interaction.guild.get_member(author_id)
        if member:
            try:
                roles_map = {"Podanie Admin JB": ["Junior Admin JB", "Administracja JB"], "Podanie Zaufany JB": ["Zaufany JB", "Administracja JB"], "Podanie Admin DC": ["Admin Discord"]}
                roles_to_add_names = roles_map.get(post_type, [])
                roles_to_add = [discord.utils.get(interaction.guild.roles, name=name) for name in roles_to_add_names]
                await member.add_roles(*[r for r in roles_to_add if r], reason=f"Akceptacja podania: {post_type}")
            except discord.Forbidden:
                await original_interaction.channel.send(f"⚠️ **Błąd uprawnień!** Nie udało się nadać roli {member.mention}. Upewnij się, że rola bota jest wyżej w hierarchii niż nadawane role.")
            except Exception as e:
                print(f"Błąd podczas nadawania roli: {e}")
    elif action == "reject_application":
        dm_message = f"😔 Niestety, Twoje podanie na **{post_type.replace('Podanie ', '')}** zostało odrzucone."

    new_view = None if action_details["final"] else ManagementView(post_type, author_id, is_in_progress=True)
    
    await original_message.edit(embed=original_embed, view=new_view)
    await original_interaction.channel.send(embed=decision_embed)

    if action_details["final"]:
        current_name = original_interaction.channel.name
        new_name = f"{action_details['prefix']} {current_name}"
        if len(new_name) > 100: new_name = new_name[:97] + "..."
        await original_interaction.channel.edit(name=new_name, locked=True, archived=True)
    
    if dm_message:
        try:
            member = interaction.guild.get_member(author_id)
            if member: await member.send(dm_message)
        except discord.Forbidden:
            await original_interaction.channel.send(f"⚠️ Nie udało się wysłać wiadomości DM.", silent=True)

    await log_action(interaction.guild, f"Zarządzano postem: {action_details['text']}", interaction.user, f"Post: {original_interaction.channel.mention}")

# --- FUNKCJE TWORZĄCE POSTY ---
async def create_generic_post(modal: discord.ui.Modal, interaction: discord.Interaction, post_type: str, emoji: str):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title=f"{emoji} Nowe zgłoszenie: {post_type}", color=COLORS["main"], timestamp=datetime.now(POLAND_TZ))
    for item in modal.children:
        embed.add_field(name=item.label, value=item.value, inline=False)
    embed.add_field(name="👤 Autor", value=interaction.user.mention, inline=False)
    embed.add_field(name="📊 Status", value="Oczekuje na decyzję", inline=True)
    embed.set_thumbnail(url=interaction.user.display_avatar.url) # Używamy avatara autora
    embed.set_footer(text=FOOTER_TEXT)

    try:
        forum_channel = interaction.channel.parent if isinstance(interaction.channel, discord.Thread) else interaction.channel
        tag = discord.utils.get(forum_channel.available_tags, name=post_type)
        if not tag:
            await interaction.followup.send(f"❌ Błąd: Nie znaleziono tagu '{post_type}'.", ephemeral=True)
            return

        post_title = f"{post_type}: {interaction.user.display_name}"
        thread_message = await forum_channel.create_thread(name=post_title, embed=embed, applied_tags=[tag], view=ManagementView(post_type, interaction.user.id))
        
        data = {item.label: item.value for item in modal.children}
        if post_type.startswith("Propozycja"): save_suggestion(str(interaction.user.id), interaction.user.display_name, post_type, data.get('Opis propozycji'), data.get('Dlaczego ma zostać wprowadzona?'), str(thread_message.thread.id))
        elif post_type.startswith("Błąd"): save_bug_report(str(interaction.user.id), post_type, "Nieokreślony", data.get('Opis błędu'), data.get('Dowody (linki do screenów, filmów)'), str(thread_message.thread.id))
        elif post_type.startswith("Skarga"): save_complaint(str(interaction.user.id), post_type, data.get('Nick osoby, na którą składasz skargę'), data, str(thread_message.thread.id))
        elif post_type.startswith("Odwołanie"): save_appeal(str(interaction.user.id), post_type, data, str(thread_message.thread.id))
        elif post_type.startswith("Podanie"): save_application(str(interaction.user.id), interaction.user.display_name, post_type, data, str(thread_message.thread.id))

        await log_action(interaction.guild, f"Złożono: {post_type}", interaction.user, f"Post: {thread_message.thread.mention}")
        await send_notification(interaction.guild, post_type, thread_message.thread.jump_url)
        await interaction.followup.send(f"✅ Twoje zgłoszenie zostało opublikowane w poście {thread_message.thread.mention}!", ephemeral=True)

    except Exception as e:
        print(f"Błąd podczas tworzenia posta ({post_type}): {e}")
        await interaction.followup.send("❌ Wystąpił nieoczekiwany błąd. Spróbuj ponownie.", ephemeral=True)

# --- GŁÓWNE MENU WYBORU ---
class ForumSelectionView(discord.ui.View):
    def __init__(self, view_type: str):
        super().__init__(timeout=None)
        self.add_item(ForumSelect(view_type=view_type, custom_id=f"persistent_forum_select_{view_type}"))

class ForumSelect(discord.ui.Select):
    def __init__(self, view_type: str, custom_id: str):
        options, placeholder = [], "Wybierz akcję..."
        if view_type == "proposals_bugs":
            placeholder, options = "Wybierz akcję (propozycje i błędy)...", [discord.SelectOption(label="Propozycja JB", emoji="💡", value="Propozycja JB"), discord.SelectOption(label="Propozycja DC", emoji="💡", value="Propozycja DC"), discord.SelectOption(label="Błąd JB", emoji="🐛", value="Błąd JB"), discord.SelectOption(label="Błąd DC", emoji="🐛", value="Błąd DC")]
        elif view_type == "complaints_appeals":
            placeholder, options = "Wybierz akcję (skargi i odwołania)...", [discord.SelectOption(label="Skarga JB", emoji="⚠️", value="Skarga JB"), discord.SelectOption(label="Skarga DC", emoji="⚠️", value="Skarga DC"), discord.SelectOption(label="Odwołanie JB", emoji="🔓", value="Odwołanie JB"), discord.SelectOption(label="Odwołanie DC", emoji="🔓", value="Odwołanie DC")]
        elif view_type == "recruitment":
            placeholder = "Wybierz stanowisko, na które aplikujesz..."
            conn = sqlite3.connect('/data/bot_database.db')
            cursor = conn.cursor()
            options = []
            for position in RECRUITMENT_TYPES:
                cursor.execute("SELECT is_open FROM recruitment_status WHERE position = ?", (position,))
                status = cursor.fetchone()
                is_open = status[0] if status else 1  # Domyślnie otwarte
                label = position
                if not is_open:
                    label += " (Zamknięta)"
                options.append(discord.SelectOption(label=label, value=position, emoji="📄"))
            conn.close()

        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        conn = sqlite3.connect('/data/bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT is_open FROM recruitment_status WHERE position = ?", (choice,))
        status = cursor.fetchone()
        conn.close()
        is_open = status[0] if status else 1

        if not is_open:
            await interaction.response.send_message("❌ Rekrutacja na to stanowisko jest obecnie zamknięta.", ephemeral=True)
            return

        modal_map = {"Propozycja JB": SuggestionModal, "Propozycja DC": SuggestionModal, "Błąd JB": BugReportModal, "Błąd DC": BugReportModal, "Skarga JB": ComplaintModal, "Skarga DC": ComplaintModal, "Odwołanie JB": AppealModal, "Odwołanie DC": AppealModal}
        if choice in modal_map: await interaction.response.send_modal(modal_map[choice](choice)); return
        if choice.startswith("Podanie"):
            requirements_map = {"Podanie Admin JB": "• Minimum 16 lat\n• ...", "Podanie Zaufany JB": "• Minimum 14 lat\n• ...", "Podanie Admin DC": "• Doświadczenie z Discordem\n• ..."}
            embed = discord.Embed(title=f"📝 Wymagania - {choice}", description=requirements_map.get(choice, "Brak zdefiniowanych wymagań."), color=COLORS["main"])
            if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
            embed.set_footer(text=FOOTER_TEXT)
            await interaction.response.send_message(embed=embed, view=RequirementsView(choice), ephemeral=True)

class RequirementsView(discord.ui.View):
    def __init__(self, application_type: str):
        super().__init__(timeout=180)
        self.application_type = application_type

        continue_btn = discord.ui.Button(label="Akceptuję i chcę kontynuować", style=discord.ButtonStyle.success, emoji="✅")
        continue_btn.callback = self.continue_callback
        self.add_item(continue_btn)

        if application_type in ["Podanie Admin JB", "Podanie Zaufany JB"]:
            stats_btn = discord.ui.Button(label="Statystyki serwera", style=discord.ButtonStyle.link, url="https://tsarvar.com/pl/servers/counter-strike-2/91.224.117.153:27015", emoji="📊")
            self.add_item(stats_btn)

    async def continue_callback(self, interaction: discord.Interaction):
        modal_map = {"Podanie Admin JB": AdminApplicationModal, "Podanie Zaufany JB": TrustedApplicationModal, "Podanie Admin DC": DiscordAdminApplicationModal}
        if self.application_type in modal_map:
            await interaction.response.send_modal(modal_map[self.application_type]())
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
            options = [discord.SelectOption(label="Błąd naprawiony", value="resolve_bug", emoji="✅"), discord.SelectOption(label="Odrzuć zgłoszenie", value="reject_bug", emoji="❌")]
        else:
            options_map = {
                "Podanie": [discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_application", emoji="✅"), discord.SelectOption(label="Rozpatrz negatywnie", value="reject_application", emoji="❌")],
                "Propozycja": [discord.SelectOption(label="Przyjmij propozycję", value="accept_suggestion", emoji="✅"), discord.SelectOption(label="Odrzuć propozycję", value="reject_suggestion", emoji="❌")],
                "Błąd": [discord.SelectOption(label="Błąd przyjęty do naprawy", value="accept_bug", emoji="🛠️"), discord.SelectOption(label="Odrzuć zgłoszenie", value="reject_bug", emoji="❌")],
                "Skarga": [discord.SelectOption(label="Rozpatrz pozytywnie", value="accept_complaint", emoji="✅"), discord.SelectOption(label="Odrzuć skargę", value="reject_complaint", emoji="❌")],
                "Odwołanie": [discord.SelectOption(label="Zaakceptuj odwołanie", value="accept_appeal", emoji="✅"), discord.SelectOption(label="Odrzuć odwołanie", value="reject_appeal", emoji="❌")]}
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
        for item in self.children: item.disabled = True
        await interaction.edit_original_response(content="✅ Decyzja została podjęta.", view=self)

    @discord.ui.button(label="Inny powód (wpisz ręcznie)", style=discord.ButtonStyle.secondary)
    async def custom_reason_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DecisionReasonModal(original_interaction=self.original_interaction, action=self.action, post_type=self.post_type, author_id=self.author_id)
        await interaction.response.send_modal(modal)
        self.stop()
        await interaction.edit_original_response(content="Otwarto okno do wpisania własnego powodu...", view=self)

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

        conn = sqlite3.connect('/data/bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT votes FROM polls WHERE message_id = ?", (message_id,))
        votes_json = cursor.fetchone()
        if not votes_json: conn.close(); return

        votes = json.loads(votes_json[0])
        voter_id_str = str(interaction.user.id)
        
        for option_votes in votes.values():
            if voter_id_str in option_votes: option_votes.remove(voter_id_str)

        votes[str(button_index)].append(voter_id_str)
        cursor.execute("UPDATE polls SET votes = ? WHERE message_id = ?", (json.dumps(votes), message_id))
        conn.commit()
        
        cursor.execute("SELECT question, options, author_id FROM polls WHERE message_id = ?", (message_id,))
        poll_data = cursor.fetchone()
        conn.close()

        question, options, author_id = poll_data
        options, author = json.loads(options), interaction.guild.get_member(author_id) or await bot.fetch_user(author_id)

        new_embed = discord.Embed(title="📊 Ankieta", description=f"**{question}**", color=COLORS["main"])
        for i, option_text in enumerate(options):
            voter_ids = votes.get(str(i), [])
            voter_mentions = [f"<@{uid}>" for uid in voter_ids]
            value_text = "\n".join(voter_mentions) if voter_mentions else "Brak głosów"
            if len(value_text) > 1024: value_text = value_text[:1020] + "\n..."
            new_embed.add_field(name=f"{option_text} ({len(voter_ids)})", value=value_text, inline=False)
        new_embed.set_footer(text=f"Ankieta stworzona przez: {author.display_name} | {FOOTER_TEXT}")
        if LOGO_URL: new_embed.set_thumbnail(url=LOGO_URL)
        await interaction.edit_original_response(embed=new_embed)

# --- SYSTEM SKLEPU ---
async def create_shop_embed(category: str):
    """Tworzy embed dla wybranej kategorii sklepu."""
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, cost, description, stock FROM shop_items WHERE category = ? ORDER BY cost ASC", (category,))
    items = cursor.fetchall()
    conn.close()

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
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
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
        self.load_items()

    def load_items(self):
        conn = sqlite3.connect('/data/bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cost, stock FROM shop_items WHERE category = ? ORDER BY cost ASC", (self.category,))
        items = cursor.fetchall()
        conn.close()
        
        options = []
        if not items:
            options.append(discord.SelectOption(label="Brak przedmiotów w tej kategorii", value="disabled"))
            self.disabled = True
        else:
            for item_id, name, cost, stock in items:
                if stock is not None and stock <= 0:
                    continue
                label = f"{name} ({cost} rep.)"
                options.append(discord.SelectOption(label=label, value=str(item_id)))
        
        if not options:
            options.append(discord.SelectOption(label="Brak dostępnych przedmiotów", value="disabled"))
            self.disabled = True

        self.options = options

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        item_id = int(self.values[0])
        
        conn = sqlite3.connect('/data/bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, cost, role_id, stock, category FROM shop_items WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        item_name, item_cost, role_id, stock, category = item

        if stock is not None and stock <= 0:
            await interaction.followup.send("❌ Ten przedmiot jest już wyprzedany!", ephemeral=True)
            conn.close()
            return
            
        if category == "Specjalne role":
            cursor.execute("SELECT 1 FROM shop_purchases WHERE user_id = ? AND item_id = ?", (interaction.user.id, item_id))
            if cursor.fetchone():
                await interaction.followup.send("❌ Już posiadasz ten unikalny przedmiot!", ephemeral=True)
                conn.close()
                return

        cursor.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(interaction.user.id),))
        user_points_row = cursor.fetchone()
        user_points = user_points_row[0] if user_points_row else 0

        if user_points < item_cost:
            await interaction.followup.send(f"❌ Nie masz wystarczającej reputacji! Potrzebujesz **{item_cost}**, a masz **{user_points}**.", ephemeral=True)
            conn.close()
            return

        new_points = user_points - item_cost
        cursor.execute("UPDATE reputation_points SET points = ? WHERE user_id = ?", (new_points, str(interaction.user.id)))
        if stock is not None:
            cursor.execute("UPDATE shop_items SET stock = stock - 1 WHERE id = ?", (item_id,))
        if category == "Specjalne role":
            cursor.execute("INSERT INTO shop_purchases (user_id, item_id) VALUES (?, ?)", (interaction.user.id, item_id))
        conn.commit()
        conn.close()

        # Logika nadawania nagrody
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
                await interaction.followup.send(f"✅ Zakupiono **{item_name}**, ale wystąpił błąd przy nadawaniu roli. Administracja została powiadomiona.", ephemeral=True)
                if SHOP_CONFIG.get("channel_id"):
                    notif_channel = bot.get_channel(SHOP_CONFIG["channel_id"])
                    if notif_channel:
                        await notif_channel.send(f"⚠️ **Błąd automatyzacji!** Użytkownik {interaction.user.mention} kupił rolę `{item_name}`, ale nie udało się jej nadać. Proszę o ręczne nadanie.")
        else:
            await interaction.followup.send(f"✅ Gratulacje! Kupiłeś **{item_name}** za **{item_cost}** reputacji. Twoje saldo: **{new_points}** rep.\nAdministracja została powiadomiona i wkrótce otrzymasz swoją nagrodę.", ephemeral=True)
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
recruitment_group = app_commands.Group(name="rekrutacja", description="Zarządzanie statusami rekrutacji.", default_permissions=discord.Permissions(administrator=True))

# --- KOMENDY SLASH ---
@bot.tree.command(name="setup_logi", description="Konfiguruje kanał logów bota.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_logi(interaction: discord.Interaction, kanal: discord.TextChannel):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = kanal.id
    await interaction.response.send_message(f"✅ Kanał logów został ustawiony na {kanal.mention}.", ephemeral=True)

@bot.tree.command(name="setup_powiadomienia", description="Konfiguruje powiadomienia dla opiekunów.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_powiadomienia(interaction: discord.Interaction, typ_zgloszenia: str, kanal: discord.TextChannel, rola: Optional[discord.Role] = None):
    NOTIFICATION_CONFIG[typ_zgloszenia] = {'channel_id': kanal.id, 'role_id': rola.id if rola else None}
    await interaction.response.send_message(f"✅ Ustawiono powiadomienia dla `{typ_zgloszenia}` na kanale {kanal.mention}" + (f" z rolą {rola.mention}." if rola else "."), ephemeral=True)

@bot.tree.command(name="setup_przypomnienia", description="Włącza lub wyłącza automatyczne przypomnienia o starych postach.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_przypomnienia(interaction: discord.Interaction, wlaczone: bool, dni: app_commands.Range[int, 1, 30] = 3):
    REMINDER_CONFIG["enabled"] = wlaczone
    REMINDER_CONFIG["delay_days"] = dni
    status = "włączone" if wlaczone else "wyłączone"
    await interaction.response.send_message(f"✅ Automatyczne przypomnienia zostały **{status}**. Czas oczekiwania: **{dni} dni**.", ephemeral=True)

@bot.tree.command(name="setup_forum_propozycje", description="Tworzy panel zgłaszania propozycji i błędów.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_forum_propozycje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    embed = discord.Embed(title="💡 Propozycje i Błędy 🐛", description="Masz pomysł na ulepszenie serwera lub znalazłeś błąd? Użyj menu poniżej!", color=COLORS["main"])
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Zgłoszeń - Propozycje i Błędy", embed=embed, view=ForumSelectionView("proposals_bugs"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="setup_forum_skargi", description="Tworzy panel składania skarg i odwołań.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_forum_skargi(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    embed = discord.Embed(title="⚠️ Skargi i Odwołania 🔓", description="Chcesz złożyć skargę lub odwołać się od kary? Użyj menu poniżej.", color=COLORS["main"])
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Zgłoszeń - Skargi i Odwołania", embed=embed, view=ForumSelectionView("complaints_appeals"))
    await interaction.response.send_message(f"✅ Panel utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="setup_forum_rekrutacje", description="Tworzy panel rekrutacyjny na kanale forum.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_forum_rekrutacje(interaction: discord.Interaction, kanal_forum: discord.ForumChannel):
    embed = discord.Embed(title="📝 Centrum Rekrutacji", description="Chcesz dołączyć do ekipy? Wybierz stanowisko z menu poniżej.", color=COLORS["main"])
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    await kanal_forum.create_thread(name="Panel Rekrutacyjny", embed=embed, view=ForumSelectionView("recruitment"))
    await interaction.response.send_message(f"✅ Panel rekrutacyjny utworzony na {kanal_forum.mention}!", ephemeral=True)

@bot.tree.command(name="info", description="Wyświetla informacje o aktywności użytkownika.")
@app_commands.checks.has_permissions(manage_messages=True)
async def info(interaction: discord.Interaction, uzytkownik: discord.Member):
    await interaction.response.defer(ephemeral=True)
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    embed = discord.Embed(title=f"📊 Kartoteka: {uzytkownik.display_name}", color=uzytkownik.color, timestamp=datetime.now(POLAND_TZ))
    embed.set_thumbnail(url=uzytkownik.display_avatar.url)
    cursor.execute("SELECT points FROM reputation_points WHERE user_id = ?", (str(uzytkownik.id),))
    rep = cursor.fetchone()
    embed.add_field(name="⭐ Reputacja", value=rep[0] if rep else "0", inline=False)
    tables = {"applications": "Podania", "suggestions": "Propozycje", "bug_reports": "Błędy", "complaints": "Skargi", "appeals": "Odwołania"}
    for table, name in tables.items():
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (str(uzytkownik.id),))
        count = cursor.fetchone()[0]
        if count > 0: embed.add_field(name=name, value=str(count), inline=True)
    conn.close()
    embed.set_footer(text=FOOTER_TEXT)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="moje_zgłoszenia", description="Wyświetla listę Twoich zgłoszeń i ich status.")
async def moje_zgłoszenia(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    embed = discord.Embed(title=f"📝 Twoje zgłoszenia", color=interaction.user.color, timestamp=datetime.now(POLAND_TZ))
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    tables_map = {"Propozycje": ("suggestions", "category", "status"), "Błędy": ("bug_reports", "category", "status"), "Skargi": ("complaints", "complaint_type", "status"), "Odwołania": ("appeals", "appeal_type", "status"), "Podania": ("applications", "application_type", "status")}
    content = ""
    for name, (table, type_col, status_col) in tables_map.items():
        cursor.execute(f"SELECT {type_col}, {status_col}, thread_id FROM {table} WHERE user_id = ?", (str(interaction.user.id),))
        rows = cursor.fetchall()
        if rows:
            content += f"**{name}**\n"
            for row in rows:
                thread_link = f" ([Link](https://discord.com/channels/{interaction.guild.id}/{row[2]}))" if row[2] else ""
                content += f"- `{row[0]}`: *{row[1]}*{thread_link}\n"
            content += "\n"
    embed.description = content if content else "Nie znaleziono żadnych Twoich zgłoszeń."
    conn.close()
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ankieta", description="Tworzy ankietę z przyciskami.")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(pytanie="Pytanie ankiety.", opcje="Opcje odpowiedzi, oddzielone średnikiem (;). Maks. 5 opcji.")
async def ankieta(interaction: discord.Interaction, pytanie: str, opcje: str):
    options_list = [opt.strip() for opt in opcje.split(';') if opt.strip()][:5]
    if len(options_list) < 2:
        await interaction.response.send_message("❌ Ankieta musi mieć co najmniej 2 opcje.", ephemeral=True)
        return

    embed = discord.Embed(title="📊 Ankieta", description=f"**{pytanie}**", color=COLORS["main"])
    for opt in options_list:
        embed.add_field(name=f"{opt} (0)", value="Brak głosów", inline=False)
    embed.set_footer(text=f"Ankieta stworzona przez: {interaction.user.display_name} | {FOOTER_TEXT}")
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    
    await interaction.response.send_message("Tworzenie ankiety...", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    view = PollView(options=options_list, message_id=message.id)
    await message.edit(view=view)

    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    initial_votes = json.dumps({str(i): [] for i in range(len(options_list))})
    cursor.execute("INSERT INTO polls (message_id, question, options, votes, author_id) VALUES (?, ?, ?, ?, ?)",
                   (message.id, pytanie, json.dumps(options_list), initial_votes, interaction.user.id))
    conn.commit()
    conn.close()
    await interaction.edit_original_response(content="✅ Ankieta została utworzona!")

# --- NOWE KOMENDY SKLEPU ---
@bot.tree.command(name="setup_powiadomienia_sklep", description="Konfiguruje kanał powiadomień o zakupach w sklepie.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_powiadomienia_sklep(interaction: discord.Interaction, kanal: discord.TextChannel):
    SHOP_CONFIG["channel_id"] = kanal.id
    await interaction.response.send_message(f"✅ Skonfigurowano kanał powiadomień o zakupach na {kanal.mention}.", ephemeral=True)

@bot.tree.command(name="dodaj_przedmiot", description="Dodaje przedmiot do sklepu (wymaga ręcznego nadania).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(kategoria="Kategoria przedmiotu", nazwa="Nazwa przedmiotu", koszt="Cena w reputacji", opis="Opis przedmiotu")
async def dodaj_przedmiot(interaction: discord.Interaction, kategoria: str, nazwa: str, koszt: app_commands.Range[int, 1], opis: str):
    if kategoria not in SHOP_CATEGORIES:
        await interaction.response.send_message(f"❌ Nieprawidłowa kategoria. Dostępne kategorie: {', '.join(SHOP_CATEGORIES)}", ephemeral=True)
        return
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?, ?, ?, ?, NULL, NULL)", (nazwa, koszt, opis, kategoria))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Dodano przedmiot `{nazwa}` (ręczna nagroda) do kategorii `{kategoria}` za **{koszt}** reputacji.", ephemeral=True)

@bot.tree.command(name="dodaj_specjalna_role", description="Dodaje limitowaną rolę do sklepu (nadawana automatycznie).")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(nazwa="Nazwa przedmiotu", koszt="Cena w reputacji", rola="Rola do nadania", ilosc="Liczba dostępnych sztuk", opis="Opis przedmiotu")
async def dodaj_specjalna_role(interaction: discord.Interaction, nazwa: str, koszt: app_commands.Range[int, 1], rola: discord.Role, ilosc: app_commands.Range[int, 1], opis: str):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO shop_items (name, cost, description, category, role_id, stock) VALUES (?, ?, ?, ?, ?, ?)", (nazwa, koszt, opis, "Specjalne role", rola.id, ilosc))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Dodano rolę {rola.mention} jako przedmiot `{nazwa}` (automatyczna nagroda, {ilosc} szt.) za **{koszt}** reputacji.", ephemeral=True)

@dodaj_przedmiot.autocomplete('kategoria')
async def dodaj_przedmiot_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=cat, value=cat) for cat in SHOP_CATEGORIES if current.lower() in cat.lower() and cat != "Specjalne role"]

@bot.tree.command(name="usun_przedmiot", description="Usuwa przedmiot ze sklepu reputacji.")
@app_commands.checks.has_permissions(administrator=True)
async def usun_przedmiot(interaction: discord.Interaction, id_przedmiotu: int):
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_items WHERE id = ?", (id_przedmiotu,))
    conn.commit()
    if cursor.rowcount > 0:
        await interaction.response.send_message(f"✅ Usunięto przedmiot o ID **{id_przedmiotu}** ze sklepu.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Nie znaleziono przedmiotu o ID **{id_przedmiotu}**.", ephemeral=True)
    conn.close()

@bot.tree.command(name="setup_sklep_panel", description="Tworzy interaktywny panel sklepu na kanale.")
@app_commands.checks.has_permissions(administrator=True)
async def setup_sklep_panel(interaction: discord.Interaction, kanal: discord.TextChannel):
    embed = await create_shop_embed(SHOP_CATEGORIES[0]) # Wyświetl pierwszą kategorię domyślnie
    view = ShopView(initial_category=SHOP_CATEGORIES[0])
    await kanal.send(embed=embed, view=view)
    await interaction.response.send_message(f"✅ Panel sklepu został utworzony na kanale {kanal.mention}.", ephemeral=True)

@bot.tree.command(name="ranking", description="Wyświetla ranking użytkowników z największą reputacją.")
async def ranking(interaction: discord.Interaction):
    await interaction.response.defer()
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, points FROM reputation_points ORDER BY points DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()

    embed = discord.Embed(title="🏆 Ranking Reputacji - Top 10", color=COLORS["main"])
    if LOGO_URL: embed.set_thumbnail(url=LOGO_URL)
    embed.set_footer(text=FOOTER_TEXT)
    
    if not top_users:
        embed.description = "Ranking jest pusty. Bądź pierwszy i zdobądź reputację!"
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

@reputation_group.command(name="dodaj", description="Dodaje reputację użytkownikowi.")
@app_commands.checks.has_permissions(administrator=True)
async def reputacja_dodaj(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 1]):
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='add')
    await interaction.response.send_message(f"✅ Dodano **{ilosc}** reputacji dla {uzytkownik.mention}. Nowe saldo: **{new_balance}** rep.", ephemeral=True)
    await log_action(interaction.guild, "Ręcznie dodano reputację", interaction.user, f"Cel: {uzytkownik.mention}, Ilość: +{ilosc}")

@reputation_group.command(name="usun", description="Usuwa reputację użytkownikowi.")
@app_commands.checks.has_permissions(administrator=True)
async def reputacja_usun(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 1]):
    new_balance = await update_reputation(uzytkownik.id, -ilosc, mode='add')
    await interaction.response.send_message(f"✅ Usunięto **{ilosc}** reputacji użytkownikowi {uzytkownik.mention}. Nowe saldo: **{new_balance}** rep.", ephemeral=True)
    await log_action(interaction.guild, "Ręcznie usunięto reputację", interaction.user, f"Cel: {uzytkownik.mention}, Ilość: -{ilosc}")

@reputation_group.command(name="ustaw", description="Ustawia reputację użytkownika na konkretną wartość.")
@app_commands.checks.has_permissions(administrator=True)
async def reputacja_ustaw(interaction: discord.Interaction, uzytkownik: discord.Member, ilosc: app_commands.Range[int, 0]):
    new_balance = await update_reputation(uzytkownik.id, ilosc, mode='set')
    await interaction.response.send_message(f"✅ Ustawiono reputację {uzytkownik.mention} na **{new_balance}** rep.", ephemeral=True)
    await log_action(interaction.guild, "Ręcznie ustawiono reputację", interaction.user, f"Cel: {uzytkownik.mention}, Nowa wartość: {ilosc}")

@recruitment_group.command(name="otworz", description="Otwiera rekrutację na dane stanowisko.")
async def rekrutacja_otworz(interaction: discord.Interaction, stanowisko: str):
    if stanowisko not in RECRUITMENT_TYPES:
        await interaction.response.send_message(f"❌ Nieprawidłowe stanowisko. Dostępne: {', '.join(RECRUITMENT_TYPES)}", ephemeral=True)
        return
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 1)", (stanowisko,))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Rekrutacja na stanowisko **{stanowisko}** została **otwarta**.\n> Pamiętaj, aby odświeżyć panel komendą `/setup_forum_rekrutacje`!", ephemeral=True)

@recruitment_group.command(name="zamknij", description="Zamyka rekrutację na dane stanowisko.")
async def rekrutacja_zamknij(interaction: discord.Interaction, stanowisko: str):
    if stanowisko not in RECRUITMENT_TYPES:
        await interaction.response.send_message(f"❌ Nieprawidłowe stanowisko. Dostępne: {', '.join(RECRUITMENT_TYPES)}", ephemeral=True)
        return
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO recruitment_status (position, is_open) VALUES (?, 0)", (stanowisko,))
    conn.commit()
    conn.close()
    await interaction.response.send_message(f"✅ Rekrutacja na stanowisko **{stanowisko}** została **zamknięta**.\n> Pamiętaj, aby odświeżyć panel komendą `/setup_forum_rekrutacje`!", ephemeral=True)

@rekrutacja_otworz.autocomplete('stanowisko')
@rekrutacja_zamknij.autocomplete('stanowisko')
async def rekrutacja_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    return [app_commands.Choice(name=pos, value=pos) for pos in RECRUITMENT_TYPES if current.lower() in pos.lower()]


# --- ZADANIA W TLE ---
@tasks.loop(hours=1)
async def check_for_old_posts():
    if not REMINDER_CONFIG["enabled"]:
        return

    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    
    delay = timedelta(days=REMINDER_CONFIG["delay_days"])
    time_threshold = datetime.now(POLAND_TZ) - delay

    tables_to_check = {
        "suggestions": "category", "bug_reports": "category", "complaints": "complaint_type",
        "appeals": "appeal_type", "applications": "application_type"
    }

    for table, type_col in tables_to_check.items():
        cursor.execute(f"SELECT thread_id, {type_col} FROM {table} WHERE status NOT LIKE '%odrzucon%' AND status NOT LIKE '%przyjęt%' AND status NOT LIKE '%naprawion%' AND reminder_sent = 0 AND created_at < ?", (time_threshold.strftime('%Y-%m-%d %H:%M:%S.%f'),))
        
        old_posts = cursor.fetchall()
        for thread_id, post_type in old_posts:
            for guild in bot.guilds:
                try:
                    thread = await guild.fetch_channel(int(thread_id))
                    if not thread.locked:
                        await send_notification(guild, post_type, thread.jump_url, is_reminder=True)
                        cursor.execute(f"UPDATE {table} SET reminder_sent = 1 WHERE thread_id = ?", (thread_id,))
                        conn.commit()
                except (discord.NotFound, discord.Forbidden):
                    continue
    conn.close()


# --- EVENTY BOTA ---
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}!')
    init_database()
    
    bot.add_view(ForumSelectionView("proposals_bugs"))
    bot.add_view(ForumSelectionView("complaints_appeals"))
    bot.add_view(ForumSelectionView("recruitment"))
    bot.add_view(ShopView()) # Rejestracja widoku sklepu
    
    post_types = ["Propozycja JB", "Propozycja DC", "Błąd JB", "Błąd DC", "Skarga JB", "Skarga DC", "Odwołanie JB", "Odwołanie DC", "Podanie Admin JB", "Podanie Zaufany JB", "Podanie Admin DC"]
    for post_type in post_types:
        bot.add_view(ManagementView(post_type, author_id=0))
    
    conn = sqlite3.connect('/data/bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT message_id, options FROM polls")
    for row in cursor.fetchall():
        message_id, options_json = row
        options = json.loads(options_json)
        bot.add_view(PollView(options, message_id))
    conn.close()
    
    bot.tree.add_command(reputation_group)
    bot.tree.add_command(recruitment_group)
    check_for_old_posts.start()

    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

# --- URUCHOMIENIE BOTA ---
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN == 'TWÓJ_TOKEN_BOTA_TUTAJ':
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print("!!! PROSZĘ ZASTĄPIĆ 'TWÓJ_TOKEN_BOTA_TUTAJ' PRAWDZIWYM TOKENEM !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
else:
    bot.run(TOKEN)
