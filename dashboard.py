"""
dashboard.py — APEX
Main Flask backend. All API routes. 
Starts pipeline worker, scheduler, and serves the frontend.
"""

import os, sys, json, re, threading, time
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_sock import Sock

BASE_DIR = Path(__file__).parent
app  = Flask(__name__, static_folder=str(BASE_DIR/"static"), static_url_path="/static")
sock = Sock(app)

# ── Nova push channel ─────────────────────────────────────────────────────────
_nova_queue = []
_nova_lock  = threading.Lock()
_ws_clients = []

def push_nova(text: str):
    with _nova_lock:
        _nova_queue.append({"content": text, "ts": datetime.utcnow().isoformat()})
        if len(_nova_queue) > 50:
            _nova_queue.pop(0)

@app.route("/api/chat_updates")
def api_chat_updates():
    with _nova_lock:
        msgs = list(_nova_queue)
        _nova_queue.clear()
    return jsonify({"messages": msgs})

# ── Safe route decorator ──────────────────────────────────────────────────────
def safe_route(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return wrapper

# ── Config ────────────────────────────────────────────────────────────────────
def _load_config():
    cfg_path = BASE_DIR / ".apex_config"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            for k, v in cfg.items():
                if v: os.environ[k] = v
        except Exception:
            pass

_load_config()

# ── Import all modules ────────────────────────────────────────────────────────
import llm_provider, memory, audit_log, approval, job_queue
import apex_agent, image_engine, video_builder, thumbnail_gen
import rights_ledger, preview as _preview_mod, publisher
import pipeline as _pipeline
import research_engine, content_plan, experiment_registry
import analytics as _analytics, enhancement_engine, scheduler
import quality_check, hardening, google_ads as _gads
import desktop_agent as _desktop, browser_agent as _browser

# ── Start background workers ──────────────────────────────────────────────────
_pipeline.start(poll_interval=2.0)
scheduler.start_scheduler()

# ── Frontend ──────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR/"static"), "index.html")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(str(BASE_DIR/"static"), filename)

# ── Chat ──────────────────────────────────────────────────────────────────────
NOVA_SYSTEM = """You are Nova — APEX CEO, AI YouTube content agent.
You manage the Sunridge Town comedy channel (Trishul, Sandy, Libhu — original characters).
You speak directly, call the owner Boss, and take action immediately.
You are proactive, confident, and get things done.
Current date: """ + datetime.utcnow().strftime("%Y-%m-%d")

def respond(text: str, source: str = "nova") -> object:
    memory.save_message("assistant", text)
    return jsonify({"reply": text, "source": source})

@app.route("/api/chat", methods=["POST"])
@safe_route
def api_chat():
    data = request.json or {}
    msg  = data.get("message","").strip()
    if not msg: return jsonify({"reply":"","source":"nova"})

    # Sanitise input
    cleaned, violations = hardening.sanitise_user_input(msg)
    if violations:
        push_nova(f"I blocked some suspicious content in your message, Boss.")
    msg = cleaned
    memory.save_message("user", msg)

    # ── Desktop command detection ─────────────────────────────────────────────
    desktop_keywords = ["screenshot","show desktop","what's on screen","open folder","open file",
                        "list files","find file","search files","click at","press key","type on","run command"]
    if any(kw in msg.lower() for kw in desktop_keywords):
        dcmd = _desktop.parse_desktop_command(msg)
        if dcmd:
            result = _desktop.execute_desktop_command(dcmd)
            if result.get("ok"):
                action = dcmd["action"]
                if action == "screenshot" and result.get("b64"):
                    reply = f"Done Boss — screenshot taken. Screen is {result.get('width')}x{result.get('height')}. I can see your desktop now."
                elif action == "list_folder":
                    items   = result.get("items",[])
                    folders = [i["name"] for i in items if i["type"]=="folder"][:5]
                    files   = [i["name"] for i in items if i["type"]=="file"][:8]
                    reply   = f"Folder: {result.get('path','')}\nFolders: {', '.join(folders) or 'none'}\nFiles: {', '.join(files) or 'none'}"
                elif action == "run_command":
                    out   = result.get("stdout","").strip()
                    reply = f"Command done.\n{out[:500]}" if out else "Command completed."
                else:
                    reply = f"Done Boss — {result.get('action',dcmd['action'])}."
            else:
                reply = f"Desktop action failed: {result.get('error','unknown')}. Make sure pyautogui is installed."
            return respond(reply, "desktop")

    # ── Browser command detection ─────────────────────────────────────────────
    browser_keywords = ["open browser","browse to","go to http","navigate to","open url","browser screenshot"]
    if any(kw in msg.lower() for kw in browser_keywords):
        bcmd = _browser.parse_browser_command(msg)
        if bcmd:
            if not _browser.is_running(): _browser.start_browser(headless=False, private=True)
            result = _browser.execute_browser_command(bcmd)
            reply  = f"Done Boss — {result.get('action',bcmd['action'])}. {result.get('title','')}" if result.get("ok") else f"Browser failed: {result.get('error','')}"
            return respond(reply, "browser")

    # ── Episode queue intent ──────────────────────────────────────────────────
    make_keywords = ["make a video","create video","make video","new episode","create episode","produce video","generate video"]
    if any(kw in msg.lower() for kw in make_keywords):
        topic = msg
        for kw in make_keywords: topic = topic.lower().replace(kw,"").strip()
        topic = topic.strip("about of for ").strip() or "Trishul has a brilliant plan"
        ep_num = apex_agent.get_episode_count() + 1
        jid    = _pipeline.queue_episode(topic, ep_num)
        reply  = f"On it Boss! Queuing episode {ep_num}: '{topic}'. I'll write the script, generate images, record narration, render the video, and send it to your Approvals tab for review. Job ID: {jid[:8]}"
        push_nova(reply)
        return respond(reply)

    # ── Approval intent ───────────────────────────────────────────────────────
    if any(kw in msg.lower() for kw in ["approve","yes upload","go ahead","publish it"]):
        cards = approval.pending_cards()
        if cards:
            card = cards[0]; result = approval.approve(card["card_id"])
            if result["ok"]:
                reply = f"Approved Boss! Card {card['card_id'][:8]} approved. Upload queued. Check the Published tab shortly."
            else:
                reply = f"Approval failed: {result.get('reason','unknown')}"
            return respond(reply)

    # ── Status intent ─────────────────────────────────────────────────────────
    if any(kw in msg.lower() for kw in ["status","what's happening","how are we doing","briefing"]):
        s     = _pipeline.status()
        jobs  = s.get("jobs",{})
        reply = (f"Status update Boss: {s.get('scripts_written',0)} scripts written, "
                 f"{s.get('videos_published',0)} videos published, "
                 f"{jobs.get('pending',0)} jobs pending, "
                 f"{jobs.get('running',0)} running, "
                 f"{s.get('approval_cards_pending',0)} awaiting your approval. "
                 f"Image usage today: {s.get('image_usage',{}).get('pollinations',{}).get('used',0)} Pollinations.")
        return respond(reply)

    # ── LLM fallback ─────────────────────────────────────────────────────────
    context_msgs = memory.get_context_messages(limit=8)
    context_msgs.append({"role":"user","content":msg})
    try:
        reply = llm_provider.generate(NOVA_SYSTEM, context_msgs, max_tokens=400)
    except Exception as e:
        reply = f"I'm running in limited mode (no LLM key set). Add a free DeepSeek or Gemini key in Settings. Error: {e}"
    return respond(reply)

@app.route("/api/briefing")
@safe_route
def api_briefing():
    h   = datetime.utcnow().hour
    greet = "Good morning" if h<12 else "Good afternoon" if h<17 else "Good evening"
    s   = _pipeline.status()
    text= (f"{greet} Boss! APEX is ready. "
           f"{s.get('scripts_written',0)} scripts written, "
           f"{s.get('videos_published',0)} videos published. "
           f"{s.get('approval_cards_pending',0)} items waiting for your approval. "
           f"Say 'make a video' to start production, or ask me anything.")
    return jsonify({"text": text})

# ── Settings ──────────────────────────────────────────────────────────────────
@app.route("/api/settings/status")
@safe_route
def api_settings_status():
    cfg_path = BASE_DIR / ".apex_config"
    cfg      = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    result   = {}
    for k in ["DEEPSEEK_API_KEY","GEMINI_API_KEY","GROQ_API_KEY","OPENAI_API_KEY",
               "YOUTUBE_DATA_API_KEY","TELEGRAM_BOT_TOKEN","BITLY_ACCESS_TOKEN",
               "IDEOGRAM_API_KEY","LEONARDO_API_KEY"]:
        result[k] = "set" if (cfg.get(k) or os.environ.get(k)) else "not_set"
    result["LLM_PROVIDER"] = os.environ.get("LLM_PROVIDER", llm_provider.LLM_PROVIDER)
    return jsonify(result)

@app.route("/api/settings/save_key", methods=["POST"])
@safe_route
def api_settings_save_key():
    data     = request.json or {}
    key      = data.get("key",""); value = data.get("value","").strip()
    if not key: return jsonify({"error":"key required"}),400
    cfg_path = BASE_DIR / ".apex_config"
    cfg      = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    if value:
        cfg[key] = value; os.environ[key] = value
    cfg_path.write_text(json.dumps(cfg,indent=2))
    if key == "LLM_PROVIDER":
        llm_provider.LLM_PROVIDER = value
    audit_log.record("SECRET_SET", subject=key, payload={"key": key})
    return jsonify({"ok": True, "key": key})

# ── Pipeline ──────────────────────────────────────────────────────────────────
@app.route("/api/pipeline/status")
@safe_route
def api_pipeline_status(): return jsonify(_pipeline.status())

@app.route("/api/pipeline/queue_episode", methods=["POST"])
@safe_route
def api_pipeline_queue_episode():
    data   = request.json or {}
    topic  = data.get("topic","").strip()
    ep_num = data.get("episode_num", apex_agent.get_episode_count()+1)
    if not topic: return jsonify({"error":"topic required"}),400
    jid = _pipeline.queue_episode(topic, ep_num)
    push_nova(f"Episode {ep_num} queued — topic: '{topic}'. I'll report back when it's ready for review, Boss.")
    return jsonify({"job_id":jid,"status":"queued","episode_num":ep_num})

@app.route("/api/pipeline/queue_publish", methods=["POST"])
@safe_route
def api_pipeline_queue_publish():
    data    = request.json or {}
    card_id = data.get("card_id",""); dry_run = data.get("dry_run",False)
    if not card_id: return jsonify({"error":"card_id required"}),400
    jid = _pipeline.queue_publish(card_id, dry_run=dry_run)
    return jsonify({"job_id":jid,"status":"queued"})

# ── Approvals ─────────────────────────────────────────────────────────────────
@app.route("/api/approvals/pending")
@safe_route
def api_approvals_pending(): return jsonify({"cards":approval.pending_cards()})

@app.route("/api/approvals/<card_id>")
@safe_route
def api_approval_get(card_id):
    card=approval.get_card(card_id)
    return jsonify(card) if card else (jsonify({"error":"not found"}),404)

@app.route("/api/approvals/<card_id>/approve", methods=["POST"])
@safe_route
def api_approval_approve(card_id):
    data   = request.json or {}
    result = approval.approve(card_id, decided_by="owner", notes=data.get("notes",""))
    if result["ok"]:
        card = approval.get_card(card_id)
        if card and card.get("action_type") == "YOUTUBE_UPLOAD":
            # GAP 1 FIX: automatically queue the publish job after approval
            jid = _pipeline.queue_publish(card_id, dry_run=data.get("dry_run", False))
            result["publish_job_id"] = jid
            push_nova(
                f"Approved Boss. Card {card_id[:8]} approved — "
                f"upload job {jid[:8]} queued. "
                f"I will notify you when the video is live on YouTube."
            )
        elif card and card.get("action_type") == "COMMUNITY_POST":
            # GAP 4 FIX: queue community post publish
            jid = job_queue.enqueue("publish_community_post",
                                    {"card_id": card_id, "payload": card.get("payload", {})})
            result["community_job_id"] = jid
            push_nova(f"Community post approved Boss. Queued for publishing.")
        else:
            push_nova(f"Card {card_id[:8]} approved Boss.")
    return jsonify(result)

@app.route("/api/approvals/<card_id>/reject", methods=["POST"])
@safe_route
def api_approval_reject(card_id):
    data=request.json or {}; notes=data.get("notes","Not ready")
    result=approval.reject(card_id,decided_by="owner",notes=notes)
    if result["ok"]: push_nova(f"Card {card_id[:8]} rejected. No upload will happen. Reason: {notes}")
    return jsonify(result)

# ── Scripts ───────────────────────────────────────────────────────────────────
@app.route("/api/scripts")
@safe_route
def api_scripts_list(): return jsonify({"scripts":apex_agent.list_scripts()})

@app.route("/api/scripts/<episode_id>")
@safe_route
def api_script_get(episode_id):
    script=apex_agent.load_script(episode_id)
    return jsonify(script) if script else (jsonify({"error":"not found"}),404)

# ── Videos ───────────────────────────────────────────────────────────────────
@app.route("/api/videos")
@safe_route
def api_videos_list(): return jsonify({"published":publisher.list_published(),"community_drafts":publisher.list_community_drafts()})

@app.route("/api/videos/publish", methods=["POST"])
@safe_route
def api_videos_publish():
    data=request.json or {}; card_id=data.get("card_id",""); dry_run=data.get("dry_run",False)
    if not card_id: return jsonify({"error":"card_id required"}),400
    return jsonify(publisher.upload(card_id,dry_run=dry_run))

# ── Research ──────────────────────────────────────────────────────────────────
@app.route("/api/research/briefs")
@safe_route
def api_research_list(): return jsonify({"briefs":research_engine.list_briefs()})

@app.route("/api/research/brief", methods=["POST"])
@safe_route
def api_research_build():
    data=request.json or {}; topic=data.get("topic","").strip(); ideas=data.get("ideas",[])
    if not topic: return jsonify({"error":"topic required"}),400
    def _run():
        try:
            brief=research_engine.build_brief(topic,ideas or None)
            push_nova(f"Research done Boss. Topic: '{topic}'. {brief['evidence']['total_sources']} sources. Top idea: {(brief.get('top_idea') or {}).get('idea','—')}")
        except Exception as e: push_nova(f"Research error: {e}")
    threading.Thread(target=_run,daemon=True).start()
    return jsonify({"status":"started","topic":topic})

@app.route("/api/research/youtube", methods=["POST"])
@safe_route
def api_research_youtube():
    data=request.json or {}; query=data.get("query","").strip()
    if not query: return jsonify({"error":"query required"}),400
    return jsonify({"results":research_engine.search_youtube(query,max_results=10)})

# ── Experiments ───────────────────────────────────────────────────────────────
@app.route("/api/experiments")
@safe_route
def api_experiments_list(): return jsonify({"experiments":experiment_registry.list_experiments()})

@app.route("/api/experiments", methods=["POST"])
@safe_route
def api_experiments_create():
    data=request.json or {}
    eid=experiment_registry.create(data.get("name",""),data.get("hypothesis",""),
        data.get("metric","CTR"),data.get("variants",[]),data.get("guardrails",[]))
    return jsonify({"exp_id":eid})

@app.route("/api/experiments/<exp_id>/result", methods=["POST"])
@safe_route
def api_experiment_log(exp_id):
    data=request.json or {}
    ok=experiment_registry.log_result(exp_id,data.get("variant",""),float(data.get("value",0)),data.get("episode_id",""),data.get("note",""))
    return jsonify({"ok":ok})

@app.route("/api/experiments/<exp_id>/summary")
@safe_route
def api_experiment_summary(exp_id): return jsonify(experiment_registry.summary(exp_id))

# ── Content Plans ─────────────────────────────────────────────────────────────
@app.route("/api/content_plans")
@safe_route
def api_plans_list(): return jsonify({"plans":content_plan.list_plans()})

@app.route("/api/content_plans/<plan_id>")
@safe_route
def api_plan_get(plan_id):
    plan=content_plan.get_plan(plan_id)
    return jsonify(plan) if plan else (jsonify({"error":"not found"}),404)

@app.route("/api/content_plans/<plan_id>/approve", methods=["POST"])
@safe_route
def api_plan_approve(plan_id):
    ok=content_plan.approve_plan(plan_id)
    if ok: push_nova(f"Content plan {plan_id[:8]} approved Boss. Episodes queued for production.")
    return jsonify({"ok":ok})

# ── Analytics ─────────────────────────────────────────────────────────────────
@app.route("/api/analytics/channel")
@safe_route
def api_analytics_channel(): return jsonify(_analytics.channel_summary())

@app.route("/api/analytics/videos")
@safe_route
def api_analytics_videos(): return jsonify({"videos":_analytics.list_tracked_videos()})

@app.route("/api/analytics/<youtube_id>")
@safe_route
def api_analytics_video(youtube_id):
    days=int(request.args.get("days",28))
    return jsonify(_analytics.fetch_video_metrics(youtube_id,days_back=days))

@app.route("/api/analytics/register", methods=["POST"])
@safe_route
def api_analytics_register():
    data=request.json or {}
    _analytics.register_video(data.get("youtube_id",""),data.get("episode_id",""),data.get("title",""),data.get("published_at",""))
    return jsonify({"ok":True})

# ── Enhancement ───────────────────────────────────────────────────────────────
@app.route("/api/enhancement/brief", methods=["POST"])
@safe_route
def api_enhancement_brief():
    data=request.json or {}; youtube_ids=data.get("youtube_ids",[])
    if not youtube_ids:
        videos=_analytics.list_tracked_videos(); youtube_ids=[v["youtube_id"] for v in videos[:5]]
    return jsonify(enhancement_engine.build_enhancement_brief(youtube_ids,data.get("next_topic","")))

@app.route("/api/enhancement/analyse", methods=["POST"])
@safe_route
def api_enhancement_analyse():
    data=request.json or {}; youtube_ids=data.get("youtube_ids",[])
    if not youtube_ids:
        videos=_analytics.list_tracked_videos(); youtube_ids=[v["youtube_id"] for v in videos[:5]]
    return jsonify(enhancement_engine.analyse_performance(youtube_ids))

# ── Scheduler ─────────────────────────────────────────────────────────────────
@app.route("/api/schedules")
@safe_route
def api_schedules_list(): return jsonify({"schedules":scheduler.list_schedules()})

@app.route("/api/schedules", methods=["POST"])
@safe_route
def api_schedules_create():
    data=request.json or {}
    sid=scheduler.create_schedule(data.get("name","Daily Schedule"),data.get("topic_pool",[]),
        data.get("time_of_day","09:00"),data.get("days_of_week","mon,tue,wed,thu,fri,sat,sun"),
        data.get("use_enhancement",True))
    return jsonify({"schedule_id":sid,"status":"created_pending_approval"})

@app.route("/api/schedules/<sid>/approve", methods=["POST"])
@safe_route
def api_schedule_approve(sid):
    ok=scheduler.approve_schedule(sid)
    if ok: push_nova(f"Daily schedule approved Boss. APEX will auto-queue videos on schedule. You still approve every upload.")
    return jsonify({"ok":ok})

@app.route("/api/schedules/<sid>/pause", methods=["POST"])
@safe_route
def api_schedule_pause(sid): return jsonify({"ok":scheduler.pause_schedule(sid)})

@app.route("/api/schedules/<sid>/resume", methods=["POST"])
@safe_route
def api_schedule_resume(sid): return jsonify({"ok":scheduler.resume_schedule(sid)})

# ── Quality check ─────────────────────────────────────────────────────────────
@app.route("/api/quality/check", methods=["POST"])
@safe_route
def api_quality_check():
    data=request.json or {}; episode_id=data.get("episode_id","")
    script=apex_agent.load_script(episode_id)
    if not script: return jsonify({"error":"Script not found"}),404
    result=quality_check.run(script,data.get("video_path",""),data.get("img_paths",[]),data.get("audio_paths",[]))
    summary_text=quality_check.check_summary(result)
    if not result["passed"]: push_nova(f"Quality check failed for {episode_id}. Issues: {'; '.join(result['issues'][:2])}")
    else: push_nova(f"Quality check passed for {episode_id} — score {result['overall_score']:.0%}. Ready for approval.")
    return jsonify({"result":result,"summary":summary_text})

# ── Rights ────────────────────────────────────────────────────────────────────
@app.route("/api/rights/<episode_id>")
@safe_route
def api_rights_check(episode_id): return jsonify(rights_ledger.check_episode_rights(episode_id))

@app.route("/api/rights/assets")
@safe_route
def api_rights_list(): return jsonify({"assets":rights_ledger.list_assets(request.args.get("episode_id") or None)})

# ── Audit ─────────────────────────────────────────────────────────────────────
@app.route("/api/audit")
@safe_route
def api_audit_tail():
    limit=int(request.args.get("limit",50)); action=request.args.get("action","")
    return jsonify({"events":audit_log.tail(limit=limit,action_filter=action or None),"summary":audit_log.summary()})

# ── Images ────────────────────────────────────────────────────────────────────
@app.route("/api/images/usage")
@safe_route
def api_images_usage(): return jsonify(image_engine.usage_report())

# ── Character bible ───────────────────────────────────────────────────────────
@app.route("/api/bible")
@safe_route
def api_bible():
    from character_bible import CHARACTERS, WORLD, is_locked
    return jsonify({"characters":CHARACTERS,"world":WORLD,"locked":is_locked()})

# ── Google Ads ────────────────────────────────────────────────────────────────
@app.route("/api/ads/summary")
@safe_route
def api_ads_summary(): return jsonify(_gads.ads_summary())

@app.route("/api/ads/campaigns")
@safe_route
def api_ads_campaigns():
    if request.args.get("live")=="true":
        return jsonify({"campaigns":_gads.fetch_campaigns(os.environ.get("GOOGLE_ADS_CUSTOMER_ID",""))})
    return jsonify({"campaigns":_gads.get_cached_campaigns()})

@app.route("/api/ads/draft", methods=["POST"])
@safe_route
def api_ads_draft():
    data=request.json or {}
    result=_gads.draft_campaign(data.get("name",""),float(data.get("budget",1.0)),
        data.get("keywords",[]),data.get("ad_text",""),data.get("video_id",""))
    if result["ok"]: push_nova(f"Ad campaign drafted Boss: {data.get('name','')}. Needs approval in Approvals tab.")
    return jsonify(result)

# ── Health & Backup ───────────────────────────────────────────────────────────
@app.route("/api/health")
@safe_route
def api_health(): return jsonify(hardening.health_check())

@app.route("/api/backup", methods=["POST"])
@safe_route
def api_backup():
    data=request.json or {}; result=hardening.create_backup(label=data.get("label",""))
    if result["ok"]: push_nova(f"Backup created Boss — {result['files']} files, {result['size_kb']}KB.")
    return jsonify(result)

@app.route("/api/backups")
@safe_route
def api_backups_list(): return jsonify({"backups":hardening.list_backups()})

# ── Desktop Agent ─────────────────────────────────────────────────────────────
@app.route("/api/desktop/screenshot", methods=["POST"])
@safe_route
def api_desktop_screenshot():
    data=request.json or {}; result=_desktop.screenshot(label=data.get("label","nova"))
    return jsonify({"ok":result["ok"],"path":result.get("path",""),"width":result.get("width"),
                    "height":result.get("height"),"b64":result.get("b64",""),"error":result.get("error","")})

@app.route("/api/desktop/click", methods=["POST"])
@safe_route
def api_desktop_click():
    data=request.json or {}; return jsonify(_desktop.click(x=data.get("x"),y=data.get("y"),button=data.get("button","left"),double=data.get("double",False)))

@app.route("/api/desktop/move", methods=["POST"])
@safe_route
def api_desktop_move():
    data=request.json or {}; return jsonify(_desktop.move_to(data.get("x",0),data.get("y",0)))

@app.route("/api/desktop/type", methods=["POST"])
@safe_route
def api_desktop_type():
    data=request.json or {}; return jsonify(_desktop.type_text(data.get("text","")))

@app.route("/api/desktop/key", methods=["POST"])
@safe_route
def api_desktop_key():
    data=request.json or {}; return jsonify(_desktop.press_key(data.get("key","")))

@app.route("/api/desktop/scroll", methods=["POST"])
@safe_route
def api_desktop_scroll():
    data=request.json or {}; return jsonify(_desktop.scroll(direction=data.get("direction","down"),clicks=data.get("clicks",3)))

@app.route("/api/desktop/open", methods=["POST"])
@safe_route
def api_desktop_open():
    data=request.json or {}; return jsonify(_desktop.open_path(data.get("path",".")))

@app.route("/api/desktop/ls", methods=["POST"])
@safe_route
def api_desktop_ls():
    data=request.json or {}; return jsonify(_desktop.list_folder(data.get("folder",".")))

@app.route("/api/desktop/search", methods=["POST"])
@safe_route
def api_desktop_search():
    data=request.json or {}; return jsonify(_desktop.search_files(data.get("query",""),data.get("folder","."),data.get("ext","")))

@app.route("/api/desktop/run", methods=["POST"])
@safe_route
def api_desktop_run():
    data=request.json or {}; cmd=data.get("cmd","")
    blocked=["rm -rf","del /f","format","shutdown","reboot","rmdir /s"]
    if any(b in cmd.lower() for b in blocked): return jsonify({"ok":False,"error":"Command blocked for safety"}),403
    return jsonify(_desktop.run_command(cmd,data.get("cwd")))

@app.route("/api/desktop/mouse_pos")
@safe_route
def api_desktop_mouse_pos(): return jsonify(_desktop.mouse_position())

# ── Browser Agent ─────────────────────────────────────────────────────────────
@app.route("/api/browser/start", methods=["POST"])
@safe_route
def api_browser_start():
    data=request.json or {}; return jsonify(_browser.start_browser(headless=data.get("headless",False),private=data.get("private",True)))

@app.route("/api/browser/stop", methods=["POST"])
@safe_route
def api_browser_stop(): return jsonify(_browser.stop_browser())

@app.route("/api/browser/status")
@safe_route
def api_browser_status(): return jsonify({"running":_browser.is_running(),"url":_browser.current_url()})

@app.route("/api/browser/navigate", methods=["POST"])
@safe_route
def api_browser_navigate():
    url=(request.json or {}).get("url",""); return jsonify(_browser.navigate(url))

@app.route("/api/browser/screenshot", methods=["POST"])
@safe_route
def api_browser_screenshot():
    label=(request.json or {}).get("label",""); return jsonify(_browser.screenshot(label))

@app.route("/api/browser/click", methods=["POST"])
@safe_route
def api_browser_click():
    data=request.json or {}; return jsonify(_browser.click(selector=data.get("selector"),text=data.get("text")))

@app.route("/api/browser/get_text", methods=["POST"])
@safe_route
def api_browser_get_text():
    sel=(request.json or {}).get("selector","body"); return jsonify(_browser.get_text(sel))

# ── Wizard ────────────────────────────────────────────────────────────────────
@app.route("/api/wizard/status")
@safe_route
def api_wizard_status():
    cfg_path=BASE_DIR/".apex_config"; cfg={}
    if cfg_path.exists():
        try: cfg=json.loads(cfg_path.read_text())
        except Exception: pass
    import shutil
    has_brain=bool(cfg.get("DEEPSEEK_API_KEY") or cfg.get("GEMINI_API_KEY") or cfg.get("GROQ_API_KEY") or
                   os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY") or
                   shutil.which("ollama"))
    return jsonify({"needs_setup":not has_brain,"has_brain":has_brain,
                    "has_youtube":os.path.exists(str(BASE_DIR/"youtube_token.json")),
                    "has_deepseek":bool(cfg.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")),
                    "has_gemini":bool(cfg.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")),
                    "provider":llm_provider.LLM_PROVIDER})

@app.route("/api/wizard/save", methods=["POST"])
@safe_route
def api_wizard_save():
    data=request.json or {}; cfg_path=BASE_DIR/".apex_config"
    cfg=json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    key_map={"deepseek_key":"DEEPSEEK_API_KEY","gemini_key":"GEMINI_API_KEY","groq_key":"GROQ_API_KEY",
             "openai_key":"OPENAI_API_KEY","bitly_token":"BITLY_ACCESS_TOKEN","telegram_token":"TELEGRAM_BOT_TOKEN"}
    saved=[]
    for field,env_key in key_map.items():
        val=data.get(field,"").strip()
        if val: cfg[env_key]=val; os.environ[env_key]=val; saved.append(env_key)
    cfg_path.write_text(json.dumps(cfg,indent=2))
    llm_provider.LLM_PROVIDER=llm_provider._auto_detect_provider()
    push_nova(f"Setup complete Boss! Keys saved. Brain: {llm_provider.LLM_PROVIDER}. I'm ready — say anything to start.")
    return jsonify({"ok":True,"saved":saved,"provider":llm_provider.LLM_PROVIDER})


# ── Missing routes fix ────────────────────────────────────────────────────────

@app.route("/api/clients")
@safe_route
def api_clients_list():
    cfg_path = BASE_DIR / ".apex_clients.json"
    clients  = json.loads(cfg_path.read_text()) if cfg_path.exists() else {"own":{"name":"My Channel","active":True}}
    return jsonify({"clients": clients})

@app.route("/api/clients", methods=["POST"])
@safe_route
def api_clients_create():
    data     = request.json or {}
    cfg_path = BASE_DIR / ".apex_clients.json"
    clients  = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    cid      = "client_" + str(len(clients)+1)
    clients[cid] = {"name":data.get("name","New Client"),"topic":data.get("topic",""),"active":False}
    cfg_path.write_text(json.dumps(clients, indent=2))
    return jsonify({"ok":True,"client_id":cid})

@app.route("/api/clients/<cid>/switch", methods=["POST"])
@safe_route
def api_clients_switch(cid):
    cfg_path = BASE_DIR / ".apex_clients.json"
    clients  = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    for k in clients: clients[k]["active"] = (k == cid)
    cfg_path.write_text(json.dumps(clients, indent=2))
    name = clients.get(cid,{}).get("name",cid)
    push_nova(f"Switched to client: {name}. All production now targets their channel, Boss.")
    return jsonify({"ok":True,"active":cid})

@app.route("/api/backup/restore", methods=["POST"])
@safe_route
def api_backup_restore():
    data   = request.json or {}
    path   = data.get("path","")
    if not path: return jsonify({"error":"path required"}),400
    result = hardening.restore_backup(path)
    return jsonify(result)

# ── Animation routes (Manim + Kling) ─────────────────────────────────────────

@app.route("/api/animation/status")
@safe_route
def api_animation_status():
    import manim_engine, kling_engine
    return jsonify({
        "manim_available":  manim_engine.is_available(),
        "kling_available":  kling_engine.is_available(),
        "kling_provider":   kling_engine.best_available_provider(),
        "manim_install":    manim_engine.install_instructions() if not manim_engine.is_available() else "installed",
        "tiers": {
            "tier1_free":  "Narrated slideshow (Pollinations images + gTTS) — always available",
            "tier2_free":  "Manim 2D animation (smooth animated scenes) — install: pip install manim",
            "tier3_paid":  "Kling/Pika/Runway (cartoon-quality animation) — needs API key",
        }
    })

@app.route("/api/animation/render_manim", methods=["POST"])
@safe_route
def api_animation_render_manim():
    data       = request.json or {}
    episode_id = data.get("episode_id","")
    script     = apex_agent.load_script(episode_id)
    if not script: return jsonify({"error":"Script not found"}),404
    import manim_engine
    if not manim_engine.is_available():
        return jsonify({"ok":False,"error":"Manim not installed","install":"pip install manim"})
    def _run():
        result = manim_engine.render_episode(script)
        if result["ok"]:
            push_nova(f"Manim animation done, Boss! {result.get('scenes',0)} scenes rendered. Check the Published tab.")
        else:
            push_nova(f"Manim render failed: {result.get('error','unknown')}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status":"started","episode_id":episode_id})

@app.route("/api/animation/render_kling", methods=["POST"])
@safe_route
def api_animation_render_kling():
    data       = request.json or {}
    episode_id = data.get("episode_id","")
    script     = apex_agent.load_script(episode_id)
    if not script: return jsonify({"error":"Script not found"}),404
    import kling_engine
    if not kling_engine.is_available():
        return jsonify({"ok":False,"error":"No animation API key","howto":"Add KLING_API_KEY or PIKA_API_KEY in Settings"})
    def _run():
        result = kling_engine.render_episode(script)
        if result["ok"]:
            push_nova(f"Animated video done Boss! {result.get('clips',0)} clips via {result.get('provider','')}. Ready for approval.")
        else:
            push_nova(f"Animation failed: {result.get('error','unknown')}")
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status":"started","episode_id":episode_id,"provider":kling_engine.best_available_provider()})

@app.route("/api/animation/generate_code", methods=["POST"])
@safe_route
def api_animation_generate_code():
    """Return the Manim Python code for an episode (for review/download)."""
    data       = request.json or {}
    episode_id = data.get("episode_id","")
    script     = apex_agent.load_script(episode_id)
    if not script: return jsonify({"error":"Script not found"}),404
    import manim_engine
    code = manim_engine.generate_episode_code(script)
    return jsonify({"ok":True,"code":code,"episode_id":episode_id,"lines":len(code.splitlines())})

if __name__ == "__main__":
    print("\n  APEX v1 - AI YouTube Agent")
    print("  Trishul / Sandy / Libhu - Sunridge Town")
    print(f"  Brain: {llm_provider.LLM_PROVIDER}")
    print("  Starting at http://127.0.0.1:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
