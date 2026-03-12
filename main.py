from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

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


@app.get("/balance/{telegram_id}")
def get_balance(telegram_id: int):

    db = get_db()

    user = db.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (telegram_id,)
    ).fetchone()

    if not user:
        db.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, ?)",
            (telegram_id, 0)
        )
        db.commit()
        return {"balance": 0}

    return {"balance": user["balance"]}


# ПОКУПКА
@app.post("/buy")
def buy_item(data: dict):

    telegram_id = data["telegram_id"]
    item_id = data["item_id"]

    db = get_db()

    item = db.execute(
        "SELECT * FROM items WHERE id = ?",
        (item_id,)
    ).fetchone()

    if not item:
        return {"error": "item not found"}

    price = item["price"]

    user = db.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (telegram_id,)
    ).fetchone()

    if user["balance"] < price:
        return {"error": "not enough balance"}

    new_balance = user["balance"] - price

    db.execute(
        "UPDATE users SET balance = ? WHERE user_id = ?",
        (new_balance, telegram_id)
    )

    db.execute(
        "DELETE FROM items WHERE id = ?",
        (item_id,)
    )

    db.commit()

    return {
        "success": True,
        "balance": new_balance
    }

@app.get("/items")
def get_items():

    db = get_db()

    items = db.execute(
        "SELECT * FROM items"
    ).fetchall()

    return [dict(item) for item in items]