#!/bin/bash
# ========================================================
# AdMan Facebook Bot - سكريبت التثبيت التلقائي لتيرموكس (Termux)
# ========================================================
set -e

echo "🚀 جاري تحديث الحزم وتثبيت المتطلبات الأساسية في Termux..."
pkg update -y && pkg upgrade -y
pkg install -y python python-pip git clang libffi libxml2 libxslt curl jq openssl

echo "📦 ترقية pip وتثبيت مكتبات بايثون..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo "🌐 تثبيت متصفح Chromium المخصص لـ Playwright..."
playwright install chromium || echo "⚠️ إذا واجهت مشكلة في المتصفح، تأكد من تثبيت x11-repo و chromium عبر pkg"

echo ""
echo "========================================================"
echo "✅ تم تثبيت AdMan Facebook Bot بنجاح!"
echo "▶️ لتشغيل النظام والواجهة:"
echo "   python3 run.py"
echo "🌐 افتح الرابط في المتصفح: http://127.0.0.1:8081"
echo "========================================================"
