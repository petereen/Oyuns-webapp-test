# Implementation Notes

## What Has Been Created

A complete Telegram Mini App (Web App) for the OYUNS AIO currency exchange bot. The app provides a modern, user-friendly interface for exchanging RUB ↔ MNT currencies.

## Files Created

1. **index.html** - Main HTML structure with all screens
2. **styles.css** - Modern styling matching Telegram's design language
3. **app.js** - Complete application logic with Supabase integration
4. **config.js** - Configuration file for Supabase and constants
5. **README.md** - Comprehensive documentation
6. **SETUP.md** - Quick setup guide
7. **bot_integration_example.py** - Example code for integrating with Python bot

## Key Features Implemented

✅ User verification check  
✅ Real-time exchange rates display  
✅ Direction selection (RUB→MNT / MNT→RUB)  
✅ Promo code support  
✅ Quick amount buttons  
✅ Custom amount input  
✅ Volume discount calculation  
✅ Bank selection (for RUB→MNT)  
✅ Payment instructions display  
✅ Receipt photo upload  
✅ Bank details input with saved bank option  
✅ Transaction creation in Supabase  
✅ Success screen  

## Important: Bank Details Implementation

The bank details are currently **simplified/placeholder**. You need to implement one of these options:

### Option 1: Store in Supabase Table (Recommended)

Create a `bank_details` table:

```sql
CREATE TABLE bank_details (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT,
    bank_key TEXT,
    bank_name TEXT,
    bank_info TEXT,
    currency TEXT CHECK (currency IN ('rub', 'mnt')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert bank details
INSERT INTO bank_details (admin_id, bank_key, bank_name, bank_info, currency) VALUES
(5564298862, 'sberbank_rub', 'Сбербанк', '🏦 СБЕРБАНК\n\nУтасны дугаар: +7 999 685 74 63\nДансны нэр: Тэгшмагнай', 'rub'),
(1409343588, 'sberbank_rub2', 'Сбербанк 1', '🏦 СБЕРБАНК\n\nКартын дугаар: 2202 2084 1034 6242\nУтасны дугаар: +7 996 437 18 92\nДансны нэр: Анужин', 'rub'),
(1409343588, 'bank_mnt', 'Хаан Банк', '🏦 ХААН БАНК\n\nДансны нэр: Амгаланбаатар\nДанс: MN82000500 5314497192', 'mnt');
```

Then update `showPaymentInstructions()` in `app.js`:

```javascript
async function showPaymentInstructions() {
    try {
        const { data: shiftData } = await supabaseClient
            .from('admin_shifts')
            .select('current_admin_id')
            .eq('id', 1)
            .single();
        
        if (!shiftData || !shiftData.current_admin_id) {
            showError('Одоогоор ээлж хаалттай байна');
            return;
        }
        
        const adminId = shiftData.current_admin_id;
        const currency = currentDirection === 'rub_mnt' ? 'rub' : 'mnt';
        
        // Get bank details from database
        const { data: bankData, error } = await supabaseClient
            .from('bank_details')
            .select('bank_info')
            .eq('admin_id', adminId)
            .eq('currency', currency)
            .eq('is_active', true)
            .limit(1)
            .single();
        
        if (error || !bankData) {
            showError('Банкны мэдээлэл олдсонгүй');
            return;
        }
        
        document.getElementById('invoice-number').textContent = currentInvoice;
        document.getElementById('bank-details').textContent = bankData.bank_info;
        document.getElementById('payment-amount').textContent = 
            `${transactionData.amount.toLocaleString('mn-MN')} ${transactionData.currencyFrom.toUpperCase()}`;
        
    } catch (error) {
        console.error('Show payment error:', error);
        showError('Мэдээлэл харуулахад алдаа гарлаа');
    }
}
```

### Option 2: Create API Endpoint

Create a simple API endpoint that returns bank details based on admin_id and currency. Then fetch from that endpoint in the Mini App.

### Option 3: Use Python Bot's Config

If you prefer to keep bank details in the Python bot, you can:
1. Create a simple API endpoint in your Python bot
2. Or use Supabase Edge Functions
3. Or store the config in Supabase and fetch it

## Admin Notifications

Currently, the Mini App creates transactions directly in Supabase. Your existing Python bot handlers (`confirm_`, `reject_`) will still work because they query Supabase.

However, you may want to add real-time notifications when transactions are created from the Mini App. Options:

1. **Supabase Realtime**: Subscribe to transaction inserts
2. **Webhook**: Create a webhook endpoint that the Mini App calls
3. **Polling**: Python bot polls for new transactions (less efficient)

## Testing Checklist

- [ ] Supabase connection works
- [ ] User verification check works
- [ ] Exchange rates load correctly
- [ ] Direction selection works
- [ ] Promo codes work
- [ ] Amount calculation is correct
- [ ] Bank selection works (RUB→MNT)
- [ ] Payment instructions show correct bank details
- [ ] Receipt upload works
- [ ] Bank details submission works
- [ ] Transaction is created in Supabase
- [ ] Python bot can see and process the transaction

## Known Limitations

1. **Bank Details**: Currently simplified - needs proper implementation (see above)
2. **Admin Notifications**: No real-time notification when Mini App creates transaction
3. **Receipt File ID**: Currently using filename instead of Telegram file_id (may need adjustment)
4. **Error Handling**: Some edge cases may need additional handling
5. **Offline Support**: No offline mode or caching

## Future Enhancements

- [ ] Real-time transaction status updates
- [ ] Transaction history view
- [ ] Push notifications
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Receipt image compression
- [ ] Better error messages
- [ ] Loading states for all async operations
- [ ] Form validation improvements
- [ ] Accessibility improvements

## Security Considerations

1. ✅ Using Supabase anon key (public key) - safe for client-side
2. ✅ RLS policies should restrict data access
3. ⚠️ Bank details should be validated on server side
4. ⚠️ Transaction amounts should be validated on server side
5. ⚠️ Receipt images should be validated (size, format)
6. ⚠️ User verification should be double-checked on server

## Support

If you encounter issues:
1. Check browser console for errors
2. Check Supabase logs
3. Verify RLS policies
4. Verify Supabase credentials
5. Check network requests in browser DevTools

