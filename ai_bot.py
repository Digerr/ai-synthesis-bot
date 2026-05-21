# -*- coding: utf-8 -*-
import time
import sqlite3
import feedparser
import telebot
import requests
import re
import logging
import sys
from threading import RLock
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# КОНФИГ
BOT_TOKEN = "8750116500:AAFJE-N1L3Rr3X9zSP0F6DSzzVFxVFiK6u0"
CHANNEL_ID = "@твой_канал_здесь" # НЕ ЗАБУДЬ ВСТАВИТЬ ID КАНАЛА
TG_INTERVAL = 1800 # 30 минут, чтобы постить качественную аналитику

# ИСТОЧНИКИ AI
RSS_FEEDS = {
    "Hugging Face": "https://huggingface.co/blog/feed.xml",
    "OpenAI": "https://openai.com/news/feed.xml",
    "The Decoder": "https://thedecoder.com/rss/",
    "AI Breakfast": "https://aibreakfast.beehiiv.com/feed"
}

bot = telebot.TeleBot(BOT_TOKEN)
db_lock = RLock()

def init_db():
    conn = sqlite3.connect("ai_bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS posted (url TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, source TEXT, title TEXT, summary TEXT, link TEXT UNIQUE)")
    conn.commit(); conn.close()

def parse_ai_news():
    translator = GoogleTranslator(source='auto', target='ru')
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(requests.get(url, timeout=10).content)
            for entry in feed.entries[:3]:
                link = entry.link
                conn = sqlite3.connect("ai_bot.db")
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM posted WHERE url = ?", (link,))
                if not cursor.fetchone():
                    title = translator.translate(entry.title)
                    summary = translator.translate(entry.summary[:300])
                    cursor.execute("INSERT OR IGNORE INTO queue (source, title, summary, link) VALUES (?, ?, ?, ?)", 
                                   (source, title, summary, link))
                    conn.commit()
                conn.close()
        except: continue

def post_news():
    conn = sqlite3.connect("ai_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, title, summary, link FROM queue ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    if row:
        q_id, src, title, summary, link = row
        text = f"🤖 <b>{title}</b>\n\n{summary}...\n\n🔗 Источник: {src}\n\n#AI #Tech #Synthesis"
        try:
            bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            cursor.execute("INSERT INTO posted (url) VALUES (?)", (link,))
            cursor.execute("DELETE FROM queue WHERE id = ?", (q_id,))
            conn.commit()
        except: pass
    conn.close()

if __name__ == "__main__":
    init_db()
    while True:
        parse_ai_news()
        post_news()
        time.sleep(TG_INTERVAL)
