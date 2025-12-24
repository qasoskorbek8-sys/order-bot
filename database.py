import sqlite3
import json

conn = sqlite3.connect("orders.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY,
    data TEXT
)
""")
conn.commit()


def save_order(order_id: int, data: dict):
    cursor.execute(
        "INSERT OR REPLACE INTO orders (order_id, data) VALUES (?, ?)",
        (order_id, json.dumps(data))
    )
    conn.commit()


def get_order(order_id: int):
    cursor.execute(
        "SELECT data FROM orders WHERE order_id = ?",
        (order_id,)
    )
    row = cursor.fetchone()
    if row:
        return json.loads(row[0])
    return None
