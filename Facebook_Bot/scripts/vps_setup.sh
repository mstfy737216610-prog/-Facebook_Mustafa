#!/bin/bash
# ========================================================
# AdMan Facebook Bot - سكريبت التثبيت على سيرفر VPS (Ubuntu / Debian)
# ========================================================
set -e

echo "🚀 تحديث النظام وتثبيت متطلبات بايثون وبيئة التشغيل..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl wget libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

echo "📦 تثبيت الحزم المطلوبة..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "🌐 تثبيت المتصفح ومتطلبات Playwright لنظام Linux..."
playwright install chromium
playwright install-deps chromium || true

echo ""
echo "========================================================"
echo "✅ تم تثبيت AdMan Facebook بنجاح على السيرفر!"
echo "▶️ للتشغيل كخدمة مستمرة بالخلفية:"
echo "   nohup python3 run.py > bot.log 2>&1 &"
echo "🌐 أو التشغيل المباشر:"
echo "   python3 run.py"
echo "========================================================"
