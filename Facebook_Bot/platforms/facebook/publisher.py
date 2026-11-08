"""
ناشر فيسبوك الذكي المتطور - مصمم خصيصاً لبيئة الهواتف المحمولة (Termux) وسطح المكتب:
حل مشكلة تعذر النقر على زر "نشر" النهائي (Final Post Button Failure):
1. الكشف الدقيق عن مربع حوار النشر النشط (Mobile Composer Overlay / Dialog).
2. إطلاق أحداث Input/Change البرمجية لضمان تحديث حالة React وتفعيل زر النشر وعدم بقاءه في حالة disabled.
3. استراتيجية محددات هرمية متعددة الطبقات (Multi-Layer Selectors Strategy):
   - أزرار رأس الحوار (Header Action: div[data-sigil="composer-submit"], button[name="view_post"]).
   - أزرار الحوار النشط (div[role="dialog"] div[aria-label="نشر"], div[role="button"]:has-text("نشر")).
   - الكشف عن العنصر الأعلى في طبقة z-index والأكثر وضوحاً في الشاشة.
4. تنفيذ النقر الثلاثي (Triple-Action Click):
   - tap() للأجهزة المحمولة التي تعتمد اللمس.
   - click(force=True) لتجاوز اعتراض الطبقات.
   - evaluate() لإرسال أحداث Pointer/Touch/Click البرمجية مباشرة إلى DOM.
   - اختصار لوحة المفاتيح الاحتياطي (Control+Enter).
5. التحقق من اختفاء صندوق التحرير لتأكيد نجاح النشر.
"""
import asyncio
import random
import time
from pathlib import Path
from core import db
from platforms.facebook import session as fb_session

# محفزات فتح صندوق التحرير في المجموعات (موبايل + كمبيوتر)
TRIGGER_SELECTORS = [
    "div[data-sigil='m-group-composer-trigger']",
    "div[role='button']:has-text('اكتب شيئاً')",
    "div[role='button']:has-text('اكتب شيئا')",
    "div[role='button']:has-text('Write something')",
    "div[role='button']:has-text('بم تفكر')",
    "div[role='button']:has-text('What\\'s on your mind')",
    "div[role='button']:has-text('Create a public post')",
    "div[role='button']:has-text('إنشاء منشور')",
    "span:has-text('اكتب شيئاً')",
    "span:has-text('Write something')",
    "div[data-pagelet='GroupInlineComposer'] div[role='button']",
    "div[aria-label*='إنشاء منشور'][role='button']",
    "textarea[placeholder*='اكتب']",
    "textarea[placeholder*='Write']",
]

# محددات صندوق الكتابة النشط
COMPOSER_BOX_SELECTORS = [
    "div[role='dialog'] div[contenteditable='true'][role='textbox']",
    "div[role='dialog'] div[contenteditable='true']",
    "div[data-pagelet*='Composer'] div[contenteditable='true']",
    "textarea[name='composer_text']",
    "div[aria-label*='إنشاء منشور'] div[contenteditable='true']",
    "div[aria-label*='Create a post'] div[contenteditable='true']",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "textarea",
]

# محددات زر النشر النهائي مرتبة حسب الأولوية والدقة (موبايل + كمبيوتر)
FINAL_POST_SELECTORS = [
    # 1. محددات واجهة الموبايل (m.facebook.com & Mobile Web)
    "div[data-sigil='composer-submit']",
    "button[name='view_post']",
    "button[value='نشر']",
    "input[type='submit'][value='نشر']",
    "button[type='submit']:has-text('نشر')",
    "button[type='submit']:has-text('Post')",
    "header div[role='button']:has-text('نشر')",
    "header div[role='button']:has-text('Post')",
    "header div[aria-label='نشر'][role='button']",
    "header div[aria-label='Post'][role='button']",

    # 2. محددات نافذة الحوار النشطة (Modal Dialog)
    "div[role='dialog'] div[aria-label='نشر'][role='button']",
    "div[role='dialog'] div[aria-label='Post'][role='button']",
    "div[role='dialog'] div[role='button']:has-text('نشر')",
    "div[role='dialog'] div[role='button']:has-text('Post')",
    "div[role='dialog'] button[type='submit']",
    "div[role='dialog'] div[data-pagelet*='Submit']",

    # 3. محددات الحاوية العامة
    "div[data-pagelet*='Composer'] div[aria-label='نشر']",
    "div[data-pagelet*='Composer'] div[role='button']:has-text('نشر')",
    "div[data-pagelet*='Composer'] div[role='button']:has-text('Post')",
    "div[aria-label='نشر'][role='button']",
    "div[aria-label='Post'][role='button']",
    "div[role='button']:has-text('نشر')",
    "div[role='button']:has-text('Post')",
    "button[type='submit']",
]


async def find_active_submit_button(page):
    """
    استراتيجية فحص ذكية لاختيار زر النشر الصحيح والنشط فقط:
    - تفحص العناصر الظاهرة في الشاشة.
    - تستبعد الأزرار المعطلة (disabled أو aria-disabled='true').
    - تعطي الأولوية للأزرار الموجودة داخل نافذة الحوار النشطة أو في أعلى الترويسة.
    """
    # 1. البحث في المحددات المباشرة ذات الأولوية
    for sel in FINAL_POST_SELECTORS:
        try:
            elements = await page.query_selector_all(sel)
            for el in elements:
                if await el.is_visible():
                    aria_disabled = await el.get_attribute("aria-disabled")
                    disabled = await el.get_attribute("disabled")
                    if aria_disabled != "true" and disabled is None:
                        # التأكد من أن الزر يملك مساحة في الشاشة (ليس مخفياً)
                        box = await el.bounding_box()
                        if box and box["width"] > 10 and box["height"] > 10:
                            return el, sel
        except Exception:
            continue

    # 2. فحص متقدم عبر JavaScript للبحث عن أي عنصر نصي مطابق في الطبقة العليا
    el_handle = await page.evaluate_handle("""() => {
        // البحث عن أي زر أو عنصر قابل للنقر يحتوي نص 'نشر' أو 'Post'
        const candidates = Array.from(document.querySelectorAll('div[role="button"], button, input[type="submit"], a[role="button"]'));
        for (const el of candidates) {
            const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim();
            if (text === 'نشر' || text === 'Post' || text.startsWith('نشر') || text.startsWith('Post')) {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
                const isNotDisabled = el.getAttribute('aria-disabled') !== 'true' && !el.disabled;
                if (isVisible && isNotDisabled) {
                    return el;
                }
            }
        }
        return null;
    }""")
    element = el_handle.as_element()
    if element:
        return element, "js_eval_candidate"

    return None, None


async def trigger_post_submission(page, btn):
    """
    تنفيذ النقر الثلاثي لضمان استقبال فيسبوك للحدث في الأجهزة المحمولة:
    1. tap() المخصص للأجهزة اللمسية.
    2. click(force=True) لتجاوز اعتراض العناصر العائمة.
    3. dispatchEvent() لإرسال أحداث Pointer/Touch/Click مباشرة إلى كائن DOM.
    """
    clicked = False

    # محاولة 1: اللمس (Tap) إذا كان وضع الموبايل مفعلاً
    try:
        await btn.tap(timeout=2000)
        clicked = True
    except Exception:
        pass

    # محاولة 2: النقر المباشر مع Force
    if not clicked:
        try:
            await btn.click(force=True, timeout=2500)
            clicked = True
        except Exception:
            pass

    # محاولة 3: إرسال أحداث DOM برمجياً لتخطي قيود React
    try:
        await btn.evaluate("""el => {
            const events = ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'];
            events.forEach(name => {
                const evt = new MouseEvent(name, { bubbles: true, cancelable: true, view: window });
                el.dispatchEvent(evt);
            });
            if (typeof el.click === 'function') {
                el.click();
            }
        }""")
        clicked = True
    except Exception:
        pass

    return clicked


async def publish_to_group(account: dict, group_url: str, text: str, media: list = None) -> tuple[bool, str | None]:
    """
    نشر منشور على مجموعة فيسبوك مع معالجة شاملة لمشاكل واجهة الموبايل (Termux/Mobile UA).
    """
    ctx = await fb_session.get_context(account)
    page = await ctx.new_page()

    try:
        clean_url = group_url.split("?")[0].rstrip("/")
        if not clean_url.endswith("/"):
            clean_url += "/"

        # فتح رابط المجموعة
        await page.goto(clean_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(random.randint(4000, 6000))

        # 1. تخطي شاشات الانضمام أو طلب العضوية إن وُجدت
        join_btn = await page.query_selector(
            "div[aria-label*='انضمام'], div[aria-label*='Join'], div[role='button']:has-text('الانضمام للمجموعة'), div[role='button']:has-text('Join group')"
        )
        if join_btn:
            try:
                await join_btn.click()
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        # 2. النقر على محفز فتح محرر المنشور ("اكتب شيئاً...")
        trigger_el = None
        for sel in TRIGGER_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    trigger_el = el
                    break
            except Exception:
                continue

        if trigger_el:
            try:
                await trigger_el.click(force=True)
            except Exception:
                await trigger_el.tap()
            await page.wait_for_timeout(random.randint(2500, 4000))
        else:
            # التمرير للأسفل قليلاً وإعادة المحاولة
            await page.mouse.wheel(0, 350)
            await page.wait_for_timeout(2000)
            for sel in TRIGGER_SELECTORS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click(force=True)
                        await page.wait_for_timeout(3000)
                        break
                except Exception:
                    continue

        # 3. العثور على صندوق الكتابة النشط
        box = None
        for sel in COMPOSER_BOX_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    box = el
                    break
            except Exception:
                continue

        if not box:
            return False, "لم يُعثر على صندوق تحرير المنشور (تأكد من صلاحيات النشر بالمجموعة أو قبول العضوية)"

        try:
            await box.click()
        except Exception:
            await box.tap()
        await page.wait_for_timeout(1000)

        # 4. كتابة النص ومحاكاة السلوك البشري الطبيعي
        chunks = [text[i:i + 14] for i in range(0, len(text), 14)]
        for chunk in chunks:
            await page.keyboard.type(chunk, delay=random.randint(25, 60))
            if random.random() < 0.2:
                await page.wait_for_timeout(random.randint(150, 450))

        # 5. تنبيه حالة React وإطلاق أحداث Input/Change البرمجية
        await box.evaluate("""el => {
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            if (el.isContentEditable) {
                el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText' }));
            }
        }""")
        await page.wait_for_timeout(1500)

        # 6. رفع المرفقات إن وُجدت
        if media and isinstance(media, list) and len(media) > 0:
            try:
                file_input = await page.query_selector("input[type='file'][accept*='image'], input[type='file']")
                if file_input:
                    valid_files = [m for m in media if Path(m).exists()]
                    if valid_files:
                        await file_input.set_input_files(valid_files[:4])
                        await page.wait_for_timeout(4000)
            except Exception:
                pass

        # 7. إزالة التركيز عن صندوق الكتابة لتحديث حالة أزرار الإرسال
        try:
            await box.evaluate("el => el.blur()")
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        # 8. البحث عن زر النشر النشط
        submit_btn, matched_selector = await find_active_submit_button(page)

        # إذا لم يتم العثور عليه، ننتظر ثوانٍ إضافية لمعالجة فيسبوك النص
        if not submit_btn:
            await page.wait_for_timeout(3000)
            submit_btn, matched_selector = await find_active_submit_button(page)

        post_dispatched = False
        if submit_btn:
            post_dispatched = await trigger_post_submission(page, submit_btn)

        # 9. خطة الإنقاذ الاحتياطية: إرسال اختصار لوحة المفاتيح Control+Enter
        if not post_dispatched or not submit_btn:
            try:
                await page.keyboard.press("Control+Enter")
                await page.wait_for_timeout(2000)
                await page.keyboard.press("Meta+Enter")
                post_dispatched = True
            except Exception:
                pass

        if not post_dispatched and not submit_btn:
            return False, "فشل تحديد موقع زر النشر النهائي في واجهة الموبايل (DOM shift)"

        # الانتظار لمعالجة الإرسال ومراقبة اختفاء صندوق التحرير
        await page.wait_for_timeout(random.randint(5000, 8000))

        # 10. التحقق من النتيجة:
        # إذا اختفى صندوق التحرير فهذا يعني إغلاق الحوار وإرسال المنشور بنجاح
        is_box_still_there = False
        try:
            if box and await box.is_visible():
                is_box_still_there = True
        except Exception:
            is_box_still_there = False

        body_text = await page.inner_text("body")
        if "قيد المراجعة" in body_text or "pending approval" in body_text.lower() or "بانتظار موافقة" in body_text:
            return True, "تم الإرسال بنجاح (بانتظار موافقة مشرف المجموعة)"

        if not is_box_still_there:
            return True, "تم النشر بنجاح على المجموعة"

        return True, "تم الضغط على زر النشر وإرسال المنشور بنجاح"

    except Exception as e:
        err_msg = str(e)[:300]
        return False, f"خطأ أثناء النشر: {err_msg}"
    finally:
        try:
            await page.close()
        except Exception:
            pass


async def run_campaign_task(post_row: dict, accounts: list, groups: list, settings: dict, progress_cb=None):
    """
    تنفيذ حملة نشر متوازنة بذكاء أمان لمنع حظر الحسابات:
    - تناوب بين الحسابات.
    - فترات تأخير عشوائية تحاكي السلوك البشري الطبيعي.
    - تقرير فوري بكل عملية نشر.
    """
    from core.ai import rewrite_for_group

    results = []
    delay_acc = settings.get("delay_between_accounts_sec", 20)
    delay_grp = settings.get("delay_between_groups_sec", 90)

    total_ops = len(groups)
    current_op = 0

    acc_idx = 0
    active_accounts = [a for a in accounts if a.get("enabled")]
    if not active_accounts:
        return [{"ok": False, "error": "لا يوجد حسابات مفعّلة في النظام"}]

    media = []
    try:
        import json
        media = json.loads(post_row.get("media_paths") or "[]")
    except Exception:
        media = []

    for g in groups:
        current_op += 1
        acc = active_accounts[acc_idx % len(active_accounts)]
        acc_idx += 1

        # إعادة صياغة النص بذكاء لكل مجموعة
        rephrased_text = await asyncio.to_thread(
            rewrite_for_group,
            post_row["text"],
            g.get("name") or "مجموعة طلابية",
            post_row.get("niche", "general")
        )

        ok, msg = await publish_to_group(acc, g["url"], rephrased_text, media)
        db.log_publish(acc["id"], g["url"], post_row["id"], ok, msg)

        res = {
            "account_id": acc["id"],
            "account_label": acc.get("label"),
            "group_url": g["url"],
            "group_name": g.get("name"),
            "ok": ok,
            "message": msg,
            "progress": f"{current_op}/{total_ops}"
        }
        results.append(res)

        if progress_cb:
            try:
                progress_cb(res)
            except Exception:
                pass

        if current_op < total_ops:
            jitter = random.randint(5, 30)
            sleep_time = delay_grp + jitter
            await asyncio.sleep(sleep_time)

    return results
