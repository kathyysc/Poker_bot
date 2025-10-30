import os
import sqlite3
import pandas as pd
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio  # 必要

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
    c.execute('INSERT INTO records (game_id, user_id, username, action, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?
