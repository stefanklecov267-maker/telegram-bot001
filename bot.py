import os
import uuid
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 34563616
API_HASH = "836a6cc95181459b6b35cba305bd1f1d"
BOT_TOKEN = "8893865728:REPLACE_THIS_WITH_NEW_TOKEN"

bot = Client(
    "video_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

video_cache = {}


# --------------------------
# Получение инфо + качество
# --------------------------
def get_video_info(url):
    ydl_opts = {"quiet": True, "noplaylist": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    qualities = []

    # только для YouTube
    if "youtube" in info.get("extractor", ""):
        seen = set()
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


# --------------------------
# Скачать видео (YouTube quality or best)
# --------------------------
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
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


# --------------------------
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


# --------------------------
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply(
        "👋 Отправь ссылку на видео"
    )


# --------------------------
@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):
    url = message.text.strip()

    try:
        info = get_video_info(url)

        uid = str(uuid.uuid4())
        video_cache[uid] = info

        buttons = []

        # если YouTube → показываем качество
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
                    "📹 Скачать видео",
                    callback_data=f"video|{uid}|best"
                )
            ])

        buttons.append([
            InlineKeyboardButton(
                "🎵 MP3",
                callback_data=f"audio|{uid}"
            )
        ])

        await message.reply(
            f"🎬 {info['title']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await message.reply(f"❌ Ошибка:\n{e}")


# --------------------------
@bot.on_callback_query()
async def callback(_, callback_query):
    data = callback_query.data.split("|")

    action = data[0]
    uid = data[1]

    info = video_cache.get(uid)

    if not info:
        await callback_query.answer("Устарело")
        return

    await callback_query.answer()

    msg = await callback_query.message.reply("⏳ Скачиваю...")

    try:

        if action == "video":
            quality = data[2]
            quality = None if quality == "best" else int(quality)

            file_path = download_video(info["url"], quality)

            await callback_query.message.reply_video(
                file_path,
                caption=info["title"],
                supports_streaming=True
            )

            os.remove(file_path)

        elif action == "audio":
            audio = download_audio(info["url"])

            await callback_query.message.reply_audio(
                audio,
                title=info["title"]
            )

            os.remove(audio)

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка:\n{e}")


print("Bot started")
bot.run()

