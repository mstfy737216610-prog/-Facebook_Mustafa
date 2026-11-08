"""
ناشر فيسبوك الذكي المتطور:
- يتعامل مع واجهات فيسبوك الحديثة (سطح المكتب والموبايل).
- ينقر أولاً على محفز كتابة المنشور ("اكتب شيئاً..." / "What's on your mind?").
- ينتظر ظهور صندوق التحرير النموذجي (Modal Composer).
- يكتب بسرعة بشرية واقعية متغيرة مع فترات توقف صغيرة.
- يرفع المرفقات (إن وُجدت).
- يضغط زر النشر ويتأكد من إرسال المنشور أو وضعه قيد موافقة المشرف.
"""
import asyncio
import random
import time
from core import db
from platforms.facebook import session as fb_session

TRIGGER_SELECTORS = [
    # محفزات فتح صندوق النشر في المجموعات (عربي وإنجليزي)
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
]

COMPOSER_SELECTORS = [
    "div[role='dialog'] div[contenteditable='true'][role='textbox']",
    "div[aria-label*='إنشاء منشور'] div[contenteditable='true']",
    "div[aria-label*='Create a post'] div[contenteditable='true']",
    "div[contenteditable='true'][role='textbox']",
    "div[contenteditable='true']",
    "textarea[name='composer_text']",
]

SUBMIT_SELECTORS = [
    "div[role='dialog'] div[aria-label='نشر'][role='button']",
    "div[role='dialog'] div[aria-label='Post'][role='button']",
    "div[role='dialog'] div[role='button']:has-text('نشر')",
    "div[role='dialog'] div[role='button']:has-text('Post')",
    "div[aria-label='نشر'][role='button']",
    "div[aria-label='Post'][role='button']",
    "button[type='submit']",
]


async def publish_to_group(account: dict, group_url: str, text: str, media: list = None) -> tuple[bool, str | None]:
    """
    نشر منشور على مجموعة فيسبوك مع التحقق من الصلاحيات وواجهة التحرير.
    يرجع (نجاح/فشل, رسالة_خطأ_أو_ملاحظة).
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

        # التحقق مما إذا كانت المجموعة تتطلب الانضمام أولاً
        join_btn = await page.query_selector("div[aria-label*='انضمام'], div[aria-label*='Join'], div[role='button']:has-text('الانضمام للمجموعة'), div[role='button']:has-text('Join group')")
        if join_btn:
            # زر الانضمام ظاهر ويعني أن الحساب ليس عضواً كاملاً بعد
            try:
                # نختبر إذا كان يمكن النشر رغم ذلك أو نطلب الانضمام
                await join_btn.click()
                await page.wait_for_timeout(2000)
            except Exception:
                pass

        # البحث عن محفز فتح محرر المنشور والنقر عليه
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
            await trigger_el.click()
            await page.wait_for_timeout(random.randint(2000, 3500))
        else:
            # محاولة التمرير لأسفل قليلاً والبحث ثانية
            await page.mouse.wheel(0, 400)
            await page.wait_for_timeout(2000)
            for sel in TRIGGER_SELECTORS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        trigger_el = el
                        await trigger_el.click()
                        await page.wait_for_timeout(2500)
                        break
                except Exception:
                    continue

        # العثور على صندوق الكتابة النشط
        box = None
        for sel in COMPOSER_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    box = el
                    break
            except Exception:
                continue

        if not box:
            return False, "لم يُعثر على صندوق تحرير المنشور (قد تكون المجموعة مقيدة للمشرفين فقط أو تحتاج قبول العضوية)"

        await box.click()
        await page.wait_for_timeout(1000)

        # محاكاة كتابة واقعية ومقسمة مع تأخيرات بشرية
        chunks = [text[i:i + 12] for i in range(0, len(text), 12)]
        for chunk in chunks:
            await page.keyboard.type(chunk, delay=random.randint(25, 65))
            if random.random() < 0.25:
                await page.wait_for_timeout(random.randint(200, 600))

        # رفع المرفقات إن توفرت
        if media and isinstance(media, list) and len(media) > 0:
            try:
                file_input = await page.query_selector("input[type='file'][accept*='image'], input[type='file']")
                if file_input:
                    valid_files = [m for m in media if Path(m).exists()]
                    if valid_files:
                        await file_input.set_input_files(valid_files[:4])
                        await page.wait_for_timeout(4000)
            except Exception as me:
                print(f"[Warning] Media upload skipped: {me}")

        await page.wait_for_timeout(random.randint(2000, 4000))

        # البحث عن زر النشر
        submit_btn = None
        for sel in SUBMIT_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    # التحقق أن الزر غير معطل
                    aria_disabled = await el.get_attribute("aria-disabled")
                    disabled = await el.get_attribute("disabled")
                    if aria_disabled != "true" and disabled is None:
                        submit_btn = el
                        break
            except Exception:
                continue

        if not submit_btn:
            # ربما زر النشر هو Enter أو اختصار أو selector بديل
            return False, "لم يُعثر على زر تأكيد النشر مفعلاً بعد كتابة المحتوى"

        await submit_btn.click()
        await page.wait_for_timeout(random.randint(5000, 8000))

        # فحص رسائل الملاحظات مثل "منشورك بانتظار المشرف"
        body_text = await page.inner_text("body")
        if "قيد المراجعة" in body_text or "pending approval" in body_text.lower() or "بانتظار موافقة" in body_text:
            return True, "تم الإرسال بنجاح (بانتظار موافقة مشرف المجموعة)"

        return True, "تم النشر بنجاح على المجموعة"

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
