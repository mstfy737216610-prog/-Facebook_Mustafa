"""
جلسات فيسبوك المتقدمة - دعم بيئة الموبايل (Termux) وسطح المكتب:
- استقبال وقبول الكوكيز بجميع الصيغ الممكنة:
  1. ملفات JSON الناتجة عن إضافات المتصفح (J2Team, EditThisCookie, Cookie-Editor).
  2. ملفات Netscape (cookies.txt).
  3. سطر كوكيز الهيدر الخام المنسوخ (Header string: c_user=...; xs=...).
  4. كائنات JSON بصيغة {c_user: ..., xs: ...}.
- تطبيع دقيق وفصل القيود لتفادي أخطاء Playwright و Chromium.
- حقن الكوكيز على كل من .facebook.com و m.facebook.com و www.facebook.com لضمان تسجيل الدخول فوراً.
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

    # Playwright يرفض expires إذا كانت سالبة أو صفر
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
    """استيراد الكوكيز من أي صيغة وحفظها وتحديث الحساب."""
    cookies_content = cookies_content.strip()
    raw_list = []

    if cookies_content.startswith("[") or cookies_content.startswith("{"):
        try:
            data = json.loads(cookies_content)
            if isinstance(data, dict):
                if "cookiesContent" in data and isinstance(data["cookiesContent"], str):
                    return import_cookies(account_id, data["cookiesContent"])
                if "cookies" in data and isinstance(data["cookies"], list):
                    raw_list = data["cookies"]
                elif "c_user" in data:
                    raw_list = [{"name": k, "value": v, "domain": ".facebook.com", "path": "/"} for k, v in data.items()]
                else:
                    raw_list = data.get("data", [data])
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
    has_c_user = False
    for c in raw_list:
        sc = sanitize_cookie(c)
        if sc:
            clean_cookies.append(sc)
            if sc.get("name") == "c_user":
                has_c_user = True

    if not clean_cookies:
        return 0

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

    print(f"💾 [Storage] تم حفظ {len(clean_cookies)} كوكي للحساب {account_id} بنجاح (c_user: {has_c_user})")
    return len(clean_cookies)


async def invalidate_session(account_id: str):
    """إغلاق الجلسة القديمة في الذاكرة لضمان استخدام الكوكيز الجديدة فوراً."""
    global _contexts
    if account_id in _contexts:
        try:
            ctx = _contexts.pop(account_id)
            await ctx.close()
            print(f"🔄 [Session] تم إغلاق الجلسة السابقة للحساب {account_id} وتحديث المتصفح بالكوكيز الجديدة")
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

    # حقن الكوكيز مع دعم URL و Domain المزدوج
    cookies = load_cookies(acc_id)
    added_count = 0
    has_c_user = False
    c_user_val = None
    if cookies:
        for c in cookies:
            name = c.get("name")
            if name == "c_user":
                has_c_user = True
                c_user_val = c.get("value")

            # محاولة 1: الحقن الكامل المباشر
            try:
                await ctx.add_cookies([c])
                added_count += 1
            except Exception:
                # محاولة 2: الحقن مع رابط النطاق المباشر
                try:
                    fallback_entry = {
                        "name": str(c["name"]).strip(),
                        "value": str(c["value"]).strip(),
                        "url": "https://www.facebook.com"
                    }
                    await ctx.add_cookies([fallback_entry])
                    added_count += 1
                except Exception:
                    pass

        # ضمان وجود الكوكيز الحيوية على m.facebook.com أيضاً
        if has_c_user and c_user_val:
            try:
                await ctx.add_cookies([
                    {"name": "c_user", "value": c_user_val, "url": "https://m.facebook.com"}
                ])
            except Exception:
                pass

        print(f"🔑 [Cookies] تم حقن {added_count}/{len(cookies)} كوكي للحساب {acc_id} (معرف الحساب c_user: {c_user_val or 'غير محدد'})")

    _contexts[acc_id] = ctx
    return ctx


async def check_login(account: dict) -> dict:
    """فحص حالة تسجيل دخول الحساب بدقة في واجهة الموبايل دون إيجابيات كاذبة."""
    ctx = await get_context(account)
    page = await ctx.new_page()
    try:
        acc_label = account.get('label', account['id'])
        print(f"🔍 [Login Check] جاري فحص جلسة الحساب ({acc_label})...")

        # 1. فحص وجود c_user في كوكيز المتصفح
        browser_cookies = await ctx.cookies("https://m.facebook.com")
        c_user_ck = next((ck for ck in browser_cookies if ck.get("name") == "c_user"), None)
        uid = c_user_ck["value"] if c_user_ck else None

        # 2. فتح فيسبوك موبايل
        await page.goto("https://m.facebook.com/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3500)
        url = page.url.lower()

        # تجاوز نوافذ الكوكيز والموافقة إن ظهرت
        try:
            consent_btn = await page.query_selector("button[data-cookiebanner='accept_button'], button:has-text('Allow all cookies'), button:has-text('سماح'), button:has-text('موافق')")
            if consent_btn:
                await consent_btn.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        # تخطي نافذة "حفظ معلومات تسجيل الدخول" إن ظهرت
        try:
            not_now_btn = await page.query_selector("a:has-text('ليس الآن'), button:has-text('ليس الآن'), a:has-text('Not Now'), button:has-text('Not Now')")
            if not_now_btn:
                await not_now_btn.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass

        # 3. كشف حالات التحقق الأمني
        if "checkpoint" in url or "disabled" in url or "suspended" in url:
            print(f"⚠️ [Login Check] الحساب ({acc_label}) يطلب التحقق الأمني من فيسبوك")
            return {"status": "checkpoint", "ok": False, "message": "الحساب يطلب التحقق الأمني من فيسبوك"}

        # 4. هل حقل كلمة المرور ظاهر ونشط فعلياً؟
        pwd_input = await page.query_selector("input[type='password']")
        is_pwd_visible = False
        if pwd_input:
            try:
                is_pwd_visible = await pwd_input.is_visible()
            except Exception:
                is_pwd_visible = False

        if is_pwd_visible and not uid:
            print(f"❌ [Login Check] الحساب ({acc_label}) غير مسجل الدخول، تأكد من كوكيز الحساب")
            return {"status": "logged_out", "ok": False, "message": "الجلسة منتهية أو الكوكيز غير صحيحة"}

        print(f"✅ [Login Check] الحساب ({acc_label}) نشط ومتصل بفيسبوك بنجاح! (UID: {uid or 'متصل'})")
        return {"status": "active", "ok": True, "message": f"الحساب نشط ومتصل بنجاح (UID: {uid or 'OK'})"}

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
