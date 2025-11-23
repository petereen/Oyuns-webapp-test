# Integration code for your Telegram bot
# Add this to your demo_bot_oyuns_aio.py file

from telebot.types import MenuButtonWebApp, WebAppInfo

# ⚠️ IMPORTANT: Replace with your actual Netlify URL
MINI_APP_URL = "https://earnest-brigadeiros-a41706.netlify.app/"  # 👈 CHANGE THIS!

def setup_mini_app_menu_button():
    """
    Set up the menu button for the Mini App.
    Call this after bot initialization.
    """
    try:
        bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="💱 Валют Солих",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )
        print("✅ Mini App menu button set successfully")
    except Exception as e:
        print(f"❌ Failed to set menu button: {e}")

# ============================================
# INSTRUCTIONS:
# ============================================
# 1. Copy the MINI_APP_URL and setup_mini_app_menu_button() function above
# 2. Add them to your demo_bot_oyuns_aio.py file
# 3. Replace MINI_APP_URL with your actual Netlify URL
# 4. Call setup_mini_app_menu_button() right after bot initialization
#    (after line 48: bot = telebot.TeleBot(BOT_TOKEN))
# ============================================

# Optional: Add command to open Mini App
@bot.message_handler(commands=['webapp', 'app', 'mini'])
def open_mini_app(message):
    """
    Command to open the Mini App directly.
    Users can type /webapp, /app, or /mini to open the Mini App.
    """
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(
        "💱 Валют Солих - Mini App",
        web_app=WebAppInfo(url=MINI_APP_URL)
    ))
    bot.send_message(
        message.chat.id,
        "📱 Mini App-ийг нээх бол доорх товчийг дарна уу:",
        reply_markup=markup
    )

# Optional: Add button to main menu
# Update your main_menu() function to include:
# InlineKeyboardButton("📱 Mini App", web_app=WebAppInfo(url=MINI_APP_URL))

