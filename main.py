import os
import asyncio
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, CopyTextButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

MK_API_KEY = "2c237a7e888476faed46f6f2"
BASE_API_URL = "https://mknetworkbd.com/api/v2/public"
SUPPORT_USERNAME = "tmtamimmia"
OTP_GROUP_CHAT_ID = -1004436883235

USER_STATES = {}
USER_RANGES = {}
USER_BALANCES = {}  
USER_WITHDRAW_INFO = {} 
ACTIVE_USER_NUMBERS = {} 

PANEL_LIVE_RANGES = [
    {"country": "Libya", "operator": "Mobily", "range": "2189", "status": "Idle"},
    {"country": "Madagascar", "operator": "Telma", "range": "2613", "status": "Idle"},
    {"country": "Nepal", "operator": "MTN", "range": "97797", "status": "Idle"},
    {"country": "Norway", "operator": "Telenor", "range": "h1den", "status": "Idle"},
    {"country": "Sudan", "operator": "Mobily", "range": "2491", "status": "Good"},
    {"country": "Sudan", "operator": "Mobily", "range": "249126", "status": "Idle"},
    {"country": "Sudan", "operator": "Zain", "range": "249127", "status": "Idle"},
    {"country": "Uzbekistan", "operator": "Ucell Mobile", "range": "998", "status": "Idle"},
    {"country": "Zambia", "operator": "Zamtel", "range": "260", "status": "Good"}
]

def get_country_info(phone_number, api_country=""):
    if api_country and api_country.lower() != "other":
        return api_country, "INT", "🌍"
    clean_num = str(phone_number).replace("+", "").strip()
    if clean_num.startswith("880"): return "Bangladesh", "BD", "🇧🇩"
    elif clean_num.startswith("237"): return "Cameroon", "CM", "🇨🇲"
    elif clean_num.startswith("225"): return "Ivory Coast", "CI", "🇨🇮"
    elif clean_num.startswith("228"): return "Togo", "TG", "🇹🇬"
    elif clean_num.startswith("261"): return "Madagascar", "MG", "🇲🇬"
    elif clean_num.startswith("218"): return "Libya", "LY", "🇱🇾"
    elif clean_num.startswith("977"): return "Nepal", "NP", "🇳🇵"
    elif clean_num.startswith("249"): return "Sudan", "SD", "🇸🇩"
    elif clean_num.startswith("998"): return "Uzbekistan", "UZ", "🇺🇿"
    elif clean_num.startswith("260"): return "Zambia", "ZM", "🇿🇲"
    else: return "International", "INT", "🌍"

def get_mk_number_sync(target_range):
    headers = {
        "mknetwork-key": MK_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    clean_range = str(target_range).replace("XXX", "").replace("x", "").replace("X", "").strip()
    payload = {"range": clean_range}
    try:
        res = requests.post(f"{BASE_API_URL}/getnum/number", headers=headers, json=payload, timeout=10.0)
        if res.status_code == 200:
            res_data = res.json()
            data = res_data.get("data", {})
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            phone = data.get("full_number") or data.get("number")
            req_id = data.get("request_id")
            country = data.get("country", "International")
            
            if phone and req_id:
                return str(phone), int(req_id), str(country)
    except Exception as e:
        print(f"MK API Error: {e}")
    return None, None, None

async def get_mk_number(target_range="2491"):
    return await asyncio.to_thread(get_mk_number_sync, target_range)

def check_status_sync(request_ids):
    headers = {
        "mknetwork-key": MK_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"request_ids": request_ids}
    try:
        res = requests.post(f"{BASE_API_URL}/check/status", headers=headers, json=payload, timeout=6.0)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"Check Status API Error: {e}")
    return None

async def check_status(request_ids):
    return await asyncio.to_thread(check_status_sync, request_ids)

async def personal_otp_checker(application):
    print("Personal MK Network OTP Checker Loop Started!")
    while True:
        try:
            current_time = time.time()
            req_ids_to_check = []
            req_id_to_user = {}

            for user_id, u_info in list(ACTIVE_USER_NUMBERS.items()):
                fetch_time = u_info.get("fetch_time", 0)
                if (current_time - fetch_time) > 900: 
                    continue
                req_id = u_info.get("request_id")
                if req_id:
                    req_ids_to_check.append(req_id)
                    req_id_to_user[req_id] = user_id

            if req_ids_to_check:
                res_data = await check_status(req_ids_to_check)
                if res_data and isinstance(res_data, dict):
                    data_obj = res_data.get("data", {})
                    results = data_obj.get("results", [])
                    if isinstance(results, list):
                        for item in results:
                            if not isinstance(item, dict): continue
                            req_id = item.get("request_id")
                            status = item.get("status")
                            if status != "success": continue

                            user_id = req_id_to_user.get(req_id)
                            if not user_id or user_id not in ACTIVE_USER_NUMBERS: continue

                            u_info = ACTIVE_USER_NUMBERS[user_id]
                            otp_code = item.get("otp_code")
                            full_sms = item.get("full_sms") or item.get("sms") or f"OTP: {otp_code}"
                            u_phone = item.get("number") or u_info.get("phone", "")
                            country = item.get("country", "International")

                            if not otp_code: continue

                            global_sent_otps = u_info.setdefault("global_sent_otps", set())
                            sent_set = u_info.setdefault("sent_otps", set())
                            
                            if str(otp_code) not in sent_set:
                                sent_set.add(str(otp_code))
                                
                                current_bal = USER_BALANCES.get(user_id, 0.0)
                                USER_BALANCES[user_id] = current_bal + 0.20

                                _, _, flag = get_country_info(u_phone, country)
                                
                                personal_text = (
                                    f"🟢 <b>NEW OTP RECEIVED</b>\n\n"
                                    f"🌐 <b>Service :</b> SMS\n"
                                    f"🌍 <b>Country :</b> {country} ({flag})\n"
                                    f"🎯 <b>Number :</b> <code>{u_phone}</code>\n"
                                    f"🔑 <b>OTP Code :</b> <code>{otp_code}</code>\n\n"
                                    f"✉ <b>Full Message :</b>\n<code>{full_sms}</code>\n\n"
                                    f"💰 <b>Earned :</b> +৳0.20"
                                )
                                personal_markup = InlineKeyboardMarkup([
                                    [InlineKeyboardButton(text=f"📋 Copy OTP: {otp_code}", copy_text=CopyTextButton(text=str(otp_code)))],
                                    [InlineKeyboardButton("🔄 Change Number", callback_data="change_number")]
                                ])
                                try:
                                    await application.bot.send_message(
                                        chat_id=u_info["chat_id"], 
                                        text=personal_text, 
                                        reply_markup=personal_markup,
                                        parse_mode="HTML"
                                    )
                                except Exception as per_ex:
                                    print(f"Personal Send Error: {per_ex}")

                            if str(otp_code) not in global_sent_otps:
                                global_sent_otps.add(str(otp_code))
                                _, _, flag = get_country_info(u_phone, country)
                                
                                group_text = (
                                    f"🟢 <b>SMS OTP RECEIVED</b>\n\n"
                                    f"🌍 <b>Country :</b> {country} ({flag})\n"
                                    f"🎯 <b>Number :</b> <code>{u_phone}</code>\n"
                                    f"🔑 <b>Code :</b> <code>{otp_code}</code>\n\n"
                                    f"✉ <b>Message :</b>\n<code>{full_sms}</code>"
                                )
                                group_markup = InlineKeyboardMarkup([
                                    [InlineKeyboardButton(text=f"📋 Copy OTP: {otp_code}", copy_text=CopyTextButton(text=str(otp_code)))],
                                    [InlineKeyboardButton("NUMBER BOT ↗", url=f"https://t.me/{application.bot.username}")]
                                ])
                                try:
                                    await application.bot.send_message(
                                        chat_id=OTP_GROUP_CHAT_ID, 
                                        text=group_text, 
                                        reply_markup=group_markup, 
                                        parse_mode="HTML"
                                    )
                                except Exception as g_ex:
                                    print(f"Group Send Error: {g_ex}")
        except Exception as e:
            print(f"Personal Loop Error: {e}")
        await asyncio.sleep(3)

def create_single_number_markup(phone_num):
    _, _, flag = get_country_info(phone_num)
    keyboard = [
        [InlineKeyboardButton(text=f"{flag} {phone_num}", copy_text=CopyTextButton(text=phone_num))],
        [
            InlineKeyboardButton("🔔 OTP GROUP", url="https://t.me/smm_otp_grup"),
            InlineKeyboardButton("🔄 Change", callback_data="change_number")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        USER_STATES[user_id] = None
        reply_keyboard = [
            ["📞 Get API Number", "⚙ Set Range"],
            ["🟢 Live Traffic", "💳 Balance"],
            ["💬 Support", "📣 OTP Group"]
        ]
        markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
        await update.message.reply_text("Welcome to MK Network SMS Bot! 🤖\nPlease select an option from the menu below:", reply_markup=markup)
    except Exception as e:
        print(f"Start Error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        support_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📞 সাপোর্টে যোগাযোগ করুন", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ])
        await update.message.reply_text("💬 <b>সাপোর্ট সেন্টার</b>\n\nযেকোনো সমস্যায় সরাসরি যোগাযোগ করুন:", reply_markup=support_markup, parse_mode="HTML")
    except Exception as e:
        print(f"Help Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        text = update.message.text or ""
        state = USER_STATES.get(user_id)

        if state == "WAITING_FOR_RANGE":
            clean_text = text.replace("XXX", "").replace("x", "").replace("X", "").strip()
            if len(clean_text) >= 2:
                USER_STATES[user_id] = None
                USER_RANGES[user_id] = clean_text
                await update.message.reply_text(f"🔴 Target range updated successfully to: <b>{clean_text}</b>", parse_mode="HTML")
            else:
                await update.message.reply_text("🔴 Invalid range! Please enter a valid number prefix.")
            return
        elif state == "WAITING_FOR_BKASH":
            USER_STATES[user_id] = None
            USER_WITHDRAW_INFO[user_id] = f"bKash: {text.strip()}"
            await update.message.reply_text(f"✅ bKash number saved: <code>{text.strip()}</code>", parse_mode="HTML")
            return
        elif state == "WAITING_FOR_BINANCE":
            USER_STATES[user_id] = None
            USER_WITHDRAW_INFO[user_id] = f"Binance ID: {text.strip()}"
            await update.message.reply_text(f"✅ Binance ID saved: <code>{text.strip()}</code>", parse_mode="HTML")
            return

        if "Get API Number" in text:
            USER_STATES[user_id] = None
            wait_msg = await update.message.reply_text("⏳ Allocating fresh number from MK Network...")
            user_range = USER_RANGES.get(user_id, "2491")
            
            phone, req_id, country = await get_mk_number(target_range=user_range)
            try: await wait_msg.delete()
            except: pass

            if not phone or not req_id:
                await update.message.reply_text(f"❌ No stock available for range <code>{user_range}</code>. Please select another active range from 'Live Traffic'.", parse_mode="HTML")
                return

            ACTIVE_USER_NUMBERS[user_id] = {
                "phone": phone,
                "request_id": req_id,
                "chat_id": update.effective_chat.id,
                "sent_otps": set(),
                "global_sent_otps": set(),
                "fetch_time": time.time()
            }

            _, _, flag = get_country_info(phone, country)
            header_text = f"✅ <b>Number:</b> {flag} {country}"
            reply_markup = create_single_number_markup(phone)
            await update.message.reply_text(header_text, reply_markup=reply_markup, parse_mode="HTML")

        elif "Set Range" in text:
            USER_STATES[user_id] = "WAITING_FOR_RANGE"
            await update.message.reply_text("🔴 Please send your target number range prefix (e.g. 2491 or 260):")

        elif "Live Traffic" in text or "TRAFFIC" in text:
            USER_STATES[user_id] = None
            traffic_text = f"🕒 <b>Live Gateway Matrix ({time.strftime('%I:%M %p')})</b>\n\n📊 প্যানেলের লাইভ রেঞ্জসমূহ নিচে দেওয়া হলো। যেটিতে স্টক আছে (যেমন Sudan বা Zambia) সেটিতে ক্লিক করুন:"
            
            keyboard = []
            for item in PANEL_LIVE_RANGES:
                btn_text = f"{item['country']} ({item['operator']}) - {item['range']} [{item['status']}]"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"range_{item['range']}")])
            
            keyboard.append([InlineKeyboardButton("🔄 Refresh Traffic", callback_data="refresh_traffic")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
            
            traffic_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(traffic_text, reply_markup=traffic_markup, parse_mode="HTML")

        elif "Balance" in text:
            USER_STATES[user_id] = None
            user_bal = USER_BALANCES.get(user_id, 0.0)
            saved_info = USER_WITHDRAW_INFO.get(user_id, "Not Set")
            balance_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_menu")],
                [InlineKeyboardButton("📱 Set bKash", callback_data="set_bkash"), InlineKeyboardButton("🔴 Set Binance", callback_data="set_binance")]
            ])
            await update.message.reply_text(f"💳 <b>Balance:</b> ৳{user_bal:.2f}\n📂 <b>Payout Info:</b> {saved_info}", reply_markup=balance_markup, parse_mode="HTML")

        elif "Support" in text: await help_command(update, context)
        elif "OTP Group" in text:
            group_markup = InlineKeyboardMarkup([[InlineKeyboardButton("📣 Join OTP Group", url="https://t.me/smm_otp_grup")]])
            await update.message.reply_text("📣 Join official OTP group:", reply_markup=group_markup)
    except Exception as e:
        print(f"Message Handler Error: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        data = query.data
        user_id = query.from_user.id

        if data == "back_home":
            try: await query.message.delete()
            except: pass
            await start(update, context)

        elif data.startswith("range_"):
            selected_range = data.replace("range_", "").replace("XXX", "").replace("x", "").replace("X", "").strip()
            USER_RANGES[user_id] = selected_range
            await query.answer(f"Range set to {selected_range} successfully!", show_alert=True)

        elif data == "refresh_traffic":
            await query.answer("🔄 Traffic refreshed!")
            traffic_text = f"🕒 <b>Live Gateway Matrix ({time.strftime('%I:%M %p')})</b>\n\n📊 প্যানেলের লাইভ রেঞ্জসমূহ নিচে দেওয়া হলো। যেটিতে স্টক আছে সেটিতে ক্লিক করুন:"
            keyboard = []
            for item in PANEL_LIVE_RANGES:
                btn_text = f"{item['country']} ({item['operator']}) - {item['range']} [{item['status']}]"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"range_{item['range']}")])
            keyboard.append([InlineKeyboardButton("🔄 Refresh Traffic", callback_data="refresh_traffic")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
            
            traffic_markup = InlineKeyboardMarkup(keyboard)
            try:
                await query.edit_message_text(traffic_text, reply_markup=traffic_markup, parse_mode="HTML")
            except:
                await query.message.reply_text(traffic_text, reply_markup=traffic_markup, parse_mode="HTML")

        elif data == "change_number":
            await query.answer("🔄 Fetching new number...")
            user_range = USER_RANGES.get(user_id, "2491")
            phone, req_id, country = await get_mk_number(target_range=user_range)
            
            if not phone or not req_id:
                await query.answer(f"❌ No stock available for range {user_range}.", show_alert=True)
                return

            ACTIVE_USER_NUMBERS[user_id] = {
                "phone": phone,
                "request_id": req_id,
                "chat_id": query.message.chat_id,
                "sent_otps": set(),
                "global_sent_otps": set(),
                "fetch_time": time.time()
            }

            _, _, flag = get_country_info(phone, country)
            header_text = f"✅ <b>New Number:</b> {flag} {country}"
            reply_markup = create_single_number_markup(phone)
            try:
                await query.edit_message_text(header_text, reply_markup=reply_markup, parse_mode="HTML")
            except:
                await query.message.reply_text(header_text, reply_markup=reply_markup, parse_mode="HTML")

        elif data == "set_bkash":
            USER_STATES[user_id] = "WAITING_FOR_BKASH"
            await query.message.reply_text("📲 Please send your bKash number:")
        elif data == "set_binance":
            USER_STATES[user_id] = "WAITING_FOR_BINANCE"
            await query.message.reply_text("🔴 Please send your Binance ID:")
        elif data == "withdraw_menu":
            user_bal = USER_BALANCES.get(user_id, 0.0)
            if user_bal < 50.0:
                await query.message.reply_text(f"❌ Minimum withdraw is ৳50.00. Current Balance: ৳{user_bal:.2f}")
            else:
                await query.message.reply_text("✅ Withdraw request submitted successfully.")
                USER_BALANCES[user_id] = 0.0
    except Exception as e:
        print(f"Callback Error: {e}")

async def post_init(application):
    application.create_task(personal_otp_checker(application))

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        do_HEAD = lambda s: s.do_GET()
        def do_GET(self, *a):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    app.run_polling(drop_pending_updates=True)
