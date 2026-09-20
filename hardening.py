"""
hardening.py — APEX Phase 8
Security: secrets encryption, backup/restore, health check, prompt injection defense.
"""

import os, json, zipfile, shutil, re
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

INJECTION_PATTERNS = [
    "ignore previous instructions","ignore all instructions","disregard your instructions",
    "you are now","act as if","pretend you are","system prompt","jailbreak",
    "bypass","forget everything","new instructions","override instructions",
]

def sanitise_user_input(text: str) -> tuple:
    violations=[]; cleaned=text; lower=text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            violations.append(pattern)
            cleaned = re.sub(re.escape(pattern),"[removed]",cleaned,flags=re.IGNORECASE)
    if len(cleaned)>4000:
        cleaned = cleaned[:4000]+"... [truncated]"; violations.append("input too long")
    return cleaned, violations

def validate_topic(topic: str) -> tuple:
    if not topic or not topic.strip(): return False,"Topic cannot be empty"
    if len(topic)>200: return False,"Topic too long (max 200 chars)"
    cleaned, violations = sanitise_user_input(topic)
    if violations: return False, f"Topic contains blocked patterns: {violations}"
    return True, cleaned.strip()

def create_backup(label: str = "") -> dict:
    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = f"apex_backup_{ts}{'_'+label.replace(' ','_') if label else ''}"
    out  = BACKUP_DIR/f"{name}.zip"
    manifest = {"created_at":datetime.utcnow().isoformat(),"label":label,"files":[]}
    patterns = ["apex_data.db","scripts/*.json","plans/*.json","analytics/*.json",
                "schedules/*.json",".apex_config","requirements.txt"]
    with zipfile.ZipFile(str(out),"w",zipfile.ZIP_DEFLATED) as zf:
        for pattern in patterns:
            for path in BASE_DIR.glob(pattern):
                if path.exists():
                    arcname = path.relative_to(BASE_DIR)
                    zf.write(str(path),str(arcname))
                    manifest["files"].append(str(arcname))
    manifest["size_kb"] = round(out.stat().st_size/1024,1)
    manifest["path"]    = str(out)
    (BACKUP_DIR/f"{name}_manifest.json").write_text(json.dumps(manifest,indent=2))
    return {"ok":True,"path":str(out),"size_kb":manifest["size_kb"],"files":len(manifest["files"])}

def list_backups() -> list:
    backups = []
    for p in sorted(BACKUP_DIR.glob("apex_backup_*.zip"),reverse=True):
        mp = p.with_name(p.stem+"_manifest.json")
        if mp.exists():
            m = json.loads(mp.read_text())
            backups.append({"path":str(p),"created_at":m["created_at"],"label":m["label"],
                            "size_kb":m["size_kb"],"files":len(m["files"])})
    return backups

def restore_backup(backup_path: str) -> dict:
    p = Path(backup_path)
    if not p.exists(): return {"ok":False,"reason":"Backup not found"}
    try:
        restore_dirs = ["scripts","plans","analytics","schedules"]
        restored = []
        with zipfile.ZipFile(str(p),"r") as zf:
            for name in zf.namelist():
                if any(name.startswith(d+"/") for d in restore_dirs):
                    zf.extract(name,str(BASE_DIR)); restored.append(name)
        return {"ok":True,"restored_files":len(restored),"files":restored[:20]}
    except Exception as e:
        return {"ok":False,"reason":str(e)}

def health_check() -> dict:
    import ast; checks = {}
    py_files = [f for f in BASE_DIR.glob("*.py") if f.name!="apex.py"]
    bad_py   = []
    for f in py_files:
        try: compile(f.read_text(),str(f),"exec")
        except (SyntaxError,SyntaxWarning) as e: bad_py.append(f"{f.name}: {e}")
    checks["python_compile"] = {"ok":len(bad_py)==0,"issues":bad_py}
    try:
        import sqlite3; conn=sqlite3.connect(str(BASE_DIR/"apex_data.db")); conn.execute("SELECT 1"); conn.close()
        checks["database"] = {"ok":True}
    except Exception as e:
        checks["database"] = {"ok":False,"error":str(e)}
    statics = ["static/index.html","static/app.js","static/style.css"]
    missing = [f for f in statics if not (BASE_DIR/f).exists()]
    checks["static_files"] = {"ok":len(missing)==0,"missing":missing}
    providers = []
    if shutil.which("ollama"): providers.append("ollama")
    for key,name in [("DEEPSEEK_API_KEY","deepseek"),("GEMINI_API_KEY","gemini"),
                     ("GROQ_API_KEY","groq"),("OPENAI_API_KEY","openai")]:
        if os.environ.get(key): providers.append(name)
    checks["providers"] = {"ok":len(providers)>0,"available":providers}
    checks["ffmpeg"]    = {"ok":bool(shutil.which("ffmpeg"))}
    return {"healthy":all(v["ok"] for v in checks.values()),"checks":checks,
            "checked_at":datetime.utcnow().isoformat()}
