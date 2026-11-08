#!/usr/bin/env python3
"""
تشغيل واجهة فيسبوك: python3 run.py ثم افتح http://127.0.0.1:8081
لتشغيل وضع عرض كافة الأخطاء والرسائل التفصيلية:
python3 run.py --debug
"""
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import json
import uvicorn
from core import db

# تهيئة السجل في Termux
is_debug = "--debug" in sys.argv
log_level = "debug" if is_debug else "info"

logging.basicConfig(
    level=logging.DEBUG if is_debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

db.init_db()
s = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))["system"]

print("=" * 60)
print(f"📘 خادم بوت فيسبوك يعمل الآن: http://{s['web_host']}:{s['web_port']}")
if is_debug:
    print("🐞 وضع تتبع الأخطاء الدقيق مفعّل (Debug Mode ON)")
else:
    print("💡 لمشاهدة جميع الأخطاء بتفاصيل كاملة شغل: python3 run.py --debug")
print("=" * 60)

uvicorn.run(
    "web.app:app",
    host=s["web_host"],
    port=int(s["web_port"]),
    log_level=log_level,
    access_log=True
)
