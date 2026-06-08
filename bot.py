import os
import uuid
import asyncio
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 34563616
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

bot = Client(
    "video_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

video_cache = {}
progress_message = {}


# -------------------- PROGRESS --------------------
def progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "0%").strip()

        msg = progress_message.get("current")
        if msg:
            try:
                asyncio.create_task(msg.edit_text(f"⏳ Загрузка: {percent}"))
            except:
                pass


# -------------------- INFO --------------------
def get_video_info(url):
    ydl_opts = {"quiet": True, "noplaylist": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    qualities = []
    seen = set()

    if "youtube" in info.get("extractor", ""):
        for f in info.get("formats", []):
            h = f.get("height")
            if f.get("vcodec") != "none" and h in [360, 480, 720, 1080]:
                if h not in seen:
                    seen.add(h)
                    qualities.append(h)

    qualities.sort()

    return {
        "url": url,
        "title": info.get("title", "Видео"),
        "is_youtube": "youtube" in info.get("extractor", ""),
        "qualities": qualities
    }


# -------------------- DOWNLOAD VIDEO --------------------
def download_video(url, quality=None):
    filename = f"{uuid.uuid4()}.mp4"

    if quality:
        fmt = f"bestvideo[height<={quality}]+bestaudio/best"
    else:
        fmt = "best"

    ydl_opts = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": filename,
        "noplaylist": True,
        "progress_hooks": [progress_hook]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


# -------------------- DOWNLOAD AUDIO --------------------
def download_audio(url):
    filename = f"{uuid.uuid4()}.mp3"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": filename.replace(".mp3", ".%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


# -------------------- START --------------------
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply("👋 Отправь ссылку на видео")


# -------------------- LINK --------------------
@bot.on_message(filters.text & ~filters.command("start"))
async def handler(_, message):
    url = message.text.strip()

    try:
        info = get_video_info(url)

        uid = str(uuid.uuid4())
        video_cache[uid] = info

        buttons = []

        if info["is_youtube"] and info["qualities"]:
            for q in info["qualities"]:
                buttons.append([
                    InlineKeyboardButton(
                        f"📹 {q}p",
                        callback_data=f"video|{uid}|{q}"
                    )
                ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    "📹 Скачать",
                    callback_data=f"video|{uid}|best"
                )
            ])

        buttons.append([
            InlineKeyboardButton("🎵 MP3", callback_data=f"audio|{uid}")
        ])

        await message.reply(
            f"🎬 {info['title']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# -------------------- CALLBACK --------------------
@bot.on_callback_query()
async def cb(_, call):
    data = call.data.split("|")

    action = data[0]
    uid = data[1]

    info = video_cache.get(uid)
    if not info:
        await call.answer("Устарело")
        return

    await call.answer()

    msg = await call.message.reply("⏳ Загрузка: 0%")
    progress_message["current"] = msg

    try:
        if action == "video":
            q = data[2]
            q = None if q == "best" else int(q)

            file = download_video(info["url"], q)

            await call.message.reply_video(
                file,
                caption=info["title"],
                supports_streaming=True
            )

            os.remove(file)

        elif action == "audio":
            file = download_audio(info["url"])

            await call.message.reply_audio(file, title=info["title"])

            os.remove(file)

        progress_message.pop("current", None)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


print("Bot started")
bot.run()
