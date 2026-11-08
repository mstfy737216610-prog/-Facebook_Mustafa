"""
قاعدة بيانات فيسبوك المنفصلة والمحسنة (AdMan FB Memory DB):
- تخزين دائم لمجموعات فيسبوك المستكشفة مع ضمان عدم تكرارها.
- إدارة الحسابات، الكوكيز، البروكسيات، وسجلات النشر الدقيقة.
- فهارس تسريع للأداء وتحمل المهام المتزامنة.
"""
import sqlite3
import json
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "db" / "facebook_memory.db"
_local = threading.local()

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT UNIQUE,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    niche TEXT DEFAULT 'general',          -- masters | phd | services | research | general
    members INTEGER DEFAULT 0,
    account_id TEXT,                       -- الحساب الذي اكتشفها
    status TEXT DEFAULT 'new',             -- new | approved | excluded | joined
    notes TEXT,
    discovered_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_groups_niche ON groups(niche);
CREATE INDEX IF NOT EXISTS idx_groups_status ON groups(status);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE,                       -- مفتاح المنشور في المكتبة
    niche TEXT NOT NULL,                   -- الفئة: masters, phd, services...
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    media_paths TEXT DEFAULT '[]',
    enabled INTEGER DEFAULT 1,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_niche ON posts(niche);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    niche TEXT NOT NULL,
    post_id INTEGER,
    status TEXT DEFAULT 'pending',         -- pending | publishing | done | failed
    target_group TEXT,
    error TEXT,
    run_at REAL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS publish_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    group_url TEXT,
    post_id INTEGER,
    success INTEGER NOT NULL,
    error TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_created ON publish_log(created_at DESC);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    username TEXT,
    proxy TEXT,
    enabled INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',          -- active | stopped | checkpoint | restricted
    cookies_valid INTEGER DEFAULT 0,
    last_checked REAL,
    last_error TEXT,
    created_at REAL NOT NULL
);
"""


def get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return _local.conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    seed_defaults()


def q(sql, params=(), one=False):
    conn = get_conn()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.commit()
    if one:
        return rows[0] if rows else None
    return rows


def add_group(url, name=None, members=0, niche="general", account_id=None, group_id=None):
    clean_url = url.split("?")[0].rstrip("/")
    try:
        q("""INSERT INTO groups (group_id, url, name, niche, members, account_id, status, discovered_at)
             VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
             ON CONFLICT(url) DO UPDATE SET
               name = COALESCE(excluded.name, groups.name),
               members = MAX(groups.members, excluded.members)""",
          (group_id, clean_url, name, niche, members, account_id, time.time()))
        return True
    except Exception:
        return False


def get_groups(niche="", status="", limit=500):
    sql = "SELECT * FROM groups"
    conds = []
    params = []
    if niche:
        conds.append("niche = ?")
        params.append(niche)
    if status:
        conds.append("status = ?")
        params.append(status)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY members DESC, id DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in q(sql, tuple(params))]


def add_post(key, niche, title, text, media_paths=None):
    media_json = json.dumps(media_paths or [], ensure_ascii=False)
    q("""INSERT INTO posts (key, niche, title, text, media_paths, created_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(key) DO UPDATE SET
           title = excluded.title,
           niche = excluded.niche,
           text = excluded.text,
           media_paths = excluded.media_paths""",
      (key, niche, title, text, media_json, time.time()))


def get_posts(niche=""):
    if niche:
        rows = q("SELECT * FROM posts WHERE niche = ? ORDER BY id DESC", (niche,))
    else:
        rows = q("SELECT * FROM posts ORDER BY id DESC")
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["media_paths"] = json.loads(d.get("media_paths") or "[]")
        except Exception:
            d["media_paths"] = []
        out.append(d)
    return out


def save_account(acc):
    q("""INSERT INTO accounts (id, label, username, proxy, enabled, status, cookies_valid, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           label = excluded.label,
           username = excluded.username,
           proxy = excluded.proxy,
           enabled = excluded.enabled,
           status = excluded.status,
           cookies_valid = excluded.cookies_valid""",
      (acc["id"], acc.get("label", ""), acc.get("username"), acc.get("proxy"),
       1 if acc.get("enabled", True) else 0, acc.get("status", "active"),
       1 if acc.get("cookies_valid") else 0, time.time()))


def get_accounts():
    return [dict(r) for r in q("SELECT * FROM accounts ORDER BY created_at DESC")]


def log_publish(account_id, group_url, post_id, success, error=None):
    q("""INSERT INTO publish_log (account_id, group_url, post_id, success, error, created_at)
         VALUES (?, ?, ?, ?, ?, ?)""",
      (account_id, group_url, post_id, 1 if success else 0, error, time.time()))


def get_logs(limit=150):
    return [dict(r) for r in q("SELECT * FROM publish_log ORDER BY id DESC LIMIT ?", (limit,))]


def seed_defaults():
    """تعبئة بيانات نموذجية لمكاتب الخدمات الطلابية إن كانت الجداول فارغة."""
    post_count = q("SELECT COUNT(*) as c FROM posts", one=True)
    if post_count and post_count["c"] == 0:
        sample_posts = [
            {
                "key": "masters_thesis_01",
                "niche": "masters",
                "title": "إعداد وتنسيق رسائل الماجستير والأطروحات العلمية",
                "text": "📚 لطلبة الماجستير والدراسات العليا الأعزاء:\nيسر مكتبنا الأكاديمي تقديم استشارات بحثية شاملة:\n• المساعدة في اقتراح خطط البحث (البروبوزال) المعتمدة\n• التدقيق اللغوي والإملائي الاحترافي (عربي/إنجليزي)\n• التحليل الإحصائي للبيانات ببرامج SPSS و AMOS\n• فحص وتخفيض نسبة الاقتباس الأدبي (Turnitin) بأمانة تامة\n\n📞 للتواصل المباشر عبر واتساب: 009647700000000\nخدماتنا تضمن السرية التامة والالتزام الصارم بالمواعيد الجامعية."
            },
            {
                "key": "phd_defense_01",
                "niche": "phd",
                "title": "دعم متكامل لأبحاث وأطروحات الدكتوراه والنشر في مجلات Scopus",
                "text": "🎓 باحثي ومرشحي الدكتوراه الكرام:\nنوفر لكم دعماً أكاديمياً متخصصاً بإشراف نخبة من الأساتذة:\n• مراجعة الإطار النظري والدراسات السابقة المعاصرة\n• المساعدة في إعادة صياغة الأوراق البحثية للنشر في مجلات Scopus و Clarivate\n• إعداد العروض التقديمية الاحترافية للسيمنار والمناقشة النهائية\n\nللاستفسار والحجز الفوري: واتساب / تليجرام متوفر 24/7."
            },
            {
                "key": "student_services_01",
                "niche": "services",
                "title": "خدمات طلابية جامعية شاملة: تقارير، أبحاث تخرج، وترجمة",
                "text": "🌟 لجميع طلبة الكليات والجامعات:\nأنجز متطلباتك الدراسية بأعلى درجات الإتقان وبأسعار طلابية مخفضة:\n1. إعداد مشاريع التخرج والتقارير العلمية التخصصية\n2. الترجمة الأكاديمية الدقيقة والمعتمدة\n3. تصميم البوسترات العلمية والعروض التقديمية PowerPoint\n4. تلخيص الكتب والمقررات الدراسية بطريقة مبسطة\n\nتواصل معنا الآن واضمن تفوقك الدراسي!"
            }
        ]
        for sp in sample_posts:
            add_post(sp["key"], sp["niche"], sp["title"], sp["text"])

    group_count = q("SELECT COUNT(*) as c FROM groups", one=True)
    if group_count and group_count["c"] == 0:
        sample_groups = [
            ("https://www.facebook.com/groups/masters.iraq.students", "ملتقى طلبة الماجستير والدراسات العليا في العراق", 48500, "masters", "approved"),
            ("https://www.facebook.com/groups/phd.researchers.arab", "رابطة باحثي الدكتوراه والرسائل الجامعية", 62000, "phd", "approved"),
            ("https://www.facebook.com/groups/baghdad.students.services", "خدمات طلبة جامعة بغداد والجامعات العراقية", 39200, "services", "approved"),
            ("https://www.facebook.com/groups/academic.research.assistance", "استشارات البحوث والتحليل الإحصائي SPSS", 27400, "masters", "approved"),
            ("https://www.facebook.com/groups/scopus.publishing.group", "مجموعة النشر العلمي في مجلات سكوبس العالمية", 51800, "phd", "approved"),
            ("https://www.facebook.com/groups/general.college.projects", "مشاريع تخرج وهندسة وحاسبات عام", 18300, "services", "new"),
        ]
        for url, name, members, niche, status in sample_groups:
            q("""INSERT INTO groups (url, name, members, niche, status, discovered_at)
                 VALUES (?, ?, ?, ?, ?, ?)""", (url, name, members, niche, status, time.time()))

    acc_count = q("SELECT COUNT(*) as c FROM accounts", one=True)
    if acc_count and acc_count["c"] == 0:
        save_account({
            "id": "fb_demo_01",
            "label": "حساب فيسبوك 1 (المكتب الرئيسي)",
            "username": "adman_office_1",
            "proxy": "",
            "enabled": True,
            "status": "active",
            "cookies_valid": True
        })
