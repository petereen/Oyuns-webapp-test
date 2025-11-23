# OYUNS AIO Telegram Mini App

This is a Telegram Mini App (Web App) for the OYUNS AIO currency exchange bot. It provides a modern, user-friendly interface for exchanging RUB ↔ MNT currencies.

## Features

- 💱 Real-time exchange rates display
- 🇷🇺 RUB → MNT exchange
- 🇲🇳 MNT → RUB exchange
- 🎟️ Promo code support
- 💰 Quick amount selection
- 📸 Receipt photo upload
- 🏦 **Database-based bank details** (flexible, admin-specific)
- ✅ Transaction tracking

## Setup Instructions

### 1. Update Supabase Configuration

Edit `config.js` and update the Supabase credentials:

```javascript
const SUPABASE_CONFIG = {
    url: "YOUR_SUPABASE_URL",
    anonKey: "YOUR_SUPABASE_ANON_KEY"
};
```

**Important**: You need to use the `anon` (public) key, not the `service_role` key. Make sure your Supabase Row Level Security (RLS) policies allow:
- Reading from `exchange_rates` table
- Reading from `users` table (for current user)
- Reading from `promo_codes` table
- Inserting into `transactions` table (for current user)
- Uploading to `bills` storage bucket

### 2. Set Up Bank Details Database

1. Go to **SQL Editor** in Supabase Dashboard
2. Run the `database_setup.sql` file to create the `bank_details` table
3. This will populate initial bank data based on your Python bot configuration
4. See `BANK_DETAILS_SETUP.md` for detailed instructions

### 3. Configure Supabase RLS Policies

You'll need to set up RLS policies in Supabase. Here are the recommended policies:

#### For `exchange_rates` table:
```sql
-- Allow anyone to read latest exchange rates
CREATE POLICY "Allow read exchange rates" ON exchange_rates
FOR SELECT USING (true);
```

#### For `users` table:
```sql
-- Users can only read their own data
CREATE POLICY "Users can read own data" ON users
FOR SELECT USING (auth.uid() = id::text);
```

#### For `transactions` table:
```sql
-- Users can insert their own transactions
CREATE POLICY "Users can insert own transactions" ON transactions
FOR INSERT WITH CHECK (auth.uid() = user_id::text);

-- Users can read their own transactions
CREATE POLICY "Users can read own transactions" ON transactions
FOR SELECT USING (auth.uid() = user_id::text);
```

#### For `promo_codes` table:
```sql
-- Allow reading active promo codes
CREATE POLICY "Allow read active promo codes" ON promo_codes
FOR SELECT USING (active = true);
```

#### For `bank_details` table:
```sql
-- Allow reading active bank details
CREATE POLICY "Allow read active bank details" ON bank_details
FOR SELECT USING (is_active = true);
```

#### For Storage (`bills` bucket):
- Allow authenticated users to upload files
- Allow users to read their own files

### 4. Deploy the Web App

You can deploy this Mini App to any static hosting service:

- **Vercel**: `vercel deploy`
- **Netlify**: Drag and drop the folder
- **GitHub Pages**: Push to a repository and enable Pages
- **Any static host**: Upload the files

### 5. Set Up Telegram Bot

In your Telegram bot, you need to:

1. Set the web app URL using BotFather:
   ```
   /setmenubutton
   ```
   Then set the button text and URL to your deployed web app.

2. Or add a menu button programmatically in your Python bot:
   ```python
   from telebot.types import MenuButtonWebApp, WebAppInfo
   
   bot.set_chat_menu_button(
       menu_button=MenuButtonWebApp(
           text="💱 Валют Солих",
           web_app=WebAppInfo(url="https://your-domain.com")
       )
   )
   ```

### 6. Bank Details Management

Bank details are now stored in the `bank_details` table in Supabase. To update:

1. Use Supabase Dashboard → Table Editor → `bank_details`
2. Or use SQL queries (see `BANK_DETAILS_SETUP.md`)
3. Or update from your Python bot using the Supabase client

The system automatically:
- Fetches banks based on current admin shift
- Shows only active banks (`is_active = true`)
- Orders banks by `display_order`
- Caches bank details for performance

## File Structure

```
.
├── index.html          # Main HTML structure
├── styles.css          # Styling
├── app.js             # Main application logic
├── config.js           # Configuration (Supabase credentials, constants)
└── README.md          # This file
```

## How It Works

1. **User Authentication**: The app uses Telegram Web App SDK to get user information
2. **Verification Check**: Checks if user is registered and verified in Supabase
3. **Exchange Flow**:
   - User selects direction (RUB→MNT or MNT→RUB)
   - Optionally enters promo code
   - Enters or selects amount
   - For RUB→MNT: Selects bank
   - Views payment instructions
   - Uploads receipt photo
   - Enters bank details
   - Transaction is created in Supabase
4. **Notifications**: The Python bot should handle notifications to admins (you may need to add webhooks or polling)

## Integration with Python Bot

The Mini App works alongside your Python bot:

- **User Registration/Verification**: Still handled by the bot
- **Exchange Transactions**: Can be initiated from either the bot or the Mini App
- **Admin Operations**: Still handled by the bot
- **Notifications**: Bot receives transaction notifications and handles admin workflows

## Security Notes

1. **Never expose service_role key** in client-side code
2. **Use RLS policies** to restrict data access
3. **Validate all inputs** on the server side (Python bot)
4. **Sanitize user inputs** before storing in database
5. **Use HTTPS** for all deployments

## Troubleshooting

### "Telegram хэрэглэгчийн мэдээлэл олдсонгүй"
- Make sure the app is opened from Telegram, not a regular browser
- Check that Telegram Web App SDK is loaded correctly

### "Ханш ачаалахад алдаа гарлаа"
- Check Supabase connection
- Verify RLS policies allow reading exchange_rates
- Check network tab for specific error

### "Гүйлгээ бүртгэхэд алдаа гарлаа"
- Verify RLS policies allow inserting transactions
- Check that all required fields are provided
- Verify user_id matches Telegram user ID

## Future Enhancements

- [ ] Real-time transaction status updates
- [ ] Transaction history view
- [ ] Push notifications for transaction status
- [ ] Multi-language support
- [ ] Dark mode support
- [ ] Offline mode with sync
- [ ] Receipt image compression
- [ ] Bank details auto-fill from saved profile

## License

Same as the main OYUNS AIO bot project.

# Oyuns-webapp-test
