# Quick Setup Guide

## Step 1: Get Supabase Anon Key

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **API**
4. Copy the **anon/public** key (NOT the service_role key)
5. Paste it in `config.js`:

```javascript
const SUPABASE_CONFIG = {
    url: "https://fblvzsxuyamfvgrfcstj.supabase.co",
    anonKey: "PASTE_YOUR_ANON_KEY_HERE"
};
```

## Step 2: Set Up Bank Details Database

1. Go to **SQL Editor** in Supabase Dashboard
2. Run the `database_setup.sql` file (see BANK_DETAILS_SETUP.md for details)
3. This creates the `bank_details` table and populates it with initial data

## Step 3: Configure Supabase RLS Policies

Run these SQL commands in your Supabase SQL Editor:

```sql
-- Allow reading exchange rates
CREATE POLICY "Allow read exchange rates" ON exchange_rates
FOR SELECT USING (true);

-- Allow users to read their own user data
CREATE POLICY "Users can read own data" ON users
FOR SELECT USING (true); -- Adjust based on your auth setup

-- Allow users to insert their own transactions
CREATE POLICY "Users can insert own transactions" ON transactions
FOR INSERT WITH CHECK (true); -- You may want to add user_id validation

-- Allow reading active promo codes
CREATE POLICY "Allow read active promo codes" ON promo_codes
FOR SELECT USING (active = true);

-- Allow reading admin shifts
CREATE POLICY "Allow read admin shifts" ON admin_shifts
FOR SELECT USING (true);

-- Allow reading active bank details
CREATE POLICY "Allow read active bank details" ON bank_details
FOR SELECT USING (is_active = true);
```

## Step 3: Configure Storage Bucket

1. Go to **Storage** in Supabase Dashboard
2. Create or select the `bills` bucket
3. Set it to **Public** or configure policies:

```sql
-- Allow authenticated users to upload
CREATE POLICY "Users can upload bills" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'bills');

-- Allow users to read their own files
CREATE POLICY "Users can read own bills" ON storage.objects
FOR SELECT USING (bucket_id = 'bills');
```

## Step 4: Deploy

### Option A: Vercel (Recommended)

1. Install Vercel CLI: `npm i -g vercel`
2. Run: `vercel`
3. Follow the prompts
4. Copy the deployment URL

### Option B: Netlify

1. Go to https://app.netlify.com
2. Drag and drop the project folder
3. Copy the deployment URL

### Option C: GitHub Pages

1. Create a GitHub repository
2. Push your code
3. Go to Settings → Pages
4. Select source branch
5. Copy the GitHub Pages URL

## Step 5: Connect to Telegram Bot

### Using BotFather:

1. Open BotFather in Telegram
2. Send `/setmenubutton`
3. Select your bot
4. Set button text: `💱 Валют Солих`
5. Set URL: `https://your-deployed-url.com`

### Or in your Python bot code:

Add this to your bot initialization:

```python
from telebot.types import MenuButtonWebApp, WebAppInfo

# After bot initialization
bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="💱 Валют Солих",
        web_app=WebAppInfo(url="https://your-deployed-url.com")
    )
)
```

## Step 6: Update Bank Details

The bank details are currently simplified. You need to:

1. **Option A**: Store bank details in a Supabase table and fetch them
2. **Option B**: Create an API endpoint that returns bank details
3. **Option C**: Update the `showPaymentInstructions()` function in `app.js` to fetch from your database

Example for Option A - Create a `bank_details` table:

```sql
CREATE TABLE bank_details (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT,
    bank_key TEXT,
    bank_name TEXT,
    bank_info TEXT,
    currency TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Then update `app.js` to fetch from this table.

## Testing

1. Open your Telegram bot
2. Click the menu button or send `/start` and click the web app button
3. The Mini App should open
4. Test the exchange flow

## Troubleshooting

### "Telegram хэрэглэгчийн мэдээлэл олдсонгүй"
- Make sure you're opening from Telegram, not a browser
- Check browser console for errors

### "Ханш ачаалахад алдаа гарлаа"
- Verify Supabase URL and anon key are correct
- Check RLS policies are set up
- Check browser console for specific error

### CORS Errors
- Make sure your Supabase project allows requests from your domain
- Check Supabase Dashboard → Settings → API → CORS settings

### Storage Upload Fails
- Verify storage bucket exists and is named `bills`
- Check storage policies allow uploads
- Verify file size limits (default is 50MB)

