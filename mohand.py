import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp

# ---------------------------------------------------------
# 👮‍♂️ منطقة العمليات (الإعدادات)
# ---------------------------------------------------------
# ضع التوكن الخاص بك هنا بدلاً من النص الموجود
TOKEN = "8395122731:AAFU7fSt4iiau5xtwzqrM11ZtApgk_PHQvc"

# اسم ملف الكوكيز (يجب أن يكون مرفوعاً بنفس الاسم تماماً)
COOKIES_FILE = 'cookies.txt'

# ---------------------------------------------------------
# 🛠️ إعدادات المراقبة (Logging)
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 🚀 أوامر القيادة
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أهلاً سيادة الملازم! 🫡\n"
        "أرسل رابط يوتيوب وسأحوله لك فوراً (فيديو، MP3، أو بصمة).\n"
        "جاهز للتنفيذ! 🚀"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "youtube.com" in text or "youtu.be" in text:
        context.user_data['url'] = text
        
        # لوحة التحكم
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو (MP4)", callback_data='video'),
             InlineKeyboardButton("🎧 صوت (MP3)", callback_data='mp3')],
            [InlineKeyboardButton("🎼 ملف (WAV)", callback_data='wav'),
             InlineKeyboardButton("🎙️ بصمة (Voice)", callback_data='voice')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("تم استلام الهدف. اختر نوع الذخيرة: 👇", reply_markup=reply_markup)
    else:
        await update.message.reply_text("الرابط غير صالح سيدي! أرسل رابط يوتيوب صحيح. ❌")

# ---------------------------------------------------------
# ⚙️ محرك التحميل (Core Engine)
# ---------------------------------------------------------
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode = query.data
    url = context.user_data.get('url')
    
    await query.answer()
    await query.edit_message_text(text=f"جاري التعامل مع الهدف بوضع ({mode.upper()})... ⏳")

    try:
        # إعدادات الـ yt-dlp الأساسية
        ydl_opts = {
            # ✅ الحل الجذري لمشكلة الاسم العربي: استخدام ID الفيديو كاسم للملف
            'outtmpl': '%(id)s.%(ext)s', 
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            # ✅ تفعيل الكوكيز لتفادي الحظر
            'cookiefile': COOKIES_FILE,
        }

        # تخصيص الإعدادات حسب النوع
        if mode == 'video':
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })
        
        elif mode == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

        elif mode == 'wav':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
            })
            
        elif mode == 'voice':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'vorbis', # OGG للبصمات
                }],
                'outtmpl': '%(id)s.ogg' # إجبار الصيغة
            })

        # --- التنفيذ ---
        filename = ""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # استنتاج اسم الملف المحمل بناءً على الـ ID
            file_id = info['id']
            
            if mode == 'video':
                filename = f"{file_id}.mp4"
            elif mode == 'mp3':
                filename = f"{file_id}.mp3"
            elif mode == 'wav':
                filename = f"{file_id}.wav"
            elif mode == 'voice':
                filename = f"{file_id}.ogg"
            
            # في حال لم يجد الامتداد المتوقع، يبحث عن الملف الموجود
            if not os.path.exists(filename):
                # محاولة طوارئ للعثور على الملف
                for file in os.listdir('.'):
                    if file.startswith(file_id):
                        filename = file
                        break

        # --- الإرسال ---
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            await query.edit_message_text(text="جاري الرفع... 🚀")
            chat_id = update.effective_chat.id
            
            with open(filename, 'rb') as f:
                if mode == 'video':
                    await context.bot.send_video(chat_id=chat_id, video=f, caption="تمت المهمة 🫡")
                elif mode == 'voice':
                    await context.bot.send_voice(chat_id=chat_id, voice=f, caption="بصمة صوتية 🎙️")
                else:
                    await context.bot.send_audio(chat_id=chat_id, audio=f, title=info.get('title', file_id), caption="ملف صوتي 🎧")
            
            # تنظيف السيرفر
            os.remove(filename)
        else:
            await query.edit_message_text(text="خطأ: الملف فارغ أو لم يتم تحميله! قد يكون FFmpeg غير مثبت.")

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text(text=f"حدث خطأ فني: {str(e)}")

# ---------------------------------------------------------
# 🔌 التشغيل
# ---------------------------------------------------------
def main():
    if not os.path.exists(COOKIES_FILE):
        print(f"⚠️ تحذير خطير: ملف {COOKIES_FILE} غير موجود! البوت سيفشل.")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("Bot is Live! 🟢")
    application.run_polling()

if __name__ == "__main__":
    main()
