FROM python:3.10-slim

# تنصيب FFmpeg (ضروري للموجات الصوتية)
RUN apt-get update && \
    apt-get install -y ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# إعداد المجلد
WORKDIR /app

# نسخ الملفات
COPY . .

# تنصيب المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python", "mohand.py"]