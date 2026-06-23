#!/usr/bin/env python3
"""
다트해킹(@darthacking) → 주(월~금) DART 공시를 요일별 + 공시목적별로 정리.
핵심 한 줄 요약 / 산업섹터 태그 / 중요도 별점(★~★★★) / 주간 요약 칸 /
목적별 한눈에 클릭 점프 / 주차 선택기로 지난 주 열람.
출력: index.html(최신 주), archive/YYYY-Www.html, archive/index.html
사용:
  python3 generate_digest.py                # 이번 주만 (일일 자동실행용)
  python3 generate_digest.py 2026-06-18     # 해당 날짜가 속한 주
  python3 generate_digest.py --backfill 4   # 이번 주 + 지난 4주 (최초 1회 채우기)
"""
import re, html as H, subprocess, os, sys, glob, json
from datetime import datetime, timedelta, timezone

CHANNEL="darthacking"; KST=timezone(timedelta(hours=9)); UTC=timezone.utc
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCH=os.path.join(ROOT,"archive"); WD=["월","화","수","목","금"]
SECPATH=os.path.join(ROOT,"data","sectors.json")
SECTORS=json.load(open(SECPATH,encoding="utf-8")) if os.path.exists(SECPATH) else {}

post_pat=re.compile(r'data-post="([^"]+)"'); dt_pat=re.compile(r'datetime="([^"]+)"')
text_pat=re.compile(r'tgme_widget_message_text[^>]*>(.*?)</div>',re.DOTALL)

def fetch(u):
    try:
        r=subprocess.run(['curl','-s','--max-time','30',u],capture_output=True); return r.stdout.decode('utf-8','replace')
    except Exception: return ""

def collect_range(start_utc,end_utc):
    """[start,end] UTC 문자열 구간의 모든 게시물 수집."""
    out={}; url=f'https://t.me/s/{CHANNEL}'
    for _ in range(90):
        c=fetch(url)
        if not c: break
        ids=[]; oldest=None
        for b in re.split(r'(?=<div[^>]*data-post=")',c):
            pm,dm=post_pat.search(b),dt_pat.search(b)
            if not pm or not dm: continue
            pid=pm.group(1); num=int(pid.split('/')[-1]); ids.append(num)
            dt=dm.group(1).replace('+00:00','').replace('Z','')
            if oldest is None or dt<oldest: oldest=dt
            if not (start_utc<=dt<=end_utc): continue
            tm=text_pat.search(b); raw=tm.group(1) if tm else ''
            txt=re.sub(r'<br\s*/?>','\n',raw); txt=re.sub(r'<[^>]+>','',txt); txt=H.unescape(txt).strip()
            kst=datetime.fromisoformat(dt).replace(tzinfo=UTC).astimezone(KST)
            out[pid]={'num':num,'kst':kst,'text':txt}
        if not ids: break
        if oldest and oldest<start_utc: break
        url=f'https://t.me/s/{CHANNEL}?before={min(ids)}'
    return sorted(out.values(),key=lambda x:x['num'])

CATDEF=[
 ("contract","📈","수주·공급계약","#0d9488","#0d948822","#5eead4",["단일판매","공급계약","수주"]),
 ("return","💰","주주환원·자기주식","#ca8a04","#ca8a0422","#fde68a",["자기주식","주식소각","소각","현금배당","배당","주주환원","이익소각"]),
 ("capital","🪙","증자·자본정책","#d97706","#d9770622","#fcd34d",["유상증자","무상증자","전환사채","신주인수권","교환사채","주식병합","주식분할","감자","액면"]),
 ("stake","🏛️","지분변동·대량보유","#7c3aed","#7c3aed22","#c4b5fd",["대량보유","최대주주","임원ㆍ주요주주","특정증권","주식등의대량"]),
 ("rnd","🔬","사업·R&D·투자판단","#2563eb","#2563eb22","#93c5fd",["투자판단","임상","기술이전","특허","신규시설투자","타법인주식","출자","연구개발","품목허가"]),
 ("clarify","🗣️","해명·조회공시","#b45300","#b4530022","#fbbf24",["풍문","보도","조회공시","해명","답변"]),
 ("risk","⚠️","사업변동·시장조치","#dc2626","#dc262622","#fca5a5",["영업정지","감사의견","상장폐지","관리종목","거래정지","기타시장안내","횡령","배임","소송","불성실공시","상장적격성"]),
 ("ir","📣","IR·기업설명회","#0891b2","#0891b222","#67e8f9",["기업설명회","IR","컨퍼런스콜"]),
 ("etc","🗂️","기타 공시","#475569","#47556922","#cbd5e1",[]),
 ("note","📊","채널 리서치 노트","#db2777","#db277722","#f9a8d4",[]),
]
ORDER=[c[0] for c in CATDEF]; META={c[0]:c for c in CATDEF}
SECCOLOR={"반도체":"#5eead4","IT·전기전자":"#7dd3fc","2차전지":"#a5b4fc","2차전지·소재":"#a5b4fc","바이오·제약":"#f9a8d4",
 "헬스케어·의료기기":"#f9a8d4","화학":"#d8b4fe","철강·금속":"#fca5a5","조선·기계":"#fbbf24","자동차·부품":"#fcd34d",
 "건설·건자재":"#fde68a","에너지·정유":"#fdba74","에너지·플랜트":"#fdba74","음식료":"#bef264","유통·소비재":"#bbf7d0",
 "유통·상사":"#bbf7d0","금융·증권·보험":"#93c5fd","지주":"#cbd5e1","통신":"#67e8f9","미디어·엔터":"#f0abfc",
 "인터넷·게임·SW":"#c4b5fd","게임·SW":"#c4b5fd","운송·물류":"#a7f3d0","방산":"#fca5a5","기타":"#94a3b8"}
KW=[("바이오·제약",["바이오","제약","팜","파마","셀트","온코","테라","메디","진단","백신"]),("반도체",["반도체","세미","마이크로","웨이퍼","소자"]),
 ("2차전지·소재",["에너지머티","2차전지","배터리","엘앤에프","양극"]),("IT·전기전자",["전자","전기","일렉","디스플","옵트"]),
 ("에너지·정유",["에너지","가스","석유","정유","오일","수소"]),("건설·건자재",["건설","건축","토건","이앤씨","E&C","산업개발"]),
 ("화학",["화학","케미","소재","섬유"]),("철강·금속",["철강","금속","스틸","제철"]),("조선·기계",["중공업","조선","기계","기어","베어링","엔진","해양"]),
 ("자동차·부품",["자동차","모비스","오토","타이어"]),("게임·SW",["게임","소프트","엔씨","넷마블","크래프톤"]),("통신",["통신","텔레콤"]),
 ("미디어·엔터",["엔터","미디어","콘텐","방송","스튜디오"]),("음식료",["식품","푸드","제과","유업","음료","사조","제분"]),
 ("금융·증권·보험",["증권","금융","은행","보험","캐피탈","저축","화재"]),("지주",["지주","홀딩스","HOLDINGS"]),
 ("운송·물류",["항공","해운","물류","운송","터미널"]),("방산",["방산","항공우주","에어로","우주"])]

def sector_for(tk,co):
    if tk and tk in SECTORS: return SECTORS[tk]
    for sec,kws in KW:
        if any(kw in co for kw in kws): return sec
    return "기타"
def classify(report,d):
    if not d: return "note"
    for k,_,_,_,_,_,kws in CATDEF:
        if any(kw in report for kw in kws): return k
    return "etc"
def npct(t,l):
    m=re.search(l+r'\s*[:：]?\s*([0-9.]+)\s*%',t); return float(m.group(1)) if m else None
def to_eok(s):
    """금액 문자열 → 억원 단위 float. 예: '13조 2,815억'→132815, '27억'→27, '500만원'→0.05"""
    if not s: return 0.0
    s=s.replace(',','').replace(' ',''); tot=0.0; hit=False
    m=re.search(r'([\d.]+)조',s)
    if m: tot+=float(m.group(1))*10000; hit=True
    m=re.search(r'([\d.]+)억',s)
    if m: tot+=float(m.group(1)); hit=True
    if not hit:
        m=re.search(r'([\d.]+)만',s)
        if m: tot+=float(m.group(1))/10000
        else:
            m=re.search(r'([\d.]+)원',s)
            if m: tot+=float(m.group(1))/1e8
    return tot
def magnitude(key,t,mc,report=""):
    """카테고리별 정렬용 크기값(클수록 상위). 단위는 카테고리 내에서만 비교."""
    if key in ("contract","risk"):
        v=npct(t,"매출대비"); return v if v is not None else to_eok(field(t,"정지금액") or field(t,"계약금액"))
    if key=="return":
        v=npct(t,"시총대비"); return v if v is not None else to_eok(field(t,"예정금액") or field(t,"취득예정금액"))
    if key=="stake":
        a=npct(t,"보고후"); b=npct(t,"보고전")
        if a is not None and b is not None: return a-b   # 지분율 증가폭(부호): 증가 위 → 감소 아래
        if "최대주주변경" in report or "최대주주 변경" in report: return 9999.0
        return -9999.0
    if key=="capital":
        return to_eok(field(t,"발행금액") or field(t,"신주의수") or field(t,"금액"))
    return 0.0
def importance(report,t,key):
    s=npct(t,"매출대비"); cap=npct(t,"시총대비")
    if key=="risk":
        if any(k in report for k in ["상장폐지","감사의견","관리종목","거래정지","횡령","배임","불성실"]): return 3
        if "영업정지" in report: return 3 if (s and s>=10) else 2
        return 2
    if key=="contract": return 3 if (s and s>=30) else (2 if (s and s>=10) else 1)
    if key=="return": return (3 if (cap and cap>=3) else 2) if "소각" in report else 2
    if key=="capital": return 3 if any(k in report for k in ["유상증자","무상증자","전환사채","신주인수권","교환사채","감자"]) else 2
    if key=="stake":
        if "최대주주변경" in report or "최대주주 변경" in report: return 3
        return 2 if "경영권 영향" in t else 1
    if key=="rnd": return 2
    if key=="clarify": return 2 if any(k in t for k in ["인수","매각","합병","지분 매각","피인수"]) else 1
    return 1
def field(t,label):
    m=re.search(re.escape(label)+r'\s*[:：]\s*([^\n]+)',t); return m.group(1).strip() if m else ''
def block(t,header):
    m=re.search(re.escape(header)+r'[^\n]*\n+\s*([^\n]+)',t); return m.group(1).strip() if m else ''
def clip(s,n): return (s[:n]+'…') if len(s)>n else s
def sani(s): return re.sub(r'\s+',' ',re.sub(r'(?<![a-zA-Z])br(?![a-zA-Z])',' ',s or '')).strip()
def lead_clean(s): return re.sub(r'^\s*(\*\s*)?(제목|내용)\s*[:：]\s*','',s or '').strip()
def detail(t):
    body=[l for l in (x.strip() for x in t.split('\n')) if l and not re.match(r'^\d{4}\.\d{2}\.\d{2}',l)
          and not l.startswith(('기업명:','보고서명:','공시링크','회사정보','최근계약','http'))]
    return clip(sani(' '.join(body)),300)
def oneline(key,t,report):
    try:
        if key=="contract":
            cp=field(t,'계약상대') or field(t,'계약상대방'); cn=field(t,'계약내용') or field(t,'계약의 내용')
            amt=field(t,'계약금액'); s=field(t,'매출대비')
            seg=[x for x in [cp, clip(cn,22) if cn else '', (amt+' 수주' if amt else '')] if x]
            return (' · '.join(seg)+(f' (매출 {s})' if s else '')) or report
        if key=="return":
            if '소각' in report:
                cnt=re.search(r'보통주\s*[:：]\s*([\d,]+)\s*주',t); amt=field(t,'예정금액'); cap=field(t,'시총대비')
                return '자기주식'+(f' {cnt.group(1)}주' if cnt else '')+' 소각'+(f' {amt}' if amt else '')+(f' (시총 {cap})' if cap else '')
            amt=field(t,'취득예정금액') or field(t,'예정금액')
            return '자기주식 취득'+(f' {amt}' if amt else '') if amt else (('배당 '+field(t,'배당금총액')) if field(t,'배당금총액') else report)
        if key=="capital":
            if '병합' in report:
                a=field(t,'병합전'); b=field(t,'병합후'); return f'액면병합 {a}→{b}' if a and b else report
            if '분할' in report:
                a=field(t,'분할전'); b=field(t,'분할후'); return f'액면분할 {a}→{b}' if a and b else report
            return clip(re.sub(r'주요사항보고서|결정|\(|\)','',report).strip(),40) or report
        if key=="stake":
            rep=field(t,'대표보고'); bf=field(t,'보고전'); af=field(t,'보고후'); pur=field(t,'보유목적')
            nm=rep.split('/')[0] if rep else ''; seg=[]
            if nm: seg.append(nm)
            if bf and af: seg.append(f'{bf}→{af}')
            return (' '.join(seg)+(f' ({pur})' if pur else '')) or report
        if key=="rnd":
            if '임상' in report:
                dz=field(t,'대상질환'); stg=field(t,'임상단계')
                seg=' · '.join([x for x in [clip(dz,22) if dz else '', stg] if x])
                if seg: return seg
            return clip(field(t,'제목') or block(t,'제목') or field(t,'계약상대방') or lead_clean(detail(t)),60)
        if key=="clarify":
            if '조회공시' in report:
                return '조회공시 답변 — 중요정보 없음' if ('중요한 정보가 없' in t or '중요정보없음' in report) else '조회공시 요구에 대한 답변'
            return clip(field(t,'보도내용') or lead_clean(detail(t)),58)
        if key=="risk":
            if '영업정지' in report:
                fld=field(t,'정지분야'); amt=field(t,'정지금액'); s=field(t,'매출대비')
                return (fld+' ' if fld else '')+'영업정지'+(f' {amt}' if amt else '')+(f' (매출 {s})' if s else '')
            return clip(field(t,'제목') or block(t,'제목') or lead_clean(detail(t)),60)
        if key=="ir":
            d=field(t,'개최일자'); pp=block(t,'*IR 목적') or block(t,'IR 목적')
            return ((d+' ' if d else '')+(clip(pp,40) if pp else 'IR 개최')).strip()
        first=[l for l in t.split('\n') if l.strip() and not re.match(r'^\d{4}\.',l)]
        return clip(report or (first[0] if first else ''),76)
    except Exception:
        return report

def parse(rec,monday):
    t=rec['text']; k=rec['kst']
    co=re.search(r'기업명:\s*([^(]+)',t); rep=re.search(r'보고서명:\s*(.+)',t)
    dart=re.search(r'(https://dart\.fss\.or\.kr[^\s]+)',t)
    mc=re.search(r'시가총액:\s*([^)]+)',t); tk=re.search(r'\)\s*(A\d{6})',t)
    disc=bool(co and rep)
    report=re.sub(r'\s{2,}',' ',rep.group(1).strip()) if rep else t.split('\n')[0][:60]
    key=classify(report,disc); coname=co.group(1).strip() if co else report[:26]; tkid=tk.group(1) if tk else ""
    delta=None
    if disc and key=="stake":
        a=npct(t,"보고후"); b=npct(t,"보고전")
        if a is not None and b is not None: delta=round(a-b,2)
    return {"co":coname,"mc":mc.group(1).strip() if mc else "","tk":tkid,
            "sector":sector_for(tkid,coname) if disc else "","report":report,
            "one":sani(oneline(key,t,report)) if disc else clip(sani(t),76),
            "key":key,"imp":importance(report,t,key) if disc else 1,"disc":disc,
            "mag":magnitude(key,t,mc.group(1).strip() if mc else "",report) if disc else 0.0,"delta":delta,
            "wd":(k.date()-monday.date()).days,"date":k.strftime('%m/%d'),"time":k.strftime('%H:%M'),
            "url":f"https://t.me/{CHANNEL}/{rec['num']}","dart":dart.group(1) if dart else ""}

def star(n): return f'<span class="st s{n}" title="중요도 {n}/3">{"★"*n}{"☆"*(3-n)}</span>'
def sectag(s):
    if not s: return ''
    return f'<span class="sec" style="color:{SECCOLOR.get(s,"#94a3b8")};border-color:{SECCOLOR.get(s,"#94a3b8")}55">{H.escape(s)}</span>'
def card(it,show_wd=False):
    meta=H.escape(it["co"])+(f' · {it["mc"]}' if it["mc"] else '')+(f' · {it["tk"]}' if it["tk"] else '')
    wb=f'<span class="wdb">{WD[it["wd"]]}</span>' if show_wd and 0<=it["wd"]<5 else ''
    dl=f'<a class="src" href="{it["dart"]}" target="_blank">DART ↗</a>' if it["dart"] else ''
    badge=''
    d=it.get("delta")
    if it["key"]=="stake" and d is not None:
        if d>0: badge=f'<span class="dlt up">▲ +{d:.2f}%p</span> '
        elif d<0: badge=f'<span class="dlt down">▼ {d:.2f}%p</span> '
        else: badge='<span class="dlt flat">±0.00%p</span> '
    one_html=badge+H.escape(it["one"])
    return (f'<div class="card"><div class="card-head"><span class="co">{wb}{sectag(it["sector"])}{meta}</span>'
      f'<span class="rt">{star(it["imp"])}<span class="time">{it["time"]}</span></span></div>'
      f'<div class="card-title">{H.escape(it["report"])}</div>'
      f'<div class="oneline">{one_html}</div>'
      f'<div class="card-links"><a class="src tg" href="{it["url"]}" target="_blank">텔레그램 ↗</a>{dl}</div></div>')
def chips(items,scope):
    cnt={}
    for it in items: cnt[it["key"]]=cnt.get(it["key"],0)+1
    return "".join(f'<a class="chip" style="background:{META[k][4]};color:{META[k][5]}" onclick="jump(\'{scope}\',\'{k}\')">{META[k][1]} {META[k][2]} {cnt[k]}</a>' for k in ORDER if k in cnt)
def cat_sections(items,scope,show_wd):
    by={}
    for it in items: by.setdefault(it["key"],[]).append(it)
    out=""
    for k in ORDER:
        if k not in by: continue
        _,ic,nm,col,bg,fg,_=META[k]; lst=sorted(by[k],key=lambda x:(-x["mag"],-x["imp"],x["time"]))
        out+=(f'<section class="catsec" id="sec-{scope}-{k}"><div class="cathead" style="--c:{col}">'
              f'<span class="catname">{ic} {nm}</span><span class="catcount" style="background:{bg};color:{fg}">{len(lst)}건</span></div>'
              f'<div class="cards">{"".join(card(it,show_wd) for it in lst)}</div></section>')
    return out
def weekly_summary(items):
    big=sorted([it for it in items if it["imp"]>=2 and it["disc"]],key=lambda x:(-x["imp"],-x["mag"],x["wd"],x["time"]))
    rows="".join(f'<li>{star(it["imp"])} <b>[{WD[it["wd"]] if 0<=it["wd"]<5 else "-"}]</b> {sectag(it["sector"])}'
                 f'<span class="sco">{H.escape(it["co"])}</span> <span class="stag" style="background:{META[it["key"]][4]};color:{META[it["key"]][5]}">{META[it["key"]][1]}{META[it["key"]][2]}</span> {H.escape(it["one"])}</li>'
                 for it in big[:12])
    return rows or '<li class="empty">이번 주 중요 공시(★★ 이상)가 없습니다.</li>'

def key_of(monday): i=monday.isocalendar(); return f"{i[0]}-W{i[1]:02d}"
def label_of(monday): return f"{monday.strftime('%Y.%m.%d')}(월)~{(monday+timedelta(days=4)).strftime('%m.%d')}(금)"
def monday_of_key(key):
    y,w=key.split('-W'); return datetime.fromisocalendar(int(y),int(w),1).replace(tzinfo=KST)

def picker(loc,cur_key,allweeks,latest_key):
    opts=""
    for key in allweeks:
        href=('index.html' if key==latest_key else f'archive/{key}.html') if loc=='root' else ('../index.html' if key==latest_key else f'{key}.html')
        opts+=f'<option value="{href}"{" selected" if key==cur_key else ""}>{label_of(monday_of_key(key))}{" · 최신" if key==latest_key else ""}</option>'
    listhref='archive/index.html' if loc=='root' else 'index.html'
    return f'<select class="wk" onchange="if(this.value)location.href=this.value">{opts}</select> <a class="src list" href="{listhref}">📚 전체 목록</a>'

def render_page(posts,key,label,loc,allweeks,latest_key):
    days=sorted({it["wd"] for it in posts if 0<=it["wd"]<5}); total=len(posts)
    s3=sum(1 for it in posts if it["imp"]==3 and it["disc"]); s2=sum(1 for it in posts if it["imp"]==2 and it["disc"])
    gen=datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    tb='<button class="tab active" data-p="all" onclick="showTab(\'all\')">📋 주간 전체</button>'
    for d in range(5):
        cnt=sum(1 for it in posts if it["wd"]==d)
        tb+=f'<button class="tab{"" if d in days else " disabled"}" data-p="d{d}" onclick="showTab(\'d{d}\')">{WD[d]}<span class="tn">{cnt}</span></button>'
    panels=(f'<div class="panel" id="panel-all"><div class="overview"><h2>📋 한눈에 — 목적을 누르면 해당 섹션으로 이동</h2>'
            f'<div class="chips">{chips(posts,"all")}</div></div>{cat_sections(posts,"all",True)}</div>')
    for d in range(5):
        di=[it for it in posts if it["wd"]==d]
        inner=(f'<div class="overview"><div class="chips">{chips(di,f"d{d}")}</div></div>{cat_sections(di,f"d{d}",False)}'
               if di else '<div class="empty-day">해당 요일 공시 없음 (또는 아직 미도래)</div>')
        panels+=f'<div class="panel" id="panel-d{d}" hidden>{inner}</div>'
    return HEAD+f'''
<div class="kicker">DART WEEKLY DIGEST</div><h1>주간 공시 다이제스트</h1>
<div class="sub">채널 다트해킹(@darthacking) · {label} · 총 {total}건 · ★★★ {s3} / ★★ {s2} · 생성 {gen}</div>
<div class="nav"><span class="navlabel">주차</span> {picker(loc,key,allweeks,latest_key)}</div>
<div class="wbox"><h2>🗓️ 주간 요약</h2><ul class="wsum">{weekly_summary(posts)}</ul></div>
<div class="tabs">{tb}</div>{panels}
<footer><div>출처: 텔레그램 다트해킹 / 금융감독원 DART. 별점·섹터는 자동 추정 참고치입니다.</div>
<div>본 다이제스트는 정보 정리 목적이며 투자 권유가 아닙니다. 투자 판단과 책임은 본인에게 있습니다.</div></footer>
'''+TAIL

HEAD='''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>주간 DART 공시 다이제스트</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#08090c;--card:#10121a;--line:#222634;--txt:#e6e8ee;--mut:#8b91a3;--acc:#5eead4}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:'Noto Sans KR',sans-serif;line-height:1.6}
.wrap{max-width:940px;margin:0 auto;padding:26px 18px 90px}
.kicker{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:2px;color:var(--acc);text-transform:uppercase}
h1{font-size:30px;font-weight:900;margin:6px 0 4px;letter-spacing:-.5px}
.sub{color:var(--mut);font-size:13px;font-family:'JetBrains Mono',monospace}
.nav{margin-top:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.navlabel{font-size:12px;color:var(--mut);font-family:'JetBrains Mono',monospace}
.wk{background:var(--card);color:var(--txt);border:1px solid var(--line);border-radius:9px;padding:7px 11px;font-family:'Noto Sans KR';font-size:13px;font-weight:700;cursor:pointer}
.src.list{color:var(--acc);text-decoration:none;font-size:13px;border:none}
.wbox{margin:18px 0;padding:18px 20px;border-radius:16px;background:linear-gradient(135deg,#15130a,#0d1830 60%,#1a1030);border:1px solid #3a3320}
.wbox h2{font-size:14px;letter-spacing:1px;color:#fde68a;margin-bottom:10px;font-family:'JetBrains Mono',monospace}
.wsum{list-style:none;display:flex;flex-direction:column;gap:7px}
.wsum li{font-size:13.5px;color:#d3d7e0}.wsum li.empty{color:var(--mut)}
.sco{font-weight:700;color:#fff}
.stag{font-size:11px;font-weight:700;padding:1px 7px;border-radius:6px;margin:0 3px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:18px 0 6px;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:50;border-bottom:1px solid var(--line)}
.tab{background:var(--card);color:var(--mut);border:1px solid var(--line);border-radius:10px;padding:8px 16px;font-family:'Noto Sans KR';font-size:14px;font-weight:700;cursor:pointer}
.tab.active{background:#16344d;color:#67e8f9;border-color:#1d4e6e}.tab:disabled{opacity:.35;cursor:not-allowed}
.tab .tn{margin-left:6px;font-size:11px;color:var(--mut);font-family:'JetBrains Mono',monospace}
.overview{margin:16px 0;padding:14px 16px;border-radius:14px;background:#0d0f16;border:1px solid var(--line)}
.overview h2{font-size:13px;color:var(--acc);margin-bottom:10px;font-family:'JetBrains Mono',monospace;letter-spacing:1px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-size:13px;font-weight:700;padding:6px 12px;border-radius:999px;cursor:pointer;user-select:none}
.chip:hover{filter:brightness(1.22)}
.catsec{margin-top:26px;scroll-margin-top:64px}
.cathead{display:flex;align-items:center;justify-content:space-between;padding-bottom:11px;border-bottom:2px solid var(--c,#333);margin-bottom:13px}
.catname{font-size:18px;font-weight:900}.catcount{font-size:12px;font-weight:700;padding:3px 10px;border-radius:999px;font-family:'JetBrains Mono',monospace}
.cards{display:flex;flex-direction:column;gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 16px}
.card:hover{border-color:#3d4860}
.card-head{display:flex;justify-content:space-between;gap:10px;margin-bottom:5px;align-items:center}
.co{font-size:12.5px;color:var(--mut);font-family:'JetBrains Mono',monospace;display:flex;align-items:center;flex-wrap:wrap}
.wdb{display:inline-block;background:#1d2740;color:#9db7e8;font-size:11px;font-weight:700;padding:1px 7px;border-radius:6px;margin-right:7px}
.sec{display:inline-block;font-size:11px;font-weight:700;padding:1px 8px;border-radius:6px;margin-right:8px;border:1px solid;background:#ffffff08}
.rt{display:flex;align-items:center;gap:8px;white-space:nowrap}
.st{font-size:13px;letter-spacing:1px}.st.s3{color:#f59e0b}.st.s2{color:#5eead4}.st.s1{color:#4b5160}
.time{font-size:12px;color:#5b6171;font-family:'JetBrains Mono',monospace}
.card-title{font-size:15px;font-weight:700;margin-bottom:4px;line-height:1.4}
.oneline{font-size:13.5px;color:#aeb6c6}
.dlt{display:inline-block;font-size:11.5px;font-weight:700;padding:1px 7px;border-radius:6px;font-family:'JetBrains Mono',monospace;margin-right:3px}
.dlt.up{color:#fb923c;background:#fb923c1f;border:1px solid #fb923c55}
.dlt.down{color:#38bdf8;background:#38bdf81f;border:1px solid #38bdf855}
.dlt.flat{color:#94a3b8;background:#94a3b81f;border:1px solid #94a3b855}
.card-links{display:flex;gap:14px;margin-top:9px}
.src{font-size:12px;color:var(--mut);text-decoration:none;font-family:'JetBrains Mono',monospace;border-bottom:1px dashed #333}
.src:hover{color:var(--acc);border-color:var(--acc)}.src.tg{color:#5ea9ea}
.empty-day{color:var(--mut);padding:30px;text-align:center}
footer{margin-top:46px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:#5b6171;line-height:1.7}
</style></head><body><div class="wrap">'''
TAIL='''</div><script>
function showTab(p){document.querySelectorAll('.panel').forEach(e=>e.hidden=e.id!=='panel-'+p);
 document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.p===p));window.scrollTo({top:0,behavior:'smooth'});}
function jump(s,k){showTab(s);setTimeout(()=>{var el=document.getElementById('sec-'+s+'-'+k);if(el)el.scrollIntoView({behavior:'smooth',block:'start'});},60);}
</script></body></html>'''

def write_archive_index(allweeks,latest_key):
    links="".join(f'<li><a href="{("../index.html" if k==latest_key else k+".html")}">{label_of(monday_of_key(k))}{" · 최신" if k==latest_key else ""}</a></li>' for k in allweeks)
    open(os.path.join(ARCH,"index.html"),"w",encoding="utf-8").write(
     '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
     '<title>주간 다이제스트 아카이브</title><style>body{background:#08090c;color:#e6e8ee;font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 18px}'
     'a{color:#5eead4;text-decoration:none}h1{font-size:22px}li{margin:9px 0;font-family:monospace}</style></head>'
     f'<body><h1>📚 주간 DART 공시 다이제스트</h1><p><a href="../index.html">← 최신 주로</a></p><ul>{links}</ul></body></html>')

if __name__=="__main__":
    now=datetime.now(KST); cur_mon=(now-timedelta(days=now.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    if len(sys.argv)>=3 and sys.argv[1]=="--backfill":
        n=int(sys.argv[2]); mondays=[cur_mon-timedelta(days=7*i) for i in range(n+1)]
    elif len(sys.argv)>1:
        r=datetime.strptime(sys.argv[1],"%Y-%m-%d").replace(tzinfo=KST); mondays=[(r-timedelta(days=r.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)]
    else:
        mondays=[cur_mon]
    mondays=sorted(set(mondays))
    os.makedirs(ARCH,exist_ok=True)
    # 필요한 전체 구간 한 번에 수집
    span_start=min(mondays).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    span_end=(max(mondays)+timedelta(days=5)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    allrecs=collect_range(span_start,span_end)
    # 주차별 posts
    week_posts={}
    for mon in mondays:
        fe=mon+timedelta(days=5)
        recs=[r for r in allrecs if mon<=r['kst']<fe]
        week_posts[key_of(mon)]=(mon,[parse(r,mon) for r in recs])
    # 기존 아카이브 + 이번 생성분 → 전체 주차 집합(최신순)
    existing=[os.path.basename(f)[:-5] for f in glob.glob(os.path.join(ARCH,"20*-W*.html"))]
    allset=sorted(set(existing)|set(week_posts.keys()),reverse=True)
    latest_key=allset[0]
    latest_mon=monday_of_key(latest_key)
    # latest 주가 이번에 수집되지 않았다면(드문 경우) 수집
    if latest_key not in week_posts:
        fe=latest_mon+timedelta(days=5)
        recs=collect_range(latest_mon.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"),fe.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"))
        week_posts[latest_key]=(latest_mon,[parse(r,latest_mon) for r in recs])
    # 각 주차 아카이브 페이지 작성
    for key,(mon,posts) in week_posts.items():
        open(os.path.join(ARCH,f"{key}.html"),"w",encoding="utf-8").write(
            render_page(posts,key,label_of(mon),"archive",allset,latest_key))
    # 루트 index.html = 최신 주
    lm,lposts=week_posts[latest_key]
    open(os.path.join(ROOT,"index.html"),"w",encoding="utf-8").write(
        render_page(lposts,latest_key,label_of(lm),"root",allset,latest_key))
    write_archive_index(allset,latest_key)
    print("생성 주차:", ", ".join(f"{k}({len(p)})" for k,(m,p) in sorted(week_posts.items())))
    print("전체 열람 가능 주차:", ", ".join(allset))
