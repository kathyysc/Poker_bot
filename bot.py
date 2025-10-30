import os
import sqlite3
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

DB_FILE = "poker_records.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            user_id INTEGER,
            username TEXT,
            action TEXT,
            amount INTEGER,
            timestamp TEXT
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_game_user ON records (game_id, user_id)')
    conn.commit()
    conn.close()

def get_current_game_id():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT game_id FROM records ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

ADMIN_USER_ID = 1922308870

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

async def newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 僅場主可用")
        return
    game_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO records (game_id, user_id, username, action, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
              (game_id, update.effective_user.id, update.effective_user.full_name, "NEW_GAME", 0, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ 新牌局開局！\n局號：`{game_id}`", parse_mode='Markdown')

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: 
        await update.message.reply_text("⚠️ 用法：/join 1000")
        return
    try: amount = int(context.args[0])
    except: 
        await update.message.reply_text("⚠️ 請輸入數字")
        return
    if amount <= 0: 
        await update.message.reply_text("⚠️ 金額要 > 0")
        return

    game_id = get_current_game_id()
    if not game_id:
        await update.message.reply_text("❌ 先用 /newgame 開局")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO records (game_id, user_id, username, action, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
              (game_id, update.effective_user.id, update.effective_user.full_name, "BUY_IN", amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ {update.effective_user.full_name} 買入 **{amount}**", parse_mode='Markdown')

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: 
        await update.message.reply_text("⚠️ 用法：/add 500")
        return
    try: amount = int(context.args[0])
    except: 
        await update.message.reply_text("⚠️ 請輸入數字")
        return
    if amount <= 0: 
        await update.message.reply_text("⚠️ 金額要 > 0")
        return

    game_id = get_current_game_id()
    if not game_id:
        await update.message.reply_text("❌ 尚未開局")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO records (game_id, user_id, username, action, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
              (game_id, update.effective_user.id, update.effective_user.full_name, "ADD_CHIP", amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"➕ 加碼 **{amount}**", parse_mode='Markdown')

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: 
        await update.message.reply_text("⚠️ 用法：/leave 1500")
        return
    try: amount = int(context.args[0])
    except: 
        await update.message.reply_text("⚠️ 請輸入數字")
        return

    game_id = get_current_game_id()
    if not game_id:
        await update.message.reply_text("❌ 尚未開局")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO records (game_id, user_id, username, action, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
              (game_id, update.effective_user.id, update.effective_user.full_name, "CASH_OUT", amount, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    df = pd.read_sql_query(f"SELECT * FROM records WHERE game_id = ? AND action != 'NEW_GAME'", sqlite3.connect(DB_FILE), params=(game_id,))
    user_df = df[df['user_id'] == update.effective_user.id]
    total_in = user_df[user_df['action'].isin(['BUY_IN', 'ADD_CHIP'])]['amount'].sum()
    total_out = user_df[user_df['action'] == 'CASH_OUT']['amount'].sum()
    profit = total_out - total_in

    await update.message.reply_text(f"✅ 離場帶走 **{amount}**\n💰 淨輸贏：**{profit:+}**", parse_mode='Markdown')

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_id = get_current_game_id()
    if not game_id: 
        await update.message.reply_text("❌ 尚未開局")
        return
    df = pd.read_sql_query(f"SELECT * FROM records WHERE game_id = ? AND action != 'NEW_GAME'", sqlite3.connect(DB_FILE), params=(game_id,))
    user_df = df[df['user_id'] == update.effective_user.id]
    if user_df.empty:
        await update.message.reply_text("您尚未入場")
        return
    total_in = user_df[user_df['action'].isin(['BUY_IN', 'ADD_CHIP'])]['amount'].sum()
    total_out = user_df[user_df['action'] == 'CASH_OUT']['amount'].sum()
    profit = total_out - total_in
    await update.message.reply_text(f"👤 **{update.effective_user.full_name}**\n入金：{total_in}\n出金：{total_out}\n淨輸贏：**{profit:+}**", parse_mode='Markdown')

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_id = get_current_game_id()
    if not game_id: 
        await update.message.reply_text("❌ 尚未開局")
        return
    df = pd.read_sql_query(f"SELECT * FROM records WHERE game_id = ? AND action != 'NEW_GAME'", sqlite3.connect(DB_FILE), params=(game_id,))
    if df.empty:
        await update.message.reply_text("無記錄")
        return
    lines = []
    for uid in df['user_id'].unique():
        u = df[df['user_id'] == uid].iloc[0]
        tin = df[(df['user_id'] == uid) & (df['action'].isin(['BUY_IN', 'ADD_CHIP']))]['amount'].sum()
        tout = df[(df['user_id'] == uid) & (df['action'] == 'CASH_OUT')]['amount'].sum()
        profit = tout - tin
        status = "在場" if tout == 0 else "離場"
        lines.append(f"{u['username']}：{tin}→{tout}（{profit:+}）[{status}]")
    await update.message.reply_text(f"🎲 **總覽**\n" + "\n".join(lines), parse_mode='Markdown')

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 僅場主可匯出")
        return
    game_id = get_current_game_id()
    if not game_id: 
        await update.message.reply_text("❌ 尚未開局")
        return
    df = pd.read_sql_query(f"SELECT * FROM records WHERE game_id = ? AND action != 'NEW_GAME'", sqlite3.connect(DB_FILE), params=(game_id,))
    if df.empty:
        await update.message.reply_text("無資料")
        return
    csv_file = f"game_{game_id}.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    await update.message.reply_document(open(csv_file, 'rb'), filename=csv_file)
    os.remove(csv_file)

async def main():
    init_db()
    TOKEN = "8468464630:AAESwrwK91z_uTh3clWoW4Hwuug4zeHpeoU"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("join", join))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(CommandHandler("export", export_csv))
    print("德州撲克記帳 Bot 啟動中...")
    while True:  # 永久循環，防止任何退出
        try:
            await app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            print(f"Bot 錯誤：{e}，5 秒後重啟...")
            await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(main())
