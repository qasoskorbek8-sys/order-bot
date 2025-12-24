import sqlite3

conn = sqlite3.connect("data/orders.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    phone TEXT,
    product TEXT,
    width REAL,
    height REAL,
    status TEXT
)
""")

conn.commit()

def save_order(user_id, phone, product, w, h):
    cursor.execute(
        "INSERT INTO orders VALUES (NULL,?,?,?,?,?)",
        (user_id, phone, product, w, h, "Yangi")
    )
    conn.commit()




def update_status(order_id, status):
    cursor.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (status, order_id)
    )
    conn.commit()
