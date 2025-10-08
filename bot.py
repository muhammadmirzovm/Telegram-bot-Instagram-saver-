import os
import tempfile
import asyncio
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from yt_dlp import YoutubeDL


TELEGRAM_TOKEN = "8178278739:AAH6x58IKHWitGaVRiNRFDvCUvBm5eJgXjU"  
MAX_TELEGRAM_BYTES = 50 * 1024 * 1024  


ydl_opts = {
    "outtmpl": "%(id)s.%(ext)s",
    "format": "bestvideo+bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
}



async def download_with_ytdlp(url: str, download_dir: str):
    """Download media from Instagram using yt-dlp."""
    loop = asyncio.get_running_loop()

    def sync_download():
        with YoutubeDL({**ydl_opts, "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s")}) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    file_path = await loop.run_in_executor(None, sync_download)
    return file_path


def compress_video(input_path: str) -> str:
    """Compress video using FFmpeg to fit Telegram limits."""
    compressed_path = input_path.replace(".mp4", "_compressed.mp4")

    print("🎞️ Compressing video...")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-vf", "scale=-2:720",   
            "-b:v", "1M",            
            "-b:a", "128k",          
            "-preset", "fast",
            "-c:v", "libx264",
            "-c:a", "aac",
            compressed_path
        ], check=True)
        return compressed_path
    except Exception as e:
        print("Compression failed:", e)
        return input_path




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hello! I’m your *Instagram Downloader Bot* 🚀\n\n"
        "Just send me any Instagram link (video, reel, or photo), and I’ll fetch it for you!"
        "\n\n📸 Example:\nhttps://www.instagram.com/reel/xxxxxx/",
        parse_mode="Markdown"
    )


async def handle_instagram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not ("instagram.com" in url or "instagr.am" in url):
        await update.message.reply_text("⚠️ Please send a valid Instagram link.")
        return

    await update.message.reply_text("⏳ Downloading your content... please wait.")

    with tempfile.TemporaryDirectory() as td:
        try:

            file_path = await download_with_ytdlp(url, td)


            if file_path.endswith(".mp4"):
                file_path = compress_video(file_path)

            size = os.path.getsize(file_path)


            if size <= MAX_TELEGRAM_BYTES:
                caption = "✅ Here’s your Instagram video/photo! 😎"
                if file_path.endswith(".mp4"):
                    await update.message.reply_video(video=open(file_path, "rb"), caption=caption)
                else:
                    await update.message.reply_document(document=open(file_path, "rb"), caption=caption)
            else:
                await update.message.reply_text(
                    f"⚠️ File size is {size/(1024*1024):.1f} MB (too large for Telegram).\n"
                    "Try a shorter video or different link."
                )

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")




def main():
    print("🤖 Starting Instagram Downloader Bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    from telegram.ext import CommandHandler

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_instagram))

    app.run_polling()



if __name__ == "__main__":
    main()
