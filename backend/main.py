import os
import sqlite3
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# === CONFIG ===
ADMIN_ID = 5815294733  # seniki

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "users.db")
WEBAPP_DIR = os.path.join(BASE_DIR, "webapp")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # keyin productionda domen bilan cheklaymiz
    allow_methods=["*"],
    allow_headers=["*"],
)

def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    db = conn()
    cur = db.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        usdt REAL DEFAULT 0,
        rub  REAL DEFAULT 0,
        uzs  INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        currency TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS withdraws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        currency TEXT,
        amount REAL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    db.commit()
    db.close()

init_db()

# === Serve WebApp static ===
app.mount("/static", StaticFiles(directory=WEBAPP_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(WEBAPP_DIR, "index.html"))

@app.get("/api/health")
def health():
    return {"ok": True}

# === Users ===
@app.post("/api/user/upsert")
def user_upsert(user_id: int, username: str = ""):
    db = conn()
    cur = db.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
    db.commit()
    db.close()
    return {"status": "ok"}

@app.get("/api/balance/{user_id}")
def balance(user_id: int):
    db = conn()
    cur = db.cursor()
    cur.execute("SELECT usdt, rub, uzs FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    db.close()
    if not row:
        raise HTTPException(404, "User not found")
    return {"usdt": row["usdt"], "rub": row["rub"], "uzs": row["uzs"]}

# === Deposit / Withdraw requests ===
def _validate_currency_amount(currency: str, amount: float):
    currency = currency.lower().strip()
    if currency not in ("usdt", "rub", "uzs"):
        raise HTTPException(400, "Bad currency")
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0")
    return currency

@app.post("/api/deposit/request")
def deposit_request(user_id: int, currency: str, amount: float):
    currency = _validate_currency_amount(currency, amount)

    db = conn()
    cur = db.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        db.close()
        raise HTTPException(404, "User not found")

    cur.execute("INSERT INTO deposits (user_id, currency, amount) VALUES (?, ?, ?)", (user_id, currency, amount))
    db.commit()
    db.close()
    return {"status": "pending"}

@app.post("/api/withdraw/request")
def withdraw_request(user_id: int, currency: str, amount: float):
    currency = _validate_currency_amount(currency, amount)

    db = conn()
    cur = db.cursor()
    cur.execute("SELECT usdt, rub, uzs FROM users WHERE user_id=?", (user_id,))
    u = cur.fetchone()
    if not u:
        db.close()
        raise HTTPException(404, "User not found")

    # balans yetarlimi (withdraw so'rovi berishda tekshiramiz)
    if currency == "usdt" and u["usdt"] < amount:
        db.close(); raise HTTPException(400, "Insufficient USDT")
    if currency == "rub" and u["rub"] < amount:
        db.close(); raise HTTPException(400, "Insufficient RUB")
    if currency == "uzs" and u["uzs"] < amount:
        db.close(); raise HTTPException(400, "Insufficient UZS")

    cur.execute("INSERT INTO withdraws (user_id, currency, amount) VALUES (?, ?, ?)", (user_id, currency, amount))
    db.commit()
    db.close()
    return {"status": "pending"}

# === History ===
@app.get("/api/history/{user_id}")
def history(user_id: int):
    db = conn()
    cur = db.cursor()

    cur.execute("""
        SELECT id, currency, amount, status, created_at
        FROM deposits
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 50
    """, (user_id,))
    deps = [dict(r) | {"type": "deposit"} for r in cur.fetchall()]

    cur.execute("""
        SELECT id, currency, amount, status, created_at
        FROM withdraws
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 50
    """, (user_id,))
    wds = [dict(r) | {"type": "withdraw"} for r in cur.fetchall()]

    db.close()
    items = sorted(deps + wds, key=lambda x: x["created_at"], reverse=True)
    return {"items": items[:50]}

# === Admin ===
@app.post("/api/admin/add_balance")
def admin_add_balance(
    admin_id: int = Query(...),
    user_id: int = Query(...),
    usdt: float = 0,
    rub: float = 0,
    uzs: int = 0,
):
    if admin_id != ADMIN_ID:
        raise HTTPException(403, "Not admin")

    db = conn()
    cur = db.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        db.close()
        raise HTTPException(404, "User not found")

    cur.execute("""
        UPDATE users
        SET usdt = usdt + ?,
            rub  = rub  + ?,
            uzs  = uzs  + ?
        WHERE user_id = ?
    """, (usdt, rub, uzs, user_id))

    db.commit()
    db.close()
    return {"status": "ok"}

@app.get("/api/admin/pending")
def admin_pending(admin_id: int = Query(...)):
    if admin_id != ADMIN_ID:
        raise HTTPException(403, "Not admin")

    db = conn()
    cur = db.cursor()

    cur.execute("""
        SELECT id, user_id, currency, amount, status, created_at
        FROM deposits
        WHERE status='pending'
        ORDER BY id DESC
        LIMIT 100
    """)
    deps = [dict(r) | {"type": "deposit"} for r in cur.fetchall()]

    cur.execute("""
        SELECT id, user_id, currency, amount, status, created_at
        FROM withdraws
        WHERE status='pending'
        ORDER BY id DESC
        LIMIT 100
    """)
    wds = [dict(r) | {"type": "withdraw"} for r in cur.fetchall()]

    db.close()
    items = sorted(deps + wds, key=lambda x: x["created_at"], reverse=True)
    return {"items": items}

@app.post("/api/admin/decision")
def admin_decision(
    admin_id: int = Query(...),
    req_type: str = Query(...),  # deposit / withdraw
    req_id: int = Query(...),
    action: str = Query(...),    # approve / reject
):
    if admin_id != ADMIN_ID:
        raise HTTPException(403, "Not admin")
    if req_type not in ("deposit", "withdraw"):
        raise HTTPException(400, "Bad req_type")
    if action not in ("approve", "reject"):
        raise HTTPException(400, "Bad action")

    table = "deposits" if req_type == "deposit" else "withdraws"

    db = conn()
    cur = db.cursor()
    cur.execute(f"SELECT id, user_id, currency, amount, status FROM {table} WHERE id=?", (req_id,))
    r = cur.fetchone()
    if not r:
        db.close(); raise HTTPException(404, "Not found")
    if r["status"] != "pending":
        db.close(); raise HTTPException(400, "Already processed")

    if action == "reject":
        cur.execute(f"UPDATE {table} SET status='rejected' WHERE id=?", (req_id,))
        db.commit(); db.close()
        return {"status": "rejected"}

    uid, curcy, amt = r["user_id"], r["currency"], r["amount"]

    # approve:
    if req_type == "deposit":
        if curcy == "usdt":
            cur.execute("UPDATE users SET usdt = usdt + ? WHERE user_id=?", (amt, uid))
        elif curcy == "rub":
            cur.execute("UPDATE users SET rub = rub + ? WHERE user_id=?", (amt, uid))
        else:
            cur.execute("UPDATE users SET uzs = uzs + ? WHERE user_id=?", (int(amt), uid))
    else:
        cur.execute("SELECT usdt, rub, uzs FROM users WHERE user_id=?", (uid,))
        u = cur.fetchone()
        if not u:
            db.close(); raise HTTPException(404, "User not found")

        if curcy == "usdt" and u["usdt"] < amt:
            db.close(); raise HTTPException(400, "Insufficient USDT now")
        if curcy == "rub" and u["rub"] < amt:
            db.close(); raise HTTPException(400, "Insufficient RUB now")
        if curcy == "uzs" and u["uzs"] < amt:
            db.close(); raise HTTPException(400, "Insufficient UZS now")

        if curcy == "usdt":
            cur.execute("UPDATE users SET usdt = usdt - ? WHERE user_id=?", (amt, uid))
        elif curcy == "rub":
            cur.execute("UPDATE users SET rub = rub - ? WHERE user_id=?", (amt, uid))
        else:
            cur.execute("UPDATE users SET uzs = uzs - ? WHERE user_id=?", (int(amt), uid))

    cur.execute(f"UPDATE {table} SET status='approved' WHERE id=?", (req_id,))
    db.commit()
    db.close()
    return {"status": "approved"}
