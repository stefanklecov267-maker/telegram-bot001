import asyncio
import os
import sys

# Важные настройки для запуска на Render
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import uuid
import tempfile
import yt_dlp
from aiohttp import web
from pyrogram import Client, filters

# Конфигурация
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

bot = Client("video_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
video_cache = {}

async def web_handler(request):
    return web.Response(text="Bot is running")

def get_video_info(url):
    ydl_opts = {"quiet": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    qualities = sorted(list(set(fmt.get("height") for fmt in info.get("formats", []) 
                      if fmt.get("height") and fmt.get("vcodec") != "none")))
    return {"url": url, "title": info.get("title", "Video"), "qualities": qualities}

async def download_file(url, quality=None, is_audio=False):
    tmp = tempfile.gettempdir()
    name = os.path.join(tmp, str(uuid.uuid4()))
    opts = {
        "format": "bestaudio/best" if is_audio else (f"bestvideo[height<={quality}]+bestaudio/best" if quality else "best"),
        "outtmpl": f"{name}.%(ext)s",
        "merge_output_format": "mp4"
    }
    if is_audio:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    return f"{name}.mp3" if is_audio else f"{name}.mp4"

@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply("Привет! Отправь мне ссылку на видео.")

@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):
    url = message.text.strip()
    wait = await message.reply("🔍 Получаю информацию...")
    try:
        info = get_video_info(url)
        uid = str(uuid.uuid4())
        video_cache[uid] = info
        await wait.edit_text(f"🎬 {info['title']}\n\nВыберите качество:")
    except Exception as e:
        await wait.edit_text(f"❌ Ошибка: {e}")

async def run_bot():
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    await bot.start()
    print("Бот запущен!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop.run_until_complete(run_bot())
