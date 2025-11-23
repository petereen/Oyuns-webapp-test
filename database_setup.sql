-- Create bank_details table for storing bank account information
CREATE TABLE IF NOT EXISTS bank_details (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    bank_key TEXT NOT NULL,  -- e.g., "sberbank_rub", "alphabank_rub1", "bank_mnt"
    bank_name TEXT NOT NULL,  -- Display name, e.g., "Сбербанк", "Альфа 1"
    bank_info TEXT NOT NULL,  -- Full bank details with formatting
    currency TEXT NOT NULL CHECK (currency IN ('rub', 'mnt')),
    is_active BOOLEAN DEFAULT true,
    display_order INTEGER DEFAULT 0,  -- For ordering banks in the list
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(admin_id, bank_key, currency)  -- Prevent duplicates
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_bank_details_admin_currency ON bank_details(admin_id, currency, is_active);

-- Insert bank details based on Python bot configuration
-- Admin 5564298862
INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(5564298862, 'sberbank_rub', 'Сбербанк', 
'🏦 *СБЕРБАНК*\n\nУтасны дугаар: `+7 999 685 74 63`\nДансны нэр: *Тэгшмагнай*', 
'rub', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(5564298862, 'bank_mnt', 'Хаан Банк', 
'🏦 *ХААН БАНК*\n\nДансны нэр: *Амгаланбаатар*\nДанс: `MN59000500 5314495763`', 
'mnt', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

-- Admin 1932946217
INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1932946217, 'alphabank_rub2', 'Альфа 1', 
'🏦 *АЛЬФА БАНК*\n\nКартын дугаар: `2200 1529 9148 7847`\nУтасны дугаар: `+7 999 642 63 28`\nДансны нэр: *Ачитбаатар*', 
'rub', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1932946217, 'alphabank_rub1', 'Альфа 2', 
'🏦 *АЛЬФА БАНК*\n\nКартын дугаар: `2200 1529 0483 3053`\nУтасны дугаар: `+7 950 096 92 87`\nДансны нэр: *Тувшинжаргал Мунхзаяа*', 
'rub', 2)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1932946217, 'bank_mnt', 'Хаан Банк', 
'🏦 *ХААН БАНК*\n\nДансны нэр: *Амгаланбаатар*\nДанс: `MN82000500 5314497192`', 
'mnt', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

-- Admin 1409343588
INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1409343588, 'sberbank_rub2', 'Сбербанк 1', 
'🏦 *СБЕРБАНК*\n\nКартын дугаар: `2202 2084 1034 6242`\nУтасны дугаар: `+7 996 437 18 92`\nДансны нэр: *Анужин*', 
'rub', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1409343588, 'sberbank_rub1', 'Сбербанк 2', 
'🏦 *СБЕРБАНК*\n\nКартын дугаар: `2202 2063 0354 3297`\nУтасны дугаар: `+7 999 686 78 93`\nДансны нэр: *Анударь*', 
'rub', 2)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1409343588, 'alphabank_rub1', 'Альфа 1', 
'🏦 *АЛЬФА БАНК*\n\nКартын дугаар: `2200 1529 0483 3053`\nУтасны дугаар: `+7 950 096 92 87`\nДансны нэр: *Тувшинжаргал Мунхзаяа*', 
'rub', 3)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1409343588, 'alphabank_rub2', 'Альфа 2', 
'🏦 *АЛЬФА БАНК*\n\nКартын дугаар: `2200 1529 9148 7847`\nУтасны дугаар: `+7 999 642 63 28`\nДансны нэр: *Ачитбаатар*', 
'rub', 4)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency, display_order) VALUES
(1409343588, 'bank_mnt', 'Хаан Банк', 
'🏦 *ХААН БАНК*\n\nДансны нэр: *Амгаланбаатар*\nДанс: `MN82000500 5314497192`', 
'mnt', 1)
ON CONFLICT (admin_id, bank_key, currency) DO UPDATE SET bank_info = EXCLUDED.bank_info;

-- RLS Policy: Allow reading bank details for active banks
CREATE POLICY "Allow read active bank details" ON bank_details
FOR SELECT USING (is_active = true);

-- Optional: Allow admins to manage their own bank details
-- CREATE POLICY "Admins can manage own bank details" ON bank_details
-- FOR ALL USING (admin_id = auth.uid()::bigint);

