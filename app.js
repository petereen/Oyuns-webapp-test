// Initialize Telegram Web App
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Initialize Supabase
let supabaseClient;
let currentUser = null;
let exchangeRates = { BUY_RATE: 0, SELL_RATE: 0 };
let currentDirection = 'rub_mnt';
let promoDiscount = 0;
let promoCode = null;
let selectedAmount = 0;
let selectedBank = null;
let currentInvoice = null;
let transactionData = {};

// App State
let currentScreen = 'loading';

// Initialize App
async function initApp() {
    try {
        // Initialize Supabase
        supabaseClient = supabase.createClient(SUPABASE_CONFIG.url, SUPABASE_CONFIG.anonKey);
        
        // Get Telegram user
        const tgUser = tg.initDataUnsafe?.user;
        if (!tgUser) {
            showError('Telegram хэрэглэгчийн мэдээлэл олдсонгүй');
            return;
        }
        
        currentUser = tgUser;
        
        // Check if user is verified
        await checkUserVerification();
        
        // Load exchange rates
        await loadExchangeRates();
        
        // Setup UI
        setupEventListeners();
        
        // Show main screen
        showScreen('main-screen');
        
    } catch (error) {
        console.error('Init error:', error);
        showError('Апп эхлүүлэхэд алдаа гарлаа');
    }
}

// Check user verification
async function checkUserVerification() {
    try {
        const { data, error } = await supabaseClient
            .from('users')
            .select('verified, agreed_terms')
            .eq('id', currentUser.id)
            .single();
        
        if (error && error.code !== 'PGRST116') {
            throw error;
        }
        
        if (!data) {
            // User doesn't exist, need to register
            tg.showAlert('Та эхлээд бүртгүүлэх ёстой. Telegram бот руу буцаж /register команд ашиглана уу.');
            tg.close();
            return;
        }
        
        if (!data.agreed_terms) {
            tg.showAlert('Та эхлээд хэрэглэгчийн гэрээг зөвшөөрөх ёстой.');
            tg.close();
            return;
        }
        
        if (!data.verified) {
            tg.showAlert('Таны бүртгэл баталгаажаагүй байна. Админ баталгаажуулах хүртэл хүлээнэ үү.');
            tg.close();
            return;
        }
        
    } catch (error) {
        console.error('Verification check error:', error);
        showError('Хэрэглэгчийн мэдээлэл шалгахад алдаа гарлаа');
    }
}

// Load exchange rates
async function loadExchangeRates() {
    try {
        const { data, error } = await supabaseClient
            .from('exchange_rates')
            .select('student_buy, student_sell')
            .order('id', { ascending: false })
            .limit(1)
            .single();
        
        if (error) throw error;
        
        exchangeRates.BUY_RATE = parseFloat(data.student_buy);
        exchangeRates.SELL_RATE = parseFloat(data.student_sell);
        
        // Update UI
        document.getElementById('buy-rate').textContent = `${exchangeRates.BUY_RATE} ₮`;
        document.getElementById('sell-rate').textContent = `${exchangeRates.SELL_RATE} ₮`;
        
    } catch (error) {
        console.error('Load rates error:', error);
        showError('Ханш ачаалахад алдаа гарлаа');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Direction buttons
    document.querySelectorAll('.direction-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.direction-btn').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            currentDirection = e.currentTarget.dataset.direction;
            updateCurrencyDisplay();
            updateQuickAmounts();
            clearAmount();
        });
    });
    
    // Amount input
    const amountInput = document.getElementById('amount-input');
    amountInput.addEventListener('input', handleAmountInput);
    
    // Promo code
    document.getElementById('apply-promo-btn').addEventListener('click', applyPromoCode);
    
    // Continue button
    document.getElementById('continue-btn').addEventListener('click', handleContinue);
    
    // Receipt upload
    document.getElementById('upload-receipt-btn').addEventListener('click', () => {
        document.getElementById('receipt-input').click();
    });
    
    document.getElementById('receipt-input').addEventListener('change', handleReceiptUpload);
    document.getElementById('submit-receipt-btn').addEventListener('click', submitReceipt);
    
    // Bank details
    document.getElementById('submit-bank-btn').addEventListener('click', submitBankDetails);
    document.getElementById('bank-details-input').addEventListener('input', (e) => {
        document.getElementById('submit-bank-btn').disabled = !e.target.value.trim();
    });
    
    // Upload area click
    document.getElementById('upload-area').addEventListener('click', () => {
        document.getElementById('receipt-input').click();
    });
}

// Update currency display
function updateCurrencyDisplay() {
    const currencyFrom = currentDirection === 'rub_mnt' ? 'RUB' : 'MNT';
    const currencyTo = currentDirection === 'rub_mnt' ? 'MNT' : 'RUB';
    document.getElementById('currency-from').textContent = currencyFrom;
}

// Update quick amount buttons
function updateQuickAmounts() {
    const amounts = currentDirection === 'rub_mnt' ? QUICK_AMOUNTS_RUB : QUICK_AMOUNTS_MNT;
    const container = document.getElementById('quick-amounts');
    container.innerHTML = amounts.map(amt => {
        const formatted = amt.toLocaleString('mn-MN');
        return `<button class="quick-amount-btn" onclick="selectQuickAmount(${amt})">${formatted}</button>`;
    }).join('');
}

// Select quick amount
function selectQuickAmount(amount) {
    document.getElementById('amount-input').value = amount;
    handleAmountInput({ target: { value: amount.toString() } });
}

// Clear amount
function clearAmount() {
    document.getElementById('amount-input').value = '';
    selectedAmount = 0;
    document.getElementById('exchange-preview').style.display = 'none';
    document.getElementById('continue-btn').disabled = true;
}

// Handle amount input
function handleAmountInput(e) {
    const value = parseFloat(e.target.value) || 0;
    selectedAmount = value;
    
    if (value > 0) {
        calculateExchange(value);
        document.getElementById('exchange-preview').style.display = 'block';
        document.getElementById('continue-btn').disabled = false;
    } else {
        document.getElementById('exchange-preview').style.display = 'none';
        document.getElementById('continue-btn').disabled = true;
    }
}

// Calculate exchange
function calculateExchange(amount) {
    const isRubToMnt = currentDirection === 'rub_mnt';
    const baseRate = isRubToMnt ? exchangeRates.BUY_RATE : exchangeRates.SELL_RATE;
    
    // Calculate volume discount
    let volDisc = 0;
    if (isRubToMnt) {
        if (amount >= MIN_VOLUME_RUB_2) {
            volDisc = VOLUME_DISCOUNT_MNT_2;
        } else if (amount >= MIN_VOLUME_RUB) {
            volDisc = VOLUME_DISCOUNT_MNT;
        }
    } else {
        const rubEquiv = amount / baseRate;
        if (rubEquiv >= MIN_VOLUME_RUB_2) {
            volDisc = VOLUME_DISCOUNT_MNT_2;
        } else if (rubEquiv >= MIN_VOLUME_RUB) {
            volDisc = VOLUME_DISCOUNT_MNT;
        }
    }
    
    // Apply best discount
    const bestDisc = Math.max(promoDiscount, volDisc);
    
    // Calculate final rate
    let finalRate;
    if (isRubToMnt) {
        finalRate = baseRate + bestDisc;
    } else {
        finalRate = baseRate - bestDisc;
    }
    finalRate = Math.max(finalRate, 0.01);
    
    // Calculate converted amount
    let converted;
    if (isRubToMnt) {
        converted = Math.round(amount * finalRate);
    } else {
        converted = Math.round((amount / finalRate) * 100) / 100;
    }
    
    // Check minimum for MNT → RUB
    if (!isRubToMnt) {
        const minMnt = Math.ceil(MIN_RUB * finalRate);
        if (amount < minMnt) {
            showError(`Доод хэмжээ: ${minMnt.toLocaleString('mn-MN')} MNT (${MIN_RUB.toLocaleString('mn-MN')} RUB)`);
            document.getElementById('continue-btn').disabled = true;
            return;
        }
    }
    
    // Update preview
    const currencyFrom = isRubToMnt ? 'RUB' : 'MNT';
    const currencyTo = isRubToMnt ? 'MNT' : 'RUB';
    
    document.getElementById('preview-from').textContent = `${amount.toLocaleString('mn-MN')} ${currencyFrom}`;
    document.getElementById('preview-to').textContent = `${converted.toLocaleString('mn-MN')} ${currencyTo}`;
    document.getElementById('preview-rate').textContent = `${finalRate.toFixed(2)} ₮`;
    
    // Store transaction data
    transactionData = {
        amount,
        currencyFrom: currencyFrom.toLowerCase(),
        currencyTo: currencyTo.toLowerCase(),
        rate: finalRate,
        converted
    };
}

// Apply promo code
async function applyPromoCode() {
    const promoInput = document.getElementById('promo-input');
    const code = promoInput.value.trim().toLowerCase();
    
    if (!code) {
        showError('Промокод оруулна уу');
        return;
    }
    
    try {
        const { data, error } = await supabaseClient
            .from('promo_codes')
            .select('code, aliases, discount')
            .eq('active', true);
        
        if (error) throw error;
        
        let discount = 0;
        for (const promo of data || []) {
            const validKeys = [promo.code.toLowerCase(), ...(promo.aliases || []).map(a => a.toLowerCase())];
            if (validKeys.includes(code)) {
                discount = parseFloat(promo.discount);
                promoCode = promo.code;
                break;
            }
        }
        
        if (discount > 0) {
            promoDiscount = discount;
            showError(`✅ Промокод амжилттай! Хөнгөлөлт: ${discount} MNT`, 'success');
            promoInput.value = '';
            if (selectedAmount > 0) {
                calculateExchange(selectedAmount);
            }
        } else {
            showError('❌ Буруу промокод');
        }
        
    } catch (error) {
        console.error('Promo code error:', error);
        showError('Промокод шалгахад алдаа гарлаа');
    }
}

// Handle continue button
async function handleContinue() {
    if (!selectedAmount || selectedAmount <= 0) {
        showError('Дүн оруулна уу');
        return;
    }
    
    // Generate invoice
    currentInvoice = generateInvoice();
    
    // If RUB → MNT, show bank selection
    if (currentDirection === 'rub_mnt') {
        await loadBankOptions();
        showScreen('bank-screen');
    } else {
        // MNT → RUB, show payment instructions
        await showPaymentInstructions();
        showScreen('payment-screen');
    }
}

// Generate invoice
function generateInvoice() {
    const now = new Date();
    const moscowTime = new Date(now.getTime() + (3 * 60 * 60 * 1000)); // UTC+3
    const randomSuffix = Math.floor(Math.random() * 100).toString().padStart(2, '0');
    return moscowTime.toISOString().slice(0, 10).replace(/-/g, '') + 
           '-' + 
           moscowTime.toTimeString().slice(0, 8).replace(/:/g, '') + 
           '-' + 
           randomSuffix;
}

// Load bank options (for RUB → MNT)
async function loadBankOptions() {
    try {
        // Get current admin shift config
        const { data: shiftData, error: shiftError } = await supabaseClient
            .from('admin_shifts')
            .select('current_admin_id')
            .eq('id', 1)
            .single();
        
        if (shiftError || !shiftData || !shiftData.current_admin_id) {
            showError('Одоогоор ээлж хаалттай байна');
            return;
        }
        
        const adminId = shiftData.current_admin_id;
        
        // Fetch bank options from database
        const { data: banksData, error: banksError } = await supabaseClient
            .from('bank_details')
            .select('bank_key, bank_name, bank_info')
            .eq('admin_id', adminId)
            .eq('currency', 'rub')
            .eq('is_active', true)
            .order('display_order', { ascending: true });
        
        if (banksError) {
            console.error('Load banks error:', banksError);
            showError('Банкны мэдээлэл ачаалахад алдаа гарлаа');
            return;
        }
        
        if (!banksData || banksData.length === 0) {
            showError('Одоогоор банкны мэдээлэл байхгүй байна');
            return;
        }
        
        // Store bank data for later use
        window.bankDetailsCache = {};
        banksData.forEach(bank => {
            window.bankDetailsCache[bank.bank_key] = bank.bank_info;
        });
        
        // Render bank list
        const container = document.getElementById('bank-list');
        container.innerHTML = banksData.map(bank => {
            // Escape HTML to prevent XSS
            const bankName = bank.bank_name.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const bankKey = bank.bank_key.replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return `
                <div class="bank-item" onclick="selectBank('${bankKey}', '${bankName}')">
                    <div class="bank-item-name">${bankName}</div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Load banks error:', error);
        showError('Банкны мэдээлэл ачаалахад алдаа гарлаа');
    }
}

// Select bank
async function selectBank(bankKey, bankName) {
    selectedBank = { key: bankKey, name: bankName };
    await showPaymentInstructions();
    showScreen('payment-screen');
}

// Show payment instructions
async function showPaymentInstructions() {
    try {
        // Get current admin shift config
        const { data: shiftData, error: shiftError } = await supabaseClient
            .from('admin_shifts')
            .select('current_admin_id')
            .eq('id', 1)
            .single();
        
        if (shiftError || !shiftData || !shiftData.current_admin_id) {
            showError('Одоогоор ээлж хаалттай байна');
            return;
        }
        
        const adminId = shiftData.current_admin_id;
        const currency = currentDirection === 'rub_mnt' ? 'rub' : 'mnt';
        
        let bankDetails;
        
        // If RUB → MNT and bank was selected, use cached bank info
        if (currentDirection === 'rub_mnt' && selectedBank && selectedBank.key) {
            // Check cache first
            if (window.bankDetailsCache && window.bankDetailsCache[selectedBank.key]) {
                bankDetails = window.bankDetailsCache[selectedBank.key];
            } else {
                // Fetch from database if not in cache
                const { data: bankData, error: bankError } = await supabaseClient
                    .from('bank_details')
                    .select('bank_info')
                    .eq('admin_id', adminId)
                    .eq('bank_key', selectedBank.key)
                    .eq('currency', currency)
                    .eq('is_active', true)
                    .single();
                
                if (bankError || !bankData) {
                    showError('Банкны мэдээлэл олдсонгүй');
                    return;
                }
                bankDetails = bankData.bank_info;
            }
        } else {
            // For MNT → RUB, fetch the MNT bank details
            const { data: bankData, error: bankError } = await supabaseClient
                .from('bank_details')
                .select('bank_info')
                .eq('admin_id', adminId)
                .eq('currency', currency)
                .eq('is_active', true)
                .order('display_order', { ascending: true })
                .limit(1)
                .single();
            
            if (bankError || !bankData) {
                showError('Банкны мэдээлэл олдсонгүй');
                return;
            }
            bankDetails = bankData.bank_info;
        }
        
        // Remove markdown formatting for display (or keep it if you want formatting)
        // For now, we'll display as plain text (you can enhance this to parse markdown)
        const plainBankDetails = bankDetails
            .replace(/\*([^*]+)\*/g, '$1')  // Remove bold
            .replace(/`([^`]+)`/g, '$1');   // Remove code
        
        document.getElementById('invoice-number').textContent = currentInvoice;
        document.getElementById('bank-details').textContent = plainBankDetails;
        document.getElementById('payment-amount').textContent = 
            `${transactionData.amount.toLocaleString('mn-MN')} ${transactionData.currencyFrom.toUpperCase()}`;
        
    } catch (error) {
        console.error('Show payment error:', error);
        showError('Мэдээлэл харуулахад алдаа гарлаа');
    }
}

// Handle receipt upload
function handleReceiptUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.type.startsWith('image/')) {
        showError('Зөвхөн зураг оруулна уу');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (event) => {
        const img = document.getElementById('receipt-preview');
        img.src = event.target.result;
        img.style.display = 'block';
        document.querySelector('.upload-placeholder').style.display = 'none';
        document.getElementById('submit-receipt-btn').disabled = false;
    };
    reader.readAsDataURL(file);
}

// Submit receipt
async function submitReceipt() {
    const fileInput = document.getElementById('receipt-input');
    const file = fileInput.files[0];
    
    if (!file) {
        showError('Зураг сонгоно уу');
        return;
    }
    
    try {
        tg.showPopup({
            title: 'Уншиж байна...',
            message: 'Баримтын зургийг хадгалж байна',
            buttons: [{ type: 'ok' }]
        });
        
        // Upload to Supabase storage
        const fileName = `${currentInvoice}_${currentUser.id}.jpg`;
        const { data: uploadData, error: uploadError } = await supabaseClient.storage
            .from('bills')
            .upload(fileName, file, {
                contentType: 'image/jpeg',
                upsert: true
            });
        
        if (uploadError) throw uploadError;
        
        // Get public URL
        const { data: urlData } = supabaseClient.storage
            .from('bills')
            .getPublicUrl(fileName);
        
        // Get file ID from Telegram (we'll need to send it to bot or store differently)
        // For now, we'll use the file name
        
        // Update transaction with receipt
        const { error: updateError } = await supabase
            .from('transactions')
            .update({
                bill_id: fileName,
                receipt_id: fileName,
                bill_url: urlData.publicUrl
            })
            .eq('invoice', currentInvoice);
        
        if (updateError) throw updateError;
        
        // Move to bank details screen
        checkSavedBank();
        showScreen('bank-details-screen');
        
    } catch (error) {
        console.error('Submit receipt error:', error);
        showError('Баримт илгээхэд алдаа гарлаа');
    }
}

// Check if user has saved bank
async function checkSavedBank() {
    try {
        const { data, error } = await supabaseClient
            .from('users')
            .select('bank_mnt, bank_rub')
            .eq('id', currentUser.id)
            .single();
        
        if (error) throw error;
        
        const bankField = currentDirection === 'rub_mnt' ? 'bank_mnt' : 'bank_rub';
        const hasSavedBank = data[bankField] && data[bankField].trim();
        
        if (hasSavedBank) {
            document.getElementById('saved-bank-option').style.display = 'block';
        }
        
        // Update format info
        const formatInfo = currentDirection === 'rub_mnt'
            ? 'Банк, Утасны дугаар, Картын дугаар, Карт эзэмшэгчийн нэр'
            : 'Банк, IBAN дансны дугаар, Данс эзэмшэгчийн нэр';
        
        document.getElementById('bank-format-info').textContent = 
            `Та өөрийн дансны мэдээллийг дараах форматаар оруулна уу:\n${formatInfo}`;
        
    } catch (error) {
        console.error('Check saved bank error:', error);
    }
}

// Use saved bank
async function useSavedBank() {
    try {
        const { data, error } = await supabaseClient
            .from('users')
            .select('bank_mnt, bank_rub')
            .eq('id', currentUser.id)
            .single();
        
        if (error) throw error;
        
        const bankField = currentDirection === 'rub_mnt' ? 'bank_mnt' : 'bank_rub';
        const bankInfo = data[bankField];
        
        if (!bankInfo) {
            showError('Хадгалсан дансны мэдээлэл олдсонгүй');
            return;
        }
        
        document.getElementById('bank-details-input').value = bankInfo;
        document.getElementById('submit-bank-btn').disabled = false;
        
    } catch (error) {
        console.error('Use saved bank error:', error);
        showError('Хадгалсан дансны мэдээлэл авахад алдаа гарлаа');
    }
}

// Submit bank details
async function submitBankDetails() {
    const bankDetails = document.getElementById('bank-details-input').value.trim();
    
    if (!bankDetails) {
        showError('Дансны мэдээлэл оруулна уу');
        return;
    }
    
    // Validate format
    const expectedFields = currentDirection === 'rub_mnt' ? 4 : 3;
    const parts = bankDetails.split(',').map(p => p.trim());
    
    if (parts.length !== expectedFields || parts.some(p => !p)) {
        showError(`Формат буруу. ${expectedFields} талбар шаардлагатай`);
        return;
    }
    
    try {
        // Create transaction
        const { error: txnError } = await supabase
            .from('transactions')
            .insert({
                user_id: currentUser.id,
                invoice: currentInvoice,
                amount: transactionData.amount,
                currency_from: transactionData.currencyFrom,
                currency_to: transactionData.currencyTo,
                rate: transactionData.rate,
                buy_rate: exchangeRates.BUY_RATE,
                sell_rate: exchangeRates.SELL_RATE,
                bank_details: bankDetails,
                status: 'pending',
                promo_code: promoCode,
                timestamp: new Date().toISOString()
            });
        
        if (txnError) throw txnError;
        
        // Show success
        showScreen('success-screen');
        
        // Notify via bot (you may want to implement a webhook or API call here)
        
    } catch (error) {
        console.error('Submit bank details error:', error);
        showError('Гүйлгээ бүртгэхэд алдаа гарлаа');
    }
}

// Screen navigation
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
    currentScreen = screenId;
}

function goBack() {
    if (currentScreen === 'bank-screen') {
        showScreen('main-screen');
    } else if (currentScreen === 'payment-screen') {
        if (currentDirection === 'rub_mnt') {
            showScreen('bank-screen');
        } else {
            showScreen('main-screen');
        }
    } else if (currentScreen === 'receipt-screen') {
        showScreen('payment-screen');
    } else if (currentScreen === 'bank-details-screen') {
        showScreen('receipt-screen');
    }
}

function resetApp() {
    currentDirection = 'rub_mnt';
    promoDiscount = 0;
    promoCode = null;
    selectedAmount = 0;
    selectedBank = null;
    currentInvoice = null;
    transactionData = {};
    
    document.getElementById('amount-input').value = '';
    document.getElementById('promo-input').value = '';
    document.getElementById('receipt-input').value = '';
    document.getElementById('bank-details-input').value = '';
    document.getElementById('receipt-preview').style.display = 'none';
    document.querySelector('.upload-placeholder').style.display = 'block';
    
    updateCurrencyDisplay();
    updateQuickAmounts();
    showScreen('main-screen');
}

// Error handling
function showError(message, type = 'error') {
    const toast = document.getElementById('error-toast');
    const messageEl = document.getElementById('error-message');
    
    messageEl.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

