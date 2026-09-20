"""
browser_agent.py — APEX
Nova controls a real browser using Playwright.
Navigate, click, type, screenshot, get text.
"""

import os, json, base64, threading
from datetime import datetime
from pathlib import Path
import audit_log

BASE_DIR      = Path(__file__).parent
SCREENSHOT_DIR= BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

_browser=None; _page=None; _playwright=None; _lock=threading.Lock()

def start_browser(headless:bool=False, private:bool=True) -> dict:
    global _browser,_page,_playwright
    try:
        from playwright.sync_api import sync_playwright
        _playwright=sync_playwright().start()
        args=["--autoplay-policy=no-user-gesture-required"]
        if private:
            ctx=_playwright.chromium.launch_persistent_context(
                user_data_dir=str(BASE_DIR/"browser_profile"),headless=headless,args=args)
            _page=ctx.pages[0] if ctx.pages else ctx.new_page(); _browser=ctx
        else:
            _browser=_playwright.chromium.launch(headless=headless,args=args)
            ctx=_browser.new_context(); _page=ctx.new_page()
        audit_log.record("RESEARCH_STARTED",subject="browser",payload={"headless":headless})
        return {"ok":True,"status":"Browser started"}
    except ImportError:
        return {"ok":False,"error":"Playwright not installed. Run: pip install playwright && playwright install chromium"}
    except Exception as e: return {"ok":False,"error":str(e)}

def stop_browser():
    global _browser,_page,_playwright
    try:
        if _browser: _browser.close()
        if _playwright: _playwright.stop()
        _browser=_page=_playwright=None
        return {"ok":True}
    except Exception as e: return {"ok":False,"error":str(e)}

def is_running() -> bool: return _page is not None

def navigate(url:str) -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try:
        if not url.startswith("http"): url="https://"+url
        _page.goto(url,wait_until="domcontentloaded",timeout=30000)
        title=_page.title()
        audit_log.record("RESEARCH_DONE",subject=url,payload={"title":title})
        return {"ok":True,"url":_page.url,"title":title}
    except Exception as e: return {"ok":False,"error":str(e)}

def click(selector:str=None, text:str=None) -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try:
        if text: _page.get_by_text(text,exact=False).first.click(timeout=8000)
        elif selector: _page.click(selector,timeout=8000)
        else: return {"ok":False,"error":"Provide selector or text"}
        return {"ok":True,"action":f"clicked {text or selector}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def type_text(selector:str, text:str, clear_first:bool=True) -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try:
        if clear_first: _page.fill(selector,text,timeout=8000)
        else: _page.type(selector,text,timeout=8000)
        return {"ok":True,"action":f"typed in {selector}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def screenshot(label:str="") -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try:
        ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        name=f"{label}_{ts}.png" if label else f"shot_{ts}.png"
        path=SCREENSHOT_DIR/name
        _page.screenshot(path=str(path),full_page=False)
        b64=base64.b64encode(path.read_bytes()).decode()
        return {"ok":True,"path":str(path),"b64":b64,"name":name}
    except Exception as e: return {"ok":False,"error":str(e)}

def get_text(selector:str="body") -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try: return {"ok":True,"text":_page.inner_text(selector,timeout=8000)[:3000]}
    except Exception as e: return {"ok":False,"error":str(e)}

def scroll(direction:str="down", amount:int=500) -> dict:
    if not _page: return {"ok":False,"error":"Browser not running"}
    try:
        _page.mouse.wheel(0,amount if direction=="down" else -amount)
        return {"ok":True,"action":f"scrolled {direction}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def current_url() -> str:
    try: return _page.url if _page else ""
    except: return ""

def parse_browser_command(text:str) -> dict | None:
    t=text.lower().strip()
    for prefix in ["open ","go to ","navigate to ","browse to ","visit "]:
        if t.startswith(prefix): return {"action":"navigate","url":text[len(prefix):].strip()}
    if any(w in t for w in ["youtube studio","open studio","yt studio"]):
        return {"action":"navigate","url":"https://studio.youtube.com"}
    if any(w in t for w in ["screenshot","take a screenshot","show me the screen"]):
        return {"action":"screenshot","label":"user_request"}
    if "scroll down" in t: return {"action":"scroll","direction":"down"}
    if "scroll up"   in t: return {"action":"scroll","direction":"up"}
    for prefix in ["click ","click on "]:
        if t.startswith(prefix): return {"action":"click","text":text[len(prefix):].strip()}
    return None

def execute_browser_command(cmd:dict) -> dict:
    a=cmd.get("action","")
    if a=="navigate":   return navigate(cmd.get("url",""))
    if a=="click":      return click(text=cmd.get("text"),selector=cmd.get("selector"))
    if a=="type":       return type_text(cmd.get("selector",""),cmd.get("text",""))
    if a=="screenshot": return screenshot(cmd.get("label",""))
    if a=="scroll":     return scroll(cmd.get("direction","down"))
    if a=="get_text":   return get_text(cmd.get("selector","body"))
    return {"ok":False,"error":f"Unknown action: {a}"}
