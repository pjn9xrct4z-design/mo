import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp

# ---------------------------------------------------------
# 👮‍♂️ إعدادات القيادة (تعديل التوكن هنا)
# ---------------------------------------------------------
TOKEN = "هنا_تضع_التوكن_الجديد_الخاص_ببوتك"  # 👈 امسح هذا النص وضع التوكن الخاص بك

# اسم ملف الكوكيز (يجب أن يكون مرفوعاً في GitHub)
COOKIES_FILE = 'cookies.txt'

# ---------------------------------------------------------
# 🛠️ إعدادات السجلات (Logs) لكشف الأخطاء
# ---------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# 🚀 دالة البداية (Welcome)
# ---------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f" بوت مهند الحلبوسي 1 {user.first_name}! \n"
        "أرسل لي رابط يوتيوب وسأقوم بتحميله لك بالصيغة التي تختارها.\n"
        "القائمة المتاحة: (Video, MP3, WAV, Voice Note)"
    )

# ---------------------------------------------------------
# 📨 معالجة الرابط (إظهار الأزرار)
# ---------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "youtube.com" in text or "youtu.be" in text:
        # حفظ الرابط لاستخدامه عند ضغط الزر
        context.user_data['url'] = text
        
        # تصميم لوحة الأزرار
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو (MP4)", callback_data='video'),
             InlineKeyboardButton("🎧 صوت (MP3)", callback_data='mp3')],
            [InlineKeyboardButton("🎼 جودة عالية (WAV)", callback_data='wav'),
             InlineKeyboardButton("🎙️ بصمة صوتية (Voice)", callback_data='voice')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر نوع التحميل يا بطل: 👇", reply_markup=reply_markup)
    else:
        await update.message.reply_text("يرجى إرسال رابط يوتيوب صحيح. ❌")

# ---------------------------------------------------------
# ⚙️ المحرك الرئيسي للتحميل (Download Engine)
# ---------------------------------------------------------
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode = query.data
    url = context.user_data.get('url')
    
    await query.answer()
    await query.edit_message_text(text=f"جاري التحميل بوضع: {mode.upper()}... ⏳\nيرجى الانتظار، العمليات جارية.")

    try:
        # إعدادات عامة ومشتركة
        ydl_opts = {
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'cookiefile': COOKIES_FILE,  # ✅ الكوكيز موجود في كل الأوضاع
        }

        # تخصيص الإعدادات حسب الوضع المختار
        if mode == 'video':
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best', # أفضل جودة متاحة
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
            
        elif mode == 'voice': # بصمة صوتية للتليجرام
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'vorbis', # OGG format
                }],
                'outtmpl': '%(title)s.ogg' # نجبر الصيغة لتكون OGG
            })

        # --- بدء التحميل الفعلي ---
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # الحصول على اسم الملف المحمل
            if mode == 'voice':
                 filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".ogg"
            elif mode == 'mp3':
                 filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            elif mode == 'wav':
                 filename = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".wav"
            else: # video
                 filename = ydl.prepare_filename(info)
                 if not filename.endswith('.mp4'): # fix for merged files
                     filename = filename.rsplit('.', 1)[0] + ".mp4"

        # --- الإرسال للمستخدم ---
        await query.edit_message_text(text="جاري الرفع... 🚀")
        
        chat_id = update.effective_chat.id
        with open(filename, 'rb') as f:
            if mode == 'video':
                await context.bot.send_video(chat_id=chat_id, video=f, caption=" حلابسة")
            elif mode == 'voice':
                await context.bot.send_voice(chat_id=chat_id, voice=f, caption="بصمة صوتية 🎙️")
            else: # mp3 or wav
                await context.bot.send_audio(chat_id=chat_id, audio=f, title=info.get('title', 'Audio'), caption="تم سحب الصوت 🎧")

        # --- تنظيف المخلفات (حذف الملف) ---
        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        logger.error(f"Error: {e}")
        await query.edit_message_text(text=f"حدث خطأ أثناء العملية: {str(e)}")

# ---------------------------------------------------------
# 🔌 التشغيل الرئيسي
# ---------------------------------------------------------
def main():
    # التأكد من وجود ملف الكوكيز
    if not os.path.exists(COOKIES_FILE):
        print(f"⚠️ تحذير: ملف {COOKIES_FILE} غير موجود! البوت قد يفشل في التحميل.")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    print("Bot is running... 🟢")
    application.run_polling()

if __name__ == "__main__":
    main()
