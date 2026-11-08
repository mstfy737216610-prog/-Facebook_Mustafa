"""
واجهة فيسبوك المحسنة: إدارة الحسابات، الكوكيز، المجموعات، مكتبة المنشورات، ومحاكي الحملات.
"""
import json
import secrets
import time
import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core import db
from platforms.facebook import groups_discovery, publisher
from platforms.facebook.session import import_cookies, check_login
from core.ai import rewrite_for_group

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="AdMan Facebook Enterprise", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "web" / "static"), name="static")

_sessions = set()
_running_campaign = {"active": False, "task": None, "results": [], "total": 0, "current": 0}


def _auth(request: Request):
    token = request.headers.get("X-Auth-Token") or request.query_params.get("token")
    if token not in _sessions:
        raise HTTPException(401, detail="Unauthorized")


@app.on_event("startup")
async def startup():
    db.init_db()


@app.post("/api/login")
async def login(payload: dict):
    pw = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))["system"]["web_password"]
    if payload.get("password") == pw:
        t = secrets.token_hex(16)
        _sessions.add(t)
        return {"ok": True, "token": t}
    raise HTTPException(401, detail="Invalid password")


@app.get("/", response_class=HTMLResponse)
async def index():
    return (ROOT / "web" / "static" / "index.html").read_text(encoding="utf-8")


def _settings():
    return json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))


@app.get("/api/accounts")
async def get_accounts(request: Request):
    _auth(request)
    return db.get_accounts()


@app.post("/api/accounts")
async def save_account(acc: dict, request: Request):
    _auth(request)
    if not acc.get("id"):
        acc["id"] = "fb_" + uuid.uuid4().hex[:8]
    db.save_account(acc)
    return {"ok": True, "id": acc["id"]}


@app.delete("/api/accounts/{acc_id}")
async def del_account(acc_id: str, request: Request):
    _auth(request)
    db.q("DELETE FROM accounts WHERE id=?", (acc_id,))
    return {"ok": True}


@app.post("/api/accounts/{acc_id}/cookies")
async def upload_cookies(acc_id: str, request: Request, file: UploadFile = None):
    """رفع أو لصق كوكيز فيسبوك (JSON أو Netscape cookies.txt أو Header string) وتطبيعها."""
    _auth(request)
    content = ""
    if file:
        content = (await file.read()).decode("utf-8", "ignore")
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                content = body.get("cookiesContent") or body.get("cookies") or json.dumps(body)
                if isinstance(content, (list, dict)):
                    content = json.dumps(content)
            elif isinstance(body, list):
                content = json.dumps(body)
            else:
                content = str(body)
        except Exception:
            body_bytes = await request.body()
            content = body_bytes.decode("utf-8", "ignore")

    count = import_cookies(acc_id, content)
    if count > 0:
        await fb_session.invalidate_session(acc_id)
        db.q("UPDATE accounts SET cookies_valid=1, status='active' WHERE id=?", (acc_id,))
        return {"ok": True, "cookies_count": count, "message": f"تم حفظ وتطبيع {count} كوكي بنجاح وتحديث المتصفح"}
    return {"ok": False, "error": "لم يتم العثور على كوكيز صالحة. تأكد من الصيغة (JSON أو cookies.txt أو c_user=...)"}


@app.post("/api/accounts/{acc_id}/check")
async def test_account_session(acc_id: str, request: Request):
    """اختبار جلسة الحساب المباشرة والتأكد من عدم وجود حظر أو طلب تحقق."""
    _auth(request)
    acc = next((a for a in db.get_accounts() if a["id"] == acc_id), None)
    if not acc:
        raise HTTPException(404, detail="Account not found")
    status = await check_login(acc)
    new_status = "active" if status["ok"] else ("checkpoint" if status.get("status") == "checkpoint" else "stopped")
    db.q("UPDATE accounts SET status=?, last_checked=?, last_error=? WHERE id=?",
         (new_status, time.time(), status.get("message"), acc_id))
    return status


@app.post("/api/accounts/{acc_id}/discover")
async def discover(acc_id: str, request: Request, payload: dict = None):
    """اكتشاف مجموعات جديدة بناء على الكلمات المفتاحية."""
    _auth(request)
    acc = next((a for a in db.get_accounts() if a["id"] == acc_id), None)
    if not acc:
        raise HTTPException(404, detail="Account not found")
    kw = (payload or {}).get("keywords") or None
    try:
        n = await groups_discovery.discover(acc, kw)
        return {"ok": True, "new_groups": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/groups")
async def get_groups(request: Request, niche: str = "", status: str = ""):
    _auth(request)
    return db.get_groups(niche=niche, status=status)


@app.post("/api/groups/{gid}/{action}")
async def group_action(gid: int, action: str, request: Request, payload: dict = None):
    _auth(request)
    if action == "approve":
        db.q("UPDATE groups SET status='approved' WHERE id=?", (gid,))
    elif action == "exclude":
        db.q("UPDATE groups SET status='excluded' WHERE id=?", (gid,))
    elif action == "set_niche" and payload:
        db.q("UPDATE groups SET niche=? WHERE id=?", (payload.get("niche", "general"), gid))
    elif action == "delete":
        db.q("DELETE FROM groups WHERE id=?", (gid,))
    return {"ok": True}


@app.get("/api/posts")
async def get_posts(request: Request, niche: str = ""):
    _auth(request)
    return db.get_posts(niche=niche)


@app.post("/api/posts")
async def save_post(post: dict, request: Request):
    _auth(request)
    key = post.get("key") or f"{post.get('niche', 'general')}_{uuid.uuid4().hex[:8]}"
    db.add_post(
        key,
        post.get("niche", "general"),
        post.get("title", "منشور بدون عنوان"),
        post.get("text", ""),
        post.get("media_paths", [])
    )
    return {"ok": True, "key": key}


@app.delete("/api/posts/{pid}")
async def del_post(pid: int, request: Request):
    _auth(request)
    db.q("DELETE FROM posts WHERE id=?", (pid,))
    return {"ok": True}


@app.post("/api/ai/rewrite")
async def ai_rewrite(payload: dict, request: Request):
    _auth(request)
    text = payload.get("text", "")
    group = payload.get("group_name", "")
    niche = payload.get("niche", "general")
    rewritten = rewrite_for_group(text, group, niche)
    return {"ok": True, "rewritten": rewritten}


@app.post("/api/campaign/simulate")
async def simulate_campaign(payload: dict, request: Request):
    """محاكاة تفاعلية لخطة النشر قبل التنفيذ الفعلي لحساب التأخيرات وتفادي الحظر."""
    _auth(request)
    niche = payload.get("niche", "general")
    posts = db.get_posts(niche=niche)
    groups = db.get_groups(niche=niche, status="approved")
    accounts = [a for a in db.get_accounts() if a.get("enabled")]

    if not posts:
        return {"ok": False, "error": "لا يوجد منشورات مخصصة لهذه الفئة"}
    if not groups:
        return {"ok": False, "error": "لا توجد مجموعات معتمدة لهذه الفئة"}
    if not accounts:
        return {"ok": False, "error": "لا يوجد حسابات مفعّلة"}

    plan = []
    settings = _settings()["system"]
    delay_grp = settings.get("delay_between_groups_sec", 90)

    post = posts[0]
    for idx, g in enumerate(groups[:25]):
        acc = accounts[idx % len(accounts)]
        variation = rewrite_for_group(post["text"], g.get("name") or "", niche)
        plan.append({
            "step": idx + 1,
            "account": acc.get("label"),
            "group": g.get("name") or g.get("url"),
            "group_url": g.get("url"),
            "post_title": post.get("title"),
            "preview_text": variation[:160] + "...",
            "estimated_delay_sec": delay_grp
        })

    return {"ok": True, "total_targets": len(plan), "plan": plan}


@app.post("/api/campaign/run")
async def run_campaign(payload: dict, request: Request):
    _auth(request)
    global _running_campaign
    if _running_campaign["active"]:
        return {"ok": False, "error": "هناك حملة جارية بالفعل حالياً"}

    niche = payload.get("niche", "general")
    posts = db.get_posts(niche=niche)
    groups = db.get_groups(niche=niche, status="approved")
    accounts = [a for a in db.get_accounts() if a.get("enabled")]

    if not posts or not groups or not accounts:
        return {"ok": False, "error": "تحتاج منشوراً + مجموعات معتمدة + حساباً مفعّلاً بهذه الفئة"}

    _running_campaign["active"] = True
    _running_campaign["results"] = []
    _running_campaign["total"] = len(groups)
    _running_campaign["current"] = 0

    s = _settings()["system"]
    post = posts[0]

    def _progress_cb(res):
        _running_campaign["results"].append(res)
        _running_campaign["current"] += 1

    async def _runner():
        try:
            await publisher.run_campaign_task(post, accounts, groups, s, progress_cb=_progress_cb)
        finally:
            _running_campaign["active"] = False

    task = asyncio.create_task(_runner())
    _running_campaign["task"] = task
    return {"ok": True, "message": "بدأت الحملة بنجاح مع صمامات الحماية وتوزيع المهام"}


@app.post("/api/campaign/stop")
async def stop_campaign(request: Request):
    _auth(request)
    global _running_campaign
    if _running_campaign.get("task") and not _running_campaign["task"].done():
        _running_campaign["task"].cancel()
    _running_campaign["active"] = False
    return {"ok": True, "message": "تم إيقاف الحملة"}


@app.get("/api/logs")
async def get_logs(request: Request, limit: int = 150):
    _auth(request)
    return db.get_logs(limit=limit)
