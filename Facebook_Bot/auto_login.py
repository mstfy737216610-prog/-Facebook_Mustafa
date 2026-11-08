#!/usr/bin/env python3
"""
سكريبت تسجيل الدخول المباشر واستخراج الكوكيز تلقائياً من المتصفح:
يقوم بفتح متصفح فيسبوك، وبمجرد تسجيل الدخول (يدوياً أو بالبيانات)،
يقوم باستخراج الكوكيز فوراً من المتصفح وحفظها في data/sessions/<account_id>/cookies.json
دون الحاجة لأي إضافات خارجية أو نسخ ولصق يدوي.
"""
import sys
import json
import time
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from playwright.async_api import async_playwright
from core import db
from platforms.facebook.session import sanitize_cookie, SESSIONS


async def capture_cookies_interactive(account_id: str, email: str = None, password: str = None, headless: bool = False):
    """
    تسجيل الدخول المباشر واستخراج الكوكيز تلقائياً.
    """
    db.init_db()
    acc_dir = SESSIONS / account_id
    acc_dir.mkdir(parents=True, exist_ok=True)
    profile_dir = acc_dir / "browser_profile"

    print(f"\n🚀 بدء جلسة تسجيل الدخول لحساب [{account_id}]...")
    print("🌐 جاري فتح المتصفح لموقع فيسبوك...")

    async with async_playwright() as pw:
        # تشغيل المتصفح بملف تعريف مخصص
        ctx = await pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=headless,
            viewport={"width": 412, "height": 915},
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            locale="ar-EG,ar;q=0.9",
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = await ctx.new_page()
        await page.goto("https://m.facebook.com/login/", wait_until="domcontentloaded")

        # إذا تم تمرير البريد وكلمة المرور، نقوم بملئهما تلقائياً
        if email and password:
            print(f"🔑 إدخال بيانات الدخول للبريد: {email}")
            try:
                await page.fill("input[name='email'], input#m_login_email", email)
                await page.fill("input[name='pass'], input#m_login_password", password)
                await page.click("button[name='login'], button[type='submit']")
                print("⏳ تم الضغط على زر الدخول، بانتظار استجابة فيسبوك...")
            except Exception as e:
                print(f"⚠️ تنبيه أثناء إدخال البيانات: {e}")

        print("\n👉 يمكنك الآن إكمال تسجيل الدخول (أو كتابة رمز 2FA إن وُجد)...")
        print("⏳ البرنامج يراقب الجلسة تلقائياً لالتقاط الكوكيز...")

        # مراقبة ظهور كوكيز الجلسة الأساسية (c_user أو xs)
        logged_in = False
        start_time = time.time()
        timeout = 180  # 3 دقائق كحد أقصى

        while time.time() - start_time < timeout:
            cookies = await ctx.cookies()
            has_c_user = any(c["name"] == "c_user" for c in cookies)
            has_xs = any(c["name"] == "xs" for c in cookies)

            # التحقق أيضاً من رابط الصفحة
            url = page.url.lower()
            if has_c_user or (has_xs and ("feed" in url or "home" in url or "groups" in url)):
                logged_in = True
                print("\n🎉 تم اكتشاف تسجيل الدخول بنجاح داخل المتصفح!")

                # تنظيف الكوكيز وتنسيقها
                clean_cookies = []
                for c in cookies:
                    sc = sanitize_cookie(c)
                    if sc:
                        clean_cookies.append(sc)

                # حفظ الكوكيز مباشرة في ملف cookies.json
                cookies_file = acc_dir / "cookies.json"
                cookies_file.write_text(json.dumps(clean_cookies, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"💾 تم حفظ {len(clean_cookies)} كوكي مباشرة في: {cookies_file}")

                # تحديث حالة الحساب في قاعدة البيانات
                db.save_account({
                    "id": account_id,
                    "label": f"حساب فيسبوك ({account_id})",
                    "username": email or account_id,
                    "enabled": True,
                    "status": "active",
                    "cookies_valid": True
                })
                print(f"✅ تم تفعيل الحساب [{account_id}] في قاعدة البيانات وأصبح جاهزاً للنشر فوراً!")
                break

            await asyncio.sleep(2)

        if not logged_in:
            print("\n❌ انتهى الوقت ولم يتم استكمال تسجيل الدخول. يمكنك المحاولة مجدداً.")

        await ctx.close()
        return logged_in


def main():
    acc_id = sys.argv[1] if len(sys.argv) > 1 else f"fb_acc_{int(time.time())}"
    email = sys.argv[2] if len(sys.argv) > 2 else None
    password = sys.argv[3] if len(sys.argv) > 3 else None
    headless = "--headless" in sys.argv

    asyncio.run(capture_cookies_interactive(acc_id, email, password, headless=headless))


if __name__ == "__main__":
    main()
