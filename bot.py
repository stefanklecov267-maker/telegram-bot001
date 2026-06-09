import os
import uuid
import asyncio
import tempfile
import yt_dlp
from aiohttp import web
from pyrogram import Client, filters

# Настройки
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

bot = Client("video_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
video_cache = {}

# Заглушка для Render (обязательно)
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
    await message.reply("Отправь ссылку.")

@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, message):
    url = message.text.strip()
    wait = await message.reply("🔍...")
    try:
        info = get_video_info(url)
        uid = str(uuid.uuid4())
        video_cache[uid] = info
        buttons = [[{"text": f"{q}p", "callback_data": f"v|{uid}|{q}"} for q in info["qualities"]],
                   [{"text": "🎵 MP3", "callback_data": f"a|{uid}"}]]
        await wait.edit_text(f"🎬 {info['title']}", reply_markup=None) # Добавь кнопки через InlineKeyboardMarkup
    except Exception as e:
        await wait.edit_text(f"❌ Ошибка: {e}")

@bot.on_callback_query()
async def cb(_, cq):
    data = cq.data.split("|")
    info = video_cache.get(data[1])
    status = await cq.message.reply("⏳ Скачиваю...")
    try:
        path = await download_file(info["url"], data[2] if data[0] == "v" else None, data[0] == "a")
        if data[0] == "v": await cq.message.reply_video(path)
        else: await cq.message.reply_audio(path)
        os.remove(path)
        await status.delete()
    except Exception as e: await status.edit_text(f"❌ {e}")

async def main():
    app = web.Application()
    app.router.add_get('/', web_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    await bot.start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    bot.loop.run_until_complete(main())
