from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
BOT_TOKEN = "7003462537:AAH1vCC20ZbLtbvu9UiD7pQiWJHCQEmB1CY"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect("bot_data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/balance/{user_id}")
def get_balance(user_id: int):

    db = get_db()

    user = db.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        return {"balance": 0}

    return {"balance": user["balance"]}

@app.post("/buy")
async def buy_item(data: dict):

    telegram_id = data.get("telegram_id")
    item_id = data.get("item_id")

    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, price FROM items WHERE id=?", (item_id,))
    item = cursor.fetchone()

    if not item:
        return {"error": "Предмет не найден"}

    name, price = item

    cursor.execute("SELECT balance FROM users WHERE user_id=?", (telegram_id,))
    user = cursor.fetchone()

    if not user:
        return {"error": "Пользователь не найден"}

    balance = float(user[0])

    if balance < price:
        return {"error": "Недостаточно средств"}

    new_balance = balance - price

    cursor.execute(
        "UPDATE users SET balance=? WHERE user_id=?",
        (new_balance, telegram_id)
    )

    conn.commit()
    conn.close()

    # отправка сообщения через Telegram
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": telegram_id,
            "text": f"🎁 Вы купили подарок!\n\n"
                    f"ID: {item_id}\n"
                    f"Название: {name}\n"
                    f"Цена: {price} 💎"
        }
    )

    cursor.execute(
        "DELETE FROM items WHERE id = ?",
        (item_id,)
    )

    return {
        "balance": new_balance
    }

@app.get("/items")
def get_items():

    db = get_db()

    items = db.execute(
        "SELECT * FROM items"
    ).fetchall()

    return [dict(item) for item in items]

#Функции для бота
@app.get("/user/{telegram_id}")
def get_user(telegram_id: int):

    conn = sqlite3.connect("bot_data.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT balance, lang, ton_wallet, card_details, successful_deals, kyc, granted_by, is_admin
        FROM users
        WHERE user_id = ?
    """, (telegram_id,))

    row = cur.fetchone()

    conn.close()

    if row is None:
        return {"error": "user not found"}

    return {
        "balance": row[0],
        "lang": row[1],
        "ton_wallet": row[2],
        "card_details": row[3],
        "successful_deals": row[4],
        "kyc": row[5],
        "granted_by": row[6],
        "is_admin": row[7]
    }

@app.get("/users")
def get_all_users():

    db = get_db()

    users = db.execute(
        "SELECT user_id, balance FROM users"
    ).fetchall()

    return [dict(user) for user in users]

# изменить баланс
@app.post("/update_balance")
def update_balance(data: dict):

    user_id = data["user_id"]
    balance = data["balance"]

    db = get_db()

    db.execute(
        "UPDATE users SET balance = ? WHERE user_id = ?",
        (balance, user_id)
    )

    db.commit()

    return {"status": "ok"}


# изменить сделки
@app.post("/update_deals")
def update_deals(data: dict):

    user_id = data["user_id"]
    deals = data["deals"]

    db = get_db()

    db.execute(
        "UPDATE users SET successful_deals = ? WHERE user_id = ?",
        (deals, user_id)
    )

    db.commit()

    return {"status": "ok"}


# изменить любое поле пользователя
@app.post("/update_user_field")
def update_user_field(data: dict):

    user_id = data["user_id"]
    field = data["field"]
    value = data["value"]

    db = get_db()

    db.execute(
        f"UPDATE users SET {field} = ? WHERE user_id = ?",
        (value, user_id)
    )

    db.commit()

    return {"status": "ok"}

@app.post("/admin/add_item")
async def add_item(data: dict):

    img = data.get("img")
    gift_id = data.get("gift_id")
    name = data.get("name")
    price = data.get("price")

    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO items (id, name, price, img)
        VALUES (?, ?, ?, ?)
        """,
        (gift_id, name, price, img)
    )

    conn.commit()
    conn.close()

    return {"status": "ok"}

# сохранить платеж
@app.post("/save_payment")
def save_payment(data: dict):

    user_id = data["user_id"]
    invoice_id = data["invoice_id"]
    amount = data["amount"]
    asset = data["asset"]

    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            user_id INTEGER,
            invoice_id TEXT PRIMARY KEY,
            amount REAL,
            asset TEXT,
            status TEXT DEFAULT 'pending'
        )
        """
    )

    db.execute(
        """
        INSERT OR REPLACE INTO payments
        (user_id, invoice_id, amount, asset)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, invoice_id, amount, asset)
    )

    db.commit()

    return {"status": "saved"}