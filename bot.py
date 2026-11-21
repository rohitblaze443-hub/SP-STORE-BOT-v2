import asyncio
import sqlite3
import random
import logging
import time
import aiohttp
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, Dice, BufferedInputFile
)

# ==============================================================================
# 1. BOT CONFIGURATION & CONSTANTS
# ==============================================================================
BOT_TOKEN = "9191125265:AAF5nK5FaG9HNlqAnZXLXR7B_jcMkvE-eg0"
BOT_USERNAME = "hp_store_bot"
ADMIN_ID = 6563613044
ADMIN_CONTACT = "dark_config001"

# FamPay API (Tune privacy ke liye nahi diya, toh ye blank rahega. Admin panel se set kar sakta hai)
FAMPAY_API_KEY = "fam_77567c5053f8e96c08aab9f1d5670d4e0df13a5c" 
FAMPAY_QR_URL = "https://fampay.api/qr.php"
FAMPAY_VERIFY_URL = "https://fampay.api/verify.php"

USDT_TO_INR = 90.0
VIP_DISCOUNT_PERCENTAGE = 10.0
VIP_PRICE_INR = 1000.0

FIXED_CATEGORIES = [
    "ANDROID NON ROOT PANEL",
    "ANDROID ROOT PANEL",
    "PC PANEL"
]

DEFAULT_EMOJIS = {
    'product_store': '6163205892834598715',
    'profile': '5258011929993026890',
    'add_balance': '5985630530111020079',
    'history': '6032594876506312598',
    'support': '5967280668885913944',
    'back': '5877536313623711363',
    'upi': '5807750375033278838',
    'reseller': '5886505193180239900',
    'tutorial': '6005986106703613755',
    'telegram': '5875465628285931233',
    'whatsapp': '5954224165874569584',
    'welcome': '5994502837327892086',
    'vip': '5206607081334906820',
    'category_android_non_root': '6161172706856282588',
    'category_android_root': '6161449831031118974',
    'category_pc': '5350554349074391003',
    'grid_id': '5474625972751837256',
    'name': '5215399540814781035',
    'account_level': '6129584162992034014',
    'regular_user': '5904630315946611415',
    'wallet': '6210859306602995217',
    'current_balance': '5316711376876485361',
    'global_stats': '6161437856662298090',
    'total_orders': '6160968017304888311',
    'total_spent': '5197503331215361533',
    'joined_grid': '5433614043006903194',
    'info_icon': '6037421444789440735',
    'check_icon': '6161241250239356403',
    'checkbox_icon': '6161437856662298090',
    'shield_icon': '6086672466132865380',
    'money_icon': '5890848474563352982',
    'redeem_icon': '5377624166436445368',
    'wallet_left': '6210859306602995217',
    'wallet_right': '5305699699204837855',
    'point_down': '6161302621027049305',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot_activity.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def fmt_curr(amount: float) -> str:
    return f"₹{amount:,.2f}"

def fancy(text: str) -> str:
    bold_caps = {chr(ord("A") + i): chr(0x1D400 + i) for i in range(26)}
    small_caps = {
        "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
        "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ",
        "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ",
    }
    value = str(text)
    out = []
    at_word_start = True
    for ch in value:
        if ch.isascii() and ch.isalpha():
            if at_word_start:
                out.append(bold_caps.get(ch.upper(), ch))
                at_word_start = False
            else:
                out.append(small_caps.get(ch.lower(), ch))
        else:
            out.append(ch)
            if ch.isspace() or ch in "/\\|•":
                at_word_start = True
    return "".join(out)

def safe_float(val, default=0.0):
    if val is None or val == "": return default
    try: return float(val)
    except: return default

# ==============================================================================
# 2. DATABASE FUNCTIONS
# ==============================================================================
def db_query(query: str, params: tuple = (), fetchone: bool = False, fetchall: bool = False, commit: bool = True) -> Any:
    conn = sqlite3.connect('Sandii.dp')
    c = conn.cursor()
    try:
        c.execute(query, params)
        if fetchone: res = c.fetchone()
        elif fetchall: res = c.fetchall()
        else: res = None
        if commit: conn.commit()
        return res
    except Exception as e:
        logger.error(f"DB Error: {e} | Query: {query}")
        if commit: conn.rollback()
        return None
    finally:
        conn.close()

def get_setting(key: str, default: str = "") -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (key,), fetchone=True)
    return val[0] if val and val[0] else default

def set_setting(key: str, value: str) -> None:
    db_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

def log_activity(user_id: int, action: str, details: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db_query("INSERT INTO activity_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)", (user_id, action, details, timestamp))

def get_emoji(slot: str, default_id: str = None) -> str:
    stored = get_setting(f"emoji_{slot}", "")
    emoji_id = stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))
    if emoji_id: return f'<tg-emoji emoji-id="{emoji_id}">✨</tg-emoji>'
    return "✨"

def get_emoji_icon(slot: str, default_id: str = None) -> str:
    stored = get_setting(f"emoji_{slot}", "")
    return stored if stored and stored.isdigit() else (default_id or DEFAULT_EMOJIS.get(slot, ""))

UI_TEXTS = {
    "start_menu": (
        "{welcome} <b>✦ SYCO 𝗦𝗧𝗢𝗥𝗘 ✦</b>\n"
        "<i>Premium Digital Marketplace</i>\n━━━━━━━━━━━━━━━━━━\n\n"
        "{product_store} <b>𝗣𝗿𝗼𝗱𝘂𝗰𝘁 𝗦𝘁𝗼𝗿𝗲</b>\n╰ <i>Instant key delivery, 24/7</i>\n\n"
        "{profile} <b>𝗠𝘆 𝗣𝗿𝗼𝗳𝗶𝗹𝗲</b>\n╰ <i>Account, wallet and purchase history</i>\n\n"
        "{add_balance} <b>𝗔𝗱𝗱 𝗕𝗮𝗹𝗮𝗻𝗰𝗲</b>\n╰ <i>Secure and instant UPI deposits</i>\n\n"
        "{tutorial} <b>𝗧𝘂𝘁𝗼𝗿𝗶𝗮𝗹</b>\n╰ <i>Learn how to use this bot</i>\n\n"
        "{support} <b>𝗦𝘂𝗽𝗽𝗼𝗿𝘁</b>\n╰ <i>Fast help from our team</i>\n\n"
        "━━━━━━━━━━━━━━━━━━\n{point_down} <i>Select an option below</i>"
    ),
    "vip_menu": (
        "{vip} <b>✦ 𝗩𝗜𝗣 𝗠𝗘𝗠𝗕𝗘𝗥𝗦𝗛𝗜𝗣 𝗖𝗟𝗨𝗕 ✦</b>\n━━━━━━━━━━━━━━━━━━\n"
        "<i>Unlock permanent discounts and exclusive perks.</i>\n\n"
        "💎 <b>𝗩𝗜𝗣 𝗕𝗲𝗻𝗲𝗳𝗶𝘁𝘀</b>\n"
        f"╰ Flat {VIP_DISCOUNT_PERCENTAGE:g}% off on ALL products <i>(stacks with Reseller)</i>\n"
        "╰ Priority support\n╰ Exclusive VIP-only giveaways\n\n"
        f"💳 <b>𝗩𝗜𝗣 𝗣𝗿𝗶𝗰𝗲</b> ┃ {fmt_curr(VIP_PRICE_INR)} <i>(Lifetime)</i>\n"
        "👤 <b>𝗬𝗼𝘂𝗿 𝗦𝘁𝗮𝘁𝘂𝘀</b> ┃ {vip_status}"
    ),
    "add_balance_menu": (
        "{add_balance} <b>✦ 𝗔𝗗𝗗 𝗕𝗔𝗟𝗔𝗡𝗖𝗘 ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "{info_icon} <i>Choose your preferred payment method</i>\n\n"
        "{upi} <b>𝗨𝗣𝗜</b> ┃ <i>Fast Indian payments</i> {check_icon}\n\n"
        "━━━━━━━━━━━━━━━━━━\n{shield_icon} <i>All payments are verified securely</i>"
    )
}

def get_ui_text(key: str, **kwargs) -> str:
    val = db_query("SELECT value FROM settings WHERE key=?", (f"ui_{key}",), fetchone=True)
    template = val[0] if val and val[0] else UI_TEXTS.get(key, "")
    emoji_map = {
        '{product_store}': get_emoji('product_store'), '{profile}': get_emoji('profile'),
        '{add_balance}': get_emoji('add_balance'), '{history}': get_emoji('history'),
        '{tutorial}': get_emoji('tutorial'), '{support}': get_emoji('support'),
        '{telegram}': get_emoji('telegram'), '{whatsapp}': get_emoji('whatsapp'),
        '{upi}': get_emoji('upi'), '{info_icon}': get_emoji('info_icon'),
        '{check_icon}': get_emoji('check_icon'), '{shield_icon}': get_emoji('shield_icon'),
        '{money_icon}': get_emoji('money_icon'), '{redeem_icon}': get_emoji('redeem_icon'),
        '{wallet_left}': get_emoji('wallet_left'), '{wallet_right}': get_emoji('wallet_right'),
        '{point_down}': get_emoji('point_down'), '{welcome}': get_emoji('welcome'),
        '{vip}': get_emoji('vip'), '{reseller}': get_emoji('reseller'),
    }
    for placeholder, emoji_tag in emoji_map.items():
        template = template.replace(placeholder, emoji_tag)
    if kwargs:
        try: return template.format(**kwargs)
        except KeyError: pass
    return template

# ==============================================================================
# 3. DATABASE INITIALISATION
# ==============================================================================
def init_db() -> None:
    conn = sqlite3.connect('Sandii.dp')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, phone TEXT, first_name TEXT, username TEXT, balance REAL DEFAULT 0.0, account_type TEXT DEFAULT 'Regular', orders_count INTEGER DEFAULT 0, spent REAL DEFAULT 0.0, last_spin TEXT, joined_date TEXT, is_reseller INTEGER DEFAULT 0, reseller_since TEXT, total_saved REAL DEFAULT 0.0, is_banned INTEGER DEFAULT 0, warnings INTEGER DEFAULT 0, is_vip INTEGER DEFAULT 0, vip_since TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, panel_name TEXT DEFAULT '', name TEXT, price_inr REAL, reseller_price REAL DEFAULT 0.0, stock INTEGER, apk_link TEXT, validity TEXT DEFAULT 'Lifetime', device_limit TEXT DEFAULT '1 Device', is_active INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS product_keys (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, key_text TEXT, is_used INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, price_paid REAL, delivered_key TEXT, purchase_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, status TEXT DEFAULT 'Open', created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (code TEXT PRIMARY KEY, amount REAL, uses_left INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS redeemed (user_id INTEGER, code TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (order_id TEXT PRIMARY KEY, user_id INTEGER, amount_inr REAL, status TEXT, timestamp INTEGER, qr_url TEXT, upi_id TEXT, expires_at INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, details TEXT, timestamp TEXT)''')

    default_settings = [
        ('reseller_system_status', 'ON'), ('bot_status', 'ON'), ('how_to_video', 'None'),
        ('fampay_api_key', ''), ('fampay_upi_id', ''), ('vip_status', 'OFF'),
        ('reseller_setup_fee', '200.0'), ('reseller_min_balance', '500.0'),
        ('support_telegram', 'https://t.me/dark_config001'), ('support_whatsapp', 'https://t.me/dark_config001'),
        ('ui_start_menu', UI_TEXTS['start_menu']), ('ui_vip_menu', UI_TEXTS['vip_menu']), ('ui_add_balance_menu', UI_TEXTS['add_balance_menu']),
        ('manual_upi_id', ''), ('manual_qr_url', '')
    ]
    for slot, emoji_id in DEFAULT_EMOJIS.items():
        default_settings.append((f"emoji_{slot}", emoji_id))
    
    for key, val in default_settings:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
    
    conn.commit()
    conn.close()

# ==============================================================================
# 4. MIDDLEWARES
# ==============================================================================
async def hacker_loading(message: Message, text: str = "Decrypting Data") -> Message:
    msg = await message.answer(f"✦ <b>{text}</b>\n▱▱▱▱▱ 𝟬%")
    await asyncio.sleep(0.3)
    await msg.edit_text(f"✦ <b>{text}</b>\n▰▰▱▱▱ 𝟯𝟯%")
    await asyncio.sleep(0.3)
    await msg.edit_text(f"✦ <b>{text}</b>\n▰▰▰▰▱ 𝟲𝟲%")
    await asyncio.sleep(0.3)
    await msg.edit_text(f"✦ <b>{text}</b>\n▰▰▰▰▰ 𝟭𝟬𝟬%")
    return msg

class GlobalSecurityMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.last_action_times = {}
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        now = time.time()
        if user_id in self.last_action_times and now - self.last_action_times[user_id] < 0.3: return
        self.last_action_times[user_id] = now

        if user_id != ADMIN_ID:
            user_info = db_query("SELECT is_banned FROM users WHERE user_id=?", (user_id,), fetchone=True)
            if user_info and user_info[0] == 1:
                msg = "🚫 <b>✦ 𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗 ✦</b>\n━━━━━━━━━━━━━━━━━━\nYou have been banned from using this bot."
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer(msg, show_alert=True)
                return
                
            status = get_setting('bot_status', 'ON')
            if status == 'OFF':
                msg = "🛠 <b>✦ 𝗦𝗧𝗢𝗥𝗘 𝗠𝗔𝗜𝗡𝗧𝗘𝗡𝗔𝗡𝗖𝗘 ✦</b>\n━━━━━━━━━━━━━━━━━━\nThe store is offline for updates."
                if isinstance(event, Message): await event.answer(msg)
                elif isinstance(event, CallbackQuery): await event.answer("⚠️ Bot is currently OFF.", show_alert=True)
                return
        return await handler(event, data)

dp.message.middleware(GlobalSecurityMiddleware())
dp.callback_query.middleware(GlobalSecurityMiddleware())

# ==============================================================================
# 5. FSM STATES
# ==============================================================================
class UserStates(StatesGroup):
    wait_for_ticket = State()
    wait_for_redeem = State()
    custom_amount_input = State()

class AdminStates(StatesGroup):
    add_prod_category = State()
    add_prod_panel_name = State()
    add_prod_name = State()
    add_prod_validity = State()
    add_prod_device_limit = State()
    add_prod_price = State()
    add_prod_reseller_price = State()
    add_prod_apk = State()
    add_prod_keys = State()
    
    edit_prod_field = State()
    wait_for_new_value = State()
    wait_for_add_keys = State()
    
    broadcast_msg = State()
    add_coupon_code = State()
    add_coupon_amount = State()
    add_coupon_uses = State()
    
    wait_for_fampay_api = State()
    wait_for_fampay_upi = State()
    wait_for_manual_upi = State()
    wait_for_manual_qr = State()
    
    ticket_reply_msg = State()
    manage_target_user = State()
    wait_for_add_money = State()
    wait_for_minus_money = State()
    wait_for_warning = State()
    wait_for_howto_video = State()
    confirm_ban = State()

# ==============================================================================
# 6. KEYBOARDS
# ==============================================================================
def get_category_emoji(category: str) -> str:
    slot_map = {"ANDROID NON ROOT PANEL": "category_android_non_root", "ANDROID ROOT PANEL": "category_android_root", "PC PANEL": "category_pc"}
    return get_emoji_icon(slot_map.get(category, ""), DEFAULT_EMOJIS.get(slot_map.get(category, ""), ""))

def get_panel_emoji(panel_name: str) -> str:
    return get_setting(f"panel_emoji_{panel_name}", "") or get_emoji_icon("product_store")

def main_menu_kb(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    sys_status = get_setting('reseller_system_status', 'ON')
    vip_system = get_setting('vip_status', 'OFF')
    is_reseller = False
    if user_id:
        user_check = db_query("SELECT is_reseller FROM users WHERE user_id=?", (user_id,), fetchone=True)
        if user_check: is_reseller = bool(user_check[0])
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=fancy("Product Store"), callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("product_store"), style="danger")],
        [InlineKeyboardButton(text=fancy("My Profile"), callback_data="menu_profile", icon_custom_emoji_id=get_emoji_icon("profile"), style="primary"), InlineKeyboardButton(text=fancy("Add Balance"), callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("add_balance"), style="primary")],
        [InlineKeyboardButton(text=fancy("Tutorials"), callback_data="menu_how_to", icon_custom_emoji_id=get_emoji_icon("tutorial"), style="success"), InlineKeyboardButton(text=fancy("Support"), callback_data="menu_support", icon_custom_emoji_id=get_emoji_icon("support"), style="danger")]
    ])
    extras_row = []
    if sys_status == 'ON' or is_reseller: extras_row.append(InlineKeyboardButton(text=fancy("Reseller Panel"), callback_data="menu_reseller_dash", icon_custom_emoji_id=get_emoji_icon("reseller"), style="primary"))
    if vip_system == 'ON': extras_row.append(InlineKeyboardButton(text=fancy("VIP Club"), callback_data="menu_vip_dash", icon_custom_emoji_id=get_emoji_icon("vip"), style="danger"))
    if extras_row: kb.inline_keyboard.append(extras_row)
    return kb

def back_kb(callback: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=fancy("BACK"), callback_data=callback, icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])

def admin_kb() -> InlineKeyboardMarkup:
    status_val = get_setting('bot_status', 'ON')
    vip_val = get_setting('vip_status', 'OFF')
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 " + fancy("Bot Statistics"), callback_data="admin_view_stats", style="primary")],
        [InlineKeyboardButton(text="👥 " + fancy("User Control Panel"), callback_data="admin_user_control_start", style="primary")],
        [InlineKeyboardButton(text="➕ " + fancy("Add Product"), callback_data="admin_add_prod", style="primary"), InlineKeyboardButton(text="📦 " + fancy("Manage Products"), callback_data="admin_manage_prods", style="primary")],
        [InlineKeyboardButton(text="👑 " + fancy("Reseller Mgmt"), callback_data="admin_reseller_menu", style="primary")],
        [InlineKeyboardButton(text="🎟 " + fancy("Create Coupon"), callback_data="admin_create_coupon", style="primary"), InlineKeyboardButton(text="📢 " + fancy("Broadcast"), callback_data="admin_broadcast_btn", style="primary")],
        [InlineKeyboardButton(text="🎫 " + fancy("View Tickets"), callback_data="admin_view_tickets", style="primary"), InlineKeyboardButton(text="📹 " + fancy("Tutorial Video"), callback_data="admin_set_video", style="primary")],
        [InlineKeyboardButton(text="🎨 " + fancy("Edit All Emojis"), callback_data="admin_edit_emojis", style="primary")],
        [InlineKeyboardButton(text="⚙️ " + fancy("FamPay Setup"), callback_data="admin_setup_fampay", style="primary")],
        [InlineKeyboardButton(text="✏️ " + fancy("Edit UI Texts"), callback_data="admin_edit_ui_menu", style="primary"), InlineKeyboardButton(text="📝 " + fancy("Edit Reseller Price"), callback_data="admin_edit_reseller_price", style="primary")],
        [InlineKeyboardButton(text="💰 " + fancy("Reseller Fee"), callback_data="admin_set_reseller_fee", style="primary"), InlineKeyboardButton(text="💳 " + fancy("Min Balance"), callback_data="admin_set_reseller_min", style="primary")],
        [InlineKeyboardButton(text="📞 " + fancy("Set Support Links"), callback_data="admin_set_support_links", style="primary"), InlineKeyboardButton(text="🎨 " + fancy("Set Category Emojis"), callback_data="admin_set_category_emojis", style="primary")],
        [InlineKeyboardButton(text="🖼 " + fancy("Set Panel Emojis"), callback_data="admin_set_panel_emojis", style="primary")],
        [InlineKeyboardButton(text=f"{fancy('Bot Status')}: {status_val} {'🟢' if status_val == 'ON' else '🔴'}", callback_data="admin_toggle_bot", style="success" if status_val == 'ON' else "danger")],
        [InlineKeyboardButton(text=f"{fancy('VIP System')}: {vip_val} {'🟢' if vip_val == 'ON' else '🔴'}", callback_data="admin_toggle_vip_sys", style="success" if vip_val == 'ON' else "danger")]
    ])

def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=fancy("Back to Admin"), callback_data="admin_panel_back", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])

# ==============================================================================
# 7. NOTIFICATIONS
# ==============================================================================
async def send_advanced_notification(user_id: int, notif_type: str, amount: float, product: str = None, key: str = None, gateway: str = "FamPay") -> None:
    user_info = db_query("SELECT first_name, phone, username, is_reseller, is_vip FROM users WHERE user_id=?", (user_id,), fetchone=True)
    name = user_info[0] if user_info else "Unknown"
    phone = user_info[1] if user_info and user_info[1] else "Not Provided"
    username = f"@{user_info[2]}" if user_info and user_info[2] else "None"
    tags = []
    if user_info and user_info[3]: tags.append("👑 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿")
    if user_info and user_info[4]: tags.append("🌟 𝗩𝗜𝗣")
    tag_str = " | ".join(tags) if tags else "👤 𝗥𝗲𝗴𝘂𝗹𝗮𝗿"
    time_now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    
    if notif_type == "ORDER":
        title = "🛒 <b>✦ 𝗡𝗘𝗪 𝗢𝗥𝗗𝗘𝗥 ✦</b>"
        details = f"📦 <b>𝗣𝗿𝗼𝗱𝘂𝗰𝘁</b> ┃ {product}\n🔑 <b>𝗞𝗲𝘆</b> ┃ <code>{key}</code>\n💰 <b>𝗣𝗮𝗶𝗱</b> ┃ ₹{amount:.2f}\n📅 <b>𝗧𝗶𝗺𝗲</b> ┃ {time_now}"
    else:
        title = "💎 <b>✦ 𝗡𝗘𝗪 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 ✦</b>"
        details = f"💵 <b>𝗔𝗺𝗼𝘂𝗻𝘁</b> ┃ ₹{amount:.2f}\n🧾 <b>𝗚𝗮𝘁𝗲𝘄𝗮𝘆</b> ┃ {gateway}\n🆔 <b>𝗥𝗲𝗳𝗲𝗿𝗲𝗻𝗰𝗲</b> ┃ <code>{product}</code>\n📅 <b>𝗧𝗶𝗺𝗲</b> ┃ {time_now}"

    msg = f"{title}\n━━━━━━━━━━━━━━━━━━\n👤 <b>𝗡𝗮𝗺𝗲</b> ┃ {name}\n🆔 <b>𝗨𝘀𝗲𝗿 𝗜𝗗</b> ┃ <code>{user_id}</code>\n📱 <b>𝗣𝗵𝗼𝗻𝗲</b> ┃ {phone}\n🔗 <b>𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲</b> ┃ {username}\n🏷 <b>𝗦𝘁𝗮𝘁𝘂𝘀</b> ┃ {tag_str}\n━━━━━━━━━━━━━━━━━━\n{details}"
    try: await bot.send_message(ADMIN_ID, msg, parse_mode='HTML')
    except Exception as e: logger.error(f"Admin notify fail: {e}")

# ==============================================================================
# 8. FAMPAY & MANUAL UPI PAYMENT (FIXED)
# ==============================================================================
async def generate_fampay_qr(user_id: int, amount: float) -> Dict[str, Any]:
    api_key = get_setting("fampay_api_key", "")
    upi_id = get_setting("fampay_upi_id", "")
    
    # Agar API nahi hai, toh Manual UPI mode use karo
    if not api_key or not upi_id:
        manual_upi = get_setting("manual_upi_id", "")
        manual_qr = get_setting("manual_qr_url", "")
        if not manual_upi:
            return {"status": "error", "message": "Payment gateway not configured. Admin needs to set UPI ID."}
        return {
            "status": "manual",
            "data": {
                "upi_id": manual_upi,
                "qr_url": manual_qr,
                "order_id": f"MANUAL{user_id}{int(time.time())}",
                "expires_at_ist": (datetime.now() + timedelta(minutes=10)).strftime("%d-%m-%Y %H:%M:%S"),
                "created_at_ist": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            }
        }
    
    url = f"{FAMPAY_QR_URL}?upi={upi_id}&amount={amount}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    try: return await resp.json(content_type=None)
                    except: return {"status": "error", "message": "Failed to parse response"}
                else: return {"status": "error", "message": f"HTTP Error: {resp.status}"}
        except Exception as e: return {"status": "error", "message": str(e)}

async def verify_fampay_payment(order_id: str) -> Dict[str, Any]:
    api_key = get_setting("fampay_api_key", "")
    if not api_key:
        # Manual verify mode (Admin ko notify karega)
        return {"status": "manual_pending", "message": "Please wait for admin to verify your payment manually."}
    
    url = f"{FAMPAY_VERIFY_URL}?order_id={order_id}&api_key={api_key}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    try: return await resp.json(content_type=None)
                    except: return {"status": "error", "message": "Failed to parse response"}
                else: return {"status": "error", "message": f"HTTP Error: {resp.status}"}
        except Exception as e: return {"status": "error", "message": str(e)}

async def run_payment_verification(user_id: int, order_id: str, reply_target: Any) -> None:
    txn = db_query("SELECT amount_inr, status, timestamp, qr_url, upi_id, expires_at FROM transactions WHERE order_id=?", (order_id,), fetchone=True)
    if not txn:
        err = "❌ Invalid or Fake Order ID!"
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(err, show_alert=True)
        else: await reply_target.answer(err)
        return
    
    if txn[5] and time.time() > txn[5]:
        db_query("UPDATE transactions SET status='expired' WHERE order_id=?", (order_id,))
        err_msg = "⏳ <b>✦ 𝗤𝗥 𝗘𝗫𝗣𝗜𝗥𝗘𝗗 ✦</b>\n<i>Please generate a new QR code.</i>"
        if isinstance(reply_target, CallbackQuery): await reply_target.message.edit_text(err_msg, reply_markup=back_kb(), parse_mode='HTML')
        else: await reply_target.answer(err_msg, reply_markup=back_kb())
        return
        
    if txn[1] == 'paid':
        msg = "✅ This payment has already been credited."
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
        return
    
    result = await verify_fampay_payment(order_id)
    
    if result.get("status") == "success":
        txn_data = result.get("data", {})
        amount_received = txn_data.get("amount", txn[0])
        utr = txn_data.get("utr")
        
        db_query("UPDATE transactions SET status='paid' WHERE order_id=?", (order_id,))
        db_query("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount_received, user_id))
        
        success_msg = f"✅ <b>✦ 𝗣𝗔𝗬𝗠𝗘𝗡𝗧 𝗩𝗘𝗥𝗜𝗙𝗜𝗘𝗗 ✦</b>\n━━━━━━━━━━━━━━━━━━\n💎 <b>𝗖𝗿𝗲𝗱𝗶𝘁𝗲𝗱</b> ┃ {fmt_curr(amount_received)}\n🧾 <b>𝗨𝗧𝗥</b> ┃ <code>{utr}</code>"
        if isinstance(reply_target, CallbackQuery): await reply_target.message.edit_text(success_msg, reply_markup=back_kb(), parse_mode='HTML')
        else: await reply_target.answer(success_msg, reply_markup=back_kb())
        await send_advanced_notification(user_id, "DEPOSIT", amount_received, product=order_id, gateway="FamPay")
    elif result.get("status") == "manual_pending":
        msg = "⏳ <b>𝗠𝗮𝗻𝘂𝗮𝗹 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗣𝗲𝗻𝗱𝗶𝗻𝗴</b>\n<i>Admin will verify your payment shortly. Please wait.</i>"
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(msg, show_alert=True)
        else: await reply_target.answer(msg)
    else:
        err = f"⚠️ {result.get('message', 'Payment not received yet')}"
        if isinstance(reply_target, CallbackQuery): await reply_target.answer(err, show_alert=True)
        else: await reply_target.answer(err)

# ==============================================================================
# 9. START & MAIN MENU
# ==============================================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = db_query("SELECT phone FROM users WHERE user_id=?", (message.from_user.id,), fetchone=True)
    current_username = message.from_user.username or ""
    db_query("UPDATE users SET username=? WHERE user_id=?", (current_username, message.from_user.id))
    if not user or not user[0]:
        db_query("INSERT OR IGNORE INTO users (user_id, first_name, username, joined_date) VALUES (?, ?, ?, ?)", (message.from_user.id, message.from_user.first_name, current_username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    await send_main_menu(message)

async def send_main_menu(ctx: Any):
    text = get_ui_text("start_menu")
    kb = main_menu_kb(ctx.from_user.id)
    if isinstance(ctx, Message): await ctx.answer(text, reply_markup=kb, parse_mode='HTML')
    else: await ctx.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_main_menu(call)

# ==============================================================================
# 10. ADD BALANCE (FIXED FAMPAY)
# ==============================================================================
@dp.callback_query(F.data == "menu_add_balance")
async def select_gateway_menu(call: CallbackQuery):
    text = get_ui_text("add_balance_menu")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=fancy("UPI PAY"), callback_data="gateway_inr", icon_custom_emoji_id=get_emoji_icon("upi"), style="primary")],
        [InlineKeyboardButton(text=fancy("BACK"), callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "gateway_inr")
async def add_balance_inr(call: CallbackQuery):
    text = "💵 <b>✦ 𝗨𝗣𝗜 𝗗𝗘𝗣𝗢𝗦𝗜𝗧 ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n<i>Select an amount to deposit</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="₹50", callback_data="pay_50", style="primary"), InlineKeyboardButton(text="₹100", callback_data="pay_100", style="primary")],
        [InlineKeyboardButton(text="₹200", callback_data="pay_200", style="primary"), InlineKeyboardButton(text="₹500", callback_data="pay_500", style="primary")],
        [InlineKeyboardButton(text="₹1000", callback_data="pay_1000", style="primary"), InlineKeyboardButton(text="₹2000", callback_data="pay_2000", style="primary")],
        [InlineKeyboardButton(text="✏️ " + fancy("Custom Amount"), callback_data="custom_deposit_keypad", style="primary")],
        [InlineKeyboardButton(text=fancy("Back"), callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "custom_deposit_keypad")
async def show_custom_keypad(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.custom_amount_input)
    await state.update_data(amount_str="0")
    await show_keypad(call.message)

async def show_keypad(message: Message, amount_str: str = "0"):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="      1      ", callback_data="kp_1", style="primary"), InlineKeyboardButton(text="      2      ", callback_data="kp_2", style="primary"), InlineKeyboardButton(text="      3      ", callback_data="kp_3", style="primary")],
        [InlineKeyboardButton(text="      4      ", callback_data="kp_4", style="primary"), InlineKeyboardButton(text="      5      ", callback_data="kp_5", style="primary"), InlineKeyboardButton(text="      6      ", callback_data="kp_6", style="primary")],
        [InlineKeyboardButton(text="      7      ", callback_data="kp_7", style="primary"), InlineKeyboardButton(text="      8      ", callback_data="kp_8", style="primary"), InlineKeyboardButton(text="      9      ", callback_data="kp_9", style="primary")],
        [InlineKeyboardButton(text="    ⌫    ", callback_data="kp_backspace", style="danger"), InlineKeyboardButton(text="      0      ", callback_data="kp_0", style="primary"), InlineKeyboardButton(text="    C    ", callback_data="kp_clear", style="danger")],
        [InlineKeyboardButton(text=f"✅ {fancy('Confirm')} • ₹{amount_str}", callback_data="kp_confirm", style="success")],
        [InlineKeyboardButton(text=fancy("Cancel"), callback_data="gateway_inr", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await message.edit_text(f"💵 <b>✦ 𝗘𝗡𝗧𝗘𝗥 𝗔𝗠𝗢𝗨𝗡𝗧 ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n💎 <b>𝗖𝘂𝗿𝗿𝗲𝗻𝘁</b> ┃ ₹{amount_str}", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("kp_"), UserStates.custom_amount_input)
async def keypad_handler(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    amount_str = data.get("amount_str", "0")
    action = call.data.split("_")[1]
    if action == "confirm":
        if amount_str == "0": return await call.answer("Amount cannot be zero.", show_alert=True)
        try:
            amount = float(amount_str)
            if amount < 10: return await call.answer("Minimum deposit is ₹10.", show_alert=True)
            await state.clear()
            await call.message.edit_text("⏳ <b>✦ 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗜𝗡𝗚 𝗦𝗘𝗖𝗨𝗥𝗘 𝗤𝗥 ✦</b>", parse_mode='HTML')
            await generate_fampay_order(call.from_user.id, amount, call.message)
        except: await call.answer("Invalid amount.", show_alert=True)
        return
    if action == "backspace":
        amount_str = amount_str[:-1] if len(amount_str) > 1 else "0"
    elif action == "clear": amount_str = "0"
    else:
        amount_str = action if amount_str == "0" else amount_str + action
        if len(amount_str) > 6: amount_str = amount_str[:6]
    await state.update_data(amount_str=amount_str)
    await show_keypad(call.message, amount_str)
    await call.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_fampay_payment_callback(call: CallbackQuery):
    inr_amount = float(call.data.split("_")[1])
    await call.message.edit_text("⏳ <b>✦ 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗜𝗡𝗚 𝗦𝗘𝗖𝗨𝗥𝗘 𝗤𝗥 ✦</b>", parse_mode='HTML')
    await generate_fampay_order(call.from_user.id, inr_amount, call.message)

async def generate_fampay_order(user_id: int, inr_amount: float, message_obj: Message) -> None:
    result = await generate_fampay_qr(user_id, inr_amount)
    
    if result.get("status") == "error":
        return await message_obj.edit_text(f"❌ <b>𝗚𝗮𝘁𝗲𝘄𝗮𝘆 𝗘𝗿𝗿𝗼𝗿</b> ┃ {result.get('message')}", reply_markup=back_kb("gateway_inr"), parse_mode='HTML')
    
    data = result.get("data", {})
    qr_url = data.get("qr_url")
    order_id = data.get("order_id")
    upi_id = data.get("upi_id")
    expires_at_str = data.get("expires_at_ist")
    
    try:
        expiry_time = datetime.strptime(expires_at_str, "%d-%m-%Y %H:%M:%S") if expires_at_str else datetime.now() + timedelta(minutes=5)
        expires_timestamp = int(expiry_time.timestamp())
    except: expires_timestamp = int(time.time() + 300)
    
    db_query("INSERT OR REPLACE INTO transactions (order_id, user_id, amount_inr, status, timestamp, qr_url, upi_id, expires_at) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)", 
             (order_id, user_id, inr_amount, int(time.time()), qr_url, upi_id, expires_timestamp))
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 " + fancy("Verify Payment"), callback_data=f"verify_{order_id}", style="primary")],
        [InlineKeyboardButton(text="🖼 " + fancy("View QR Code"), url=qr_url if qr_url else "https://t.me", style="success")],
        [InlineKeyboardButton(text=fancy("Cancel Transaction"), callback_data="menu_add_balance", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    
    text = (f"🧾 <b>✦ 𝗦𝗘𝗖𝗨𝗥𝗘 𝗤𝗥 𝗥𝗘𝗔𝗗𝗬 ✦</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>𝗔𝗺𝗼𝘂𝗻𝘁</b> ┃ {fmt_curr(inr_amount)}\n"
            f"🆔 <b>𝗢𝗿𝗱𝗲𝗿 𝗜𝗗</b> ┃ <code>{order_id}</code>\n"
            f"🏦 <b>𝗨𝗣𝗜 𝗜𝗗</b> ┃ <code>{upi_id}</code>\n"
            f"⏳ <b>𝗘𝘅𝗽𝗶𝗿𝗲𝘀</b> ┃ {expires_at_str}\n━━━━━━━━━━━━━━━━━━\n"
            f"📱 <b>𝗛𝗼𝘄 𝘁𝗼 𝗣𝗮𝘆</b>\n╰ 1️⃣ Scan the QR or use UPI ID\n╰ 2️⃣ Send exact amount: {fmt_curr(inr_amount)}\n╰ 3️⃣ Tap <b>𝗩𝗲𝗿𝗶𝗳𝘆 𝗣𝗮𝘆𝗺𝗲𝗻𝘁</b>\n")
    
    await message_obj.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("verify_"))
async def manual_verify_callback(call: CallbackQuery):
    order_id = call.data.split("_", 1)[1]
    await run_payment_verification(call.from_user.id, order_id, call)

# ==============================================================================
# 11. SHOP & BUYING (WITH FIXED KEY DELIVERY)
# ==============================================================================
@dp.callback_query(F.data == "menu_shop")
async def view_shop_panels(call: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b>✦ 𝗦𝗘𝗟𝗘𝗖𝗧 𝗣𝗥𝗢𝗗𝗨𝗖𝗧 𝗣𝗔𝗡𝗘𝗟 ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n{get_emoji('point_down')} <b>𝗖𝗵𝗼𝗼𝘀𝗲 𝗮 𝗽𝗮𝗻𝗲𝗹</b>"
    for cat in FIXED_CATEGORIES:
        emoji_id = get_category_emoji(cat)
        kb.inline_keyboard.append([InlineKeyboardButton(text=fancy(cat), callback_data=f"cat_{cat[:30]}", icon_custom_emoji_id=emoji_id, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("BACK"), callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("cat_"))
async def view_panel_names(call: CallbackQuery):
    category = call.data.split("cat_", 1)[1]
    panel_names = db_query("SELECT DISTINCT panel_name FROM products WHERE category LIKE ? AND is_active=1 AND panel_name != ''", (category + '%',), fetchall=True)
    if not panel_names:
        prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit FROM products WHERE category LIKE ? AND is_active=1", (category + '%',), fetchall=True)
        if not prods: return await call.answer("❌ No products available.", show_alert=True)
        return await show_products_for_panel(call, prods, category)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b>✦ {fancy(category.upper() + ' PANELS')} ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n{get_emoji('point_down')} <b>𝗖𝗵𝗼𝗼𝘀𝗲 𝗮 𝗽𝗮𝗻𝗲𝗹</b>"
    for pn in panel_names:
        panel = pn[0]
        emoji_id = get_panel_emoji(panel) or get_emoji_icon("product_store")
        kb.inline_keyboard.append([InlineKeyboardButton(text=fancy(panel), callback_data=f"pnl_{category[:30]}_{panel[:30]}", icon_custom_emoji_id=emoji_id, style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("BACK"), callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("pnl_"))
async def view_products_for_panel(call: CallbackQuery):
    parts = call.data.split("pnl_", 1)[1].split("_", 1)
    if len(parts) != 2: return await call.answer("Invalid selection.", show_alert=True)
    category, panel_name = parts
    prods = db_query("SELECT id, name, price_inr, stock, reseller_price, validity, device_limit FROM products WHERE category LIKE ? AND panel_name LIKE ? AND is_active=1", (category + '%', panel_name + '%'), fetchall=True)
    if not prods: return await call.answer("No products found.", show_alert=True)
    await show_products_for_panel(call, prods, f"{category} - {panel_name}")

async def show_products_for_panel(call: CallbackQuery, prods: List[Tuple], header: str):
    user = db_query("SELECT is_reseller, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    is_reseller = bool(user[0]) if user else False
    is_vip = bool(user[1]) if user else False
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text = f"{get_emoji('product_store')} <b>✦ {fancy(header.upper() + ' PACKAGES')} ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in prods:
        prod_id, package_name, normal_price, stock, reseller_price, validity, device = p
        normal_price = safe_float(normal_price)
        reseller_price = safe_float(reseller_price)
        base_price = reseller_price if is_reseller else normal_price
        display_price = base_price - (base_price * (VIP_DISCOUNT_PERCENTAGE / 100)) if is_vip else base_price
        stock_status = "🟢 𝗜𝗻 𝗦𝘁𝗼𝗰𝗸" if stock > 0 else "🔴 𝗢𝘂𝘁 𝗼𝗳 𝗦𝘁𝗼𝗰𝗸"
        text += f"{get_emoji('product_store')} <b>{fancy(str(package_name))}</b>\n"
        if is_reseller or is_vip:
            text += f"💰 <b>𝗥𝗲𝗴𝘂𝗹𝗮𝗿</b> ┃ <s>{fmt_curr(normal_price)}</s>\n"
            if is_reseller and not is_vip: text += f"👑 <b>𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿</b> ┃ <b>{fmt_curr(display_price)}</b>\n"
            elif is_vip and not is_reseller: text += f"🌟 <b>𝗩𝗜𝗣</b> ┃ <b>{fmt_curr(display_price)}</b>\n"
            else: text += f"👑🌟 <b>𝗦𝘂𝗽𝗲𝗿</b> ┃ <b>{fmt_curr(display_price)}</b>\n"
        else: text += f"💰 <b>𝗣𝗿𝗶𝗰𝗲</b> ┃ <b>{fmt_curr(normal_price)}</b>\n"
        text += f"📱 <b>𝗟𝗶𝗺𝗶𝘁</b> ┃ {device}\n📦 <b>𝗦𝘁𝗼𝗰𝗸</b> ┃ {stock_status}\n┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n\n"
        if stock > 0:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"{fancy('Buy')} {fancy(str(package_name))} • {fmt_curr(display_price)}", callback_data=f"buy_{prod_id}", icon_custom_emoji_id=get_emoji_icon("product_store"), style="success")])
        else:
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {fancy(str(package_name))} • {fancy('Sold Out')}", callback_data="ignore_stock_click", style="danger")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("BACK TO PANELS"), callback_data="menu_shop", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "ignore_stock_click")
async def ignore_stock_click(call: CallbackQuery):
    await call.answer("⚠️ This duration is Out of Stock! Admins have been notified.", show_alert=True)

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(call: CallbackQuery):
    prod_id = int(call.data.split("_")[1])
    prod = db_query("SELECT name, price_inr, stock, apk_link, validity, device_limit, category, reseller_price, panel_name FROM products WHERE id=?", (prod_id,), fetchone=True)
    user = db_query("SELECT balance, is_reseller, total_saved, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if not prod: return await call.answer("❌ Item not found!", show_alert=True)
    
    normal_price = safe_float(prod[1]); reseller_price = safe_float(prod[7])
    is_reseller = bool(user[1]); is_vip = bool(user[3])
    base_price = reseller_price if is_reseller else normal_price
    final_price = base_price - (base_price * (VIP_DISCOUNT_PERCENTAGE / 100)) if is_vip else base_price
    savings = normal_price - final_price
    
    if user[0] < final_price: return await call.answer(f"❌ Insufficient Balance! Need {fmt_curr(final_price)}.", show_alert=True)
    
    # KEY DELIVERY LOGIC (FIXED)
    delivered_key = None
    key_data = db_query("SELECT id, key_text FROM product_keys WHERE product_id=? AND is_used=0 LIMIT 1", (prod_id,), fetchone=True)
    
    if key_data:
        delivered_key = key_data[1]
        db_query("UPDATE product_keys SET is_used=1 WHERE id=?", (key_data[0],))
        db_query("UPDATE products SET stock=stock-1 WHERE id=?", (prod_id,))
        db_query("UPDATE users SET balance=balance-?, spent=spent+?, orders_count=orders_count+1, total_saved=total_saved+? WHERE user_id=?", (final_price, final_price, savings, call.from_user.id))
    else:
        return await call.answer("❌ Out of Stock! Please contact admin. Your balance is safe.", show_alert=True)
    
    product_full_name = f"{prod[6]} - {prod[8]} ({prod[0]})"
    db_query("INSERT INTO orders (user_id, product_name, price_paid, delivered_key, purchase_date) VALUES (?, ?, ?, ?, ?)", (call.from_user.id, product_full_name, final_price, delivered_key, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    await send_advanced_notification(call.from_user.id, "ORDER", final_price, product=product_full_name, key=delivered_key)
    
    msg = (f"{get_emoji('check_icon')} <b>✦ 𝗣𝗨𝗥𝗖𝗛𝗔𝗦𝗘 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟 ✦</b>\n━━━━━━━━━━━━━━━━━━\n📦 <b>𝗣𝗮𝗻𝗲𝗹</b> ┃ {prod[6]}\n📁 <b>𝗡𝗮𝗺𝗲</b> ┃ {prod[8]}\n⏱ <b>𝗣𝗮𝗰𝗸𝗮𝗴𝗲</b> ┃ {prod[0]}\n💰 <b>𝗣𝗮𝗶𝗱</b> ┃ {fmt_curr(final_price)}\n📱 <b>𝗗𝗲𝘃𝗶𝗰𝗲</b> ┃ {prod[5]}\n━━━━━━━━━━━━━━━━━━\n")
    if prod[3] and prod[3].startswith("http"): msg += f"📥 <b>𝗔𝗣𝗞</b> ┃ <a href='{prod[3]}'>Download Now</a>\n\n"
    msg += f"🔑 <b>𝗬𝗼𝘂𝗿 𝗞𝗲𝘆</b>\n<code>{delivered_key}</code>\n\n<i>Need help?</i> <code>{ADMIN_CONTACT}</code>"
    await call.message.edit_text(msg, reply_markup=back_kb("menu_shop"), disable_web_page_preview=True, parse_mode='HTML')

# ==============================================================================
# 12. PROFILE & RESELLER
# ==============================================================================
@dp.callback_query(F.data == "menu_profile")
async def show_profile(call: CallbackQuery):
    u = db_query("SELECT user_id, first_name, account_type, balance, orders_count, spent, joined_date, is_reseller, reseller_since, total_saved, is_vip FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    acc_type = []
    if u[7]: acc_type.append(f"{get_emoji('reseller')} 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿")
    if u[10]: acc_type.append(f"{get_emoji('vip')} 𝗩𝗜𝗣")
    type_str = " | ".join(acc_type) if acc_type else f"{get_emoji('regular_user')} 𝗥𝗲𝗴𝘂𝗹𝗮𝗿"
    
    text = (f"{get_emoji('grid_id')} <b>✦ 𝗬𝗢𝗨𝗥 𝗣𝗥𝗢𝗙𝗜𝗟𝗘 ✦</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            f"{get_emoji('grid_id')} <b>𝗚𝗿𝗶𝗱 𝗜𝗗</b> ┃ <code>{u[0]}</code>\n"
            f"{get_emoji('name')} <b>𝗡𝗮𝗺𝗲</b> ┃ {u[1]}\n"
            f"{get_emoji('account_level')} <b>𝗟𝗲𝘃𝗲𝗹</b> ┃ {type_str}\n\n"
            f"{get_emoji('wallet_left')} <b>✦ 𝗪𝗔𝗟𝗟𝗘𝗧 ✦</b> {get_emoji('wallet_right')}\n"
            f"{get_emoji('wallet_left')} <b>𝗕𝗮𝗹𝗮𝗻𝗰𝗲</b> ┃ {fmt_curr(u[3])}\n\n"
            f"{get_emoji('global_stats')} <b>✦ 𝗦𝗧𝗔𝗧𝗦 ✦</b>\n"
            f"{get_emoji('total_orders')} <b>𝗢𝗿𝗱𝗲𝗿𝘀</b> ┃ {u[4]}\n"
            f"{get_emoji('total_spent')} <b>𝗦𝗽𝗲𝗻𝘁</b> ┃ {fmt_curr(u[5])}\n")
    if u[7]: text += f"{get_emoji('money_icon')} <b>𝗦𝗮𝘃𝗲𝗱</b> ┃ {fmt_curr(u[9])}\n"
    text += f"{get_emoji('joined_grid')} <b>𝗝𝗼𝗶𝗻𝗲𝗱</b> ┃ {u[6]}\n"
    
    orders = db_query("SELECT delivered_key FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (call.from_user.id,), fetchall=True)
    text += "━━━━━━━━━━━━━━━━━━\n🧾 <b>✦ 𝗛𝗜𝗦𝗧𝗢𝗥𝗬 ✦</b>\n\n"
    if orders:
        for o in orders: text += f"🔑 <code>{o[0]}</code>\n"
    else: text += "📭 <i>No purchases yet.</i>\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=fancy("Redeem Code"), callback_data="redeem_coupon", icon_custom_emoji_id=get_emoji_icon('redeem_icon'), style="success")],
        [InlineKeyboardButton(text=fancy("BACK"), callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "menu_reseller_dash")
async def reseller_dashboard(call: CallbackQuery):
    u = db_query("SELECT balance, is_reseller, reseller_since, total_saved FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    system_status = get_setting("reseller_system_status", "ON")
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    
    if u[1]:
        text = f"{get_emoji('shield_icon')} <b>✦ 𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗗𝗔𝗦𝗛𝗕𝗢𝗔𝗥𝗗 ✦</b>\n━━━━━━━━━━━━━━━━━━\n🟢 <b>𝗦𝘁𝗮𝘁𝘂𝘀</b> ┃ Active\n📅 <b>𝗦𝗶𝗻𝗰𝗲</b> ┃ {u[2]}\n{get_emoji('money_icon')} <b>𝗦𝗮𝘃𝗲𝗱</b> ┃ {fmt_curr(u[3])}\n━━━━━━━━━━━━━━━━━━"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=fancy("BACK"), callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")]])
        return await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')
    
    if system_status == "OFF": return await call.answer("⚠️ Reseller registrations are closed.", show_alert=True)
    
    text = f"👑 <b>✦ 𝗕𝗘𝗖𝗢𝗠𝗘 𝗔 𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 ✦</b>\n━━━━━━━━━━━━━━━━━━\n📋 <b>𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗺𝗲𝗻𝘁𝘀</b>\n╰ Min Balance: <b>{fmt_curr(min_balance)}</b>\n╰ Setup Fee: <b>{fmt_curr(setup_fee)}</b>\n\n💳 <b>𝗬𝗼𝘂𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲</b> ┃ {fmt_curr(u[0])}\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    if u[0] >= min_balance:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"✅ {fancy('Pay')} {fmt_curr(setup_fee)} {fancy('& Become Reseller')}", callback_data="execute_reseller_upgrade", style="success")])
    else:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ {fancy('Need')} {fmt_curr(min_balance)}", callback_data="ignore_stock_click", style="danger")])
        kb.inline_keyboard.append([InlineKeyboardButton(text="💳 " + fancy("Add Balance"), callback_data="menu_add_balance", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("BACK"), callback_data="back_main", icon_custom_emoji_id=get_emoji_icon("back"), style="danger")])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "execute_reseller_upgrade")
async def execute_reseller_upgrade(call: CallbackQuery):
    setup_fee = safe_float(get_setting("reseller_setup_fee", "200.0"))
    min_balance = safe_float(get_setting("reseller_min_balance", "500.0"))
    u = db_query("SELECT balance, is_reseller FROM users WHERE user_id=?", (call.from_user.id,), fetchone=True)
    if u[1]: return await call.answer("⚠️ You are already a Reseller!", show_alert=True)
    if u[0] < min_balance: return await call.answer(f"❌ Balance below {fmt_curr(min_balance)}.", show_alert=True)
    
    db_query("UPDATE users SET balance=balance-?, is_reseller=1, reseller_since=?, account_type='Reseller' WHERE user_id=?", (setup_fee, datetime.now().strftime("%Y-%m-%d"), call.from_user.id))
    await call.answer("🎉 Welcome to the Reseller tier!", show_alert=True)
    await reseller_dashboard(call)

# ==============================================================================
# 13. ADMIN PANEL & PRODUCT MANAGEMENT
# ==============================================================================
@dp.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear()
    await message.answer("⚙️ <b>✦ 𝗔𝗗𝗠𝗜𝗡 𝗧𝗘𝗥𝗠𝗜𝗡𝗔𝗟 ✦</b>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_panel_back")
async def back_to_admin(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⚙️ <b>✦ 𝗔𝗗𝗠𝗜𝗡 𝗧𝗘𝗥𝗠𝗜𝗡𝗔𝗟 ✦</b>", reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data == "admin_setup_fampay")
async def admin_setup_fampay(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    current_api = get_setting("fampay_api_key", "")
    current_upi = get_setting("fampay_upi_id", "")
    current_manual = get_setting("manual_upi_id", "")
    text = (f"⚙️ <b>FamPay & Manual UPI Setup</b>\n\n"
            f"FamPay API Key: <code>{current_api if current_api else 'Not Set'}</code>\n"
            f"FamPay UPI ID: <code>{current_upi if current_upi else 'Not Set'}</code>\n"
            f"Manual UPI ID: <code>{current_manual if current_manual else 'Not Set'}</code>\n\n"
            f"<i>If FamPay API is not set, the bot will use Manual UPI mode.</i>")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Set FamPay API", callback_data="admin_set_fampay_api", style="primary")],
        [InlineKeyboardButton(text="Set FamPay UPI", callback_data="admin_set_fampay_upi", style="primary")],
        [InlineKeyboardButton(text="Set Manual UPI ID", callback_data="admin_set_manual_upi", style="primary")],
        [InlineKeyboardButton(text="Set Manual QR URL", callback_data="admin_set_manual_qr", style="primary")],
        [InlineKeyboardButton(text=fancy("Back"), callback_data="admin_panel_back", style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data == "admin_set_fampay_api")
async def admin_set_fampay_api(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🔑 Send your FamPay API Key:", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.wait_for_fampay_api)

@dp.message(AdminStates.wait_for_fampay_api)
async def save_fampay_api(m: Message, state: FSMContext):
    set_setting("fampay_api_key", m.text.strip())
    await m.answer("✅ FamPay API Key saved!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "admin_set_fampay_upi")
async def admin_set_fampay_upi(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🏦 Send your FamPay UPI ID:", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.wait_for_fampay_upi)

@dp.message(AdminStates.wait_for_fampay_upi)
async def save_fampay_upi(m: Message, state: FSMContext):
    set_setting("fampay_upi_id", m.text.strip())
    await m.answer("✅ FamPay UPI saved!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "admin_set_manual_upi")
async def admin_set_manual_upi(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🏦 Send your Manual UPI ID (for fallback):", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.wait_for_manual_upi)

@dp.message(AdminStates.wait_for_manual_upi)
async def save_manual_upi(m: Message, state: FSMContext):
    set_setting("manual_upi_id", m.text.strip())
    await m.answer("✅ Manual UPI saved!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "admin_set_manual_qr")
async def admin_set_manual_qr(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🖼 Send your Manual QR Image URL:", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.wait_for_manual_qr)

@dp.message(AdminStates.wait_for_manual_qr)
async def save_manual_qr(m: Message, state: FSMContext):
    set_setting("manual_qr_url", m.text.strip())
    await m.answer("✅ Manual QR URL saved!", reply_markup=admin_kb())
    await state.clear()

# --- ADD PRODUCT WITH KEYS ---
@dp.callback_query(F.data == "admin_add_prod")
async def add_prod_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cat in FIXED_CATEGORIES:
        kb.inline_keyboard.append([InlineKeyboardButton(text=cat, callback_data=f"addprod_cat_{cat}", icon_custom_emoji_id=get_category_emoji(cat), style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("Cancel"), callback_data="admin_panel_back", style="danger")])
    await call.message.edit_text("<b>Step 1:</b> Choose Category:", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("addprod_cat_"))
async def add_prod_category_selected(call: CallbackQuery, state: FSMContext):
    category = call.data.split("addprod_cat_", 1)[1]
    await state.update_data(cat=category)
    await call.message.edit_text("<b>Step 2:</b> Enter PANEL NAME (e.g., 'MST PANEL'):", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.add_prod_panel_name)

@dp.message(AdminStates.add_prod_panel_name)
async def add_prod_panel_name(m: Message, state: FSMContext):
    await state.update_data(panel_name=m.text)
    await m.answer("<b>Step 3:</b> Enter PACKAGE NAME (e.g., '1 Hour', '3 Hours', '1 Day'):")
    await state.set_state(AdminStates.add_prod_name)

@dp.message(AdminStates.add_prod_name)
async def add_prod_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("⏳ Enter Validity (e.g., '24 Hours'):")
    await state.set_state(AdminStates.add_prod_validity)

@dp.message(AdminStates.add_prod_validity)
async def add_prod_validity(m: Message, state: FSMContext):
    await state.update_data(validity=m.text)
    await m.answer("📱 Enter Device Limit (e.g., '1 Device'):")
    await state.set_state(AdminStates.add_prod_device_limit)

@dp.message(AdminStates.add_prod_device_limit)
async def add_prod_device_limit(m: Message, state: FSMContext):
    await state.update_data(device_limit=m.text)
    await m.answer("💰 Enter Normal Price (₹):")
    await state.set_state(AdminStates.add_prod_price)

@dp.message(AdminStates.add_prod_price)
async def add_prod_price(m: Message, state: FSMContext):
    try:
        await state.update_data(price=float(m.text))
        await m.answer("👑 Enter Reseller Price (₹):")
        await state.set_state(AdminStates.add_prod_reseller_price)
    except: await m.answer("❌ Invalid number!")

@dp.message(AdminStates.add_prod_reseller_price)
async def add_prod_reseller_price(m: Message, state: FSMContext):
    try:
        await state.update_data(reseller_price=float(m.text))
        await m.answer("🔗 Enter APK Link (or 'none'):")
        await state.set_state(AdminStates.add_prod_apk)
    except: await m.answer("❌ Invalid number!")

@dp.message(AdminStates.add_prod_apk)
async def add_prod_apk(m: Message, state: FSMContext):
    await state.update_data(apk="" if m.text.lower() == 'none' else m.text)
    await m.answer("📥 <b>KEY STOCK</b>\nPaste all keys (1 per line):")
    await state.set_state(AdminStates.add_prod_keys)

@dp.message(AdminStates.add_prod_keys)
async def add_prod_keys(m: Message, state: FSMContext):
    keys = [k.strip() for k in m.text.strip().split('\n') if k.strip()]
    data = await state.get_data()
    conn = sqlite3.connect('Sandii.dp')
    c = conn.cursor()
    c.execute("INSERT INTO products (category, panel_name, name, price_inr, reseller_price, stock, apk_link, validity, device_limit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (data['cat'], data['panel_name'], data['name'], data['price'], data['reseller_price'], len(keys), data['apk'], data['validity'], data['device_limit']))
    prod_id = c.lastrowid
    for k in keys: c.execute("INSERT INTO product_keys (product_id, key_text) VALUES (?, ?)", (prod_id, k))
    conn.commit(); conn.close()
    await m.answer(f"✅ <b>Product Added!</b>\n📦 {data['cat']} → {data['panel_name']} → {data['name']}\n🔑 Stock: {len(keys)} Keys", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "admin_manage_prods")
async def admin_manage_prods(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID: return
    prods = db_query("SELECT id, name, category, panel_name, stock, is_active FROM products ORDER BY category", fetchall=True)
    if not prods: return await call.message.edit_text("📦 Empty database.", reply_markup=admin_back_kb())
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in prods:
        status = "🟢" if p[5] else "🔴"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{status} [{p[2]}] {p[3]} - {p[1]} (Stock: {p[4]})", callback_data=f"admin_view_p_{p[0]}", style="primary")])
    kb.inline_keyboard.append([InlineKeyboardButton(text=fancy("Back"), callback_data="admin_panel_back", style="danger")])
    await call.message.edit_text("📦 <b>Select Product to Edit:</b>", reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("admin_view_p_"))
async def admin_view_product(call: CallbackQuery):
    p_id = int(call.data.split("_")[3])
    prod = db_query("SELECT * FROM products WHERE id=?", (p_id,), fetchone=True)
    if not prod: return await call.answer("Product not found!", show_alert=True)
    
    text = (f"📦 <b>Product Details</b>\n━━━━━━━━━━━━━━━━━━\n"
            f"ID: <code>{prod[0]}</code>\nCategory: {prod[1]}\nPanel: {prod[2]}\nName: {prod[3]}\n"
            f"Price: {fmt_curr(safe_float(prod[4]))}\nReseller Price: {fmt_curr(safe_float(prod[5]))}\n"
            f"Stock: {prod[6]}\nValidity: {prod[8]}\nDevice: {prod[9]}\n")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Edit Price", callback_data=f"edit_p_{p_id}_price", style="primary"), InlineKeyboardButton(text="Edit Reseller Price", callback_data=f"edit_p_{p_id}_rprice", style="primary")],
        [InlineKeyboardButton(text="Add Keys ➕", callback_data=f"edit_p_{p_id}_keys", style="success")],
        [InlineKeyboardButton(text="Toggle Visibility", callback_data=f"toggle_p_{p_id}", style="danger")],
        [InlineKeyboardButton(text="Delete Product 🗑", callback_data=f"delete_p_{p_id}", style="danger")],
        [InlineKeyboardButton(text=fancy("Back"), callback_data="admin_manage_prods", style="danger")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.startswith("edit_p_"))
async def start_edit_product(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 3)
    p_id = int(parts[2]); field = parts[3]
    await state.update_data(edit_p_id=p_id, edit_field=field)
    if field == 'keys':
        await call.message.edit_text("📥 Paste NEW KEYS to add (1 per line):", reply_markup=admin_back_kb())
        await state.set_state(AdminStates.wait_for_add_keys)
    else:
        await call.message.edit_text(f"✏️ Enter new value for <b>{field}</b>:", reply_markup=admin_back_kb())
        await state.set_state(AdminStates.wait_for_new_value)

@dp.message(AdminStates.wait_for_new_value)
async def process_edit_value(m: Message, state: FSMContext):
    data = await state.get_data()
    p_id = data['edit_p_id']; field = data['edit_field']; new_val = m.text.strip()
    if field in ['price', 'rprice']:
        try: new_val = float(new_val)
        except: return await m.answer("❌ Invalid number!")
    
    db_col = {'price': 'price_inr', 'rprice': 'reseller_price'}.get(field, field)
    db_query(f"UPDATE products SET {db_col}=? WHERE id=?", (new_val, p_id))
    await m.answer("✅ Updated!", reply_markup=admin_kb())
    await state.clear()

@dp.message(AdminStates.wait_for_add_keys)
async def process_add_keys(m: Message, state: FSMContext):
    data = await state.get_data(); p_id = data['edit_p_id']
    keys = [k.strip() for k in m.text.strip().split('\n') if k.strip()]
    if not keys: return await m.answer("❌ No valid keys found.")
    
    conn = sqlite3.connect('Sandii.dp'); c = conn.cursor()
    for k in keys: c.execute("INSERT INTO product_keys (product_id, key_text) VALUES (?, ?)", (p_id, k))
    c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (len(keys), p_id))
    conn.commit(); conn.close()
    await m.answer(f"✅ {len(keys)} keys added to stock!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data.startswith("toggle_p_"))
async def admin_toggle_product(call: CallbackQuery):
    p_id = int(call.data.split("_")[2])
    current = db_query("SELECT is_active FROM products WHERE id=?", (p_id,), fetchone=True)[0]
    db_query("UPDATE products SET is_active=? WHERE id=?", (0 if current else 1, p_id))
    await call.answer("Visibility updated!")
    await admin_view_product(call)

@dp.callback_query(F.data.startswith("delete_p_"))
async def admin_delete_product(call: CallbackQuery):
    p_id = int(call.data.split("_")[2])
    db_query("DELETE FROM products WHERE id=?", (p_id,))
    db_query("DELETE FROM product_keys WHERE product_id=?", (p_id,))
    await call.answer("Product deleted!", show_alert=True)
    await admin_manage_prods(call)

# ==============================================================================
# 14. ADMIN STATS
# ==============================================================================
@dp.callback_query(F.data == "admin_view_stats")
async def admin_dashboard_stats(call: CallbackQuery):
    t_users = db_query("SELECT COUNT(*) FROM users", fetchone=True)[0]
    t_prods = db_query("SELECT COUNT(*) FROM products", fetchone=True)[0]
    t_keys = db_query("SELECT COUNT(*) FROM product_keys WHERE is_used=0", fetchone=True)[0]
    t_rev = db_query("SELECT SUM(spent) FROM users", fetchone=True)[0] or 0.0
    msg = (f"📊 <b>✦ 𝗦𝗧𝗢𝗥𝗘 𝗔𝗡𝗔𝗟𝗬𝗧𝗜𝗖𝗦 ✦</b>\n━━━━━━━━━━━━━━━━━━\n"
           f"👥 <b>Users</b> ┃ {t_users}\n📦 <b>Products</b> ┃ {t_prods}\n"
           f"🔑 <b>Unused Keys</b> ┃ {t_keys}\n💰 <b>Revenue</b> ┃ {fmt_curr(t_rev)}\n━━━━━━━━━━━━━━━━━━")
    await call.message.edit_text(msg, reply_markup=admin_back_kb(), parse_mode='HTML')

# ==============================================================================
# 15. START BOT
# ==============================================================================
async def main():
    init_db()
    logger.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
