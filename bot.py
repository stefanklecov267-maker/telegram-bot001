import os
import uuid
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==========================
# ВСТАВЬ СВОИ ДАННЫЕ
# ==========================

API_ID = 34563616
API_HASH = "836a6cc95181459b6b35cba305bd1f1d"
BOT_TOKEN = "8893865728:AAGrW3V28AojVZZN_iUjnDChPf5NJJhiylw"

# ==========================

bot = Client(
    "video_downloader_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

video_cache = {}


def get_video_info(url):
    ydl_opts = {
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "url": url,
        "title": info.get("title", "Видео")
    }


def download_video(url):
    filename = f"{uuid.uuid4()}.mp4"

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": filename,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


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


@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply(
        "👋 Отправь ссылку на видео.\n\n"
        "Поддержка:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
    )


@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):
    url = message.text.strip()

    try:
        info = get_video_info(url)

        uid = str(uuid.uuid4())
        video_cache[uid] = info

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📹 Скачать видео",
                    callback_data=f"video|{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🎵 Скачать MP3",
                    callback_data=f"audio|{uid}"
                )
            ]
        ])

        await message.reply(
            f"🎬 {info['title']}",
            reply_markup=keyboard
        )

    except Exception as e:
        await message.reply(f"❌ Ошибка:\n{e}")


@bot.on_callback_query()
async def callback_handler(_, callback_query):
    data = callback_query.data.split("|")

    action = data[0]
    uid = data[1]

    info = video_cache.get(uid)

    if not info:
        await callback_query.answer("Данные устарели")
        return

    await callback_query.answer()

    status = await callback_query.message.reply(
        "⏳ Скачиваю..."
    )

    try:

        if action == "video":
            file_path = download_video(info["url"])

            await callback_query.message.reply_video(
                file_path,
                caption=info["title"],
                supports_streaming=True
            )

            if os.path.exists(file_path):
                os.remove(file_path)

        elif action == "audio":
            audio_path = download_audio(info["url"])

            await callback_query.message.reply_audio(
                audio_path,
                title=info["title"]
            )

            if os.path.exists(audio_path):
                os.remove(audio_path)

        await status.delete()

    except Exception as e:
        await status.edit_text(f"❌ Ошибка:\n{e}")


print("Бот запущен")

bot.run()
