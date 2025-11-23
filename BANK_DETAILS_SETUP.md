# Bank Details Database Setup

This guide explains how to set up the database-based bank details system.

## Step 1: Run the SQL Migration

1. Go to your Supabase Dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of `database_setup.sql`
4. Click **Run** to execute the migration

This will:
- Create the `bank_details` table
- Insert initial bank data based on your Python bot configuration
- Set up indexes for performance
- Configure RLS policies

## Step 2: Verify the Data

Run this query to verify the data was inserted correctly:

```sql
SELECT admin_id, bank_key, bank_name, currency, is_active, display_order
FROM bank_details
ORDER BY admin_id, currency, display_order;
```

You should see bank details for all three admins (5564298862, 1932946217, 1409343588).

## Step 3: Update Bank Details

To update or add bank details, you can use the Supabase Dashboard or SQL:

### Add a new bank:

```sql
INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order)
VALUES (
    5564298862,  -- admin_id
    'vtbbank_rub',  -- bank_key (unique identifier)
    'ВТБ Банк',  -- Display name
    '🏦 *ВТБ*\n\nКартын дугаар: `1234 5678 9012 3456`\nУтасны дугаар: `+7 999 123 45 67`\nДансны нэр: *Нэр*',  -- Bank info (supports markdown)
    'rub',  -- currency: 'rub' or 'mnt'
    2  -- display_order (for sorting)
);
```

### Update existing bank:

```sql
UPDATE bank_details
SET bank_info = '🏦 *СБЕРБАНК*\n\nУтасны дугаар: `+7 999 685 74 63`\nДансны нэр: *Шинэ Нэр*',
    updated_at = NOW()
WHERE admin_id = 5564298862 
  AND bank_key = 'sberbank_rub'
  AND currency = 'rub';
```

### Deactivate a bank (instead of deleting):

```sql
UPDATE bank_details
SET is_active = false,
    updated_at = NOW()
WHERE admin_id = 5564298862 
  AND bank_key = 'old_bank_key'
  AND currency = 'rub';
```

## Step 4: RLS Policies

The migration includes a basic RLS policy that allows reading active bank details. If you need more restrictive policies:

```sql
-- Allow only authenticated users to read bank details
DROP POLICY IF EXISTS "Allow read active bank details" ON bank_details;

CREATE POLICY "Allow read active bank details" ON bank_details
FOR SELECT 
USING (is_active = true);
```

## Bank Info Format

The `bank_info` field supports Markdown formatting:
- `*text*` for bold
- `` `text` `` for code/inline code
- `\n` for new lines

Example:
```
🏦 *СБЕРБАНК*\n\nУтасны дугаар: `+7 999 685 74 63`\nДансны нэр: *Тэгшмагнай*
```

Will display as:
```
🏦 СБЕРБАНК

Утасны дугаар: +7 999 685 74 63
Дансны нэр: Тэгшмагнай
```

## Table Structure

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| admin_id | BIGINT | Telegram user ID of the admin |
| bank_key | TEXT | Unique identifier (e.g., "sberbank_rub") |
| bank_name | TEXT | Display name shown to users |
| bank_info | TEXT | Full bank details with formatting |
| currency | TEXT | 'rub' or 'mnt' |
| is_active | BOOLEAN | Whether this bank is currently active |
| display_order | INTEGER | Order for displaying banks (lower = first) |
| created_at | TIMESTAMP | When record was created |
| updated_at | TIMESTAMP | When record was last updated |

## Managing Bank Details via Supabase Dashboard

1. Go to **Table Editor** → `bank_details`
2. Click **Insert** to add new banks
3. Click on a row to edit existing banks
4. Use the filter to find banks by admin_id or currency

## Integration with Python Bot

You can also update bank details from your Python bot:

```python
def update_bank_details(admin_id, bank_key, bank_name, bank_info, currency, display_order=0):
    supabase.table("bank_details").upsert({
        "admin_id": admin_id,
        "bank_key": bank_key,
        "bank_name": bank_name,
        "bank_info": bank_info,
        "currency": currency,
        "display_order": display_order,
        "is_active": True,
        "updated_at": datetime.utcnow().isoformat()
    }).execute()
```

## Troubleshooting

### "Банкны мэдээлэл олдсонгүй"
- Check that `is_active = true` for the bank
- Verify `admin_id` matches current shift admin
- Check `currency` matches the exchange direction

### Banks not showing in correct order
- Check `display_order` values
- Lower numbers appear first
- Update `display_order` to reorder

### RLS Policy blocking reads
- Verify the RLS policy is enabled
- Check that the policy allows SELECT operations
- Test with: `SELECT * FROM bank_details WHERE is_active = true;`

