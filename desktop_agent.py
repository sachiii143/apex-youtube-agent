"""
desktop_agent.py — APEX
Eyes: full desktop screenshot
Hands: mouse click, drag, scroll, type anywhere
Legs: open folders, files, apps, run commands, search files
"""

import os, base64, subprocess, platform
from datetime import datetime
from pathlib import Path
import audit_log

BASE_DIR   = Path(__file__).parent
SHOTS_DIR  = BASE_DIR / "screenshots" / "desktop"
SHOTS_DIR.mkdir(parents=True, exist_ok=True)
SYSTEM     = platform.system()

def _gui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE    = 0.05
        return pyautogui
    except ImportError:
        raise RuntimeError("pyautogui not installed. Run: pip install pyautogui")

# ── EYES ──────────────────────────────────────────────────────────────────────

def screenshot(region=None, label="desktop") -> dict:
    try:
        gui = _gui()
        ts  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out = SHOTS_DIR / f"{label}_{ts}.png"
        img = gui.screenshot(region=region)
        img.save(str(out))
        b64 = base64.b64encode(out.read_bytes()).decode()
        w, h = img.size
        audit_log.record("RESEARCH_DONE", subject="desktop_screenshot", payload={"label":label,"size":f"{w}x{h}"})
        return {"ok":True, "path":str(out), "b64":b64, "width":w, "height":h}
    except Exception as e:
        return {"ok":False, "error":str(e)}

def screen_size() -> dict:
    try:
        gui = _gui(); w,h = gui.size(); return {"ok":True,"width":w,"height":h}
    except Exception as e: return {"ok":False,"error":str(e)}

# ── HANDS ─────────────────────────────────────────────────────────────────────

def move_to(x:int, y:int, duration:float=0.3) -> dict:
    try: gui=_gui(); gui.moveTo(x,y,duration=duration); return {"ok":True,"action":f"moved to ({x},{y})"}
    except Exception as e: return {"ok":False,"error":str(e)}

def click(x:int=None, y:int=None, button:str="left", double:bool=False) -> dict:
    try:
        gui=_gui()
        if x is not None and y is not None: gui.moveTo(x,y,duration=0.2)
        if double: gui.doubleClick(button=button)
        else: gui.click(button=button)
        pos=gui.position(); return {"ok":True,"action":f"clicked at ({pos.x},{pos.y})"}
    except Exception as e: return {"ok":False,"error":str(e)}

def right_click(x:int=None, y:int=None) -> dict:
    return click(x,y,button="right")

def drag(from_x:int, from_y:int, to_x:int, to_y:int, duration:float=0.5) -> dict:
    try:
        gui=_gui(); gui.moveTo(from_x,from_y,duration=0.2); gui.dragTo(to_x,to_y,duration=duration,button="left")
        return {"ok":True,"action":f"dragged ({from_x},{from_y})→({to_x},{to_y})"}
    except Exception as e: return {"ok":False,"error":str(e)}

def scroll(x:int=None, y:int=None, clicks:int=3, direction:str="down") -> dict:
    try:
        gui=_gui()
        if x is not None and y is not None: gui.moveTo(x,y,duration=0.2)
        gui.scroll(-clicks if direction=="down" else clicks)
        return {"ok":True,"action":f"scrolled {direction}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def type_text(text:str, interval:float=0.03) -> dict:
    try: gui=_gui(); gui.typewrite(text,interval=interval); return {"ok":True,"action":f"typed {len(text)} chars"}
    except Exception as e: return {"ok":False,"error":str(e)}

def press_key(key:str) -> dict:
    try:
        gui=_gui()
        if "+" in key: gui.hotkey(*key.split("+"))
        else: gui.press(key)
        return {"ok":True,"action":f"pressed {key}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def mouse_position() -> dict:
    try: gui=_gui(); pos=gui.position(); return {"ok":True,"x":pos.x,"y":pos.y}
    except Exception as e: return {"ok":False,"error":str(e)}

# ── LEGS ──────────────────────────────────────────────────────────────────────

def open_path(path:str) -> dict:
    try:
        p=Path(path)
        if SYSTEM=="Windows": os.startfile(str(p))
        elif SYSTEM=="Darwin": subprocess.Popen(["open",str(p)])
        else: subprocess.Popen(["xdg-open",str(p)])
        audit_log.record("RESEARCH_STARTED",subject="open_path",payload={"path":str(p)})
        return {"ok":True,"action":f"opened {path}"}
    except Exception as e: return {"ok":False,"error":str(e)}

def list_folder(path:str=".") -> dict:
    try:
        p=Path(path); items=[]
        for item in sorted(p.iterdir()):
            items.append({"name":item.name,"type":"folder" if item.is_dir() else "file",
                          "size_kb":round(item.stat().st_size/1024,1) if item.is_file() else None,
                          "modified":datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
        return {"ok":True,"path":str(p.resolve()),"items":items}
    except Exception as e: return {"ok":False,"error":str(e)}

def search_files(query:str, folder:str=".", ext:str="") -> dict:
    try:
        p=Path(folder); pattern=f"*{query}*{ext}" if ext else f"*{query}*"; results=[]
        for match in p.rglob(pattern):
            if not any(part.startswith(".") or part=="__pycache__" for part in match.parts):
                results.append({"path":str(match),"type":"folder" if match.is_dir() else "file"})
        return {"ok":True,"query":query,"results":results[:30]}
    except Exception as e: return {"ok":False,"error":str(e)}

def run_command(cmd:str, cwd:str=None) -> dict:
    try:
        result=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=30,cwd=cwd or str(BASE_DIR))
        return {"ok":result.returncode==0,"stdout":result.stdout[-2000:],"stderr":result.stderr[-500:],"code":result.returncode}
    except subprocess.TimeoutExpired: return {"ok":False,"error":"Command timed out after 30s"}
    except Exception as e: return {"ok":False,"error":str(e)}

def open_terminal(folder:str=None) -> dict:
    try:
        cwd=folder or str(Path.home())
        if SYSTEM=="Windows": subprocess.Popen(["cmd","/K",f"cd /d {cwd}"],creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif SYSTEM=="Darwin": subprocess.Popen(["open","-a","Terminal",cwd])
        else: subprocess.Popen(["x-terminal-emulator"],cwd=cwd)
        return {"ok":True,"action":f"opened terminal at {cwd}"}
    except Exception as e: return {"ok":False,"error":str(e)}

# ── Natural language parser ───────────────────────────────────────────────────

def parse_desktop_command(text:str) -> dict | None:
    t=text.lower().strip()
    if any(w in t for w in ["take screenshot","show desktop","what's on screen","screenshot desktop","show me the screen"]):
        return {"action":"screenshot"}
    for prefix in ["open folder","open file","open ","go to folder"]:
        if t.startswith(prefix): return {"action":"open_path","path":text[len(prefix):].strip()}
    if any(w in t for w in ["list files","show files","what files","show folder"]):
        folder=".";
        if "in " in t: folder=text[text.lower().find("in ")+3:].strip()
        return {"action":"list_folder","folder":folder}
    for prefix in ["search for file","find file","search files"]:
        if prefix in t: return {"action":"search_files","query":text[t.find(prefix)+len(prefix):].strip()}
    if "click at" in t:
        import re; nums=re.findall(r"\d+",text)
        if len(nums)>=2: return {"action":"click","x":int(nums[0]),"y":int(nums[1])}
    for prefix in ["press ","hit key "]:
        if t.startswith(prefix): return {"action":"press_key","key":text[len(prefix):].strip()}
    if t.startswith("type "): return {"action":"type_text","text":text[5:]}
    if "scroll down" in t: return {"action":"scroll","direction":"down"}
    if "scroll up"   in t: return {"action":"scroll","direction":"up"}
    for prefix in ["run command","run ","execute "]:
        if t.startswith(prefix): return {"action":"run_command","cmd":text[len(prefix):].strip()}
    return None

def execute_desktop_command(cmd:dict) -> dict:
    a=cmd.get("action","")
    if a=="screenshot":   return screenshot()
    if a=="open_path":    return open_path(cmd.get("path","."))
    if a=="list_folder":  return list_folder(cmd.get("folder","."))
    if a=="search_files": return search_files(cmd.get("query",""),cmd.get("folder","."))
    if a=="click":        return click(cmd.get("x"),cmd.get("y"),double=cmd.get("double",False))
    if a=="move_to":      return move_to(cmd.get("x",0),cmd.get("y",0))
    if a=="type_text":    return type_text(cmd.get("text",""))
    if a=="press_key":    return press_key(cmd.get("key",""))
    if a=="scroll":       return scroll(direction=cmd.get("direction","down"))
    if a=="run_command":  return run_command(cmd.get("cmd",""))
    if a=="open_terminal":return open_terminal(cmd.get("folder"))
    return {"ok":False,"error":f"Unknown action: {a}"}
