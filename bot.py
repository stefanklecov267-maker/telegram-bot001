import os
import uuid
import tempfile
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

API_ID = int(os.getenv("34563616"))
API_HASH = os.getenv("836a6cc95181459b6b35cba305bd1f1d")
BOT_TOKEN = os.getenv("8893865728:AAGrW3V28AojVZZN_iUjnDChPf5NJJhiylw")

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

video_cache = {}


def get_video_info(url):
    opts = {
        "quiet": True,
        "noplaylist": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "url": url,
        "title": info.get("title", "Видео")
    }


def download_video(url):
    filename = os.path.join(
        tempfile.gettempdir(),
        f"{uuid.uuid4()}.mp4"
    )

    opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": filename,
        "noplaylist": True,
        "quiet": True
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return filename


def download_audio(url):
    base = os.path.join(
        tempfile.gettempdir(),
        str(uuid.uuid4())
    )

    opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{base}.%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    return f"{base}.mp3"


@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "👋 Отправь ссылку на видео.\n\n"
        "Поддерживаются:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• X/Twitter"
    )


@bot.on_message(filters.text & ~filters.command("start"))
async def handle_url(_, message):
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

        await message.reply_text(
            f"🎬 {info['title']}",
            reply_markup=keyboard
        )

    except Exception as e:
        await message.reply_text(
            f"❌ Ошибка:\n{str(e)}"
        )


@bot.on_callback_query()
async def callback_handler(_, callback_query):
    try:
        action, uid = callback_query.data.split("|")

        info = video_cache.get(uid)

        if not info:
            await callback_query.answer(
                "Ссылка устарела",
                show_alert=True
            )
            return

        await callback_query.answer()

        status = await callback_query.message.reply_text(
            "⏳ Скачиваю..."
        )

        if action == "video":

            file_path = download_video(info["url"])

            await callback_query.message.reply_video(
                video=file_path,
                caption=info["title"],
                supports_streaming=True
            )

            if os.path.exists(file_path):
                os.remove(file_path)

        elif action == "audio":

            audio_path = download_audio(info["url"])

            await callback_query.message.reply_audio(
                audio=audio_path,
                title=info["title"]
            )

            if os.path.exists(audio_path):
                os.remove(audio_path)

        await status.delete()

    except Exception as e:
        try:
            await status.edit_text(
                f"❌ Ошибка:\n{str(e)}"
            )
        except:
            pass


if __name__ == "__main__":
    print("✅ Bot started")
    bot.run()

