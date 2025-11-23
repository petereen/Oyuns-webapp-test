# Connect Mini App to Telegram Bot

This guide will help you connect your deployed Netlify Mini App to your Telegram bot.

## Step 1: Get Your Netlify URL

1. Go to your Netlify Dashboard: https://app.netlify.com
2. Click on your deployed site
3. Copy the site URL (it should look like: `https://your-site-name.netlify.app`)
4. **Important**: Make sure the URL uses `https://` (not `http://`)

## Step 2: Choose Connection Method

You have two options to connect the Mini App to your bot:

### Option A: Using BotFather (Easiest - Recommended)

1. Open Telegram and search for **@BotFather**
2. Send the command: `/setmenubutton`
3. BotFather will ask you to select a bot - choose your OYUNS AIO bot
4. BotFather will ask for the button text - send: `💱 Валют Солих`
5. BotFather will ask for the URL - send your Netlify URL (e.g., `https://your-site-name.netlify.app`)
6. BotFather will confirm: "Success! Menu button updated."

**Done!** Users will now see the button in your bot's menu.

### Option B: Programmatically (Python Bot)

Add this code to your `demo_bot_oyuns_aio.py` file:

```python
from telebot.types import MenuButtonWebApp, WebAppInfo

# Your Netlify URL
MINI_APP_URL = "https://your-site-name.netlify.app"  # Replace with your actual Netlify URL

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

# Add this right after bot initialization (around line 48)
# After: bot = telebot.TeleBot(BOT_TOKEN)
setup_mini_app_menu_button()
```

**Location**: Add this code after line 48 in your `demo_bot_oyuns_aio.py` file (right after `bot = telebot.TeleBot(BOT_TOKEN)`).

## Step 3: Add Optional Command Handler

You can also add a command that opens the Mini App directly. Add this to your bot:

```python
@bot.message_handler(commands=['webapp', 'app', 'mini'])
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
```

This allows users to type `/webapp`, `/app`, or `/mini` to open the Mini App.

## Step 4: Test the Connection

1. **Restart your Python bot** (if you used Option B)
2. Open your Telegram bot
3. Look for the menu button (☰) in the bottom left corner of the chat
4. Click it - you should see "💱 Валют Солих"
5. Click "💱 Валют Солих" - the Mini App should open

### Troubleshooting

**If the button doesn't appear:**
- Make sure you restarted the bot (if using Option B)
- Wait a few seconds and try again
- Check that the URL is correct and uses `https://`
- Verify the bot is running

**If the Mini App doesn't open:**
- Check that your Netlify site is live (visit the URL in a browser)
- Verify the URL is correct (no typos)
- Make sure the URL uses `https://` (required by Telegram)
- Check browser console for errors (if opened in browser)

**If you see "Telegram хэрэглэгчийн мэдээлэл олдсонгүй":**
- This is normal if you open the URL directly in a browser
- The Mini App must be opened from Telegram to get user info
- Test by opening it from the bot menu button

## Step 5: Verify Everything Works

1. ✅ Menu button appears in bot
2. ✅ Mini App opens when clicked
3. ✅ Exchange rates load
4. ✅ User verification check works
5. ✅ Can select exchange direction
6. ✅ Can enter amount
7. ✅ Bank selection works (for RUB → MNT)
8. ✅ Can upload receipt
9. ✅ Transaction is created in Supabase

## Step 6: Update Main Menu (Optional)

You can also add a button in your bot's main menu to open the Mini App. Update your `main_menu()` function:

```python
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📊 Ханш", callback_data="exchange_rate"),
        InlineKeyboardButton("ℹ️ Бот ашиглах заавар", callback_data="how_to_use"),
        InlineKeyboardButton("💱 Валют солих", callback_data="exchange_menu"),
        InlineKeyboardButton("📱 Mini App", web_app=WebAppInfo(url=MINI_APP_URL)),  # Add this
        InlineKeyboardButton("👤 Хэрэглэгчийн тохиргоо", callback_data="user_profile"),
        InlineKeyboardButton("✈️ Нислэг захиалга", callback_data="flight_booking"),
        InlineKeyboardButton("📝 Бүртгүүлэх", callback_data="start_registration")
    )
    return markup
```

## Important Notes

1. **HTTPS Required**: Telegram requires `https://` URLs for Mini Apps
2. **Domain Verification**: Netlify automatically provides HTTPS, so you're good!
3. **User Data**: The Mini App gets user info from Telegram automatically
4. **Transactions**: Transactions created in Mini App appear in your bot's `/guilgee` command
5. **Admin Notifications**: Your existing admin handlers will work with Mini App transactions

## Custom Domain (Optional)

If you want to use a custom domain:

1. Go to Netlify Dashboard → Site settings → Domain management
2. Add your custom domain
3. Update `MINI_APP_URL` in your bot code
4. Update the menu button via BotFather with the new URL

## Next Steps

After connecting:
- ✅ Test the full exchange flow
- ✅ Verify transactions appear in `/guilgee`
- ✅ Test admin approval/rejection
- ✅ Monitor for any errors
- ✅ Update bank details in Supabase if needed

## Support

If you encounter issues:
1. Check Netlify deployment logs
2. Check browser console (F12) when Mini App opens
3. Check your Python bot logs
4. Verify Supabase connection in Mini App
5. Test the Netlify URL directly in a browser

