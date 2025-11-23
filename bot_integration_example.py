# Example: How to integrate the Mini App with your Python bot
# Add this to your demo_bot_oyuns_aio.py file

from telebot.types import MenuButtonWebApp, WebAppInfo

# Your deployed Mini App URL
MINI_APP_URL = "https://fblvzsxuyamfvgrfcstj.supabase.co"  # Replace with your actual URL

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

# Add this to your main bot initialization (after bot = telebot.TeleBot(BOT_TOKEN))
# setup_mini_app_menu_button()

# Optional: Add a command to open the Mini App
@bot.message_handler(commands=['webapp', 'app'])
def open_mini_app(message):
    """
    Command to open the Mini App directly.
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

# Note: The Mini App will create transactions in Supabase directly.
# Your existing admin handlers (confirm_, reject_) will still work
# because they query Supabase for pending transactions.
# 
# However, you may want to add a webhook or polling mechanism
# to notify admins when new transactions are created from the Mini App.
#
# Example webhook handler (if you set up a webhook endpoint):
#
# @app.route('/webhook/mini-app-transaction', methods=['POST'])
# def handle_mini_app_transaction():
#     data = request.json
#     invoice = data.get('invoice')
#     user_id = data.get('user_id')
#     
#     # Notify admin (similar to notify_operator function)
#     # ... your notification logic here
#     
#     return jsonify({'status': 'ok'})

