import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
# --- إضافة مكتبات السيرفر الوهمي ---
from flask import Flask
from threading import Thread

# --- إعداد السيرفر الوهمي (لإبقاء البوت مستيقظاً 24/7) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! Bot is running..."

def run():
    # Render يستخدم البورت 10000 أو المتغير PORT
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()
# -----------------------------------------------------

# --- TOKEN ---
TOKEN = "8395122731:AAEHYAUkeaU0Z9JONx0cyP0cnaTJGvkg1DM"

# ... (باقي دوال التحميل download_content نفسها بالضبط بدون تغيير) ...
# ... (دوال button_handler و start_command نفسها بالضبط) ...
# سأضع لك التغيير فقط في الأسفل عند التشغيل

# (انسخ دوالك السابقة وضعها هنا، أو استخدم الكود الكامل بالأسفل)

# ------------------------------------------------------------------
# الكود الكامل مع دمج السيرفر الوهمي:

def download_content(url, mode):
    # (نفس دالة التحميل السابقة الخاصة بك)
    if mode == 'voice_note':
        target_codec = 'opus'
        filename = 'voice.ogg'
        post_args = ['-ac', '1', '-ar', '48000', '-b:a', '32k'] 
        writethumb = False
    else:
        target_codec = mode
        filename = 'file.%(ext)s'
        post_args = []
        writethumb = True 

    ydl_opts = {
        'outtmpl': '%(id)s.%(ext)s',
        'writethumbnail': writethumb,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'source_address': '0.0.0.0',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': target_codec,
            'preferredquality': '192' if mode != 'voice_note' else '32',
        }],
        'postprocessor_args': post_args,
    }
    if mode == 'mp3': ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
    if mode == "video":
        ydl_opts = {'format': 'best', 'outtmpl': '%(title)s.%(ext)s', 'extractor_args': {'youtube': {'player_client': ['android', 'web']}}, 'source_address': '0.0.0.0', 'quiet': True, 'no_warnings': True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = info['requested_downloads'][0]['filepath'] if 'requested_downloads' in info else ydl.prepare_filename(info)
            if mode == 'voice_note':
                pre, ext = os.path.splitext(filepath)
                new_path = pre + '.ogg'
                if filepath != new_path and os.path.exists(filepath):
                    if os.path.exists(new_path): os.remove(new_path)
                    os.rename(filepath, new_path)
                    filepath = new_path
                elif not os.path.exists(filepath) and os.path.exists(new_path): filepath = new_path
            base_name = os.path.splitext(filepath)[0]
            thumb_path = None
            for ext in ['.jpg', '.webp', '.png']:
                if os.path.exists(base_name + ext): thumb_path = base_name + ext; break
            return {'filepath': filepath, 'title': info.get('title', 'Video'), 'uploader': info.get('uploader', 'Unknown'), 'thumbnail': thumb_path}
    except Exception as e: print(f"Error: {e}"); raise e

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("  بوت مهند الحلبوسي \n ارسل رابط اي مقطع من اي برنامج و انزله")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" not in url: return
    context.user_data['url'] = url
    keyboard = [[InlineKeyboardButton("فيديو 🎬", callback_data="video"), InlineKeyboardButton("صوت MP3 🎵", callback_data="mp3")], [InlineKeyboardButton("صوت WAV 🔊", callback_data="wav"), InlineKeyboardButton("بصمة صوتية 🎙️", callback_data="voice_note")]]
    await update.message.reply_text("اختار الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data, context.user_data.get('url')
    await query.edit_message_text(f"جاري المعالجة... ⏳")
    try:
        data = await asyncio.to_thread(download_content, url, mode)
        file_path = data['filepath']
        if os.path.exists(file_path):
            with open(file_path, 'rb', buffering=10485760) as f:
                args = {'chat_id': query.message.chat_id, 'write_timeout': 1000, 'read_timeout': 1000, 'connect_timeout': 1000}
                if mode == "video": await context.bot.send_video(video=f, caption=data['title'], **args)
                elif mode == "voice_note": await context.bot.send_voice(voice=f, **args)
                else:
                    thumb = open(data['thumbnail'], 'rb') if data.get('thumbnail') else None
                    await context.bot.send_audio(audio=f, title=data['title'], performer=data['uploader'], thumbnail=thumb, **args)
                    if thumb: thumb.close()
            try: await query.message.delete()
            except: pass
            if os.path.exists(file_path): os.remove(file_path)
            if data.get('thumbnail') and os.path.exists(data['thumbnail']): os.remove(data['thumbnail'])
        else: await query.message.reply_text("فشل الملف.")
    except Exception as e: await query.message.reply_text(f"حدث خطأ: {e}")

if __name__ == '__main__':
    # تشغيل السيرفر الوهمي في الخلفية
    keep_alive()
    print("BOT STARTED WITH WEB SERVER...")
    app = Application.builder().token(TOKEN).connect_timeout(1000).read_timeout(1000).write_timeout(1000).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()
