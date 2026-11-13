import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import time
import html
import json
import os
import threading

# ============ الإعدادات ============
BOT_TOKEN = "9127862554:AAHjxdnlvjzNEpM56-KyiHZj5foIx-Z8sCQ"
ADMIN_ID = 8765548885
SELLER_USERNAME = "frnk_seller"

USERS_FILE = "users.json"

PAYMENT_DETAILS = {
    "usdt_bep20": "0x38702261bcaa718fe51efad292434c8f021b89ae",
    "usdt_trc20": "TNENBDbTVtiMEZ6KavLUPds8gn2EVwqQFU",
    "ltc": "LUARfbFgvxp57x4vftup813ei7duyJnsc2",
    "btc": "12S1m2jTiihqTvxLGv91Ao6U6waAbTdmsJ",
    "binance_id": "820840544"
}

PACKAGES = {
    "pack_100":  {"name": "100 Cc",  "price": "10$"},
    "pack_500":  {"name": "500 Cc",  "price": "15$"},
    "pack_1000": {"name": "1000 Cc", "price": "30$"}
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, threaded=False)


# ============ إدارة المستخدمين ============
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_users(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(users), f)
    except Exception as e:
        logger.exception(f"Failed to save users: {e}")


def add_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.add(chat_id)
        save_users(users)
        logger.info(f"New user added: {chat_id}")


# ============ الأزرار ============
def main_menu():
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("💳 100 Cc = 10$", callback_data="pack_100"),
        InlineKeyboardButton("💳 500 Cc = 15$", callback_data="pack_500"),
        InlineKeyboardButton("💳 1000 Cc = 30$", callback_data="pack_1000"),
        InlineKeyboardButton("📦 Larger Quantity / Contact Seller", url=f"https://t.me/{SELLER_USERNAME}")
    )
    return markup


def payment_actions_markup(pack_key):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("✅ I've Paid", callback_data=f"paid|{pack_key}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{pack_key}")
    )
    return markup


def admin_decision_markup(user_id, pack_key):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Approve & Send Code", callback_data=f"approve|{user_id}|{pack_key}"),
        InlineKeyboardButton("❌ Reject Order", callback_data=f"reject|{user_id}")
    )
    return markup


# ============ /start ============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        add_user(message.chat.id)  # حفظ المستخدم
        bot.clear_step_handler_by_chat_id(message.chat.id)
        text = (
        "💳 CC/CVV 💳\n\n"

        "➡️HIGH QUALITY👽\n\n"

        "➡️All countries available 🌎\n\n"

        "Non Vbv ⚡️\n\n"

        "Warranty included in case of any problems we will replace or refund⏰✅\n\n"

        "Linkable✅\n\n"
            "Please select the package you want to purchase from the list below:\n\n"
            "📦 Need a larger quantity? Contact the seller directly."
        )
        bot.send_message(message.chat.id, text, reply_markup=main_menu())
    except Exception as e:
        logger.exception(f"Error in send_welcome: {e}")


# ============ /san (إذاعة للأدمن فقط) ============
@bot.message_handler(commands=['san'])
def broadcast_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Unauthorized.")
        return

    msg = bot.send_message(
        ADMIN_ID,
        "📢 Send the message you want to broadcast to all users.\n\n"
        "Or send /cancel to abort."
    )
    bot.register_next_step_handler(msg, broadcast_send)


def broadcast_send(message):
    try:
        if message.text and message.text.strip().lower() in ('/cancel', 'cancel'):
            bot.send_message(ADMIN_ID, "❌ Broadcast cancelled.")
            return

        # نجمع النص اللي هيتبعت
        broadcast_text = message.text or message.caption or ""

        users = load_users()
        if not users:
            bot.send_message(ADMIN_ID, "⚠️ No users found to broadcast to.")
            return

        bot.send_message(ADMIN_ID, f"📤 Broadcasting to {len(users)} users...")

        success = 0
        failed = 0

        for chat_id in users:
            try:
                # لو الرسالة اللي جاية من الأدمن فيها صورة، نبعتها كصورة
                if message.content_type == 'photo':
                    bot.send_photo(chat_id, message.photo[-1].file_id, caption=broadcast_text, parse_mode="HTML")
                else:
                    bot.send_message(chat_id, broadcast_text, parse_mode="HTML")
                success += 1
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
                failed += 1
            # تأخير بسيط لتجنب الحظر (Telegram limits ~30 msg/sec)
            time.sleep(0.05)

        bot.send_message(
            ADMIN_ID,
            f"✅ Broadcast finished.\n\n"
            f"✔️ Sent: {success}\n"
            f"❌ Failed: {failed}\n"
            f"👥 Total: {len(users)}"
        )

    except Exception as e:
        logger.exception(f"Error in broadcast_send: {e}")
        try:
            bot.send_message(ADMIN_ID, f"⚠️ Broadcast error: {e}")
        except Exception:
            pass


# ============ اختيار الباقة ============
@bot.callback_query_handler(func=lambda call: call.data in PACKAGES)
def handle_package_selection(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    try:
        add_user(call.message.chat.id)  # حفظ المستخدم لو ضغط من غير /start

        pack = PACKAGES.get(call.data)
        if not pack:
            bot.send_message(call.message.chat.id, "⚠️ Package not found.")
            return

        text = (
            f"You selected package: <b>{html.escape(pack['name'])}</b>\n"
            f"Price: <b>{html.escape(pack['price'])}</b>\n\n"
            "🌐 <b>Available Payment Methods:</b>\n\n"
            f"1️⃣ <b>USDT (BEP20):</b>\n<code>{html.escape(PAYMENT_DETAILS['usdt_bep20'])}</code>\n\n"
            f"2️⃣ <b>USDT (TRC20):</b>\n<code>{html.escape(PAYMENT_DETAILS['usdt_trc20'])}</code>\n\n"
            f"3️⃣ <b>LTC (Litecoin):</b>\n<code>{html.escape(PAYMENT_DETAILS['ltc'])}</code>\n\n"
            f"4️⃣ <b>BTC (Bitcoin):</b>\n<code>{html.escape(PAYMENT_DETAILS['btc'])}</code>\n\n"
            f"5️⃣ <b>Binance ID:</b>\n<code>{html.escape(PAYMENT_DETAILS['binance_id'])}</code>\n\n"
            "📌 <b>Next Step:</b>\n"
            "After completing the transfer, click <b>✅ I've Paid</b> below "
            "and send your <b>Transaction Hash (TXID)</b> or a <b>screenshot</b>.\n\n"
            f"📦 For larger quantities, contact: @{html.escape(SELLER_USERNAME)}"
        )

        sent = False
        try:
            bot.edit_message_text(call.message.chat.id, call.message.message_id, text,
                                  parse_mode="HTML", reply_markup=payment_actions_markup(call.data))
            sent = True
        except Exception:
            pass

        if not sent:
            try:
                bot.send_message(call.message.chat.id, text, parse_mode="HTML",
                                 reply_markup=payment_actions_markup(call.data))
            except Exception:
                plain = f"You selected: {pack['name']} ({pack['price']})\n\nClick I've Paid or Cancel."
                bot.send_message(call.message.chat.id, plain, reply_markup=payment_actions_markup(call.data))

    except Exception as e:
        logger.exception(f"Error in handle_package_selection: {e}")


# ============ زر "I've Paid" ============
@bot.callback_query_handler(func=lambda call: call.data.startswith("paid|"))
def handle_paid(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    try:
        pack_key = call.data.split("|", 1)[1]
        pack = PACKAGES.get(pack_key)
        if not pack:
            return

        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

        msg = bot.send_message(
            call.message.chat.id,
            "📤 Please send your <b>Transaction Hash (TXID)</b> "
            "or a <b>screenshot of the receipt</b> to confirm your order.\n\n"
            "Or send /cancel to abort.",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_payment_proof, pack, pack_key)
    except Exception as e:
        logger.exception(f"Error in handle_paid: {e}")


# ============ زر "Cancel" ============
@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel|"))
def handle_cancel(call):
    try:
        bot.answer_callback_query(call.id, "❌ Order cancelled.")
    except Exception:
        pass
    try:
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        bot.edit_message_text(call.message.chat.id, call.message.message_id,
                              "❌ Order cancelled. You can start again with /start.")
    except Exception:
        pass


# ============ إثبات الدفع ============
def process_payment_proof(message, pack, pack_key):
    try:
        if message.text and message.text.strip().lower() in ('/cancel', 'cancel'):
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "❌ Order cancelled. Use /start to begin again.", reply_markup=main_menu())
            return

        if message.text and message.text.startswith('/'):
            bot.send_message(message.chat.id, "⚠️ Please send the TXID or a photo, or /cancel to abort.")
            bot.register_next_step_handler(message, process_payment_proof, pack, pack_key)
            return

        if message.content_type not in ('photo', 'text'):
            bot.send_message(message.chat.id, "⚠️ Please send the TXID (text) or a photo, or /cancel to abort.")
            bot.register_next_step_handler(message, process_payment_proof, pack, pack_key)
            return

        user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
        markup = admin_decision_markup(message.from_user.id, pack_key)

        caption = (
            f"🔔 <b>New Purchase Order!</b>\n"
            f"User: {html.escape(user_info)} (ID: <code>{message.from_user.id}</code>)\n"
            f"Package: <b>{html.escape(pack['name'])}</b> ({html.escape(pack['price'])})"
        )

        if message.content_type == 'photo':
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption,
                           parse_mode="HTML", reply_markup=markup)
        else:
            caption += f"\nPayment Proof / TXID: <code>{html.escape(message.text)}</code>"
            bot.send_message(ADMIN_ID, caption, parse_mode="HTML", reply_markup=markup)

        bot.send_message(message.chat.id, "✅ Payment details submitted successfully!\n"
                                          "The admin will verify your payment and send your card code shortly.")
    except Exception as e:
        logger.exception(f"Error in process_payment_proof: {e}")


# ============ /cancel ============
@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    try:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, "❌ Order cancelled. Use /start to begin again.", reply_markup=main_menu())
    except Exception as e:
        logger.exception(f"Error in cancel_command: {e}")


# ============ قرار الأدمن ============
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve|', 'reject|')))
def admin_decision(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    try:
        if call.from_user.id != ADMIN_ID:
            bot.send_message(call.from_user.id, "⛔ Unauthorized.")
            return

        parts = call.data.split('|')
        action = parts[0]
        user_id = int(parts[1])

        if action == "approve":
            pack_key = parts[2] if len(parts) > 2 else None
            pack_name = PACKAGES.get(pack_key, {}).get("name", "Unknown") if pack_key else "Unknown"
            msg = bot.send_message(ADMIN_ID, f"Please send the card code for package ({pack_name}) "
                                              f"to be delivered to customer (ID: {user_id}):")
            bot.register_next_step_handler(msg, send_code_to_user, user_id)
        elif action == "reject":
            try:
                bot.send_message(user_id, "❌ Sorry, your payment could not be verified. Please contact support.")
            except Exception:
                pass
            try:
                if call.message.content_type == 'photo':
                    bot.edit_message_caption("❌ Order Rejected.", chat_id=ADMIN_ID, message_id=call.message.message_id)
                else:
                    bot.edit_message_text("❌ Order Rejected.", chat_id=ADMIN_ID, message_id=call.message.message_id)
            except Exception:
                pass
    except Exception as e:
        logger.exception(f"Error in admin_decision: {e}")


def send_code_to_user(message, user_id):
    try:
        if not message.text:
            bot.send_message(ADMIN_ID, "⚠️ Please send the code as text.")
            bot.register_next_step_handler(message, send_code_to_user, user_id)
            return
        code = message.text.strip()
        bot.send_message(user_id, f"🎉 <b>Payment Verified Successfully!</b>\n\n"
                                  f"Your card code:\n<code>{html.escape(code)}</code>\n\n"
                                  f"Thank you for shopping with us!", parse_mode="HTML")
        bot.send_message(ADMIN_ID, "✅ Code sent to the customer successfully.")
    except Exception as e:
        logger.exception(f"Error in send_code_to_user: {e}")


# ============ التشغيل ============
if __name__ == "__main__":
    logger.info("🚀 Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30, skip_pending=True, restart_on_change=False)
        except Exception as e:
            logger.exception(f"Polling crashed: {e}. Restarting in 5s...")
            time.sleep(5)