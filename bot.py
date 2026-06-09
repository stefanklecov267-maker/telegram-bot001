import os
import uuid
import yt_dlp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройки
API_ID = int(os.getenv("API_ID", 12345678))
API_HASH = os.getenv("API_HASH", "836a6cc95181459b6b35cba305bd1f1d")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8893865728:AAGrW3V28AojVZZN_iUjnDChPf5NJJhiylw")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
video_cache = {}

# --- Функции ---
def get_video_formats(url):
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        is_yt = "youtube.com" in url or "youtu.be" in url
        formats = []
        if is_yt:
            for f in info.get('formats', []):
                if f.get('height') in [720, 360, 1080]:
                    formats.append({"id": f['format_id'], "res": f"{f['height']}p"})
        return info, formats

# --- Хендлеры ---
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply("Пришли ссылку (YT, TikTok, Insta, Twitter).")

@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):
    url = message.text.strip()
    try:
        info, formats = get_video_formats(url)
        uid = str(uuid.uuid4())
        video_cache[uid] = {"url": url, "title": info.get("title")}

        buttons = [[InlineKeyboardButton("Скачать MP3", callback_data=f"a|{uid}")]]
        if formats:
            for f in formats:
                buttons.append([InlineKeyboardButton(f"Видео {f['res']}", callback_data=f"v|{uid}|{f['id']}")])
        else:
            buttons.append([InlineKeyboardButton("Скачать Видео", callback_data=f"v|{uid}|best")])

        await message.reply(f"🎬 {info['title']}", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        await message.reply(f"Ошибка: {e}")

@bot.on_callback_query()
async def callback_handler(_, cq):
    data = cq.data.split("|")
    type_action, uid, format_id = data[0], data[1], data[2] if len(data) > 2 else "best"
    info = video_cache.get(uid)
    if not info: return await cq.answer("Устарело")

    await cq.answer("Начинаю...")
    msg = await cq.message.reply("⏳ Скачиваю...")
    fname = f"{uuid.uuid4()}"
    
    try:
        if type_action == "a":
            ydl_opts = {"outtmpl": f"{fname}.%(ext)s", "format": "bestaudio", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([info["url"]])
            await cq.message.reply_audio(f"{fname}.mp3")
            os.remove(f"{fname}.mp3")
        else:
            ydl_opts = {"outtmpl": f"{fname}.%(ext)s", "format": f"{format_id}+bestaudio/best", "merge_output_format": "mp4"}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([info["url"]])
            for f in os.listdir('.'):
                if f.startswith(fname) and f.endswith(".mp4"):
                    await cq.message.reply_video(f)
                    os.remove(f)
                    break
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"Ошибка: {e}")

# --- Ключевое исправление ---
if __name__ == "__main__":
    bot.run()
