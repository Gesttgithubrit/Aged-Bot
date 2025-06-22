import requests
import time
import json
import os

BOT_TOKEN = "7082134763:AAFpzJASMR0HxzUpTOouyuYaB8KbjsmXlmo"
ADMIN_ID = 5342166182
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DB_FILE = "db.json"
STOCK_FILE = "stock.json"

# Account prices
PRICES = {
    "2012": 2.00,
    "2013": 1.00,
    "2014": 0.75,
    "2015": 0.60,
    "2016-2020": 0.50,
    "meta_enabled": 2.50,
    "meta_verified": 10.00,
    "custom_verification": 20.00,
}

# Crypto payment info
CRYPTO_PAYMENTS = {
    "LTC": "LW8GqutuJNtBUUunLPMjSHQT5xoTUQfNMY",
    "USDT (BEP20)": "0x62a67fdef135b295ed685701be17360b6574ccee",
}

CONTACT_ADMIN = "@TriptiDimri"

# Ensure DB files exist
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"users": {}, "txlog": []}, f)

if not os.path.exists(STOCK_FILE):
    with open(STOCK_FILE, "w") as f:
        json.dump({
            "2012": [], "2013": [], "2014": [], "2015": [],
            "2016-2020": [], "meta_enabled": [], "meta_verified": [], "custom_verification": []
        }, f)


def load(fname):
    with open(fname, "r") as f:
        return json.load(f)


def save(fname, data):
    with open(fname, "w") as f:
        json.dump(data, f)


def send(chat_id, text, buttons=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if buttons:
        data["reply_markup"] = json.dumps({"keyboard": buttons, "resize_keyboard": True, "one_time_keyboard": False})
    requests.post(f"{API_URL}/sendMessage", data=data)


def send_help(chat_id, is_admin):
    if is_admin:
        help_text = (
            "👮 *Admin Commands:*\n"
            "/addfund <user_id> <amount> - Add balance to user\n"
            "/addaccount <category> ~ user ~ pass ~ email ~ epass - Add account to stock\n"
            "/verify <user_id> <amount> <txid> - Verify deposit and credit user\n"
            "/users - List all users and balances\n"
            "/purchases <user_id> - Show user purchases\n"
        )
    else:
        help_text = (
            "📖 *User Commands:*\n"
            "/start - Restart and show menu\n"
            "📥 Deposit Funds - Get crypto deposit instructions\n"
            "💰 Check Balance - View your balance\n"
            "🛒 Buy accounts listed in menu\n"
            "📦 My Purchases - View your purchased accounts\n"
            "/referral - Get your referral link to invite friends and earn 20% commission\n"
            "📞 Contact Admin - Contact admin for support and payment methods\n"
        )
    send(chat_id, help_text)


def send_referral_link(chat_id, user_id, bot_username):
    link = f"https://t.me/{bot_username}?start={user_id}"
    text = (
        f"🔗 *Your Referral Link:*\n\n"
        f"{link}\n\n"
        "Share this link with your friends. When they start the bot using this link and make purchases, "
        "you will earn a 20% commission credited to your balance."
    )
    send(chat_id, text)


def handle(u):
    message = u.get("message")
    if not message:
        return
    cid = message["chat"]["id"]
    uid = str(cid)
    txt = message.get("text", "")

    db = load(DB_FILE)
    stock = load(STOCK_FILE)

    if uid not in db["users"]:
        # Check referral code in /start
        if txt.startswith("/start"):
            parts = txt.split()
            referrer = None
            if len(parts) > 1:
                ref_candidate = parts[1]
                if ref_candidate in db["users"] and ref_candidate != uid:
                    referrer = ref_candidate
            db["users"][uid] = {"balance": 0, "purchases": [], "referrer": referrer, "referrals": []}
            if referrer:
                db["users"][referrer].setdefault("referrals", [])
                if uid not in db["users"][referrer]["referrals"]:
                    db["users"][referrer]["referrals"].append(uid)
            save(DB_FILE, db)
        else:
            db["users"][uid] = {"balance": 0, "purchases": [], "referrer": None, "referrals": []}
            save(DB_FILE, db)

    if txt.startswith("/start"):
        buttons = [
            ["📥 Deposit Funds", "💰 Check Balance"],
            ["🛒 Buy 2012 - $2.00", "🛒 Buy 2013 - $1.00", "🛒 Buy 2014 - $0.75"],
            ["🛒 Buy 2015 - $0.60", "🛒 Buy 2016-2020 - $0.50"],
            ["🛒 Meta Enabled - $2.50", "🛒 Meta Verified - $10.00"],
            ["🛒 Custom Verification - $20.00"],
            ["📦 My Purchases", "/referral"],
            ["📞 Contact Admin", "/help"]
        ]
        send(cid, "👋 Welcome! Please choose an option:", buttons)
        return

    # Commands mapping
    buy_map = {
        "🛒 Buy 2012 - $2.00": "2012",
        "🛒 Buy 2013 - $1.00": "2013",
        "🛒 Buy 2014 - $0.75": "2014",
        "🛒 Buy 2015 - $0.60": "2015",
        "🛒 Buy 2016-2020 - $0.50": "2016-2020",
        "🛒 Meta Enabled - $2.50": "meta_enabled",
        "🛒 Meta Verified - $10.00": "meta_verified",
        "🛒 Custom Verification - $20.00": "custom_verification",
    }

    # Handle /help
    if txt == "/help":
        send_help(cid, cid == ADMIN_ID)
        return

    # Handle referral link request
    if txt == "/referral":
        try:
            res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe").json()
            bot_username = res.get("result", {}).get("username", "YourBotUsername")
        except Exception:
            bot_username = "YourBotUsername"
        send_referral_link(cid, uid, bot_username)
        return

    if txt == "📥 Deposit Funds":
        deposit_text = (
            "*Deposit Instructions:*\n\n"
            "Send cryptocurrency to add balance:\n\n"
            f"• LTC: `{CRYPTO_PAYMENTS['LTC']}`\n"
            f"• USDT (BEP20): `{CRYPTO_PAYMENTS['USDT (BEP20)']}`\n\n"
            "After sending, reply here with your TXID to get your balance updated dm @TriptiDimri after sending funds to confirmation.\n"
            "For other payment methods, contact admin @TriptiDimri."
        )
        send(cid, deposit_text)
        return

    if txt == "💰 Check Balance":
        bal = db["users"][uid]["balance"]
        send(cid, f"💰 Your balance is: *${bal:.2f}*")
        return

    if txt == "📦 My Purchases":
        purchases = db["users"][uid]["purchases"]
        if purchases:
            send(cid, "📦 Your purchases:\n\n" + "\n\n".join(purchases))
        else:
            send(cid, "📦 You have not purchased any accounts yet.")
        return

    if txt == "📞 Contact Admin":
        send(cid, "📞 You can contact the admin here: @TriptiDimri")
        return

    if txt in buy_map:
        category = buy_map[txt]
        price = PRICES[category]
        user_balance = db["users"][uid]["balance"]
        available_stock = len(stock.get(category, []))

        if user_balance < price:
            send(cid, f"❌ You have insufficient balance (${user_balance:.2f}) to buy a {category} account priced at ${price:.2f}. Please deposit funds.")
            return
        if available_stock == 0:
            send(cid, f"😓 Sorry, no {category} accounts are currently available. Please check back later.")
            return

        acc = stock[category].pop()
        db["users"][uid]["balance"] -= price
        db["users"][uid]["purchases"].append(f"{category} account:\n{acc}")

        # Referral commission: 20% of price to referrer if any
        referrer = db["users"][uid].get("referrer")
        if referrer and referrer in db["users"]:
            commission = round(price * 0.20, 2)
            db["users"][referrer]["balance"] += commission

        save(DB_FILE, db)
        save(STOCK_FILE, stock)

        send(cid, f"✅ You bought a *{category}* account for *${price:.2f}*.\n\nAccount details:\n{acc}")
        return

    # Admin commands
    if cid == ADMIN_ID:
        if txt.startswith("/addfund"):
            parts = txt.split()
            if len(parts) == 3:
                uid_target, amount_str = parts[1], parts[2]
                if uid_target in db["users"]:
                    try:
                        amount = float(amount_str)
                        db["users"][uid_target]["balance"] += amount
                        save(DB_FILE, db)
                        send(cid, f"✅ Added ${amount:.2f} to user {uid_target}")
                        send(int(uid_target), f"💰 Your balance has been credited with ${amount:.2f} by Admin.")
                    except:
                        send(cid, "❌ Invalid amount.")
                else:
                    send(cid, "❌ User ID not found.")
            else:
                send(cid, "Usage: /addfund <user_id> <amount>")
            return

        if txt.startswith("/addaccount"):
            try:
                content = txt[len("/addaccount"):].strip()
                parts = [s.strip() for s in content.split("~")]
                if len(parts) != 5:
                    send(cid, "❌ Format error. Use:\n/addaccount <category> ~ username ~ pass ~ email ~ epass")
                    return
                category, username, password, email, epass = parts
                if category not in stock:
                    send(cid, f"❌ Invalid category '{category}'.")
                    return
                entry = f"Username ~ {username}\nPassword ~ {password}\nEmail ~ {email}\nEpass ~ {epass}"
                stock[category].append(entry)
                save(STOCK_FILE, stock)
                send(cid, f"✅ Added account to stock for category '{category}'.")
            except:
                send(cid, "❌ Format error. Use:\n/addaccount <category> ~ username ~ pass ~ email ~ epass")
            return

        if txt.startswith("/verify"):
            parts = txt.split()
            if len(parts) == 4:
                user_id_v, amount_s, txid = parts[1], parts[2], parts[3]
                if user_id_v in db["users"]:
                    try:
                        amount = float(amount_s)
                        db["users"][user_id_v]["balance"] += amount
                        db["txlog"].append({"user": user_id_v, "amt": amount, "txid": txid})
                        save(DB_FILE, db)
                        send(cid, f"✅ Verified TXID and added ${amount:.2f} to user {user_id_v}.")
                        send(int(user_id_v), f"💰 Your deposit of ${amount:.2f} has been verified and credited.")
                    except:
                        send(cid, "❌ Invalid amount.")
                else:
                    send(cid, "❌ User not found.")
            else:
                send(cid, "Usage: /verify <user_id> <amount> <txid>")
            return
        
        if txt == "/users":
            users_list = [
                f"ID: {uid}, Balance: ${u['balance']:.2f}, Referrals: {len(u.get('referrals', []))}"
                for uid, u in db["users"].items()
            ]
            msg = "\n".join(users_list) if users_list else "No users."
            send(cid, f"👥 Users:\n{msg}")
            return

        if txt.startswith("/purchases"):
            parts = txt.split()
            if len(parts) == 2:
                user_p = parts[1]
                if user_p in db["users"]:
                    purchases = db["users"][user_p]["purchases"]
                    msg = "\n\n".join(purchases) if purchases else "No purchases."
                    send(cid, f"📦 Purchases for {user_p}:\n{msg}")
                else:
                    send(cid, "❌ User not found.")
            else:
                send(cid, "Usage: /purchases <user_id>")
            return

    else:
        # TXID submission by user (alphanumeric, 15+ chars)
        if len(txt) >= 15 and txt.isalnum():
            db["txlog"].append({"user": uid, "txid": txt})
            save(DB_FILE, db)
            send(cid, "✅ TXID received. Admin will verify and credit your balance soon.")
            send(ADMIN_ID, f"🔔 New TXID from user `{uid}`:\n`{txt}`")
            return

    send(cid, "❓ Unrecognized command or message. Use keyboard buttons or /help to see options.")


def main():
    offset = None
    while True:
        try:
            res = requests.get(f"{API_URL}/getUpdates", params={"timeout": 100, "offset": offset})
            updates = res.json().get("result", [])
            for u in updates:
                offset = u["update_id"] + 1
                handle(u)
            time.sleep(1)
        except Exception as e:
            print("Error:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
  
