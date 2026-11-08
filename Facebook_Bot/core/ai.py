"""
محرك الذكاء الاصطناعي لإعادة الصياغة ومنع كشف السبام في فيسبوك:
- يدعم Google Gemini (عبر GEMINI_API_KEY).
- يدعم موفري OpenAI-compatible المسجلين في config/ai.json.
- مزود بمولد بدائل لغوية عربي محلي (Arabic Spintax/Synonym Engine) كصمام أمان فوري
  يحافظ على دقة الأرقام والروابط ومعلومات التواصل 100%.
"""
import os
import re
import json
import random
import requests
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_ai():
    f = ROOT / "config" / "ai.json"
    if not f.exists():
        return {"providers": [], "model": "gemini-3.8-flash"}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return {"providers": [], "model": "gemini-3.8-flash"}


# قواميس التبديل اللغوي الذكي (Arabic Natural Variations)
INTROS = {
    "masters": [
        "لكافة الباحثين وطلاب الدراسات العليا الأعزاء،",
        "إلى إخواننا وأخواتنا طلاب الماجستير الكرام،",
        "يسر مكتبنا المتخصص في الاستشارات الأكاديمية أن يقدم:",
        "فرصة مميزة لطلبة الماجستير والدراسات العليا:",
        "لكل من يبحث عن التميز في رحلته البحثية للماجستير:",
    ],
    "phd": [
        "إلى نخبة الباحثين وطلبة الدكتوراه الكرام،",
        "لكافة الباحثين الساعين لإنجاز أطروحة الدكتوراه باحترافية،",
        "خدمات بحثية وأكاديمية متكاملة لمرشحي الدكتوراه:",
        "نضع بين أيديكم خبراتنا الطويلة في دعم أبحاث الدكتوراه:",
    ],
    "services": [
        "إلى طلابنا وطالباتنا الأعزاء في مختلف الكليات والجامعات،",
        "لكل من يبحث عن الدقة والإنجاز السريع للخدمات الطلابية:",
        "يسعدنا الإعلان عن توفير حزمة الخدمات الأكاديمية والطلابية:",
        "وفر وقتك وجهدك مع خدماتنا الطلابية الشاملة:",
    ],
    "general": [
        "تحية طيبة لأعضاء المجموعة الكرام،",
        "لكل المهتمين بالخدمات الأكاديمية والبحثية المتميزة:",
        "يسرنا أن نشارككم خدماتنا المتخصصة بأعلى معايير الجودة:",
    ]
}

SYNONYMS = [
    (r"بأعلى جودة", ["بأعلى معايير الجودة", "بجودة ودقة متناهية", "بإتقان احترافي"]),
    (r"بأسعار مناسبة", ["بأسعار منافسة وفي متناول الجميع", "بتكلفة ملائمة ومناسبة للطلاب", "بأفضل الأسعار التنافسية"]),
    (r"للتواصل", ["للحجز والاستفسار", "للتواصل والمراسلة المباشرة", "لطلب الخدمة أو الاستفسار"]),
    (r"يسعدنا", ["يسرنا ويشرفنا", "نرحب بكم ويسعدنا", "يسر مكتبنا"]),
    (r"أطروحة", ["أطروحة ورسالة", "الأطروحة والبحث العلمي", "رسالة"]),
    (r"مساعدة", ["دعم واستشارات", "مساندة وإشراف", "خدمات"]),
    (r"في أسرع وقت", ["خلال وقت قياسي", "بأسرع مدة ممكنة", "بالمواعيد المحددة دون تأخير"]),
]

OUTROS = [
    "نتمنى التوفيق والنجاح الدائم لجميع الباحثين والطلبة الأعزاء.",
    "فريق عملنا متواجد على مدار الساعة للرد على كافة استفساراتكم.",
    "معاً نحو مستقبل أكاديمي مشرق ونجاح مستمر.",
    "هدفنا رضاكم وإنجازكم بالدقة المطلوبة.",
]


def local_arabic_spin(text: str, group_name: str = "", niche: str = "general") -> str:
    """إعادة صياغة ذكية محلية تحافظ على الروابط والأرقام وتغير أسلوب النص لمنع السبام."""
    res = text

    # استبدال المرادفات باحتمال عشوائي
    for pattern, choices in SYNONYMS:
        if re.search(pattern, res):
            choice = random.choice(choices)
            res = re.sub(pattern, choice, res, count=1)

    # اختيار مقدمة مناسبة
    intro_list = INTROS.get(niche, INTROS["general"])
    intro = random.choice(intro_list)

    outro = random.choice(OUTROS)

    # بناء النص النهائي المتغير
    if group_name and "مجموعة" not in text and random.random() < 0.4:
        header = f"{intro}\nتحية خاصة لأسرة {group_name}\n\n"
    else:
        header = f"{intro}\n\n"

    footer = f"\n\n{outro}"
    return f"{header}{res.strip()}{footer}"


def rewrite_for_group(text: str, group_name: str = "", niche: str = "general") -> str:
    """
    إعادة صياغة متقدمة تجمع بين الذكاء السحابي والاحتياطي المحلي:
    1. محاولة استخدام Google Gemini إن وُجد مفتاح.
    2. محاولة استخدام الموفرين المهيئين في config/ai.json.
    3. العودة لصمام الأمان المحلي اللغوي لضمان استمرار الحملة دون توقف.
    """
    prompt = (
        f"أنت خبير صياغة منشورات تسويقية لمكتب خدمات أكاديمية وطلابية.\n"
        f"المهمة: أعد صياغة هذا المنشور بأسلوب احترافي وجذاب ومختلف تماماً لتفادي تكرار النص، "
        f"مع الحفاظ حرفياً ودون أي تحريف على: أرقام الهواتف، روابط واتساب، الأسماء، التخصصات، وأي روابط مرفقة.\n"
        f"المجموعة المستهدفة: {group_name or 'مجموعة عامة'} (الفئة: {niche}).\n\n"
        f"المنشور الأصلي:\n{text}\n\n"
        f"أعطني نص المنشور المعاد صياغته فقط دون أي شروح إضافية أو مقدمات مثل 'بالتأكيد'."
    )

    # 1. محاولة Google Gemini عبر بيئة النظام
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
            }
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                candidate = data.get("candidates", [{}])[0]
                part = candidate.get("content", {}).get("parts", [{}])[0]
                out = part.get("text", "").strip()
                if len(out) > len(text) * 0.4:
                    return out
        except Exception as ge:
            pass

    # 2. فحص موفري ai.json
    cfg = _load_ai()
    providers = sorted([p for p in cfg.get("providers", []) if p.get("enabled") and p.get("api_key")],
                       key=lambda x: x.get("priority", 99))

    for p in providers:
        try:
            r = requests.post(
                p["base_url"].rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {p['api_key']}", "Content-Type": "application/json"},
                json={
                    "model": cfg.get("model", "glm-5.3-flash"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.6,
                    "max_tokens": 1500
                },
                timeout=25
            )
            if r.status_code == 200:
                out = r.json()["choices"][0]["message"]["content"].strip()
                if len(out) > len(text) * 0.4:
                    return out
        except Exception:
            time.sleep(0.5)

    # 3. صمام الأمان الفوري: التبديل المحلي عالي التوافق
    return local_arabic_spin(text, group_name, niche)
