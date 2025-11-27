import telebot
import datetime
import requests
import tempfile
import threading
import time
import os
import io
from datetime import date
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonDefault
from supabase import create_client, Client
import os
import re

from datetime import datetime, time
from zoneinfo import ZoneInfo
from math import ceil
from telebot.types import InputMediaPhoto
from typing import Dict, List, Set

_admin_media_buffers: Dict[str, List[str]] = {}
_admin_media_flush_scheduled: Set[str] = set()

MOSCOW_TZ = ZoneInfo("Europe/Moscow")
MIN_RUB = 1000
UB_TZ = ZoneInfo("Asia/Ulaanbaatar")
MIN_VOLUME_RUB      = 50_000    # threshold in 
MIN_VOLUME_RUB_2      = 100_000
VOLUME_DISCOUNT_MNT = 0.2       # in MNT
VOLUME_DISCOUNT_MNT_2 = 0.3


def sanitize_markdown(text: str) -> str:
    if not text:
        return ""
    # Escape Markdown (v1) specials that commonly break captions
    return re.sub(r'([_*`\[\]\(\)])', r'\\\1', str(text))
    
def is_within_ub_business_hours():
    now_ub = datetime.now(MOSCOW_TZ).time()
    start = time(4, 0)           # not time(04, 00)
    end   = time(23, 0)     # up until 22:59:59
    return start <= now_ub <= end

# Replace with your bot token
BOT_TOKEN = "7842397817:AAHUp5gf_0QI8QPmp1_LFX7byNsjK9h5MEI"
bot = telebot.TeleBot(BOT_TOKEN)
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://earnest-brigadeiros-a41706.netlify.app/")


def restore_default_menu_button():
    """
    Ensure the default slash-command menu stays available even when the mini app exists.
    """
    try:
        bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        print("✅ Telegram menu button reset to default (commands available)")
    except Exception as exc:
        print(f"❌ Failed to reset menu button: {exc}")


restore_default_menu_button()


SUPABASE_URL = "https://ldolpsylyatkxqsgxhkn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxkb2xwc3lseWF0a3hxc2d4aGtuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0Mjc1OTg4MSwiZXhwIjoyMDU4MzM1ODgxfQ.LgsjFKhMoLc5mDeb_3jg9b745JaEavdBBBOjPXlds7o"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Replace with the Operator's Telegram User ID
#OPERATOR_CHAT_ID = 1932946217 # Change to real operator ID
#ADMIN_IDS = 1932946217
HIGH_VALUE_OPERATOR_CHAT_ID = 1447446407
ALWAYS_NOTIFY_OPERATOR_ID = [1932946217, 1447446407]
ALLOWED_ADMINS = {1932946217, 1447446407, 5564298862, 1409343588, 6351681039}  #pending_users
#1447446407 Surnee ah
#1932946217 Temuulen Ochirbat
#BANK_DETAILS_MNT = "🏦 ХААН БАНК\n Дансны нэр: СҮРЭНЖАВ\nДансны IBAN дугаар: IBAN MN750005005313286273\nДансны дугаар: `5313286273`\n"
#BANK_DETAILS_RUB = "🏦 СБЕРБАНК\n Дансны нэр: XXX\nДансны дугаар: 500XXXXXX"
CONTACT_SUPPORT = "📞 Холбоо барих: +976 7780 6060\n +7 (977) 801-91-43\n [https://t.me/oyuns_support]"

NOT_WORKING_TEXT = (
    "⏳ Бид одоогоор ажиллахгүй байна. Та дараа манай ажлын цаг нээгдэхээр дахин оролдоно уу.\n"
    "📞 Тусламж: @oyuns_support"
)
def ensure_admin_available(chat_id: int) -> bool:
    admin_id = get_current_admin_id()
    if not admin_id:
        bot.send_message(chat_id, NOT_WORKING_TEXT)
        return False
    return True
def ensure_exchange_available(chat_id: int) -> bool:
    if not ensure_admin_available(chat_id):
        clear_state(chat_id)
        return False
    return True
    
def update_user_session(user_id, data: dict):
    existing = get_user_session(user_id)
    existing.update(data)
    existing["user_id"] = user_id
    existing["last_updated"] = datetime.utcnow().isoformat()
    supabase.table("user_sessions").upsert(existing).execute()

def get_user_session(user_id):
    try:
        result = supabase.table("user_sessions").select("*").eq("user_id", user_id).limit(1).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        print(f"Error getting user session for {user_id}: {e}")
        return {}


def get_state(user_id):
    session = get_user_session(user_id)
    return session.get("state") or ""

def clear_state(user_id):
    supabase.table("user_sessions").update({"state": None}).eq("user_id", user_id).execute()

#HEREGLEGCHIIN GEREE

def ask_terms_agreement(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📄 Хэрэглэгчийн гэрээ", url="https://oyuns.mn/oyuns-aio-telegram-bot-%d1%85%d1%8d%d1%80%d1%8d%d0%b3%d0%bb%d1%8d%d0%b3%d1%87%d0%b8%d0%b9%d0%bd-%d0%b3%d1%8d%d1%80%d1%8d%d1%8d/"))
    markup.add(InlineKeyboardButton("✅ Зөвшөөрч байна", callback_data="accept_terms"))
    bot.send_message(chat_id, "📜 Сайн байна уу, та OYUNS AIO бот ашиглахын өмнө [хэрэглэгчийн гэрээтэй](https://oyuns.mn/oyuns-aio-telegram-bot-%d1%85%d1%8d%d1%80%d1%8d%d0%b3%d0%bb%d1%8d%d0%b3%d1%87%d0%b8%d0%b9%d0%bd-%d0%b3%d1%8d%d1%80%d1%8d%d1%8d/) уншиж танилцана уу. Хэрвээ зөвшөөрч байвал дараах товчыг дарж үргэлжлүүлээрэй.", parse_mode="Markdown", reply_markup=markup)
def has_agreed_terms(user_id):
    response = supabase.table("users").select("agreed_terms").eq("id", user_id).execute()
    return response.data and response.data[0]['agreed_terms'] == True
    
def set_agreed_terms(user_id):
    # Ensure user row exists before update
    response = supabase.table("users").select("id").eq("id", user_id).execute()
    if not response.data:
        supabase.table("users").insert({"id": user_id}).execute()

    supabase.table("users").update({"agreed_terms": True}).eq("id", user_id).execute()



@bot.callback_query_handler(func=lambda call: call.data == "accept_terms")
def handle_terms_accept(call):
    user_id = call.from_user.id
    set_agreed_terms(user_id)
    bot.answer_callback_query(call.id, "Та OYUNS AIO Telegram Bot-ын хэрэглэгчийн гэрээг зөвшөөрлөө.")
    bot.send_message(call.message.chat.id, "Баярлалаа! Та ийнхүү бидний үйлчилгээг ашиглах боломжтой боллоо.")
    def delayed_start():
        time.sleep(1.0)  # Let Supabase commit finish
        handle_start(call.message)

    threading.Thread(target=delayed_start).start()

@bot.message_handler(commands=['geree'])
def terms_handler(message):
  markup = InlineKeyboardMarkup()
  markup.add(InlineKeyboardButton("📄 Хэрэглэгчийн гэрээ:", url="https://oyuns.mn/oyuns-aio-telegram-bot-%d1%85%d1%8d%d1%80%d1%8d%d0%b3%d0%bb%d1%8d%d0%b3%d1%87%d0%b8%d0%b9%d0%bd-%d0%b3%d1%8d%d1%80%d1%8d%d1%8d/"))
  bot.send_message(message.chat.id, "📄 Та хэрэглэгчийн гэрээг эндээс уншина уу.", reply_markup=markup)
  

@bot.message_handler(commands=['webapp', 'app', 'mini'])
def open_mini_app(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "💱 Валют Солих - Mini App",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    )
    bot.send_message(
        message.chat.id,
        "📱 Mini App-ийг нээх бол доорх товчийг дарна уу:",
        reply_markup=markup
    )
    
#-------------------GUILGEENII TUUH----------------------
PAGE_SIZE = 5  # items per page

def format_ub(dt_str: str) -> str:
    # your transactions.timestamp is UTC ISO without TZ
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(UB_TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_str[:16] if dt_str else "-"

def compute_converted(txn) -> tuple[float, str]:
    amt  = float(txn["amount"])
    rate = float(txn["rate"])
    cf   = txn["currency_from"].upper()
    if cf == "RUB":
        return round(amt * rate, 2), "MNT"
    else:
        return round(amt / rate, 2), "RUB"




@bot.message_handler(commands=["shift_status"])
def show_current_shift_admin(message):
    if message.from_user.id not in ALLOWED_ADMINS:
        return  # Admin биш бол чимээгүй

    current_admin_id = get_current_admin_id()
    if current_admin_id:
        bot.send_message(
            message.chat.id,
            f"👤 Одоогийн ээлж хариуцагч: [{current_admin_id}](tg://user?id={current_admin_id})",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id, "❓ Одоогоор ээлж томилоогүй байна.")



def get_current_shift_config():
    admin_id = get_current_admin_id()
    if not admin_id:
        return None

    # Define each admin's bank details
    bank_info_by_admin = {
        5564298862: {
            "sberbank_rub": (
                "🏦 *СБЕРБАНК*\n\n"
                "Утасны дугаар: `+7 999 685 74 63`\n"
                "Дансны нэр: *Тэгшмагнай*"
            ),
            "vtbbank_rub": (
                "🏦 *ВТБ*\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: ``\n"
                "Дансны нэр: **"
            ),
            "alphabank_rub": (
                "🏦 *СБЕРБАНК*\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: ``\n"
                "Дансны нэр: **"
            ),
            "bank_mnt": (
                "🏦 *ХААН БАНК*\n\n"
                "Дансны нэр: *Амгаланбаатар*\n"
                "Данс: `MN59000500 5314495763`"
            )
        },
        1932946217: {
            "sberbank_rub": (
                "🏦 **\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: **\n"
                "Дансны нэр: **"
            ),
            "vtbbank_rub": (
                "🏦 *СБЕРБАНК*\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: **\n"
                "Дансны нэр: **"
            ),
            "alphabank_rub": (
                "🏦 *СБЕРБАНК*\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: **\n"
                "Дансны нэр: **"
            ),
            "bank_mnt": (
                "🏦 *ХААН БАНК*\n\n"
                "Дансны нэр: **\n"
                "Данс: ``"
            )
        },

        1409343588: {
            "sberbank_rub2": (
                "🏦 *СБЕРБАНК*\n\n"
                "Картын дугаар: `2202 2084 1034 6242`\n"
                "Утасны дугаар: `+7 996 437 18 92`\n"
                "Дансны нэр: *Анужин*"
            ),
            "sberbank_rub1": (
                "🏦 *СБЕРБАНК*\n\n"
                "Картын дугаар: `2202 2063 0354 3297`\n"
                "Утасны дугаар: `+7 999 686 78 93`\n"
                "Дансны нэр: *Анударь*"
            ),
            "vtbbank_rub": (
                "🏦 *ВТБ*\n\n"
                "Картын дугаар: ``\n"
                "Утасны дугаар: ``\n"
                "Дансны нэр: **"
            ),
            "alphabank_rub1": (
                "🏦 *АЛЬФА БАНК*\n\n"
                "Картын дугаар: `2200 1529 0483 3053`\n"
                "Утасны дугаар: `+7 950 096 92 87`\n"
                "Дансны нэр: *Тувшинжаргал Мунхзаяа*"
            ),
            "alphabank_rub2": (
                "🏦 *АЛЬФА БАНК*\n\n"
                "Картын дугаар: `2200 1529 9148 7847`\n"
                "Утасны дугаар: `+7 999 642 63 28`\n"
                "Дансны нэр: *Ачитбаатар*"
            ),
            "bank_mnt": (
                "🏦 *ХААН БАНК*\n\n"
                "Дансны нэр: *Амгаланбаатар*\n"
                "Данс: `MN82000500 5314497192`"
            )
        }
    }

    if admin_id not in bank_info_by_admin:
        return None

    admin_data = bank_info_by_admin[admin_id]

    # only one bank for admin 5564298862
    if admin_id == 5564298862:
        rub_options = {
            "Сбербанк": admin_data["sberbank_rub"],
        }
        bank_rub = admin_data["sberbank_rub"]
    else:
        rub_options = {
            "Альфа 1": admin_data["alphabank_rub2"],
            "Альфа 2": admin_data["alphabank_rub1"]
            
        }
        bank_rub = admin_data["sberbank_rub2"]  # choose default (or whichever you prefer)
    
    return {
        "operator_id": admin_id,
        "bank_rub": bank_rub,
        "bank_mnt": admin_data["bank_mnt"],
        "rub_bank_options": rub_options
    }


@bot.callback_query_handler(func=lambda call: call.data in ["BUY_RATE", "SELL_RATE"])
def handle_exchange_direction(call):
    if not is_within_ub_business_hours():
        bot.send_message(
            call.message.chat.id,
            "⚠️ Бид Москвагийн цагаар 04:00-23:00 хооронд, Улаанбаатарын цагаар 09:00–04:00(дараа өдрийн) цагийн хооронд ажиллаж байна.",
        )
        return
        # ⛔ stop if no admin on shift
    if not ensure_admin_available(call.message.chat.id):
        return    
    config = get_current_shift_config()
    


    #if not config:
    #    bot.send_message(call.message.chat.id,
    #        "⚠️ Бид Москвагийн цагаар 04:00–01:00(дараа өдрийн) хооронд ажиллаж байна.\n"
    #        "🕓 Та үйлчилгээний цагийн хуваарийн дагуу үйлчлүүлнэ үү.")
    #    return

    # Set globals dynamically
    global OPERATOR_CHAT_ID, BANK_DETAILS_RUB, BANK_DETAILS_MNT
    OPERATOR_CHAT_ID = config["operator_id"]
    BANK_DETAILS_RUB = config["bank_rub"]
    BANK_DETAILS_MNT = config["bank_mnt"]

    if call.data == "BUY_RATE":
        BUY_RATE(call)
    else:
        SELL_RATE(call)


# Store user states, profiles, and transactions
user_amounts = {}  # Stores the entered amount
user_profiles = {}  # {user_id: {"bank_details": "..."}}
pending_transactions = {}  # {user_id: {"invoice": "...", "bank_details": "...", "receipt_id": ...}}
user_transaction_session = {}
user_invoice = {}
transaction_counter = 1  # Tracks daily transactions
exchange_rates = {}  # To store rates dynamically
invoice_user_map = {}
user_feedback_state = {}
pending_morning_alerts = []




#Function to Get/Set Current Shift Admin
def get_current_admin_id():
    try:
        response = supabase.table("admin_shifts").select("current_admin_id").limit(1).execute()
        if response.data:
            return response.data[0]["current_admin_id"]
    except Exception as e:
        print(f"❌ Failed to fetch current admin: {e}")
    return None

def log_admin_activity(action_type: str, performed_by_admin_id: int, target_admin_id=None, previous_admin_id=None, is_automatic=False):
    """
    Log admin shift activity to Supabase.
    
    Args:
        action_type: "opened", "closed", or "transferred"
        performed_by_admin_id: ID of admin who performed the action
        target_admin_id: ID of admin who received the shift (for transfers/opens)
        previous_admin_id: ID of previous admin (for transfers)
        is_automatic: Whether the action was automatic (scheduled) or manual
    """
    try:
        log_data = {
            "action_type": action_type,
            "performed_by_admin_id": performed_by_admin_id,
            "is_automatic": is_automatic,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if target_admin_id is not None:
            log_data["target_admin_id"] = target_admin_id
        if previous_admin_id is not None:
            log_data["previous_admin_id"] = previous_admin_id
            
        supabase.table("admin_activity_logs").insert(log_data).execute()
        print(f"✅ Admin activity logged: {action_type} by {performed_by_admin_id}")
    except Exception as e:
        print(f"❌ Failed to log admin activity: {e}")

def set_current_admin_id(new_admin_id, performed_by_admin_id=None, is_automatic=False):
    try:
        # Get previous admin before updating
        previous_admin_id = get_current_admin_id()
        
        supabase.table("admin_shifts").update({
            "current_admin_id": new_admin_id,
            "last_updated": datetime.utcnow().isoformat()
        }).eq("id", 1).execute()  # 👈 "id" нь 1 гэж шууд зааж байна

        # Log the activity
        if new_admin_id is not None:
            # Determine action type
            if previous_admin_id is None:
                action_type = "opened"
            else:
                action_type = "transferred"
            
            # Use provided performed_by_admin_id or default to new_admin_id
            log_performed_by = performed_by_admin_id if performed_by_admin_id is not None else new_admin_id
            
            log_admin_activity(
                action_type=action_type,
                performed_by_admin_id=log_performed_by,
                target_admin_id=new_admin_id,
                previous_admin_id=previous_admin_id,
                is_automatic=is_automatic
            )

        print(f"✅ Admin shift transferred to {new_admin_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to set current admin: {e}")
        return False


@bot.message_handler(commands=["eelj"])
def shift_control(message):
    if message.from_user.id not in ALLOWED_ADMINS:
        return

    current_admin_id = get_current_admin_id()

    try:
        if current_admin_id:
            current_admin_chat = bot.get_chat(current_admin_id)
            current_admin_name = current_admin_chat.first_name
            if current_admin_chat.last_name:
                current_admin_name += f" {current_admin_chat.last_name}"
            current_admin_display = f"[{current_admin_name}](tg://user?id={current_admin_id})"
        else:
            current_admin_display = "❌ Ээлж хаалттай байна"
    except Exception as e:
        print(f"❌ Couldn't fetch chat info: {e}")
        current_admin_display = "❓ Тодорхойгүй"

    # Inline buttons
    markup = InlineKeyboardMarkup()

    for admin_id in ALLOWED_ADMINS:
        if admin_id != current_admin_id:
            try:
                admin_chat = bot.get_chat(admin_id)
                name = admin_chat.first_name
                if admin_chat.last_name:
                    name += f" {admin_chat.last_name}"
            except:
                name = str(admin_id)
            markup.add(InlineKeyboardButton(f"➡️ Ээлж шилжүүлэх: {name}", callback_data=f"shift_to_{admin_id}"))

    if current_admin_id:
        markup.add(InlineKeyboardButton("🔒 Ээлж хаах", callback_data="shift_close"))
    else:
        markup.add(InlineKeyboardButton("✅ Ээлж нээх", callback_data=f"shift_to_{message.from_user.id}"))

    bot.send_message(
        message.chat.id,
        f"👤 Одоогийн ээлж хариуцагч: {current_admin_display}",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("shift_to_"))
def transfer_shift(call):
    if call.from_user.id not in ALLOWED_ADMINS:
        return bot.answer_callback_query(call.id, "🚫 Зөвшөөрөлгүй!", show_alert=True)

    new_admin_id = int(call.data.replace("shift_to_", ""))
    success = set_current_admin_id(new_admin_id, performed_by_admin_id=call.from_user.id, is_automatic=False)
    if success:
        bot.edit_message_text(
            f"✅ Ээлжийг амжилттай шилжүүллээ: [{new_admin_id}](tg://user?id={new_admin_id})",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ Алдаа гарлаа.")


@bot.callback_query_handler(func=lambda call: call.data == "shift_close")
def close_shift_callback(call):
    if call.from_user.id not in ALLOWED_ADMINS:
        return bot.answer_callback_query(call.id, "🚫 Зөвшөөрөлгүй!", show_alert=True)

    try:
        previous_admin_id = get_current_admin_id()
        supabase.table("admin_shifts").update({
            "current_admin_id": None,
            "last_updated": datetime.utcnow().isoformat()
        }).eq("id", 1).execute()
        
        log_admin_activity(
            action_type="closed",
            performed_by_admin_id=call.from_user.id,
            previous_admin_id=previous_admin_id,
            is_automatic=False
        )
        
        bot.edit_message_text(
            "🔒 Ээлж амжилттай хаагдлаа.",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception as e:
        print(f"❌ Failed to close shift: {e}")
        bot.answer_callback_query(call.id, "❌ Ээлж хаах үед алдаа гарлаа.")


def get_current_shift_operator_id():
    return get_current_admin_id() or ALWAYS_NOTIFY_OPERATOR_ID[0]  # Fallback


# ✅ Fetch Exchange Rates from Supabase
def fetch_exchange_rates():
    try:
        response = supabase.table("exchange_rates").select("student_buy, student_sell").order("id", desc=True).limit(1).execute()
        rates = response.data[0]  # Get latest exchange rate

        exchange_rates["BUY_RATE"] = float(rates["student_buy"])
        exchange_rates["SELL_RATE"] = float(rates["student_sell"])
        print(f"✅ Ханш амжилттай шинэчлэгдлээ: BUY_RATE = {exchange_rates['BUY_RATE']}, SELL_RATE = {exchange_rates['SELL_RATE']}")
    except Exception as e:
        print(f"❌ Failed to fetch exchange rates: {e}")

# ✅ Fetch the Latest Invoice Number from Supabase
def get_latest_invoice_number():
    try:
        response = supabase.table("transactions").select("invoice").order("timestamp", desc=True).limit(1).execute()
        if response.data:
            latest_invoice = response.data[0]["invoice"]
            match = re.search(r"_(\d+)$", latest_invoice)  # Extract the last number
            if match:
                return int(match.group(1))  # Return the extracted number
        return 0  # If no transactions exist, start from 0
    except Exception as e:
        print(f"❌ Failed to fetch latest invoice: {e}")
        return 0

#FETCH PROMO CODES
def get_promo_discount_from_db(user_input: str):
    user_input = user_input.lower().strip()

    try:
        response = supabase.table("promo_codes").select("code, aliases, discount").eq("active", True).execute()
        for promo in response.data:
            valid_keys = [promo["code"].lower()] + [alias.lower() for alias in promo.get("aliases") or []]
            if user_input in valid_keys:
                return float(promo["discount"])
    except Exception as e:
        print(f"❌ Failed to fetch promo codes: {e}")

    return 0.0


# ✅ Generate Unique Invoice ID With Random Digits
def generate_invoice():
    import random
    # Москвагийн цаг = UTC + 3
    moscow_time = datetime.utcnow() + timedelta(hours=3)
    # Новый формат: YYYYMMDD-HHMMSS-XX где XX - случайное число от 00 до 99
    random_suffix = random.randint(0, 99)
    invoice = moscow_time.strftime("%Y%m%d-%H%M%S") + f"-{random_suffix:02d}"  # Жишээ: 20250421-194532-42
    return invoice

# ✅ Функция для проверки формата инвойса (поддерживает оба формата)
def is_valid_invoice_format(invoice_id):
    """
    Проверяет, является ли строка валидным номером инвойса.
    Поддерживает оба формата:
    - Старый: YYYYMMDD_HHMMSS
    - Новый: YYYYMMDD-HHMMSS-XX
    """
    if not invoice_id:
        return False
    
    # Проверяем новый формат: YYYYMMDD-HHMMSS-XX
    if re.fullmatch(r"\d{8}-\d{6}-\d{2}", invoice_id):
        return True
    
    # Проверяем старый формат: YYYYMMDD_HHMMSS
    if re.fullmatch(r"\d{8}_\d{6}", invoice_id):
        return True
    
    return False

# ✅ Функция для нормализации формата инвойса
def normalize_invoice_format(invoice_id):
    """
    Конвертирует старый формат в новый, если необходимо.
    Старый: YYYYMMDD_HHMMSS -> YYYYMMDD-HHMMSS-00
    Новый: YYYYMMDD-HHMMSS-XX -> остается без изменений
    """
    if not invoice_id:
        return None
    
    # Если это старый формат, конвертируем в новый
    if re.fullmatch(r"\d{8}_\d{6}", invoice_id):
        return invoice_id.replace("_", "-") + "-00"
    
    # Если это новый формат, возвращаем как есть
    if re.fullmatch(r"\d{8}-\d{6}-\d{2}", invoice_id):
        return invoice_id
    
    return None

# ✅ Function to Record Transactions in Supabase
def record_transaction(user_id, invoice_id, amount, currency_from, currency_to, rate, bank_details, status="pending", promo_code=None):

    try:
        if not exchange_rates.get("BUY_RATE") or not exchange_rates.get("SELL_RATE"):
            fetch_exchange_rates()
    except Exception as _:
        pass  # fail-soft; will still insert without crashing

    current_buy = float(exchange_rates.get("BUY_RATE") or 0)
    current_sell = float(exchange_rates.get("SELL_RATE") or 0)
    
    data = {
        "user_id":        user_id,
        "invoice":        invoice_id,
        "amount":         amount,
        "currency_from":  currency_from,
        "currency_to":    currency_to,
        "rate":           rate,            # your FINAL applied rate (after promo/volume)
        "buy_rate":       current_buy,     # base RUB→MNT rate at the moment of logging
        "sell_rate":      current_sell,    # base MNT→RUB rate at the moment of logging
        "bank_details":   bank_details,
        "status":         status,
        "timestamp":      datetime.utcnow().isoformat()
    }
    
    # Add promo_code if provided
    if promo_code:
        data["promo_code"] = promo_code
    
    print("📦 Data to insert:", data)
    try:
        response = supabase.table("transactions").insert(data).execute()
        print("✅ Insert successful:", response)
        return response
    except Exception as e:
        print("❌ Supabase insert error:", e)
        raise

def get_user_transactions(user_id):
    response = supabase.table("transactions").select("*").eq("user_id", user_id).execute()
    return response.data

     # ✅ **Update Transaction Status in Supabase**
def update_transaction_status(user_id, status):
    try:
        # Find the user's latest transaction (matching user_id)
        invoice = pending_transactions[user_id]["invoice"]
        response = supabase.table("transactions").update({"status": status}).eq("invoice", invoice).execute()
        print(f"✅ Transaction `{invoice}` updated to `{status}` in Supabase")
    except Exception as e:
        print(f"❌ Failed to update transaction status: {e}")


# 🏠 Main Menu
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📊 Ханш", callback_data="exchange_rate"),
        InlineKeyboardButton("ℹ️ Бот ашиглах заавар", callback_data="how_to_use"),
        InlineKeyboardButton("💱 Валют солих", callback_data="exchange_menu"),
        InlineKeyboardButton("📱 Mini App", web_app=WebAppInfo(url=MINI_APP_URL)),
        InlineKeyboardButton("👤 Хэрэглэгчийн тохиргоо", callback_data="user_profile"),
        InlineKeyboardButton("✈️ Нислэг захиалга", callback_data="flight_booking"),
        InlineKeyboardButton("📝 Бүртгүүлэх", callback_data="start_registration")#,
        #InlineKeyboardButton("📞 Холбоо барих", callback_data="contact_support")
    )
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "contact_support")
def contact_support_handler(call):
    bot.send_message(
        call.message.chat.id,
        "📞 *Холбоо барих мэдээлэл:*\n\n"
        "📱 +976 7780 6060\n"
        "📱 +7 (977) 801-91-43\n"
        "🔗 Telegram: [@oyuns_support](https://t.me/oyuns_support)",
        parse_mode="Markdown"
    )
@bot.callback_query_handler(func=lambda call: call.data == "restart_registration")
def restart_registration(call):
    user_id = call.message.chat.id
    bot.send_message(user_id, "🔁 Бүртгэлийг шинээр эхлүүлж байна...")
    update_user_session(user_id, {"state": "register_last_name"})
    bot.send_message(user_id, "👤 Та өөрийн овгоо оруулна уу:", reply_markup=cancel_markup())

    

# ✅ Start Command

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id

    # ⛑ Ensure user row exists
    response = supabase.table("users").select("id").eq("id", user_id).execute()
    if not response.data:
        supabase.table("users").insert({"id": user_id}).execute()

    # 🧾 Now check if they’ve agreed
    if not has_agreed_terms(user_id):
        ask_terms_agreement(user_id)
        return
    update_user_session(user_id, {"state": ""})
    bot.send_message(
        message.chat.id,
        "👋 Сайн байна уу? OYUNS All-In-One-д тавтай морил!\nТа дараах үйлчилгээнүүдээс сонгон үйлчлүүлнэ үү:",

        reply_markup=main_menu()
    )


#----------------------NISLEG-----------------------------
FLIGHT_BOOKING_TG = "OYUNS_AIO"
@bot.callback_query_handler(func=lambda call: call.data == "flight_booking")
def flight_booking_info(call):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📨 OYUNS ALL-IN-ONE", url=f"https://t.me/{FLIGHT_BOOKING_TG}"))
    kb.add(InlineKeyboardButton("🔙 Буцах", callback_data="back_main"))

    bot.send_message(
        call.message.chat.id,
        "✈️ *OYUNS онгоцны тийз захиалга*\n\n"
        "Та нислэгийн тийз захиалахын тулд хэзээ, ямар чиглэлд нисэх тухай ерөнхий мэдээллээ дараах чатаар явуулж захиалаарай:\n\n"
        f"📨 [@{FLIGHT_BOOKING_TG}](https://t.me/{FLIGHT_BOOKING_TG})",
        parse_mode="Markdown",
        reply_markup=kb,
        disable_web_page_preview=True
    )




# 📊 Exchange Rate Button Handler (with Calculator)
@bot.callback_query_handler(func=lambda call: call.data == "exchange_rate")
def exchange_rate(call):
    fetch_exchange_rates()  # Refresh rates before displaying
    DATETODAY = date.today().isoformat()
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Ханш тооцоолуур", callback_data="open_calculator"),
        InlineKeyboardButton("🔙 Буцах", callback_data="back_main")
    )
    bot.send_message(
        call.message.chat.id,
        f"💱 *Өнөөдрийн ханш* ({DATETODAY}):\n\n"
        f"🔸 АВАХ ХАНШ = `{exchange_rates['BUY_RATE']}` MNT\n"
        f"🔹 ЗАРАХ ХАНШ = `{exchange_rates['SELL_RATE']}` MNT",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "open_calculator")
def start_calculator(call):
    update_user_session(call.from_user.id, {"state": "calc_direction"})
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🇷🇺 RUB ➝ MNT", callback_data="calc_rub_mnt"),
        InlineKeyboardButton("🇲🇳 MNT ➝ RUB", callback_data="calc_mnt_rub"),
        InlineKeyboardButton("🔙 Буцах", callback_data="back_main")
    )
    bot.send_message(call.message.chat.id, "🖩 Аль чиглэлээр ханш тооцоолох вэ?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("calc_"))
def ask_amount(call):
    direction = call.data
    user_id = call.from_user.id

    if direction == "calc_rub_mnt":
        update_user_session(user_id, {"state": "calc_rub_mnt_amount"})
        bot.send_message(user_id, "💵 Тооцоолох *RUB* мөнгөн дүнгээ оруулна уу?", parse_mode="Markdown")
    elif direction == "calc_mnt_rub":
        update_user_session(user_id, {"state": "calc_mnt_rub_amount"})
        bot.send_message(user_id, "💵 Тооцоолох *MNT* мөнгөн дүнгээ оруулна уу?", parse_mode="Markdown")

@bot.message_handler(func=lambda m: get_state(m.chat.id) in ["calc_rub_mnt_amount", "calc_mnt_rub_amount"])
def perform_calculation(message):
    fetch_exchange_rates()
    user_id = message.chat.id
    session = get_user_session(user_id)
    state = session["state"] if session else None
    raw     = message.text.replace(",", "").strip()
    try:
        amount = float(raw)
    except ValueError:
        bot.send_message(
            user_id,
            "❌ Зөвхөн тоон утга оруулна уу (жишээ: 50 000 эсвэл 50,000).",
            parse_mode="Markdown"
        )
        # leave them in the same state so they can retry
        return
    # 2) Do the conversion
    if state == "calc_rub_mnt_amount":
        rate      = exchange_rates["BUY_RATE"]
        converted = round(amount * rate, 2)
        bot.send_message(
            user_id,
            f"📌 {amount} RUB ≈ `{converted} MNT`\n💱 Ханш: {rate}",
            parse_mode="Markdown"
        )

    else:  # calc_mnt_rub_amount
        rate      = exchange_rates["SELL_RATE"]
        converted = round(amount / rate, 2)
        bot.send_message(
            user_id,
            f"📌 {amount} MNT ≈ `{converted} RUB`\n💱 Ханш: {rate}",
            parse_mode="Markdown"
        )

    # 3) Only now clear the state so they don’t get stuck
    clear_state(user_id)


# --------------------------------HEREGLEGCHIIN TOHIRGOO-----------------------
@bot.callback_query_handler(func=lambda call: call.data == "user_profile")
def profile_menu(call):
    user_id = call.message.chat.id
    response = supabase.table("users").select("*").eq("id", user_id).execute()

    if not response.data:
        bot.send_message(user_id, "❗ Та эхлээд /register команд ашиглан бүртгүүлнэ үү.")
        return

    user = response.data[0]
    is_verified = user.get("verified", False)

    # 📋 User Summary Text
    text = (
        f"👤 Таны мэдээлэл:\n\n"
        f"👤 Овог: {user.get('last_name', '-')}\n"
        f"👤 Нэр: {user.get('first_name', '-')}\n"
        f"📞 Утас: {user.get('phone', '-')}\n"
        f"🪪 Паспортын дугаар: {user.get('registration_number', '-')}\n"
        f"🏦 Монгол банк: {user.get('bank_mnt', '-')}\n"
        f"🇷🇺 Орос банк: {user.get('bank_rub', '-')}\n"
        f"📷 Паспорт зураг: {'🟢 Байгаа' if user.get('passport_file_id') else '🔴 Байхгүй'}\n"
        f"\n📤 Баталгаажуулах хүсэлт: {'Илгээсэн' if user.get('ready_for_verification') else 'Илгээгүй'}\n"
        f"📎 Баталгаажсан: {'✅ Тийм' if is_verified else '❌ Үгүй'}"
    )

    # 📌 Markup (Edit / Continue Registration)
    markup = InlineKeyboardMarkup()

    # Disable editing of reg/passport if verified (optional)
    markup.add(
        InlineKeyboardButton("👤 Овог өөрчлөх", callback_data="edit_last_name"),
        InlineKeyboardButton("👤 Нэр өөрчлөх", callback_data="edit_first_name"),
        InlineKeyboardButton("📞 Утас өөрчлөх", callback_data="edit_phone")
    )

    if not is_verified:
        markup.add(
            InlineKeyboardButton("🪪 Паспортын дугаар", callback_data="edit_registration_number"),
            InlineKeyboardButton("📷 Паспорт зураг", callback_data="upload_passport")
        )

    markup.add(
        InlineKeyboardButton("🇲🇳 Монгол банк", callback_data="edit_bank_mnt"),
        InlineKeyboardButton("🇷🇺 Орос банк", callback_data="edit_bank_rub"),
        InlineKeyboardButton("📤 Баталгаажуулах хүсэлт илгээх", callback_data="submit_verification"),
        InlineKeyboardButton("📜 Гүйлгээний түүх", callback_data="txn_history_1"),
        InlineKeyboardButton("🔙 Буцах", callback_data="back_main")
    )

    bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("txn_history_"))
def txn_history_page(call):
    user_id = call.message.chat.id

    # page number from callback_data like txn_history_1
    try:
        page = int(call.data.split("_")[2])
    except Exception:
        page = 1
    page = max(1, page)

    offset = (page - 1) * PAGE_SIZE

    # Pull PAGE_SIZE + 1 rows to detect "has_next"
    fields = "invoice,amount,currency_from,currency_to,rate,status,timestamp,bill_url"
    resp = supabase.table("transactions") \
        .select(fields) \
        .eq("user_id", user_id) \
        .order("timestamp", desc=True) \
        .range(offset, offset + PAGE_SIZE) \
        .execute()

    rows = resp.data or []
    has_next = len(rows) > PAGE_SIZE
    if has_next:
        rows = rows[:PAGE_SIZE]

    if not rows and page == 1:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 Буцах", callback_data="user_profile"))
        return bot.edit_message_text(
            "📭 Таны гүйлгээний түүх хоосон байна.",
            call.message.chat.id, call.message.message_id,
            reply_markup=kb
        )

    # Build page text
    status_icon = {"pending": "🕒", "successful": "✅", "rejected": "❌"}
    lines = ["📜 *Гүйлгээний түүх*"]
    for tx in rows:
        conv, tocur = compute_converted(tx)
        icon = status_icon.get((tx.get("status") or "").lower(), "❔")
        ts   = format_ub(tx.get("timestamp") or "")
        inv  = tx.get("invoice")
        amt  = float(tx["amount"])
        cf   = tx["currency_from"].upper()
        rate = float(tx["rate"])
        line = (
            f"{icon} `{inv}` • {ts}\n"
            f"   {amt:,.2f} {cf} → {conv:,.2f} {tocur} @ {rate}₮\n"
        )
        if tx.get("bill_url"):
            line += f"   [Баримт]({tx['bill_url']})\n"
        lines.append(line)

    text = "\n".join(lines)

    # Navigation
    kb = InlineKeyboardMarkup()
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Өмнөх", callback_data=f"txn_history_{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("Дараах ➡️", callback_data=f"txn_history_{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("🔙 Буцах", callback_data="user_profile"))

    bot.edit_message_text(
        text,
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=kb,
        disable_web_page_preview=True
    )



@bot.callback_query_handler(func=lambda call: call.data == "upload_passport")
def handle_upload_passport(call):
    user_id = call.message.chat.id

    # 🛡️ Block verified users
    response = supabase.table("users").select("verified").eq("id", user_id).execute()
    if response.data and response.data[0].get("verified"):
        bot.send_message(user_id, f"⚠️ Баталгаажсан хэрэглэгч паспортын зургаа өөрчлөх боломжгүй.\n ✉️ Админтай холбогдоно уу: {CONTACT_SUPPORT}")
        return

    update_user_session(user_id, {"state": "waiting_for_passport"})
    bot.send_message(user_id, "📸 Паспортын зургаа илгээнэ үү:")

def schedule_morning_alert(user_id):
    if user_id not in pending_morning_alerts:
        pending_morning_alerts.append(user_id)
        print(f"🕓 Queued alert for user {user_id} in the morning.")




def send_verification_alert_to_operator(user_id, user):
    # who’s on shift right now?
    primary = get_current_shift_operator_id()
    # build a set of everyone to notify
    to_notify = {primary} if primary else set()
    to_notify.update(ALWAYS_NOTIFY_OPERATOR_ID)
    try:
        passport_file_id = user.get("passport_file_id")

        caption = (
            f"🆕 Шинэ баталгаажуулах хүсэлт ирлээ!\n\n"
            f"👤 Хэрэглэгч: [{user_id}](tg://user?id={user_id})\n"
            f"👤 Нэр: {user.get('last_name')} {user.get('first_name')}\n"
            f"📞 Утас: {user.get('phone')}\n"
            f"🪪 Паспортын дугаар: {user.get('registration_number')}\n"
            f"🏦 Монгол банк: {user.get('bank_mnt')}\n"
            f"🇷🇺 Орос банк: {user.get('bank_rub')}"
        )

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"verify_{user_id}"),
            InlineKeyboardButton("❌ Цуцлах", callback_data=f"rejectuser_{user_id}")
        )
        # send each person in the set
        for op_id in to_notify:
            try:
                if passport_file_id:
                    bot.send_photo(
                        op_id,
                        passport_file_id,
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
                else:
                    bot.send_message(
                        op_id,
                        caption + "\n⚠️ Паспорт зураг оруулаагүй байна!",
                        parse_mode="Markdown",
                        reply_markup=markup
                    )
            except Exception as e:
                print(f"❌ Failed to notify operator {op_id}: {e}")
        if passport_file_id:
            bot.send_photo(operator_id, passport_file_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(operator_id, caption + "\n⚠️ Паспорт зураг оруулаагүй байна!", parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        print(f"❌ Failed to send verification alert: {e}")


@bot.callback_query_handler(func=lambda call: call.data == "start_registration")
def start_registration_from_menu(call):
    call.message.text = "/register"  # fake the message to reuse the handler
    register(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "submit_verification")
def submit_verification(call):
    user_id = call.message.chat.id

    # ✅ Fetch user info
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    user = response.data[0] if response.data else None

    if not user:
        bot.send_message(user_id, "❌ Таны бүртгэлийн мэдээлэл олдсонгүй. Та эхлээд бүртгүүлнэ үү.")
        return

    required_fields = [
        'first_name', 'last_name', 'phone',
        'bank_mnt', 'passport_file_id',
        'registration_number'
    ]

    missing = [f for f in required_fields if not str(user.get(f)).strip()]
    if missing:
        bot.send_message(user_id, (
            "⚠️ Та мэдээллээ бүрэн оруулаагүй байна.\n\n"
            "Дараах мэдээлэл дутуу байж болзошгүй:\n" +
            "\n".join([f"• {field}" for field in missing]) +
            "\n\n📌 'Хэрэглэгчийн тохиргоо' хэсгээс мэдээллээ бүрэн бөглөнө үү."
        ))
        return

    # ✅ Update status in DB
    supabase.table("users").update({
        "ready_for_verification": True
    }).eq("id", user_id).execute()

    bot.send_message(user_id, "✅ Таны мэдээлэл амжилттай илгээгдлээ. Админ баталгаажуулахыг хүлээнэ үү.")

    # 🔔 Alert the operator (or schedule it)
    send_verification_alert_to_operator(user_id, user)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_profile_field(call):
    user_id = call.message.chat.id
    field = call.data.replace("edit_", "")

    # 🛡️ Check if verified
    response = supabase.table("users").select("verified").eq("id", user_id).execute()
    user = response.data[0] if response.data else {}

    is_verified = user.get("verified", False)

    # 👮‍♂️ Lock certain fields if verified
    if is_verified and field in ["passport", "registration_number"]:
        bot.send_message(user_id, f"⚠️ Энэ мэдээллийг баталгаажсан хэрэглэгч дахин өөрчлөх боломжгүй.\n✉️ Өөрчлөхийг хүсвэл админтай холбогдоно уу: {CONTACT_SUPPORT}")
        return

    update_user_session(user_id, {"state": f"editing_{field}"})

    field_names = {
        "first_name": "📝 Та өөрийн нэрээ оруулна уу:",
        "last_name": "📝 Та өөрийн овгоо оруулна уу:",
        "phone": "📞 Утасны дугаараа оруулна уу:",
        "registration_number": "🪪 Та өөрийн паспортын дугаарыг оруулна уу (жишээ нь: E1234560):",
        "bank_mnt": "🏦 Монгол дахь банкны мэдээлэл (Банк, Дансны IBAN дугаар, Данс зэмшэгчийн нэр):",
        "bank_rub": "🏦 ОХУ дахь банкны мэдээлэл (Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр):"
    }

    bot.send_message(user_id, field_names.get(field, "📝 Мэдээлэл оруулна уу:"))
@bot.message_handler(func=lambda m: isinstance(get_state(m.chat.id), str) and get_state(m.chat.id).startswith("editing_"))

def save_profile_update(message):
    user_id = message.chat.id
    session = get_user_session(user_id)
    state = session.get("state", "")
    field = state.replace("editing_", "")
    value = message.text.strip()

    # Format validation for banking info
    if field == "bank_mnt":
        parts = [x.strip() for x in value.split(",")]
        if len(parts) != 3:
            bot.send_message(user_id,
                "❌ Та дараах форматаар монгол дансны мэдээллээ оруулна уу:\n"
                "`Банк, Дансны IBAN дугаар, Данс зэмшэгчийн нэр`", parse_mode="Markdown")
            return

    elif field == "registration_number":
      if not re.match(r'^[A-Za-z0-9]+$', text):
        bot.send_message(user_id, "❌ Паспортын дугаар буруу байна. Жишээ: `E2853960`", parse_mode="Markdown")
        return

    elif field == "bank_rub":
        parts = [x.strip() for x in value.split(",")]
        if len(parts) != 4:
            bot.send_message(user_id,
                "❌ Та дараах форматаар орос дансны мэдээллээ оруулна уу:\n"
                "`Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр`", parse_mode="Markdown")
            return

    try:
        # Update Supabase
        supabase.table("users").upsert({
            "id": user_id,
            field: value,
            "updated_at": datetime.now().isoformat()
        }).execute()

        bot.send_message(user_id, f"✅ Таны *{field.replace('_', ' ')}* шинэчлэгдлээ.", parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        bot.send_message(user_id, "❌ Error updating your profile. Please try again later.")

    clear_state(user_id)

@bot.message_handler(func=lambda m: get_state(m.chat.id) == "awaiting_bank")
def get_bank(message):
    user_profiles[message.chat.id]["bank"] = message.text
    update_user_session(message.chat.id, {"state": "waiting_for_bank"})
    bot.send_message(message.chat.id, "🪪 Паспортын зургаа илгээнэ үү:")


# ℹ️ How to Use Button Handler
@bot.callback_query_handler(func=lambda call: call.data == "how_to_use")
def how_to_use(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Буцах", callback_data="back_main"))

    bot.send_message(
        call.message.chat.id, "Та энэхүү ботын тусламжтай ханшийн өдөр тутмын мэдээлэл авах, рубль болон төгрөгийн ханш хөрвүүлэн солиулах боломжтой\n\n"
                              "📖 Бот ашиглах заавар:\n\n"
                              "1️⃣ Хэрэглэгчийн бүртгэл үүсгэх. Та */register* команд ашиглан хэрэглэгчийн бүртгэл үүсгэх боломжтой.\n\n"
                              "2️⃣ Хэрэглэгчийн бүртгэл баталгаажуулах. Та хэрэглэгчийн бүртгэл үүсгэх явцад бүртгэлээ баталгаажуулах товч дарах эсвэл хэрэглэгчийн тохиргоо цэст буй бүртгэл баталгаажуулах товч дарснаар бүртгэлээ баталгаажуулах хүсэлт илгээх боломжтой.\n\n"
                              "3️⃣ Админ таны мэдээллийг тодорхой хугацааны дараа бүрэн зөв эсэхийг шалгаад баталгаажуулна. Админ баталгаажуулсан тохиолдолд танд мэдэгдэл ирнэ.\n\n"
                              "4️⃣ Ийнхүү та хэрэглэгчийн бүртгэлээ баталгаажуулсан бол ханш солих боломжтой болно. Ингэхдээ */start* команд ашиглан 💱 *Валют солих* товч дээр дарна.\n\n"
                              "5️⃣ Ханш солих чиглэлээ сонгоно.\n\n"
                              "6️⃣ Та ямар дүнгээр солиулахаа сонгох эсвэл өөрийн хүссэн дүнгээ оруулна.\n\n"
                              "7️⃣ Солих дүнгээ оруулсаны дараа ханш хөрвүүлсэн байдлаар харагдах бөгөөд танд илгээсэн дансны мэдээллийн дагуу гүйлгээ хийнэ. Гүйлгээ хийсний дараа гүйлгээний баримтыг зурган хэлбэрээр бот руу илгээнэ.\n\n"
                              "8️⃣ Oyuns AIO бот зураг хүлээж авсаны дараа та өөрийн дансны мэдээллийг бот руу илгээснээр админ таны гүйлгээний хүсэлтийг баталгаажуулах боломжтой болно.\n\n"
                              "9️⃣ Админ таны хүсэлтийг хүлээн авч хэсэг хугацааны дараа таны гүйлгээг баталгаажуулна. Баталгаажсанаас хэсэг хугацааны дараа админ таны хүсэлтийн дагуу гүйлгээ хйиж гүйлгээний баримтыг танд ботоор дамжуулан илгээх болно\n\n"
                              "*Баяр хүргэе!* Та ийнхүү амжилттай ханшаа солиуллаа!\n\n\n"
                              "📞 *Холбоо барих:*\n"
                              "+976 7780 6060\n"
                              "+7 (977) 801-91-43\n"
                              "[Telegram: @oyuns_support](https://t.me/oyuns_support)",
                              parse_mode="Markdown",
                              reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "exchange_menu")
def exchange_menu(call):
    user_id = call.message.chat.id
    update_user_session(user_id, {"state": ""})
    # Check if user exists and verified
    response = supabase.table("users").select("verified").eq("id", user_id).execute()
    user = response.data[0] if response.data else None

    if not user or not user.get("verified"):
        bot.send_message(user_id, "⚠️ Та бүртгэлээ баталгаажуулсны дараа валют солих боломжтой.\n📌 Та эхлээд /start товч даран бүртгүүлэх функц сонгох эсвэл /register команд ашиглан бүртгүүлнэ үү.")
        return
    config = get_current_shift_config()

    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🇲🇳 МНТ → РУБ", callback_data="SELL_RATE"),
        InlineKeyboardButton("🇷🇺 РУБ → МНТ", callback_data="BUY_RATE"),
        InlineKeyboardButton("🔙 Буцах", callback_data="back_main")
    )
    bot.send_message(call.message.chat.id, "💱 Та валют солих чиглэлээ сонгоно уу:", reply_markup=markup)




def show_common_rub_amounts(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("1,000 РУБ", callback_data="amount_rub_1000"),
        InlineKeyboardButton("5,000 РУБ", callback_data="amount_rub_5000"),
        InlineKeyboardButton("10,000 РУБ", callback_data="amount_rub_10000"),
        InlineKeyboardButton("20,000 РУБ", callback_data="amount_rub_20000"),
        InlineKeyboardButton("30,000 РУБ", callback_data="amount_rub_30000"),
        InlineKeyboardButton("✏️ Хүссэн дүнгээ бичих", callback_data="custom_rub"),
        InlineKeyboardButton("🔙 Буцах", callback_data="exchange_menu")
    )
    bot.send_message(user_id, "💰 Та хэдэн РУБ солиулах вэ:", reply_markup=markup)


def show_common_mnt_amounts(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("100,000 MNT", callback_data="amount_mnt_100000"),
        InlineKeyboardButton("250,000 MNT", callback_data="amount_mnt_250000"),
        InlineKeyboardButton("500,000 MNT", callback_data="amount_mnt_500000"),
        InlineKeyboardButton("1,000,000 MNT", callback_data="amount_mnt_1000000"),
        InlineKeyboardButton("3,000,000 MNT", callback_data="amount_mnt_3000000"),
        InlineKeyboardButton("✏️ Хүссэн дүнгээ бичих", callback_data="custom_mnt"),
        InlineKeyboardButton("🔙 Буцах", callback_data="exchange_menu")
    )
    bot.send_message(user_id, "💰 Та хэдэн МНТ солиулах вэ:", reply_markup=markup)



def auto_update_rates():
    while True:
        fetch_exchange_rates()
        time.sleep(1800)  # Update every 30 minutes

rate_update_thread = threading.Thread(target=auto_update_rates)
rate_update_thread.daemon = True
rate_update_thread.start()

# 🇷🇺 RUB → MNT Exchange: Show Common Amounts
@bot.callback_query_handler(func=lambda call: call.data == "BUY_RATE")
def BUY_RATE(call):
    user_id = call.message.chat.id

    # Save the direction
    update_user_session(user_id, {"state": "promo_choice_buy"})

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎟️ Промокод оруулах", callback_data="promo_enter_buy"),
        InlineKeyboardButton("❌ Промокод байхгүй, цааш үргэлжлүүлэх", callback_data="promo_skip_buy"),
        InlineKeyboardButton("🔙 Буцах", callback_data="exchange_menu")
    )
    bot.send_message(user_id, "🎁 Та промокодтой бол промокодоо ашиглах боломжтой", reply_markup=markup)


# 🇲🇳 MNT → RUB Exchange: Show Common Amounts
@bot.callback_query_handler(func=lambda call: call.data == "SELL_RATE")
def SELL_RATE(call):
    user_id = call.message.chat.id

    # Save the direction
    update_user_session(user_id, {"state": "promo_choice_sell"})

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎟️ Промокод оруулах", callback_data="promo_enter_sell"),
        InlineKeyboardButton("❌ Промокод байхгүй, цааш үргэлжлүүлэх", callback_data="promo_skip_sell"),
        InlineKeyboardButton("🔙 Буцах", callback_data="exchange_menu")
    )
    bot.send_message(user_id, "🎁 Та промокодтой бол промокодоо ашиглах боломжтой", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("promo_enter_"))
def promo_code_request(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    direction = call.data.replace("promo_enter_", "")
    update_user_session(call.message.chat.id, {"state": f"awaiting_promo_code_{direction}"})
    bot.send_message(call.message.chat.id, "🎟️ Та промокодоо оруулна уу:")

@bot.message_handler(func=lambda m: get_state(m.chat.id).startswith("awaiting_promo_code_"))
def promo_code_input_handler(message):
    user_id = message.chat.id
    if not ensure_exchange_available(message.chat.id):
        return
    session = get_user_session(user_id)
    state = session.get("state", "")
    direction = state.split("_")[-1]
    promo_code = message.text.strip()

    discount = get_promo_discount_from_db(promo_code)

    if discount <= 0:
        bot.send_message(user_id, "❌ Буруу промокод байна. Дахин оролдоно уу.")
        return

    # Save discount and promo code in session
    update_user_session(user_id, {
        "promo_discount": discount,
        "promo_code": promo_code
    })


    clear_state(user_id)
    bot.send_message(user_id, f"✅ Промокод амжилттай! Хөнгөлөлт: {discount} MNT")

    if direction == "buy":
        show_common_rub_amounts(user_id)
    else:
        show_common_mnt_amounts(user_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("promo_skip_"))
def promo_skip_handler(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    direction = call.data.replace("promo_skip_", "")


    update_user_session(user_id, {
        "promo_discount": 0.0,
        "promo_code": None
    })

    if direction == "buy":
        show_common_rub_amounts(user_id)
    else:
        show_common_mnt_amounts(user_id)


# 💰 Handle Common Amount Selection
@bot.callback_query_handler(func=lambda call: call.data.startswith("amount_"))
def selected_common_amount(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    currency, amount = call.data.split("_")[1], int(call.data.split("_")[2])
    invoice = generate_invoice()
    # Get base rate and promo discount
    base_rate = exchange_rates["BUY_RATE"] if currency == "rub" else exchange_rates["SELL_RATE"]
    session = get_user_session(user_id)
    promo     = session.get("promo_discount", 0.0)

    # compute volume discount
    vol_disc = 0.0
    if currency == "rub":
        if amount >= MIN_VOLUME_RUB_2:
            vol_disc = VOLUME_DISCOUNT_MNT_2
        elif amount >= MIN_VOLUME_RUB:
            vol_disc = VOLUME_DISCOUNT_MNT
    elif currency == "mnt":
        rub_equiv = amount / base_rate
        if rub_equiv >= MIN_VOLUME_RUB_2:
            vol_disc = VOLUME_DISCOUNT_MNT_2
        elif rub_equiv >= MIN_VOLUME_RUB:
            vol_disc = VOLUME_DISCOUNT_MNT
    # pick the higher discount
    best_disc = max(promo, vol_disc)

    # apply it
    if currency == "rub":
        final_rate = base_rate + best_disc
    else:  # mnt -> rub
        final_rate = base_rate - best_disc

    final_rate = round(max(final_rate, 0.01), 2)

    # enforce 1 000 RUB-min on MNT→RUB
    if currency == "mnt":
        # final_rate is MNT per 1 RUB, so to get MIN_RUB you need MIN_RUB * final_rate MNT
        min_mnt = ceil(MIN_RUB * final_rate)
        if amount < min_mnt:
            return bot.send_message(
                user_id,
                f"❌ Та солих доод хэмжээ буюу {MIN_RUB:,} RUB-тэй тэнцүү ({min_mnt:,} MNT) солих ёстой.\n"
                f"Та дор хаяж *{min_mnt:,} MNT* солиулна уу.",
                parse_mode="Markdown"
            )

    # save to db
    update_user_session(user_id, {
        "amount":        amount,
        "currency_from": currency,
        "currency_to":   "mnt" if currency=="rub" else "rub",
        "invoice":       invoice,
        "rate":          final_rate,
        "state":         "waiting_for_receipt"
    })

    if currency == "rub":
        # Show RUB bank options
        markup = InlineKeyboardMarkup()
        rub_bank_options = get_current_shift_config().get("rub_bank_options", {})
        for bank in rub_bank_options:
            markup.add(InlineKeyboardButton(bank, callback_data=f"rubmnt_bank_{bank}"))

        bot.send_message(
            user_id,
            "💳 Та аль банкаар РУБ-ээ илгээх вэ?\n"
            "⬇️ Дараах боломжит банкнуудаас сонгон гүйлгээ хийх банкны мэдээллээ авна уу:",
            reply_markup=markup
        )
    else:
        # MNT → RUB flow
        exchanged = amount / final_rate
        message_text = f"💱 {amount:,} MNT → {round(exchanged, 2):,} RUB"

        bot.send_message(
            user_id,
            f"*{message_text}*\n\n"
            "📸Та дараах дансаар гүйлгээ хийсний дараа шилжүүлэг хийсэн баримтаа *зургаар* оруулна уу.\n\n"
            f"{BANK_DETAILS_MNT}\n\n"
            f"💰 Гүйлгээний дүн: *{amount:,} МНТ*\n"
            f"🧾 Гүйлгээний утга: `{invoice}`",
            parse_mode="Markdown"
        )



# ✏️ Handle Custom Amount Entry
@bot.callback_query_handler(func=lambda call: call.data.startswith("custom_"))
def custom_amount(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    currency = call.data.split("_")[1]
    update_user_session(call.message.chat.id, {"state": f"custom_amount_{currency}"})

    bot.send_message(call.message.chat.id, "💰 Та солиулах дүнгээ оруулна уу:")

# 🏦 Receive Custom Amount
@bot.message_handler(func=lambda message: isinstance(get_state(message.chat.id), str) and get_state(message.chat.id).startswith("custom_amount_"))
def receive_custom_amount(message):
    user_id = message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return    
    session = get_user_session(user_id)
    state = session.get("state", "")
    currency = state.split("_")[2] if state else None
    invoice = generate_invoice()
    raw = re.sub(r"\D", "", message.text)
    if not raw.isdigit():
        bot.send_message(
            user_id,
            "❌ Зөвхөн тоон утга оруулна уу (жишээ: 50000).",
            parse_mode="Markdown"
        )
        # Make sure they stay in the same state
        update_user_session(user_id, {"state": state})
        return

    try:
        amount = int(raw)
        if amount <= 0:
            raise ValueError
        # 1) Pick the right base rate
        if currency == "rub":
            base_rate = exchange_rates["BUY_RATE"]    # MNT per RUB
        else:
            base_rate = exchange_rates["SELL_RATE"]   # RUB per MNT

        # 2) Compute volume discount
        vol_disc = 0.0
        if currency == "rub":
            if amount >= MIN_VOLUME_RUB_2:
                vol_disc = VOLUME_DISCOUNT_MNT_2
            elif amount >= MIN_VOLUME_RUB:
                vol_disc = VOLUME_DISCOUNT_MNT
        elif currency == "mnt":
            rub_equiv = amount / base_rate
            if rub_equiv >= MIN_VOLUME_RUB_2:
                vol_disc = VOLUME_DISCOUNT_MNT_2
            elif rub_equiv >= MIN_VOLUME_RUB:
                vol_disc = VOLUME_DISCOUNT_MNT

        # 3) Grab any promo code discount
        promo_disc = session.get("promo_discount", 0.0)

        # 4) Apply only the higher of the two
        best_disc = max(promo_disc, vol_disc)

        # 5) Compute final rate
        if currency == "rub":
            final_rate = base_rate + best_disc
        else:
            final_rate = base_rate - best_disc
        final_rate = round(max(final_rate, 0.01), 2)


        currency_from = currency
        currency_to = "mnt" if currency == "rub" else "rub"

        if currency=="mnt":
            min_mnt = ceil(MIN_RUB * final_rate)
            if amount < min_mnt:
                return bot.send_message(
                    user_id,
                    f"❌ Та солих доод хэмжээ буюу {MIN_RUB:,} RUB-тэй тэнцүү ({min_mnt:,} MNT) солих ёстой.\n"
                    f"Та дор хаяж *{min_mnt:,} MNT* солиулна уу.",
                    parse_mode="Markdown"
                )

        # Save session
        update_user_session(user_id, {
            "state": "waiting_for_receipt",
            "amount": amount,
            "currency_from": currency_from,
            "currency_to": currency_to,
            "rate": final_rate,
            "invoice": invoice,
            "promo_discount": best_disc,
        })


        # Respond to user
        if currency == "rub":
            exchanged = amount * final_rate
            message_text = f"💱 {amount:,} RUB → {int(exchanged):,} MNT"

            markup = InlineKeyboardMarkup()
            rub_bank_options = get_current_shift_config().get("rub_bank_options", {})
            for bank_key in rub_bank_options:
                markup.add(InlineKeyboardButton(bank_key, callback_data=f"rubmnt_bank_{bank_key}"))

            bot.send_message(
                user_id,
                f"*{message_text}*\n\n"
                "🏦 Та RUB илгээх банкаа сонгоно уу:",
                parse_mode="Markdown",
                reply_markup=markup
            )
        else:
            exchanged = amount / final_rate
            message_text = f"💱 {amount:,} MNT → {round(exchanged, 2):,} RUB"

            bot.send_message(
                user_id,
                f"*{message_text}*\n\n"
                "📸 Та дараах дансаар гүйлгээ хийсний дараа шилжүүлэг хийсэн баримтаа *зургаар* оруулна уу.\n\n"
                f"{BANK_DETAILS_MNT}\n\n"
                f"💰 Гүйлгээний дүн: *{amount:,} МНТ*\n"
                f"🧾 Гүйлгээний утга: `{invoice}`",
                parse_mode="Markdown"
            )
    except ValueError:
        # This will catch both non-positive numbers (raised above)
        # and any int(…) failures (though digits-only check handles most)
        bot.send_message(user_id, "❌ Зөвхөн тоон утга оруулна уу.")
        update_user_session(user_id, {"state": state})
        return



@bot.callback_query_handler(func=lambda call: call.data.startswith("rubmnt_bank_"))
def handle_rub_mnt_bank_selection(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    selected_bank = call.data.replace("rubmnt_bank_", "")

    # Store selected bank in session
    update_user_session(user_id, {
        "selected_rub_bank": selected_bank,
    })

    rub_bank_options = get_current_shift_config().get("rub_bank_options", {})
    bank_details = rub_bank_options.get(selected_bank, "❌ Банк олдсонгүй.")
    if bank_details.startswith("❌"):
        bot.send_message(user_id, bank_details)
        return

    session = get_user_session(user_id)
    if not session:
        bot.send_message(user_id, "⚠️ Гүйлгээний мэдээлэл олдсонгүй. Та эхнээс эхлэнэ үү.")
        return
    amount = session.get("amount")
    invoice = session.get("invoice")
    final_rate = session.get("rate")

    exchanged = amount * final_rate
    message_text = f"💱 {amount:,} RUB → {int(exchanged):,} MNT"

    bot.send_message(
        user_id,
        f"*{message_text}*\n\n"
        "📸Та дараах дансаар гүйлгээ хийсний дараа шилжүүлэг хийсэн баримтаа *зургаар* оруулна уу.\n\n"
        f"{bank_details}\n\n"
        f"💰 Гүйлгээний дүн: *{amount:,} РУБ*\n"
        f"🧾 Гүйлгээний утга: `{invoice}`",
        parse_mode="Markdown"
    )

    # ✅ Switch to receipt upload step
    update_user_session(user_id, {"state": "waiting_for_receipt"})


# 💾 Хадгалсан дансны мэдээллээ ашиглах
@bot.callback_query_handler(func=lambda call: call.data == "use_saved_bank")
def use_saved_bank(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    update_user_session(user_id, {"state": "waiting_for_receipt"})
    if get_state(user_id) == "waiting_for_bank":
        bot.send_message(user_id, "❗ Та одоогоор дансны мэдээлэл оруулах горимд байхгүй байна. Та ижил мөнгөн дүнгээр дахин ханш солиулах хүсэлт үүсгээд гүйлгээ хийсэн баримтаа дахин илгээгээрэй.")
        return

    try:
        response = supabase.table("users").select("bank_mnt, bank_rub").eq("id", user_id).execute()
        user = response.data[0] if response.data else None

        if not user:
            bot.send_message(user_id, "❗ Таны бүртгэл олдсонгүй.")
            return
        session = get_user_session(user_id)
        if not session:
            bot.send_message(user_id, "⚠️ Гүйлгээний мэдээлэл олдсонгүй. Та эхнээс эхлэнэ үү.")
            return



        currency_from = session["currency_from"]

        if currency_from == "rub":
            bank_info = user.get("bank_mnt", "").strip()
            expected_fields = 3
            format_note = "📌 Жишээ: Хаан Банк, MN01 0015 00 500XXXXXXX, Бат"
        else:
            bank_info = user.get("bank_rub", "").strip()
            expected_fields = 4
            format_note = "📌 Жишээ: Сбербанк, +79001234567, 1234567812345678, Бат"

        if not bank_info:
            bot.send_message(user_id, "⚠️ Та энэ төрлийн дансны мэдээллээ хадгалаагүй байна.\n 'Профайл тохиргоо' хэсгээс оруулна уу.")
            return

        parts = [p.strip() for p in bank_info.split(",")]
        if len(parts) != expected_fields or any(not p for p in parts):
            bot.send_message(user_id, f"⚠️ Хадгалсан дансны мэдээлэл алдаатай байна.\n{format_note}")
            return

        # ✅ Show Preview and ask for confirmation
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"confirm_saved_bank"),
            InlineKeyboardButton("❌ Цуцлах", callback_data="cancel_saved_bank")
        )

        bot.send_message(user_id,
                         f"📎 Та дараах хадгалсан дансны мэдээллийг ашиглах гэж байна:\n\n`{bank_info}`\n\n"
                         "Та зөв эсэхийг шалгаад үргэлжлүүлэх эсэхээ сонгоно уу.",
                         reply_markup=markup,
                         parse_mode="Markdown")
        update_user_session(user_id, {"state": "previewing_saved_bank"})
        user_profiles[user_id] = {"preview_bank_info": bank_info}

    except Exception as e:
        print(f"❌ Error using saved bank: {e}")
        bot.send_message(user_id, "❌ Дансны мэдээллийг татах үед алдаа гарлаа.")


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_saved_bank", "cancel_saved_bank"])
def handle_preview_decision(call):
    user_id = call.message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    if call.data == "cancel_saved_bank":
        update_user_session(user_id, {"state": "waiting_for_bank"})

        bot.send_message(user_id, "❌ Хадгалсан дансны мэдээллийг ашиглах үйлдэл цуцлагдлаа.")
        return

    # If confirmed
    bank_info = user_profiles.get(user_id, {}).get("preview_bank_info")
    if not bank_info:
        bot.send_message(user_id, "❗ Мэдээлэл олдсонгүй. Та ижил мөнгөн дүнгээр дахин валют солих хүсэлт үүсгээд гүйлгээ хийсэн баримтаа дахин илгээгээрэй.")
        return

    # Fake message to trigger the receive_bank_details function
    fake_msg = type('FakeMessage', (object,), {
        "chat": type('Chat', (), {"id": user_id}),
        "text": bank_info
    })

    receive_bank_details(fake_msg)


# ✅ **Step 2: User Sends Banking Details → Notify Operator**
@bot.message_handler(func=lambda message: get_state(message.chat.id) == "waiting_for_bank")
def receive_bank_details(message):
    user_id = message.chat.id
    if not ensure_exchange_available(user_id):
        bot.answer_callback_query(call.id)
        return
    bank_details = message.text.strip()

    # ✅ Step 1: Check if session exists
    session = get_user_session(user_id)
    if not session:
        bot.send_message(user_id, "⚠️ Гүйлгээний мэдээлэл олдсонгүй. Та эхнээс эхлэнэ үү.")
        return

    invoice = session.get("invoice")
    if not invoice:
        bot.send_message(user_id, "❗ Хүсэлтийн дугаар алга байна. Шинээр эхэлнэ үү.")
        return

    # ✅ Step 2: Validate bank format (must be 4 parts)
    currency_to = session.get("currency_to")
    expected_fields = 3 if currency_to == "mnt" else 4

    parts = [p.strip() for p in bank_details.split(",")]
    if len(parts) != expected_fields or any(not p for p in parts):
        bot.send_message(
            user_id,
            f"⚠️ Та банкны мэдээллээ зөв оруулна уу! Таслал тэмдэгээр тусгаарлаж оруулах ёстойг анхаарна уу.\n\n"
            f"📌 Жишээ нь:\n"
            + ("`Хаан Банк, MN01 0015 00 500XXXXXXX, Бат`\n\n" if expected_fields == 3 else
               "`Сбербанк, 79001234567, 5469123412341234, Бат`\n\n")
            + "Банкны нэр, Утасны дугаар, Карт/IBAN дугаар, Данс эзэмшэгчийн нэр - гэсэн дарааллаар таслалаар тусгаарлан бичнэ үү.",
            parse_mode="Markdown"
        )
        return

    # ✅ Step 3: Ensure receipt has been received (i.e. pending_transactions initialized)
    if user_id not in pending_transactions or not pending_transactions[user_id].get("receipt_id"):
        bot.send_message(user_id, "📸 Та эхлээд шилжүүлгийн баримтаа зургаар илгээнэ үү.")
        return

    # ✅ Step 4: Save bank details
    pending_transactions[user_id]["bank_details"] = bank_details
    clear_state(user_id)

    # ✅ Step 5: Record in Supabase
    try:
        record_transaction(
            user_id,
            invoice,
            float(session["amount"]),
            session["currency_from"],
            session["currency_to"],
            float(session["rate"]),
            bank_details,
            "pending",
            session.get("promo_code")
        )
    except Exception as e:
        print(f"❌ Failed to save transaction: {e}")
        return

    # ✅ Step 6: Notify operator
    try:
        amount = float(session["amount"])
        currency = session["currency_from"]
        operator_id = HIGH_VALUE_OPERATOR_CHAT_ID if (
            (currency == "rub" and amount > 50000) or (currency == "mnt" and amount > 2500000)
        ) else get_current_shift_operator_id()

        notify_operator(
            user_id,
            invoice,
            pending_transactions[user_id]["receipt_id"],
            bank_details,
            operator_id
        )

        bot.send_message(user_id, "✅ Банкны мэдээлэл хүлээн авлаа!\nАдмин таны гүйлгээг баталгаажуулах хүртэл та хүлээнэ үү.")
    except Exception as e:
        print(f"❌ Operator notify error: {e}")
        bot.send_message(user_id, "❗ Админд мэдэгдэж чадсангүй. Та дахин оролдоно уу.")



def notify_operator(user_id, invoice, receipt_id, bank_details, operator_chat_id):
    session = get_user_session(user_id)
    if not session:
        bot.send_message(user_id, "⚠️ Notify operator session олдсонгүй")
        return

    try:
        user_info = bot.get_chat(user_id)
        user_display = user_info.first_name
        if user_info.last_name:
            user_display += f" {user_info.last_name}"

        user_link = f"[{user_display}](tg://user?id={user_id})"

        if user_info.username:
            username_link = f"[@{user_info.username}](https://t.me/{user_info.username})"
        else:
            username_link = "`NoUsername`"

        id_link = f"[`{user_id}`](tg://user?id={user_id})"

        user_line = f"{user_link} — {username_link} — {id_link}"
    except:
        user_line = f"[`{user_id}`](tg://user?id={user_id})"

    rate = session.get("rate")
    amount = session.get("amount")
    currency_from = session.get("currency_from")
    currency_to = session.get("currency_to")

    converted = round(amount * rate if currency_from.lower() == "rub" else amount / rate, 2)

    # 📝 Save caption to reuse
    caption = (
        f"🔔 ШИНЭ ХҮСЭЛТ 🔔\n\n"
        f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
        f"👤 Үйлчлүүлэгч: {user_line}\n"
        f"💰 Гүйлгээ: *{amount} {currency_from} → {currency_to}*\n"
        f"💱 Хөрвүүлсэн дүн: *{converted} {currency_to}*\n"
        f"🏦 Дансны мэдээлэл: `{bank_details}`\n\n"
        "✅ Гүйлгээг баталгаажуулах эсвэл татгалзах товчийг дарна уу."
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"confirm_{user_id}"),
        InlineKeyboardButton("❌ Татгалзах", callback_data=f"reject_{user_id}")
    )
    operator_id = get_current_shift_operator_id()
    # ➤ Always send to current shift operator
    bot.send_photo(operator_id, receipt_id, caption=caption, parse_mode="Markdown", reply_markup=markup)

    # ➤ Also notify always-notify operator if it's different
    for always_id in ALWAYS_NOTIFY_OPERATOR_ID:
        bot.send_photo(
            always_id,
            receipt_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=markup
        )

    # ➤ Notify high-value operator if the amount is large
    if (currency_from == "RUB" and amount > 50000) or (currency_from == "MNT" and amount > 2500000):
        for special_op in [HIGH_VALUE_OPERATOR_CHAT_ID]:
            if special_op not in [operator_chat_id] + ALWAYS_NOTIFY_OPERATOR_ID:
                bot.send_photo(special_op, receipt_id, caption=caption, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_") or call.data.startswith("reject_") or call.data.startswith("pending_") or call.data.startswith("refresh_"))
def handle_transaction_action(call):
    if call.from_user.id not in ALLOWED_ADMINS:
        bot.answer_callback_query(call.id, "🚫 Зөвшөөрөлгүй хэрэглэгч!", show_alert=True)
        return

    action, user_id_str = call.data.split("_", 1)
    is_confirmed = action == "confirm"
    is_pending = action == "pending"
    is_refresh = action == "refresh"
    user_id = int(user_id_str)

    # Handle refresh action
    if is_refresh:
        # Extract invoice from the message and refresh the status
        text = call.message.text or ""
        invoice_match = re.search(r'`([^`]+)`', text)
        if invoice_match:
            invoice = invoice_match.group(1)
            # Send updated status message
            bot.send_message(
                call.from_user.id,
                f"/status {invoice}",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id, "🔄 Статус шинэчлэгдлээ.", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "❌ Invoice олдсонгүй.", show_alert=True)
        return

    # 1️⃣ Extract invoice number from message (поддерживаем оба формата)
    text = call.message.caption or call.message.text or ""
    
    # Сначала ищем новый формат: YYYYMMDD-HHMMSS-XX
    match = re.search(r'(\d{8}-\d{6}-\d{2})', text)
    if match:
        invoice = match.group(1)
    else:
        # Если не найден новый формат, ищем старый: YYYYMMDD_HHMMSS
        match = re.search(r'(\d{8}_\d{6})', text)
        if match:
            invoice = match.group(1)
        else:
            bot.answer_callback_query(call.id, "❌ Хүсэлтийн дугаар олдсонгүй.", show_alert=True)
            return
    
    resp = supabase.table("transactions") \
                   .select("status") \
                   .eq("invoice", invoice) \
                   .limit(1) \
                   .execute()
    current_status = resp.data[0]["status"] if resp.data else None

    if not is_pending and current_status != "pending":
        # if it's already successful or rejected, tell the admin
        return bot.answer_callback_query(
            call.id,
            "❗ Энэ гүйлгээ аль хэдийн баталгаажсан эсвэл цуцлагдсан байна.",
            show_alert=True
        )
    # 2️⃣ Get transaction from Supabase
    response = supabase.table("transactions").select("*").eq("invoice", invoice).limit(1).execute()
    if not response.data:
        bot.answer_callback_query(call.id, "❌ Гүйлгээ датабазаас олдсонгүй.", show_alert=True)
        return

    txn = response.data[0]
    currency_from = txn["currency_from"].upper()
    currency_to = txn["currency_to"].upper()
    amount = float(txn["amount"])
    rate = float(txn["rate"])
    bank_details = txn.get("bank_details", "")
    receipt_id = txn.get("receipt_id")

    # 3️⃣ Prepare timestamp and payload
    now_moscow = datetime.now(MOSCOW_TZ).isoformat()
    if is_confirmed:
        updates = {
            "status":       "successful",
            "completed_at": now_moscow,
            "completed_by_admin": call.from_user.id,
        }
    elif is_pending:
        updates = {
            "status": "pending",
            "completed_at": None,
            "completed_by_admin": None,
            "admin_comment": None
        }
    else:
        updates = {
            "status":       "rejected",
            # if you want to track when we rejected too:
            # "rejected_at": now_moscow
        }

    # 4️⃣ Write back to Supabase
    supabase.table("transactions") \
            .update(updates) \
            .eq("invoice", invoice) \
            .execute()


    # 4️⃣ Notify user
    if is_pending:
        # Notify user about status change to pending
        bot.send_message(
            user_id,
            f"🔄 Таны `{invoice}` дугаартай гүйлгээ дахин шалгагдах төлөвт орууллаа.\n"
            f"⏳ Админ таны гүйлгээг дахин шалгаж, удахгүй хариу өгөх болно.",
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "✅ Гүйлгээ pending төлөвт орууллаа.", show_alert=True)
    elif is_confirmed:
        # ✅ Calculate how much to send
        converted = round(amount * rate if currency_from == "RUB" else amount / rate, 2)

        # ✅ Notify user
        bot.send_message(
            user_id,
            f"✅ Таны `{invoice}` дугаартай гүйлгээ баталгаажлаа!\n"
            f"💸 Админ таны данс руу тун удахгүй шилжүүлэг хийх болно.",
            parse_mode="Markdown"
        )

        # ✅ Display to operator
        try:
            # Parse bank details
            if currency_to == "MNT":
                bank, iban, name = [x.strip() for x in bank_details.split(",")]
                bank_info = (
                    f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
                    f"📤 *Шилжүүлэх дүн:* `{converted} MNT`\n\n"
                    f"{bank}\n"
                    f"`{iban}`\n"
                    f"{name}\n\n"
                    f"Ханш: *{rate}*\n\n"
                    f"Энэхүү мессежд зургаар *REPLY* хийх эсвэл *CAPTION* хэсэгт invoice id-г бичиж хамт илгээнэ үү."
                )
            else:
                bank, phone, card, name = [x.strip() for x in bank_details.split(",")]
                bank_info = (
                    f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
                    f"📤 *Шилжүүлэх дүн:* `{converted} RUB`\n\n"
                    f"{bank}\n"
                    f"`{phone}`\n"
                    f"`{card}`\n"
                    f"{name}\n\n"
                    f"Ханш: *{rate}*\n\n"
                    f"Энэхүү мессежд зургаар *REPLY* хийх эсвэл *CAPTION* хэсэгт invoice id-г бичиж хамт илгээнэ үү."
                )

            msg = bot.send_message(call.message.chat.id, bank_info, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Error formatting bank details: {e}")
            bot.send_message(call.message.chat.id, "⚠️ Дансны мэдээлэл формат буруу байна.")

    else:
        # Ask for rejection comment
        update_user_session(call.from_user.id, {"state": f"awaiting_tx_rejection_comment|{invoice}|{user_id}"})
        bot.send_message(call.from_user.id, f"📝 Та `{invoice}` гүйлгээг цуцлах шалтгаанаа бичнэ үү:", parse_mode="Markdown")


    # ✅ Clean up: remove buttoned message if desired
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass


@bot.message_handler(func=lambda m: get_state(m.chat.id).startswith("awaiting_tx_rejection_comment|"))
def handle_transaction_rejection_comment(message):
    admin_id = message.chat.id
    comment = message.text.strip()

    # Full string after the prefix
    state = get_state(admin_id)
    if not state.startswith("awaiting_tx_rejection_comment|"):
        bot.send_message(admin_id, "❌ Алдаа: Хүсэлтийн төлөв олдсонгүй.")
        return
    
    # Extract invoice and user_id from state
    # Format: "awaiting_tx_rejection_comment|INVOICE|USERID"
    state_parts = state.replace("awaiting_tx_rejection_comment|", "").split("|")
    
    if len(state_parts) < 2:
        bot.send_message(admin_id, "❌ Алдаа: Хүсэлтийн мэдээлэл буруу байна.")
        return
    
    invoice = state_parts[0]
    user_id = int(state_parts[1])

    try:
        # Update DB with rejection + comment
        supabase.table("transactions").update({
            "status": "rejected",
            "rejection_comment": comment
        }).eq("invoice", invoice).execute()

        # Notify both parties
        bot.send_message(
            admin_id,
            f"❌ `{invoice}` дугаартай гүйлгээ амжилттай цуцлагдлаа.",
            parse_mode="Markdown"
        )

        bot.send_message(
            user_id,
            f"❌ Таны `{invoice}` дугаартай гүйлгээг баталгаажуулах боломжгүй байна.\n"
            f"📌 Шалтгаан: _{comment}_\n\n{CONTACT_SUPPORT}",
            parse_mode="Markdown"
        )
        update_user_session(user_id, {"invoice": None})

    except Exception as e:
        print(f"❌ Rejection DB error: {e}")
        bot.send_message(admin_id, "❌ Гүйлгээ цуцлах үед алдаа гарлаа.")
    finally:
        clear_state(admin_id)
        pending_transactions.pop(user_id, None)

# 🔙 Back to Main Menu
@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_main(call):
    bot.send_message(call.message.chat.id, "👋 Нүүр хуудас руу буцах", reply_markup=main_menu())

def payment_receipt(message):
    user_id = message.chat.id
    receipt_id = message.photo[-1].file_id
    session = get_user_session(user_id)
    invoice = session.get("invoice")
    pending_transactions[user_id] = {
        "invoice": invoice,
        "receipt_id": receipt_id,
        "bank_details": None,
        "admin_bill_id": None
    }

    invoice = session.get("invoice")
    update_user_session(user_id, {"state": "waiting_for_bank"})
    # 🧠 Detect the target currency
    session = get_user_session(user_id)
    if not session:
        bot.send_message(user_id, "⚠️ Гүйлгээний мэдээлэл олдсонгүй. Та эхнээс эхлэнэ үү.")
        return
    currency_to = session.get("currency_to") if session else "mnt"

    # 📌 Instructions based on destination currency
    if currency_to == "mnt":
        instructions = (
            "📌 Та өөрийн *монгол банкны* мэдээллийг дараах форматаар явуулна уу:\n"
            "👉 `Банк, IBAN дансны дугаар, Данс эзэмшэгчийн нэр` \n\n ⚠️ Та өөрийн нэр дээр бүртгэлтэй данснаас шилжүүлэг хийгээгүй тохиолдолд таны гүйлгээ буцаагдах болохыг анхаарна уу!"
        )
    else:
        instructions = (
            "📌 Та өөрийн *орос банкны* мэдээллийг дараах форматаар явуулна уу:\n"
            "👉 `Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр` \n\n ⚠️ Та өөрийн нэр дээр бүртгэлтэй данснаас шилжүүлэг хийгээгүй тохиолдолд таны гүйлгээ буцаагдах болохыг анхаарна уу!"
        )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💾 Хадгалсан дансны мэдээллээ ашиглах", callback_data="use_saved_bank")
    )

    bot.send_message(
        user_id,
        f"✅ Хүлээж авлаа!\n📌 Хүсэлтийн дугаар: `{invoice}`\n\n"
        f"{instructions}\n\n"
        "📎 Эсвэл хадгалсан мэдээллээ ашиглах бол доорх товчийг дарна уу.",
        reply_markup=markup,
        parse_mode="Markdown"
    )
@bot.callback_query_handler(func=lambda call: call.data == "review_registration")
def handle_review_registration(call):
    user_id = call.message.chat.id
    review_registration(user_id)

def review_registration(user_id):
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    user = response.data[0] if response.data else {}

    text = (
        "📋 **Бүртгэлийн мэдээлэл шалгах:**\n\n"
        f"👤 Овог: {user.get('last_name', '-')}\n"
        f"👤 Нэр: {user.get('first_name', '-')}\n"
        f"📞 Утас: {user.get('phone', '-')}\n"
        f"🪪 Паспортын дугаар: {user.get('registration_number', '-')}\n"
        f"🏦 Монгол банк: {user.get('bank_mnt', '-')}\n"
        f"🇷🇺 Орос банк: {user.get('bank_rub', '-')}\n"
        f"📷 Паспорт зураг: {'🟢 Байгаа' if user.get('passport_file_id') else '🔴 Байхгүй'}"
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📤 Баталгаажуулах хүсэлт илгээх", callback_data="submit_verification"),
        InlineKeyboardButton("🔙 Буцах", callback_data="back_main")
    )

    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(content_types=['document'])
def reject_file_receipts(message):
    user_id = message.chat.id
    session = get_user_session(user_id)
    state = session["state"] if session else None

    if state == "waiting_for_receipt":
        bot.send_message(
            user_id,
            "❌ *Та PDF болон өөр төрлийн файл илгээх боломжгүй!*\n\n"
            "📸 Та гүйлгээний баримтаа зөвхөн *зураг хэлбэрээр* оруулна уу.\n",
            parse_mode="Markdown"
        )
    else:
        # Optional: Handle other states if needed
        bot.send_message(user_id, "📁 Энэ файлыг одоогоор хүлээн авах боломжгүй байна.")


@bot.message_handler(commands=['batalgaajuulah'])
def cmd_reconfirm(message):
    admin_id = message.chat.id
    if admin_id not in ALLOWED_ADMINS:
        return bot.reply_to(message, "🚫 Зөвшөөрөгдөөгүй хэрэглэгч!")

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or not is_valid_invoice_format(parts[1]):
        return bot.reply_to(message, "❗ Формат: /batalgaajuulah <YYYYMMDD_HHMMSS> эсвэл <YYYYMMDD-HHMMSS-XX>")
    invoice = parts[1]

    # Fetch txn
    resp = supabase.table("transactions") \
        .select("status,amount,currency_from,currency_to,rate,bank_details,bill_url") \
        .eq("invoice", invoice) \
        .single() \
        .execute()
    if not resp.data:
        return bot.reply_to(message, f"❌ `{invoice}` гүйлгээ олдсонгүй.", parse_mode="Markdown")
    txn = resp.data

    if txn["status"] != "rejected":
        return bot.reply_to(
            message,
            f"❗ `{invoice}` төлөв нь `{txn['status']}`, дахин баталгаажуулах боломжгүй.",
            parse_mode="Markdown"
        )

    # Re‑open
    supabase.table("transactions").update({"status": "pending"}).eq("invoice", invoice).execute()

    # Compute converted amount
    amt   = float(txn["amount"])
    rate  = float(txn["rate"])
    tocur = txn["currency_to"].upper()
    conv  = round(amt * rate if txn["currency_from"].upper()=="RUB" else amt / rate, 2)
    bd    = txn.get("bank_details", "")
    url   = txn.get("bill_url", "")

    # Build caption
    if tocur == "MNT":
        bank, iban, name = [x.strip() for x in bd.split(",")]
        caption = (
            f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
            f"📤 *Шилжүүлэх дүн:* `{conv} MNT`\n\n"
            f"{bank}\n"
            f"`{iban}`\n"
            f"{name}\n\n"
            f"Ханш: *{rate}*\n\n"
            f"Энэхүү мессежд зургаар *REPLY* хийх эсвэл *CAPTION* хэсэгт invoice id-г бичиж хамт илгээнэ үү."
        )
    else:
        bank, phone, card, name = [x.strip() for x in bd.split(",")]
        caption = (
            f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
            f"📤 *Шилжүүлэх дүн:* `{conv} RUB`\n\n"
            f"{bank}\n"
            f"`{phone}`\n"
            f"`{card}`\n"
            f"{name}\n\n"
            f"Ханш: *{rate}*\n\n"
            f"Энэхүү мессежд зургаар *REPLY* хийх эсвэл *CAPTION* хэсэгт invoice id-г бичиж хамт илгээнэ үү."
        )

    # Attach public link
    if url:
        caption += f"\n\n📎 [Баримт харах]({url})"

    bot.send_message(admin_id, caption, parse_mode="Markdown")

# ✅ Admin command to show transaction status and manage it
@bot.message_handler(commands=['status'])
def cmd_status(message):
    admin_id = message.chat.id
    if admin_id not in ALLOWED_ADMINS:
        return bot.reply_to(message, "🚫 Зөвшөөрөгдөөгүй хэрэглэгч!")

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2 or not is_valid_invoice_format(parts[1]):
        return bot.reply_to(message, "❗ Формат: /status <YYYYMMDD_HHMMSS> эсвэл <YYYYMMDD-HHMMSS-XX>")
    invoice = parts[1]

    # Fetch txn
    resp = supabase.table("transactions") \
        .select("*") \
        .eq("invoice", invoice) \
        .single() \
        .execute()
    if not resp.data:
        return bot.reply_to(message, f"❌ `{invoice}` гүйлгээ олдсонгүй.", parse_mode="Markdown")
    txn = resp.data

    # Build status message
    status_emoji = {
        "pending": "⏳",
        "successful": "✅", 
        "rejected": "❌"
    }
    
    status_text = {
        "pending": "Хүлээгдэж буй",
        "successful": "Амжилттай",
        "rejected": "Цуцлагдсан"
    }

    status = txn["status"]
    emoji = status_emoji.get(status, "❓")
    status_name = status_text.get(status, status)
    
    # Calculate converted amount
    amt = float(txn["amount"])
    rate = float(txn["rate"])
    currency_from = txn["currency_from"].upper()
    currency_to = txn["currency_to"].upper()
    converted = round(amt * rate if currency_from == "RUB" else amt / rate, 2)

    message_text = (
        f"{emoji} **Гүйлгээний мэдээлэл**\n\n"
        f"📌 **Дугаар:** `{invoice}`\n"
        f"📊 **Төлөв:** {status_name}\n"
        f"💰 **Дүн:** {amt} {currency_from} → {converted} {currency_to}\n"
        f"📈 **Ханш:** {rate}\n"
        f"👤 **Хэрэглэгч ID:** {txn['user_id']}\n"
        f"🕐 **Үүсгэсэн:** {txn.get('timestamp', 'N/A')[:19] if txn.get('timestamp') else 'N/A'}\n"
    )

    if txn.get("completed_at"):
        message_text += f"✅ **Дууссан:** {txn['completed_at'][:19]}\n"
    if txn.get("completed_by_admin"):
        message_text += f"👨‍💼 **Баталгаажуулсан:** {txn['completed_by_admin']}\n"
    if txn.get("admin_comment"):
        message_text += f"💬 **Тайлбар:** {txn['admin_comment']}\n"

    # Add action buttons based on current status
    markup = InlineKeyboardMarkup()
    if status == "pending":
        # Pending transactions can be confirmed or rejected
        markup.add(
            InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"confirm_{txn['user_id']}"),
            InlineKeyboardButton("❌ Цуцлах", callback_data=f"reject_{txn['user_id']}")
        )
    elif status == "successful":
        # Successful transactions can be moved back to pending or rejected
        markup.add(
            InlineKeyboardButton("🔄 Pending рүү буцаах", callback_data=f"pending_{txn['user_id']}")
        )
    elif status == "rejected":
        # Rejected transactions can be moved back to pending or confirmed
        markup.add(
            InlineKeyboardButton("🔄 Pending рүү буцаах", callback_data=f"pending_{txn['user_id']}")
        )

    bot.reply_to(message, message_text, parse_mode="Markdown", reply_markup=markup)

def _send_rating_prompt(user_id: int):
    kb = InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(InlineKeyboardButton("⭐" * i, callback_data=f"rate_{i}"))
    kb.add(InlineKeyboardButton("✍️ Санал хүсэлт бичих", callback_data="write_feedback"))
    bot.send_message(user_id, "🤔 Та бидний энэхүү үйлчилгээг ашиглахад хэр хялбар байсан бэ?", reply_markup=kb)

def _flush_admin_media_group(mgid: str, target_user: int, caption: str, admin_id: int):
    # pop buffer and clear scheduled flag
    photos = _admin_media_buffers.pop(mgid, [])
    _admin_media_flush_scheduled.discard(mgid)
    if not photos:
        return

    media = []
    # first photo with caption
    media.append(InputMediaPhoto(media=photos[0], caption=caption, parse_mode="Markdown"))
    # rest without captions
    for fid in photos[1:]:
        media.append(InputMediaPhoto(media=fid))
    bot.send_media_group(target_user, media)

    # now prompt for rating
    _send_rating_prompt(target_user)

    # Extract invoice from caption for admin notification
    invoice_match = re.search(r'`([^`]+)`', caption)
    invoice = invoice_match.group(1) if invoice_match else "unknown"
    
    # acknowledge to admin
    bot.send_message(
        admin_id,
        f"📨 `{invoice}` дугаартай гүйлгээний баримт хэрэглэгч рүү амжилттай илгээгдлээ.",
        parse_mode="Markdown"
    )
@bot.message_handler(content_types=['photo'])
def handle_passport_or_receipt(message):
    user_id = message.chat.id
    photo_id = message.photo[-1].file_id
    state = get_state(user_id)
    admin_id = user_id  # for clarity

    # --- 1) PASSPORT UPLOAD FLOW (for new-user registration) ---
    if state in ["waiting_for_passport", "register_passport"]:
        try:
            file_info = bot.get_file(photo_id)
            file_url  = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            resp      = requests.get(file_url)
            resp.raise_for_status()

            file_name = f"{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(resp.content)
                temp_path = tmp.name

            supabase.storage.from_("passports").upload(
                file_name,
                temp_path,
                {"content-type": "image/jpeg", "x-upsert": "true"}
            )
            public_url = supabase.storage.from_("passports").get_public_url(file_name)

            supabase.table("users").update({
                "passport_file_id": photo_id,
                "passport_storage_url": public_url
            }).eq("id", user_id).execute()

            bot.send_message(user_id, "🪪 Паспортын зураг амжилттай хадгалагдлаа!")
            if state == "register_passport":
                bot.send_message(
                    user_id,
                    "🎉 Бүртгэл дууслаа!\n📋 Та бүртгэлийн мэдээллээ дахин шалгаад баталгаажуулах хүсэлт илгээнэ үү 👇",
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("📋 Мэдээлэл шалгах", callback_data="review_registration")
                    )
                )
        except Exception as e:
            print(f"❌ Passport upload error: {e}")
            bot.send_message(user_id, f"❌ Алдаа гарлаа: {e}")
        finally:
            clear_state(user_id)
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        return

    # --- 2) USER RECEIPT UPLOAD FLOW (client uploads payment proof) ---
    if state == "waiting_for_receipt":
        session = get_user_session(user_id)
        invoice = session.get("invoice")
        if not invoice:
            return bot.send_message(user_id, "❗ Хүсэлтийн дугаар алга байна. Шинээр эхлэнэ үү.")

        try:
            file_info = bot.get_file(photo_id)
            file_url  = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            resp      = requests.get(file_url); resp.raise_for_status()

            file_name = f"{invoice}_{user_id}.jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(resp.content)
                temp_path = tmp.name

            supabase.storage.from_("bills").upload(
                file_name,
                temp_path,
                {"content-type": "image/jpeg", "x-upsert": "true"}
            )
            bill_url = supabase.storage.from_("bills").get_public_url(file_name)

            supabase.table("transactions").update({
                "bill_id":     photo_id,
                "receipt_id":  photo_id,
                "bill_url":    bill_url
            }).eq("invoice", invoice).execute()

            bot.send_message(user_id, "✅ Гүйлгээний баримт амжилттай хадгалагдлаа!")
        except Exception as e:
            print(f"❌ Receipt upload error: {e}")
            bot.send_message(user_id, f"❌ Баримт хадгалах үед алдаа гарлаа: {e}")
        finally:
            update_user_session(user_id, {"state": "waiting_for_bank"})
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

        # Now prompt for bank details
        return payment_receipt(message)

    # --- 3) ADMIN CONFIRMATION FLOW (only if NOT in one of the above states) ---
    if message.from_user.id in ALLOWED_ADMINS:
            # Check if this is part of a media group that's already being processed
            mgid = message.media_group_id
            if mgid and mgid in _admin_media_flush_scheduled:
                # This is a subsequent photo in an already scheduled media group
                # Just add it to the buffer and return
                buf = _admin_media_buffers.setdefault(mgid, [])
                buf.append(photo_id)
                return

            # 1) Build a single text blob to search for invoice + comment
            source = ""
            if message.reply_to_message:
                source += (message.reply_to_message.caption or "") + "\n"
                source += (message.reply_to_message.text or "") + "\n"
            source += (message.caption or "")

            # 2) Extract the invoice (поддерживаем оба формата)
            # Сначала ищем новый формат: YYYYMMDD-HHMMSS-XX
            m = re.search(r'(\d{8}-\d{6}-\d{2})', source)
            if m:
                invoice = m.group(1)
            else:
                # Если не найден новый формат, ищем старый: YYYYMMDD_HHMMSS
                m = re.search(r'(\d{8}_\d{6})', source)
                if m:
                    invoice = m.group(1)
                else:
                    return bot.send_message(
                        user_id,
                        "⛔ Гүйлгээний дугаар тодорхойгүй байна.\n"
                        "Зурган дээр reply хийх эсвэл зургийн caption хэсэгт `YYYYMMDD_HHMMSS` эсвэл `YYYYMMDD-HHMMSS-XX` хэлбэрийн invoice id-г бичнэ үү.",
                        parse_mode="Markdown"
                    )

            # 3) Anything after the invoice in the admin's caption → comment
            #    We look only in this message's caption, not the replied-to one
            raw = message.caption or ""
            comment = raw.replace(invoice, "").strip()

            # 3) Lookup user_id
            resp = supabase.table("transactions") \
                          .select("user_id") \
                          .eq("invoice", invoice) \
                          .limit(1) \
                          .execute()
            if not resp.data:
                bot.send_message(message.chat.id, f"❌ `{invoice}` гүйлгээ олдсонгүй. Invoice ID-г шалгана уу.", parse_mode="Markdown")
                return
            target_user = resp.data[0]["user_id"]

            # 4) Update DB
            updates = {
                "status": "successful",
                "admin_bill_id": message.photo[-1].file_id,
                "completed_by_admin": message.from_user.id,            
                "completed_at": datetime.now(MOSCOW_TZ).isoformat()   
            }
            if comment:
                updates["admin_comment"] = comment
            supabase.table("transactions").update(updates).eq("invoice", invoice).execute()

            # 5) Build forward caption
            caption = f"✅ `{invoice}` дугаартай *гүйлгээ амжилттай хийгдлээ!* \n\nТа шилжүүлсэн баримтыг хүлээн авна уу."
            if comment:
                caption += f"\n\n💬 *Админы тайлбар:* {comment}"
            caption += "\n\nМанайхыг сонгон үйлчлүүлсэнд баярлалаа! 🤗"

            # 6) Send photo(s) as media_group if needed
            if mgid:
                # buffer
                buf = _admin_media_buffers.setdefault(mgid, [])
                buf.append(photo_id)
                # only schedule one flush per mgid
                if mgid not in _admin_media_flush_scheduled:
                    _admin_media_flush_scheduled.add(mgid)
                    # after 1 second, flush the entire group
                    threading.Timer(
                        1.0,
                        _flush_admin_media_group,
                        args=(mgid, target_user, caption, admin_id)
                    ).start()
            else:
                # single
                bot.send_photo(target_user, photo_id, caption=caption, parse_mode="Markdown")
                _send_rating_prompt(target_user)
                bot.send_message(
                    admin_id,
                    f"📨 `{invoice}` дугаартай гүйлгээний баримт хэрэглэгч рүү амжилттай илгээгдлээ.",
                    parse_mode="Markdown"
                )
            return

    # --- 4) FALLBACK: nobody matched ---
    bot.send_message(
        message.chat.id,
        "❓ Энэ зураг юунд зориулагдсан болохыг тодорхойлж чадсангүй.\n"
        "🕹️ Та хэрэв валют солиулахыг хүсч байвал эхлээд */start* команд ашиглан цэснээс валют солих үйлчилгээг сонгоод гүйлгээний хүсэлт үүсгэсний дараа гүйлгээний баримтын зургаа явуулна уу, эсвэл OYUNS SUPPORT чатруу хандаарай:\n"
        f"{CONTACT_SUPPORT}",
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating(call):
    user_id = call.message.chat.id
    rating = int(call.data.split("_")[1])
    session = get_user_session(user_id)
    # Optionally store invoice info
    invoice = session.get("invoice")
    # Save rating temporarily
    user_feedback_state[user_id] = {
        "rating": rating,
        "invoice": invoice
    }

    # Show feedback button
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✍️ Санал хүсэлт бичих", callback_data="write_feedback"))

    bot.send_message(
        user_id,
        f"🎉 Баярлалаа! Та бидний үйлчилгээнд {rating} ⭐ үнэлгээ өглөө.\n✉️ Хэрэв санал хүсэлт байвал дараах товчийг дарна уу.",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "write_feedback")
def ask_for_text_feedback(call):
    update_user_session(call.message.chat.id, {"state": "awaiting_feedback"})
    bot.send_message(call.message.chat.id, "📝 Та санал хүсэлтээ бичнэ үү:")
@bot.message_handler(func=lambda m: get_state(m.chat.id) == "awaiting_feedback")
def save_text_feedback(message):
    user_id = message.chat.id
    comment = message.text.strip()

    feedback_info = user_feedback_state.pop(user_id, {})
    rating = feedback_info.get("rating")
    invoice = feedback_info.get("invoice")

    if not rating:
        bot.send_message(user_id, "⚠️ Үнэлгээ бүртгэгдээгүй байна. Та дахин оролдоно уу.")
        return

    try:
        supabase.table("feedback").insert({
            "user_id": user_id,
            "rating": rating,
            "invoice": invoice,
            "comment": comment,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏠 Үндсэн цэс рүү очих", callback_data="back_main"))

        bot.send_message(
            user_id,
            "✅ Баярлалаа! Таны сэтгэгдлийг амжилттай хүлээн авлаа.\n🤗 Бид таны саналыг үйлчилгээг сайжруулахад ашиглах болно.",
            reply_markup=markup
        )
    except Exception as e:
        print(f"❌ Feedback insert error: {e}")
        bot.send_message(user_id, "❌ Уучлаарай, алдаа гарлаа. Та дахин оролдоно уу.")
    finally:
        clear_state(user_id)

def cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Цуцлах", callback_data="cancel_registration"))
    return markup

def restart_registration_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔁 Бүртгэл дахин эхлүүлэх", callback_data="restart_registration"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data == "cancel_registration")
def cancel_registration(call):
    user_id = call.message.chat.id
    clear_state(user_id)
    bot.send_message(user_id, "🚫 Бүртгэлийн үйлдэл цуцлагдлаа.")

#REGISTRATION FORM

@bot.message_handler(commands=['register'])
def register(message):
    user_id = message.chat.id
    if not has_agreed_terms(user_id):
        ask_terms_agreement(message.chat.id)
        return
    # Check if user is already verified
    response = supabase.table("users").select("verified").eq("id", user_id).execute()
    user = response.data[0] if response.data else None

    if user and user.get("verified"):
        bot.send_message(user_id, "✅ Та аль хэдийн бүртгүүлсэн байна. Хувийн мэдээлэл өөрчлөхийг хүсвэл хэрэглэгчийн тохиргоо цэсийг ашиглана уу.")
        return

    # Insert placeholder user if not exists
    if not user:
        supabase.table("users").upsert({"id": user_id}).execute()

    bot.send_message(user_id, "Та бүртгэлийн форм эхлүүлж байна.\n\n Бид таны хувийн мэдээллийг чандлан хадгалах бөгөөд энэхүү мэдээллүүд нь хэрэглэгчийн санхүүгийн аюулгүй байдлыг хангах, болзошгүй луйвраас сэргийлэх зорилготой юм. Эдгээрээс бусад зорилгоор таны мэдээллийг бид ашиглахгүй болно.\n\n📋 Та өөрийн дараах мэдээллүүдийг оруулна уу...")
    update_user_session(user_id, {"state": "register_last_name"})

    bot.send_message(user_id, "👤 Та өөрийн овгоо оруулна уу:", reply_markup=cancel_markup())

@bot.callback_query_handler(func=lambda c: c.data == "enter_rub")
def handle_rub_choice(c):
    user_id = c.message.chat.id
    # Move straight to entering RUB info
    update_user_session(user_id, {"state": "register_bank_rub"})
    bot.send_message(
        user_id,
        "🏦 Орос банкны мэдээллээ дараах форматаар таслал тэмдэг ашиглан оруулна уу:\n"
        "Банк, Орос утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр",
        parse_mode="Markdown",
        reply_markup=cancel_markup()
    )
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: get_state(m.chat.id) in [
    "register_last_name",
    "register_first_name",
    "register_phone",
    "register_reg",
    "register_bank_mnt",
    "register_bank_rub",
    "register_passport"
])

def handle_registration_sequence(message):
    user_id = message.chat.id
    session = get_user_session(user_id)
    state = session["state"] if session else None
    text = message.text.strip()

    if state == "register_last_name":
        supabase.table("users").upsert({"id": user_id, "last_name": text}).execute()
        update_user_session(user_id, {"state": "register_first_name"})
        bot.send_message(user_id, "👤 Та өөрийн нэрээ оруулна уу:", reply_markup=cancel_markup())

    elif state == "register_first_name":
        supabase.table("users").upsert({"id": user_id, "first_name": text}).execute()
        update_user_session(user_id, {"state": "register_phone"})
        bot.send_message(user_id, "📞 Утасны дугаараа оруулна уу:", reply_markup=cancel_markup())

    elif state == "register_phone":
        supabase.table("users").upsert({"id": user_id, "phone": text}).execute()
        update_user_session(user_id, {"state": "register_reg"})
        bot.send_message(user_id, "🪪 Паспортын дугаараа оруулна уу (жишээ нь: E1234560):", reply_markup=cancel_markup())

    elif state == "register_reg":
        # Remove spaces before validating
        clean_text = text.replace(" ", "")
    
        # Check only letters and numbers (spaces ignored)
        if not re.fullmatch(r'[A-Za-z0-9]+', clean_text):
            msg = bot.send_message(
                user_id,
                "❌ Паспортын дугаар буруу байна. Зөвхөн A–Z болон 0–9 тэмдэгт зөвшөөрнө. Жишээ нь: E1234560",
                reply_markup=cancel_markup()
            )
            bot.register_next_step_handler(msg, handle_registration_sequence)
            return
                
        supabase.table("users").upsert({"id": user_id, "registration_number": text}).execute()
        update_user_session(user_id, {"state": "register_bank_mnt"})
        bot.send_message(user_id, "🏦 Монгол банкны мэдээллээ дараах форматаар таслал тэмдэг ашиглан оруулна уу (Банк, IBAN дансны дугаар, Данс эзэмшэгчийн нэр):", reply_markup=cancel_markup())

    elif state == "register_bank_mnt":
        parts = [x.strip() for x in text.split(",")]
        if len(parts) != 3:
            bot.send_message(user_id,
                "❌ Зөв формат: Банк, IBAN дансны дугаар, Данс эзэмшэгчийн нэр",
                reply_markup=cancel_markup())
            return

        # Save MNT info
        supabase.table("users").upsert({"id": user_id, "bank_mnt": text}).execute()

        # **Now require RUB info immediately**
        update_user_session(user_id, {"state": "register_bank_rub"})
        bot.send_message(
            user_id,
            "📌 Орос банкны мэдээллээ дараах форматаар таслал тэмдэг ашиглан оруулна уу:\n"
            "`Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр`",
            reply_markup=cancel_markup()
        )

    elif state == "register_bank_rub":
        parts = [x.strip() for x in text.split(",")]
        if len(parts) != 4:
            bot.send_message(
                user_id,
                "❌ Зөв формат: Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр",
                reply_markup=cancel_markup()
            )
            return
        supabase.table("users").upsert({"id": user_id, "bank_rub": text}).execute()
        update_user_session(user_id, {"state": "register_passport"})
        bot.send_message(user_id, "📷 Та паспортын эхний хуудасны зургаа илгээнэ үү:", reply_markup=cancel_markup())

    elif state == "register_passport":
        bot.send_message(user_id, "❌ Та зураг илгээнэ үү, текст биш.", reply_markup=cancel_markup())
        clear_state(user_id)



@bot.callback_query_handler(func=lambda call: call.data == "cancel_registration")
def cancel_registration(call):
    user_id = call.message.chat.id
    clear_state(user_id)  # Clear current state

    # Optional: delete unverified user data
    supabase.table("users").delete().eq("id", user_id).execute()

    bot.send_message(user_id, "🚫 Бүртгэлийн үйл явц цуцлагдлаа.", reply_markup=restart_registration_markup())



@bot.message_handler(commands=['hereglegch'])
def show_pending_users(message):
    try:
        user_id = message.from_user.id
        print("🆔 Admin requesting:", user_id)

        if user_id not in ALLOWED_ADMINS:
            bot.send_message(message.chat.id, "🚫 Зөвшөөрөлгүй хэрэглэгч байна.")
            return

        response = supabase.table("users").select("*").eq("verified", False).eq("ready_for_verification", True).execute()
        users = response.data

        print("🗂 Pending user data:", users)

        if not users:
            bot.send_message(message.chat.id, "📭 Одоогоор баталгаажуулах хүсэлт илгээсэн хэрэглэгч байхгүй байна.")
            return

        for user in users:
            text = (
                f"👤 Хэрэглэгчийн мэдээлэл:\n\n"
                f"👤 Овог: {user.get('last_name', '-')}\n"
                f"👤 Нэр: {user.get('first_name', '-')}\n"
                f"📞 Утас: {user.get('phone', '-')}\n"
                f"🪪 Паспортын дугаар: {user.get('registration_number', '-')}\n"
                f"🏦 Монгол банк: {user.get('bank_mnt', '-')}\n"
                f"🇷🇺 Орос банк: {user.get('bank_rub', '-')}\n"
            )

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"verify_{user['id']}"),
                InlineKeyboardButton("❌ Цуцлах", callback_data=f"rejectuser_{user['id']}")
            )

            passport_id = user.get('passport_file_id')
            passport_url = user.get("passport_storage_url")

            if passport_id:
                # ✅ Telegram file ID байгаа үед
                bot.send_photo(message.chat.id, passport_id, caption=text, reply_markup=markup)
            elif passport_url:
                # ✅ Telegram ID байхгүй → Supabase public URL-оос татаж илгээх
                try:
                    response = requests.get(passport_url)
                    if response.status_code == 200:
                        photo_bytes = io.BytesIO(response.content)
                        photo_bytes.name = "passport.jpg"
                        bot.send_photo(message.chat.id, photo_bytes, caption=text, reply_markup=markup)
                    else:
                        raise Exception("⚠️ Supabase URL-с зураг татаж чадсангүй.")
                except Exception as e:
                    bot.send_message(message.chat.id, text + "\n⚠️ Паспортын зургийг татаж чадсангүй.", reply_markup=markup)
                    print(f"❌ Error downloading image from Supabase: {e}")
            else:
                bot.send_message(message.chat.id, text + "\n⚠️ Паспорт зураг оруулаагүй байна!", reply_markup=markup)

    except Exception as e:
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, f"❌ Алдаа гарлаа: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
def verify_user(call):
    user_id = int(call.data.replace("verify_", ""))
    try:
        supabase.table("users").update({"verified": True}).eq("id", user_id).execute()
        bot.send_message(call.message.chat.id, f"✅ Хэрэглэгч [{user_id}](tg://user?id={user_id}) баталгаажлаа.", parse_mode="Markdown")
        bot.send_message(user_id, "🎉 Таны бүртгэл амжилттай баталгаажлаа!")

        # 🧹 Delete the original message with buttons
        bot.delete_message(call.message.chat.id, call.message.message_id)

    except Exception as e:
        print(f"❌ Error verifying user: {e}")
        bot.send_message(call.message.chat.id, "❌ Баталгаажуулах үед алдаа гарлаа.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rejectuser_"))
def reject_user_with_reason_prompt(call):
    user_id = int(call.data.replace("rejectuser_", ""))
    admin_id = call.from_user.id
    update_user_session(admin_id, {"state": f"awaiting_rejection_comment_{user_id}"})

    bot.send_message(admin_id, f"✍️ `{user_id}` хэрэглэгчийн бүртгэлийг цуцлах шалтгаанаа бичнэ үү:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: get_state(m.chat.id).startswith("awaiting_rejection_comment_"))
def handle_rejection_comment(message):
    admin_id = message.chat.id
    text = message.text.strip()
    state = get_state(admin_id)
    try:
        user_id = int(state.split("_")[-1])
    except (ValueError, AttributeError, IndexError):
        bot.send_message(admin_id, "⚠️ Уучлаарай, хэрэглэгчийн мэдээллийг уншиж чадсангүй.")
        return

    # Save to DB
    supabase.table("users").update({
        "ready_for_verification": False,
    }).eq("id", user_id).execute()

    # Notify both parties
    bot.send_message(admin_id, f"❌ Хэрэглэгч `{user_id}` бүртгэл цуцлагдлаа.", parse_mode="Markdown")
    bot.send_message(
        user_id,
        f"⚠️ Таны бүртгэлийг баталгаажуулах боломжгүй байна.\n📌 Шалтгаан: _{text}_\n\n Та шаардлагатай бол мэдээллээ 👤 *Хэрэглэгчийн тохиргоо* хэсэгт засаж дахин илгээнэ үү.\n\n📞 Тусламж хэрэгтэй бол дараах хаягаар холбогдоно уу:\n+976 7780 6060\n+7 (977) 801-91-43\n📨 [@oyuns_support](https://t.me/oyuns_support)",
        parse_mode="Markdown"
    )
    clear_state(admin_id)

def build_transaction_caption_and_markup(user_id, invoice, amount, currency_from, currency_to, rate, bank_details, receipt_id=None):
    try:
        user_info = bot.get_chat(user_id)
        user_display = user_info.first_name
        if user_info.last_name:
            user_display += f" {user_info.last_name}"
        user_link = f"[{user_display}](tg://user?id={user_id})"

        if user_info.username:
            username_link = f"[@{user_info.username}](https://t.me/{user_info.username})"
        else:
            username_link = "`NoUsername`"

        id_link = f"[`{user_id}`](tg://user?id={user_id})"
        user_line = f"{user_link} — {username_link} — {id_link}"
    except:
        user_line = f"[`{user_id}`](tg://user?id={user_id})"

    converted = round(amount * rate if currency_from.upper() == "RUB" else amount / rate, 2)

    caption = (
        f"🔔 БАТАЛГААЖААГҮЙ ХҮСЭЛТ 🔔\n\n"
        f"📌 Хүсэлтийн дугаар: `{invoice}`\n"
        f"👤 Үйлчлүүлэгч: {user_line}\n"
        f"💰 Гүйлгээ: *{amount} {currency_from.upper()} → {currency_to.upper()}*\n"
        f"💱 Хөрвүүлсэн дүн: *{converted} {currency_to.upper()}*\n"
        f"🏦 Дансны мэдээлэл: `{bank_details}`\n\n"
        "✅ Гүйлгээг баталгаажуулах эсвэл татгалзах товчийг дарна уу."
    )

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Баталгаажуулах", callback_data=f"confirm_{user_id}"),
        InlineKeyboardButton("❌ Татгалзах", callback_data=f"reject_{user_id}")
    )

    return caption, markup
@bot.message_handler(commands=['guilgee'])
def show_pending_transactions(message):
    if message.from_user.id not in ALLOWED_ADMINS:
        bot.send_message(message.chat.id, "🚫 Зөвшөөрөлгүй хэрэглэгч байна.")
        return

    response = supabase.table("transactions").select("*").eq("status", "pending").execute()
    transactions = response.data

    if not transactions:
        bot.send_message(message.chat.id, "📭 Баталгаажаагүй гүйлгээ алга байна.")
        return

    for txn in transactions:
        user_id = txn["user_id"]
        invoice = txn["invoice"]
        amount = float(txn["amount"])
        currency_from = txn["currency_from"]
        currency_to = txn["currency_to"]
        bank_details = txn.get("bank_details", "")
        rate = float(txn["rate"])
        receipt_id = txn.get("receipt_id")
        bill_url = txn.get("bill_url")

        # 🔍 Try to get bill_url from bucket based on filename
        if not bill_url:
            try:
                file_name = f"{invoice}_{user_id}.jpg"
                bill_url = supabase.storage.from_("bills").get_public_url(file_name)

                # Confirm it's accessible
                check = requests.get(bill_url)
                if check.status_code == 200:
                    supabase.table("transactions").update({"bill_url": bill_url}).eq("invoice", invoice).execute()
                else:
                    bill_url = None
            except Exception as e:
                print(f"⚠️ Couldn't find or save bill_url for {invoice}: {e}")
                bill_url = None

        # 🏷️ Caption + Buttons
        caption, markup = build_transaction_caption_and_markup(
            user_id, invoice, amount, currency_from, currency_to, rate, bank_details, receipt_id
        )

        # 🖼️ Send image if receipt_id works
        if receipt_id:
            try:
                bot.send_photo(message.chat.id, receipt_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
            except Exception as e:
                print(f"⚠️ Telegram-с зураг илгээж чадсангүй: {e}")
                if bill_url:
                    bot.send_message(message.chat.id, caption + f"\n📎 [Баримт харах]({bill_url})", parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.send_message(message.chat.id, caption + "\n⚠️ Баримтын зураг олдсонгүй.", parse_mode="Markdown", reply_markup=markup)
        else:
            if bill_url:
                bot.send_message(message.chat.id, caption + f"\n📎 [Баримт харах]({bill_url})", parse_mode="Markdown", reply_markup=markup)
            else:
                bot.send_message(message.chat.id, caption + "\n⚠️ Гүйлгээний баримт байхгүй байна.", parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(commands=["haih"])
def find_user_or_invoice(message):
    admin_id = message.from_user.id
    if admin_id not in ALLOWED_ADMINS:
        return bot.reply_to(message, "🚫 Зөвшөөрөлгүй хэрэглэгч байна.")

    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return bot.reply_to(message, "❌ Зөв формат: /haih <user_id|invoice_id>")

    query = args[1].strip()

    # 1) If it looks like an invoice (поддерживаем оба формата)
    if is_valid_invoice_format(query):
        invoice = query
        try:
            # Сначала ищем точное совпадение
            resp = supabase.table("transactions") \
                           .select("user_id") \
                           .eq("invoice", invoice) \
                           .limit(1).execute()
            
            # Если не найдено и это старый формат, попробуем найти в новом формате
            if not resp.data and re.fullmatch(r"\d{8}_\d{6}", invoice):
                normalized_invoice = normalize_invoice_format(invoice)
                if normalized_invoice:
                    resp = supabase.table("transactions") \
                                   .select("user_id") \
                                   .eq("invoice", normalized_invoice) \
                                   .limit(1).execute()
            
            # Если не найдено и это новый формат, попробуем найти в старом формате
            elif not resp.data and re.fullmatch(r"\d{8}-\d{6}-\d{2}", invoice):
                old_format = invoice.replace("-", "_")[:-3]  # YYYYMMDD-HHMMSS-XX -> YYYYMMDD_HHMMSS
                resp = supabase.table("transactions") \
                               .select("user_id") \
                               .eq("invoice", old_format) \
                               .limit(1).execute()
                               
        except Exception as e:
            print(f"❌ Supabase lookup error: {e}")
            return bot.reply_to(message, "❌ Дата хайх үед алдаа гарлаа.")

        if not resp.data:
            return bot.reply_to(message, f"❌ `{invoice}` дугаартай гүйлгээ олдсонгүй.", parse_mode="Markdown")

        target_id = resp.data[0]["user_id"]
        # fall through to the user-id branch
        query = str(target_id)

    # 2) Now if it’s numeric, treat as Telegram user ID
    if query.isdigit():
        user_id = int(query)
        try:
            user_info = bot.get_chat(user_id)
            full_name = user_info.first_name + (f" {user_info.last_name}" if user_info.last_name else "")
            user_link  = f"[{full_name}](tg://user?id={user_id})"
            username_link = f"[@{user_info.username}](https://t.me/{user_info.username})" if user_info.username else "— `Username байхгүй`"
            id_link = f"[{user_id}](tg://user?id={user_id})"

            text = f"👤 Хэрэглэгч олдлоо:\n\n" \
                   f"{user_link} — {username_link} — {id_link}"
            return bot.send_message(message.chat.id, text, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ User lookup error: {e}")
            return bot.reply_to(message, "❌ Хэрэглэгчийн мэдээллийг олж чадсангүй.")
    else:
        # neither invoice nor pure-digit
        return bot.reply_to(message, "❌ Зөв формат: /haih <user_id|invoice_id>")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_unknown_text(message):
    # only fire when we're not in the middle of a flow
    if not get_state(message.chat.id):
        bot.send_message(
            message.chat.id,
            "🕹️ Та */start* команд ашиглан үйлчилгээний цэснээс сонгон өөрт хэрэгтэй үйлчилгээгээ авна уу, эсвэл OYUNS SUPPORT чат руу хандаарай:\n"
            f"{CONTACT_SUPPORT}",
            parse_mode="Markdown"
        )


# 🏃 Run the Bot
bot.polling(none_stop=True)
