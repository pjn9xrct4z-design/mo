import os
import logging
import static_ffmpeg
static_ffmpeg.add_paths()
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp

# --- الإعدادات ---
# ضع التوكن الخاص بك هنا
TOKEN = "YOUR_TOKEN_HERE" 

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # سحب اسم المستخدم الأول
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"أهلاً بك يا {user_name}! ✨\nأرسل رابط اليوتيوب وسأقوم بتحميله لك فوراً.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "youtube.com" in text or "youtu.be" in text:
        context.user_data['url'] = text
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو MP4", callback_data='video'),
             InlineKeyboardButton("🎧 صوت MP3", callback_data='mp3')],
            [InlineKeyboardButton("🎼 ملف WAV", callback_data='wav'),
             InlineKeyboardButton("🎙️ بصمة صوتية", callback_data='voice')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر الصيغة المطلوبة:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("يرجى إرسال رابط يوتيوب صحيح.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode = query.data
    url = context.user_data.get('url')
    
    await query.answer()
    await query.edit_message_text(text=f"جاري معالجة الطلب بصيغة {mode.upper()}... ⏳")

    try:
        ydl_opts = {
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': False,
            'noplaylist': True,
            # استخدام وضع أندرويد لتفادي الحظر المكاني
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }

        if mode == 'video':
            ydl_opts.update({'format': 'bestvideo+bestaudio/best', 'merge_output_format': 'mp4'})
        elif mode == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })
        elif mode == 'wav':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
            })
        elif mode == 'voice':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'vorbis'}],
                'outtmpl': '%(id)s.ogg'
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_id = info['id']
            
            # تحديد الامتدادات
            if mode == 'video': filename = f"{file_id}.mp4"
            elif mode == 'mp3': filename = f"{file_id}.mp3"
            elif mode == 'wav': filename = f"{file_id}.wav"
            elif mode == 'voice': filename = f"{file_id}.ogg"
            
            if not os.path.exists(filename):
                for file in os.listdir('.'):
                    if file.startswith(file_id):
                        filename = file
                        break

        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await query.edit_message_text(text="جاري رفع الملف الآن... 🚀")
            chat_id = update.effective_chat.id
            with open(filename, 'rb') as f:
                if mode == 'video': await context.bot.send_video(chat_id=chat_id, video=f)
                elif mode == 'voice': await context.bot.send_voice(chat_id=chat_id, voice=f)
                else: await context.bot.send_audio(chat_id=chat_id, audio=f, title=info.get('title'))
            os.remove(filename)
        else:
            await query.edit_message_text(text="عذراً، فشل التحميل. قد يكون الرابط محظوراً أو السيرفر مشغولاً.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text(text=f"حدث خطأ: {str(e)}")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    print("البوت جاهز للعمل.")
    application.run_polling()

if __name__ == "__main__":
    main()
