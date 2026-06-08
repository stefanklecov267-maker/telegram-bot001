import os
import uuid
import yt_dlp

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import asyncio

# ==========================
# ВСТАВЬ СВОЙ ТОКЕН
# ==========================
BOT_TOKEN = "8893865728:AAGrW3V28AojVZZN_iUjnDChPf5NJJhiylw"
# ==========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Отправь ссылку на видео\n\n"
        "Поддержка:\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram"
    )


@dp.message()
async def process_link(message: types.Message):
    url = message.text.strip()

    try:
        info = get_video_info(url)

        uid = str(uuid.uuid4())
        video_cache[uid] = info

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📹 Скачать видео",
                    callback_data=f"video|{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎵 Скачать MP3",
                    callback_data=f"audio|{uid}"
                )
            ]
        ])

        await message.answer(f"🎬 {info['title']}", reply_markup=keyboard)

    except Exception as e:
        await message.answer(f"❌ Ошибка:\n{e}")


@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    action, uid = callback.data.split("|")

    info = video_cache.get(uid)

    if not info:
        await callback.answer("Данные устарели")
        return

    await callback.answer()
    msg = await callback.message.answer("⏳ Скачиваю...")

    try:
        if action == "video":
            file_path = download_video(info["url"])

            await callback.message.answer_video(
                types.FSInputFile(file_path),
                caption=info["title"]
            )

            os.remove(file_path)

        elif action == "audio":
            file_path = download_audio(info["url"])

            await callback.message.answer_audio(
                types.FSInputFile(file_path),
                title=info["title"]
            )

            os.remove(file_path)

        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка:\n{e}")


async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
