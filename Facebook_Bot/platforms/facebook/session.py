"""
جلسات فيسبوك المتقدمة - دعم بيئة الموبايل (Termux) وسطح المكتب:
- استقبال وقبول الكوكيز بجميع الصيغ:
  1. ملفات JSON الناتجة عن إضافات المتصفح (J2Team, EditThisCookie...).
  2. ملفات Netscape (cookies.txt).
  3. سطر كوكيز الهيدر الخام (Header string: c_user=...; xs=...).
- تطبيع دقيق لحقول sameSite و expires و domain لضمان قبول Playwright لها بنسبة 100%.
- إضافة الكوكيز بآلية حماية ثنائية وحقن فوري.
"""
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

ROOT = Path(__file__).resolve().parent.parent.parent
SESSIONS = ROOT / "data" / "sessions"

_pw = None
_contexts: dict[str, BrowserContext] = {}


async def get_playwright():
    global _pw
    if _pw is None:
        _pw = await async_playwright().start()
    return _pw


def sanitize_cookie(c: dict) -> dict | None:
    """تطبيع الكوكيز لتوافق Playwright وتجنب أخطاء expires و sameSite."""
    if not isinstance(c, dict):
        return None
    name = c.get("name")
    value = c.get("value")
    if not name or value is None:
        return None

    domain = str(c.get("domain") or ".facebook.com").strip()
    if not domain.startswith(".") and not domain.startswith("www") and "facebook.com" in domain:
        domain = "." + domain

    path = str(c.get("path") or "/").strip()

    # معالجة sameSite - Playwright يقبل Strict, Lax, None
    raw_samesite = str(c.get("sameSite", "")).lower().strip()
    if raw_samesite in ("no_restriction", "none"):
        same_site = "None"
    elif raw_samesite in ("strict",):
        same_site = "Strict"
    else:
        same_site = "Lax"

    secure = bool(c.get("secure", True))
    # متصفح كروميوم يشترط أن يكون secure=True إذا كان sameSite=None
    if same_site == "None" and not secure:
        secure = True

    cookie = {
        "name": str(name).strip(),
        "value": str(value).strip(),
        "domain": domain,
        "path": path,
        "secure": secure,
        "httpOnly": bool(c.get("httpOnly", False)),
        "sameSite": same_site,
    }

    # Playwright يرفض بشدة expires إذا كانت قيمة سالبة أو صفر
    exp = c.get("expirationDate") or c.get("expires")
    if isinstance(exp, (int, float)) and float(exp) > 0:
        cookie["expires"] = float(exp)

    return cookie


def parse_netscape_cookies(text: str) -> list[dict]:
    """تحويل كوكيز Netscape (cookies.txt) إلى كائنات JSON متوافقة."""
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            domain, flag, path, secure, expiration, name, value = parts[:7]
            c_dict = {
                "domain": domain,
                "path": path,
                "secure": secure.upper() == "TRUE",
                "name": name,
                "value": value,
                "sameSite": "Lax"
            }
            if expiration.isdigit() and float(expiration) > 0:
                c_dict["expires"] = float(expiration)
            cookies.append(c_dict)
    return cookies


def parse_raw_header_cookies(text: str) -> list[dict]:
    """استخراج الكوكيز إذا قام المستخدم بنسخ سطر الكوكيز من الهيدر (c_user=...; xs=...)."""
    cookies = []
    pairs = text.split(";")
    for p in pairs:
        p = p.strip()
        if not p or "=" not in p:
            continue
        name, val = p.split("=", 1)
        name = name.strip()
        val = val.strip()
        if name:
            cookies.append({
                "name": name,
                "value": val,
                "domain": ".facebook.com",
                "path": "/",
                "secure": True,
                "sameSite": "Lax"
            })
    return cookies


def import_cookies(account_id: str, cookies_content: str) -> int:
    """استيراد الكوكيز من JSON أو صيغة cookies.txt أو سطر الهيدر وحفظها في sessions."""
    cookies_content = cookies_content.strip()
    raw_list = []

    if cookies_content.startswith("[") or cookies_content.startswith("{"):
        try:
            data = json.loads(cookies_content)
            if isinstance(data, dict):
                if "cookiesContent" in data and isinstance(data["cookiesContent"], str):
                    return import_cookies(account_id, data["cookiesContent"])
                raw_list = data.get("cookies", data.get("data", [data]))
            elif isinstance(data, list):
                raw_list = data
        except Exception:
            raw_list = []
    elif "\t" in cookies_content:
        raw_list = parse_netscape_cookies(cookies_content)
    elif "c_user=" in cookies_content or "xs=" in cookies_content:
        raw_list = parse_raw_header_cookies(cookies_content)
    else:
        raw_list = parse_netscape_cookies(cookies_content) or parse_raw_header_cookies(cookies_content)

    clean_cookies = []
    for c in raw_list:
        sc = sanitize_cookie(c)
        if sc:
            clean_cookies.append(sc)

    d = SESSIONS / account_id
    d.mkdir(parents=True, exist_ok=True)
    target_file = d / "cookies.json"
    target_file.write_text(json.dumps(clean_cookies, ensure_ascii=False, indent=2), encoding="utf-8")

    # تحديث قاعدة البيانات
    try:
        from core import db
        db.q("UPDATE accounts SET cookies_valid = 1, status = 'active' WHERE id = ?", (account_id,))
    except Exception:
        pass

    return len(clean_cookies)


async def invalidate_session(account_id: str):
    """إغلاق الجلسة القديمة في الذاكرة لضمان استخدام الكوكيز الجديدة فوراً."""
    global _contexts
    if account_id in _contexts:
        try:
            ctx = _contexts.pop(account_id)
            await ctx.close()
            print(f"🔄 [Session] تم تحديث الجلسة وإعادة ضبط المتصفح للحساب {account_id}")
        except Exception:
            pass


def load_cookies(account_id: str) -> list[dict]:
    f = SESSIONS / account_id / "cookies.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return [sanitize_cookie(c) for c in data if sanitize_cookie(c)]
    except Exception:
        return []


async def get_context(account: dict) -> BrowserContext:
    acc_id = account["id"]
    if acc_id in _contexts:
        try:
            if _contexts[acc_id].pages is not None:
                return _contexts[acc_id]
        except Exception:
            pass

    pw = await get_playwright()
    proxy = None
    if account.get("proxy"):
        p = account["proxy"].strip()
        if "://" in p:
            scheme, rest = p.split("://", 1)
            server_part = rest.split("@")[-1]
            proxy = {"server": f"{scheme}://{server_part}"}
            if "@" in rest:
                creds = rest.split("@")[0]
                if ":" in creds:
                    proxy["username"], proxy["password"] = creds.split(":", 1)

    profile_dir = SESSIONS / acc_id / "browser_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # اكتشاف مسار متصفح Chromium في Termux أو النظام تلقائياً
    import shutil
    import os
    executable_path = None
    termux_chrome = "/data/data/com.termux/files/usr/bin/chromium"
    if os.path.exists(termux_chrome):
        executable_path = termux_chrome
    elif shutil.which("chromium"):
        executable_path = shutil.which("chromium")
    elif shutil.which("chromium-browser"):
        executable_path = shutil.which("chromium-browser")

    # إعدادات متصفح الموبايل المحاكي لبيئة Termux وتطبيق فيسبوك ويب
    launch_kwargs = {
        "user_data_dir": str(profile_dir),
        "headless": True,
        "proxy": proxy,
        "viewport": {"width": 412, "height": 915},
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "locale": "ar-EG,ar;q=0.9,en-US;q=0.8",
        "timezone_id": "Asia/Baghdad",
        "permissions": [],
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
        ]
    }
    if executable_path:
        launch_kwargs["executable_path"] = executable_path

    ctx = await pw.chromium.launch_persistent_context(**launch_kwargs)

    # إخفاء سمة الأتمتة لمنع كشف المتصفح
    await ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)

    # حقن الكوكيز مع آلية حماية Fallback وطباعة الحالة في Termux
    cookies = load_cookies(acc_id)
    added_count = 0
    has_c_user = False
    if cookies:
        for c in cookies:
            if c.get("name") == "c_user":
                has_c_user = True
            try:
                await ctx.add_cookies([c])
                added_count += 1
            except Exception:
                # محاولة ثانية مبسطة بدون القيود الاختيارية
                try:
                    fallback_c = {
                        "name": c["name"],
                        "value": c["value"],
                        "domain": c["domain"],
                        "path": c.get("path", "/"),
                        "secure": True
                    }
                    await ctx.add_cookies([fallback_c])
                    added_count += 1
                except Exception:
                    pass

        print(f"🔑 [Cookies] تم تحميل {added_count}/{len(cookies)} كوكي للحساب {acc_id} (c_user موجود: {has_c_user})")

    _contexts[acc_id] = ctx
    return ctx


async def check_login(account: dict) -> dict:
    """فحص حالة تسجيل دخول الحساب بدقة في واجهة الموبايل."""
    ctx = await get_context(account)
    page = await ctx.new_page()
    try:
        print(f"🔍 [Login Check] جاري فحص جلسة الحساب {account.get('label', account['id'])}...")
        await page.goto("https://m.facebook.com/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        url = page.url.lower()

        # كشف حالات التحقق أو الإيقاف
        if "checkpoint" in url or "disabled" in url or "suspended" in url:
            print("⚠️ [Login Check] الحساب يطلب التحقق الأمني من فيسبوك")
            return {"status": "checkpoint", "ok": False, "message": "الحساب يطلب التحقق أو معلق مؤقتًا"}

        # كشف صفحة تسجيل الدخول
        has_login_box = await page.query_selector("input[name='email'], input#m_login_email, button[name='login']")
        if has_login_box:
            # التحقق مما إذا كانت هناك عناصر feed تدل على تسجيل الدخول الفعلي
            feed_element = await page.query_selector("div[data-sigil='feed-ufi-container'], div[data-sigil='m-timeline-feed'], a[href*='logout'], div[aria-label*='القائمة'], div[role='feed']")
            if not feed_element:
                print("❌ [Login Check] المتصفح لم يتعرف على الجلسة، تأكد من تجديد الكوكيز")
                return {"status": "logged_out", "ok": False, "message": "الجلسة منتهية أو الكوكيز غير صالحة"}

        print("✅ [Login Check] الحساب متصل ونشط بنجاح!")
        return {"status": "active", "ok": True, "message": "الحساب نشط ومتصل بنجاح"}
    except Exception as e:
        print(f"⚠️ [Login Check Exception] {e}")
        return {"status": "error", "ok": False, "message": str(e)[:200]}
    finally:
        await page.close()


async def close_all_sessions():
    for acc_id, ctx in list(_contexts.items()):
        try:
            await ctx.close()
        except Exception:
            pass
    _contexts.clear()
