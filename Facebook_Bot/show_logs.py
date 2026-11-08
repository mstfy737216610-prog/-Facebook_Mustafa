#!/usr/bin/env python3
"""
عرض سجل الأخطاء والعمليات السابقة في Termux مباشرة.
الاستخدام:
  python3 show_logs.py
  python3 show_logs.py --errors-only
  python3 show_logs.py --watch
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import db

def format_time(ts):
    if not ts:
        return "غير محدد"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(ts)))
    except Exception:
        return str(ts)

def print_header():
    print("=" * 65)
    print("📋 سجل عمليات فيسبوك وبوت النشر (Termux Log Viewer)")
    print("=" * 65)

def display_logs(errors_only=False, limit=30):
    db.init_db()
    logs = db.get_logs(limit=limit)
    if not logs:
        print("ℹ️ السجل فارغ حالياً، لم يتم تسجيل أي عمليات بعد.")
        return

    count = 0
    for l in logs:
        is_err = l.get("status") in ("failed", "error") or bool(l.get("error"))
        if errors_only and not is_err:
            continue
        
        count += 1
        t = format_time(l.get("created_at"))
        acc = l.get("account_id") or "حساب غير محدد"
        url = l.get("group_url") or "رابط غير محدد"
        status = l.get("status")
        err = l.get("error")

        if is_err:
            print(f"\033[91m❌ [خطأ] {t}\033[0m")
            print(f"   👤 الحساب: {acc}")
            print(f"   🔗 المجموعة: {url}")
            print(f"   ⚠️ السبب: \033[93m{err or 'فشل غير محدد'}\033[0m")
        else:
            print(f"\033[92m✅ [نجاح] {t}\033[0m")
            print(f"   👤 الحساب: {acc}")
            print(f"   🔗 المجموعة: {url}")
            print(f"   💬 الرسالة: {err or 'تم النشر بنجاح'}")
        print("-" * 50)

    if count == 0 and errors_only:
        print("\033[92m🎉 رائع! لا توجد أي أخطاء مسجلة في العمليات الأخيرة.\033[0m")

if __name__ == "__main__":
    errors_only = "--errors-only" in sys.argv
    watch_mode = "--watch" in sys.argv

    print_header()
    if watch_mode:
        print("👀 وضع المراقبة الحية مفعل (اضغط Ctrl+C للإلغاء)...")
        try:
            while True:
                print("\033[2J\033[H", end="") # مسح الشاشة
                print_header()
                display_logs(errors_only=errors_only, limit=20)
                time.sleep(3)
        except KeyboardInterrupt:
            print("\nتم الخروج من وضع المراقبة.")
    else:
        display_logs(errors_only=errors_only, limit=40)
