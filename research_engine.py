"""
research_engine.py — APEX Phase 2
Evidence-backed research. Every claim tagged: source, date, confidence, type.
"""

import os, json, re, urllib.request, urllib.parse, hashlib
from datetime import datetime
from pathlib import Path
import audit_log

BASE_DIR     = Path(__file__).parent
RESEARCH_DIR = BASE_DIR / "research"
RESEARCH_DIR.mkdir(exist_ok=True)

EVIDENCE = {"stated":"Directly stated by source","observed":"Observed from data",
            "inferred":"Inferred from patterns","forecast":"Projected — treat with caution"}

def _claim(text, source, url, confidence, etype="stated", date=None):
    return {"text":text,"source":source,"url":url,
            "confidence":round(min(1.0,max(0.0,confidence)),2),
            "type":etype,"date":date or datetime.utcnow().strftime("%Y-%m-%d")}

def search_web(query:str, max_results:int=6) -> list:
    try:
        params=urllib.parse.urlencode({"q":query,"kl":"us-en"})
        url=f"https://html.duckduckgo.com/html/?{params}"
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req,timeout=12) as r:
            body=r.read().decode("utf-8",errors="ignore")
        results=[]
        blocks=re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.+?)</a>.*?class="result__snippet"[^>]*>(.+?)</a>',body,re.DOTALL)
        for raw_url,title_raw,snippet_raw in blocks[:max_results]:
            title=re.sub(r"<[^>]+>","",title_raw).strip()
            snippet=re.sub(r"<[^>]+>","",snippet_raw).strip()
            actual=raw_url
            if "uddg=" in raw_url:
                m=re.search(r"uddg=([^&]+)",raw_url)
                if m: actual=urllib.parse.unquote(m.group(1))
            results.append({"title":title,"url":actual,"snippet":snippet,
                            "evidence":_claim(snippet[:200],title,actual,0.7,"stated")})
        return results
    except Exception as e:
        return [{"error":str(e),"source":"duckduckgo"}]

def search_github(query:str, max_results:int=6) -> list:
    try:
        q=urllib.parse.quote(query)
        url=f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page={max_results}"
        headers={"Accept":"application/vnd.github+json","User-Agent":"APEX/1.0"}
        if os.environ.get("GITHUB_TOKEN"): headers["Authorization"]=f"Bearer {os.environ['GITHUB_TOKEN']}"
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=12) as r:
            items=json.loads(r.read()).get("items",[])
        return [{"title":i["full_name"],"url":i["html_url"],"description":(i.get("description") or "")[:120],
                 "stars":i["stargazers_count"],"evidence":_claim(f"GitHub repo '{i['full_name']}' has {i['stargazers_count']} stars",
                 "GitHub API",i["html_url"],1.0,"observed",i.get("updated_at","")[:10])} for i in items]
    except Exception as e:
        return [{"error":str(e),"source":"github"}]

def search_youtube(query:str, max_results:int=10) -> list:
    key=os.environ.get("YOUTUBE_DATA_API_KEY")
    if not key: return [{"error":"YOUTUBE_DATA_API_KEY not set","howto":"Get free key: console.cloud.google.com → YouTube Data API v3"}]
    try:
        params=urllib.parse.urlencode({"part":"snippet","q":query,"maxResults":max_results,"type":"video","order":"viewCount","key":key})
        with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/search?{params}",timeout=12) as r:
            data=json.loads(r.read())
        return [{"video_id":item["id"].get("videoId",""),"title":item["snippet"].get("title",""),
                 "channel":item["snippet"].get("channelTitle",""),"published":item["snippet"].get("publishedAt","")[:10],
                 "url":f"https://youtube.com/watch?v={item['id'].get('videoId','')}",
                 "evidence":_claim(f"YouTube video '{item['snippet'].get('title','')}' by {item['snippet'].get('channelTitle','')}",
                 "YouTube Data API v3",f"https://youtube.com/watch?v={item['id'].get('videoId','')}",1.0,"observed")}
                for item in data.get("items",[])]
    except Exception as e: return [{"error":str(e),"source":"youtube_data_api"}]

def score_idea(idea:str, research_results:dict) -> dict:
    web_count=len([r for r in research_results.get("web",[]) if not r.get("error")])
    yt_count =len([r for r in research_results.get("youtube",[]) if not r.get("error")])
    demand   =min(1.0,(web_count*0.1+yt_count*0.08))
    diff     =max(0.1,1.0-(yt_count*0.06))
    comedy_words=["funny","comedy","sketch","cartoon","animation","kids","hilarious","silly"]
    fit      =min(1.0,0.3+sum(0.15 for w in comedy_words if w in idea.lower()))
    effort   =0.5
    composite=round((demand*0.3+diff*0.3+fit*0.3+(1-effort)*0.1),3)
    return {"idea":idea,"scores":{"demand":round(demand,3),"differentiation":round(diff,3),
            "fit":round(fit,3),"effort_inv":round(1-effort,3)},"composite":composite,
            "recommendation":"PRODUCE" if composite>=0.5 else "RESEARCH MORE" if composite>=0.35 else "SKIP",
            "evidence_count":web_count+yt_count,"scored_at":datetime.utcnow().isoformat(),
            "note":"Scores based on observed evidence only. No guaranteed outcome."}

def build_brief(topic:str, ideas:list=None) -> dict:
    brief_id=hashlib.md5(f"{topic}{datetime.utcnow().date()}".encode()).hexdigest()[:10]
    print(f"  [PULSE] Researching: {topic}")
    web_results=search_web(f"{topic} comedy animation kids YouTube",max_results=6)
    yt_results =search_youtube(f"{topic} cartoon comedy kids",max_results=8)
    print(f"  [PULSE] Web:{len(web_results)} | YouTube:{len(yt_results)}")
    scored_ideas=[score_idea(idea,{"web":web_results,"youtube":yt_results}) for idea in (ideas or [topic])]
    scored_ideas.sort(key=lambda x:x["composite"],reverse=True)
    brief={"brief_id":brief_id,"topic":topic,"created_at":datetime.utcnow().isoformat(),
           "freshness":datetime.utcnow().strftime("%Y-%m-%d"),
           "evidence":{"web_results":web_results,"yt_results":yt_results,
                       "total_sources":len(web_results)+len(yt_results)},
           "scored_ideas":scored_ideas,"top_idea":scored_ideas[0] if scored_ideas else None,
           "disclaimer":"Evidence is observed/stated only. No guaranteed views or income."}
    (RESEARCH_DIR/f"brief_{brief_id}.json").write_text(json.dumps(brief,indent=2,ensure_ascii=False))
    audit_log.record("RESEARCH_DONE",subject=brief_id,payload={"topic":topic,"sources":brief["evidence"]["total_sources"]})
    return brief

def list_briefs() -> list:
    briefs=[]
    for path in sorted(RESEARCH_DIR.glob("brief_*.json"),reverse=True):
        try:
            data=json.loads(path.read_text())
            briefs.append({"brief_id":data["brief_id"],"topic":data["topic"],
                           "created_at":data["created_at"],"sources":data["evidence"]["total_sources"],
                           "top_idea":(data.get("top_idea") or {}).get("idea","")})
        except Exception: pass
    return briefs
