import os
import uuid
import yt_dlp

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

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

    qualities = []

    extractor = info.get("extractor", "").lower()

    if "youtube" in extractor:
        seen = set()

        for fmt in info.get("formats", []):
            height = fmt.get("height")

            if (
                height
                and fmt.get("vcodec") != "none"
                and height not in seen
            ):
                seen.add(height)
                qualities.append(height)

        qualities.sort()

    return {
        "url": url,
        "title": info.get("title", "Видео"),
        "is_youtube": "youtube" in extractor,
        "qualities": qualities
    }


def download_video(url, quality=None):
    filename = f"/tmp/{uuid.uuid4()}.mp4"

    if quality:
        fmt = (
            f"bestvideo[height<={quality}]"
            "+bestaudio"
            "/best[height<={quality}]"
        )
    else:
        fmt = "bestvideo+bestaudio/best"

    ydl_opts = {
        "format": fmt,
        "merge_output_format": "mp4",
        "outtmpl": filename,
        "noplaylist": True,
        "quiet": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename


def download_audio(url):
    filename = f"/tmp/{uuid.uuid4()}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": filename + ".%(ext)s",
        "quiet": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return filename + ".mp3"


@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply(
        "👋 Отправь ссылку на видео."
    )


@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):

    url = message.text.strip()

    try:
        wait_msg = await message.reply(
            "🔍 Получаю информацию..."
        )

        info = get_video_info(url)

        uid = str(uuid.uuid4())
        video_cache[uid] = info

        buttons = []

        if info["is_youtube"] and info["qualities"]:

            row = []

            for q in info["qualities"]:

                row.append(
                    InlineKeyboardButton(
                        f"{q}p",
                        callback_data=f"video|{uid}|{q}"
                    )
                )

                if len(row) == 3:
                    buttons.append(row)
                    row = []

            if row:
                buttons.append(row)

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

        await wait_msg.edit_text(
            f"🎬 {info['title']}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        await message.reply(
            f"❌ Ошибка:\n{e}"
        )


@bot.on_callback_query()
async def callback(_, callback_query):

    data = callback_query.data.split("|")

    action = data[0]
    uid = data[1]

    info = video_cache.get(uid)

    if not info:
        await callback_query.answer(
            "Данные устарели",
            show_alert=True
        )
        return

    await callback_query.answer()

    status = await callback_query.message.reply(
        "⏳ Скачиваю..."
    )

    try:

        if action == "video":

            quality = data[2]

            if quality == "best":
                quality = None
            else:
                quality = int(quality)

            file_path = download_video(
                info["url"],
                quality
            )

            await callback_query.message.reply_video(
                file_path,
                caption=info["title"],
                supports_streaming=True
            )

            if os.path.exists(file_path):
                os.remove(file_path)

        elif action == "audio":

            audio_file = download_audio(
                info["url"]
            )

            await callback_query.message.reply_audio(
                audio_file,
                title=info["title"]
            )

            if os.path.exists(audio_file):
                os.remove(audio_file)

        await status.delete()

    except Exception as e:

        await status.edit_text(
            f"❌ Ошибка:\n{e}"
        )


print("Bot started")
bot.run()
