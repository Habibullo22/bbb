# FONX Project (Telegram Bot + WebApp + Backend)

## Local run
1) `pip install -r requirements.txt`
2) Backend:
   `uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000`
3) Bot:
   `python bot/bot.py`

## ENV
Create `.env`:
BOT_TOKEN=...
BASE_URL=http://localhost:8000

On Replit:
- add Secrets: BOT_TOKEN, BASE_URL=https://YOUR-REPLIT.repl.co
- run backend (uvicorn)
- run bot from Shell (python bot/bot.py)
