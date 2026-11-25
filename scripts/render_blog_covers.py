#!/usr/bin/env python3
"""Render article-specific WebP cover illustrations from the blog's own content."""
import argparse
import hashlib
import json
import math
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SIZE = (1200, 556)
STYLES = {
    "测试与质量": ("#132b33", "#f4f8ee", "#d0ed85", "#68ccc0"),
    "AI 工程": ("#241e39", "#fbf6ff", "#d1afff", "#f5b997"),
    "开发技术": ("#e9f0f7", "#142d4f", "#285a97", "#b64b35"),
    "工程工具": ("#182739", "#f1f5ff", "#82ceee", "#ffc97b"),
    "写作与复盘": ("#f4ecdb", "#312c39", "#67469b", "#a44735"),
}
OUT = ROOT / "images/blog-covers"
STYLE_KEYS = list(STYLES)
CJK = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
MONO = Path("/System/Library/Fonts/Menlo.ttc")
KEYWORDS = [
    ("JMeter","graph"),("InfluxDB","dashboard"),("Grafana","dashboard"),("Zabbix","dashboard"),
    ("Allure","review"),("Selenium","focus"),("WebDriver","browser"),("Docker","packages"),("Swarm","mesh"),
    ("Jenkins","flow"),("pipeline","flow"),("GitLab","diff"),("Git","diff"),("Maven","packages"),("pytest","review"),
    ("Robot Framework","review"),("WEditor","focus"),("uiautomator2","phone"),("Airtest","focus"),
    ("Redis","database"),("Nginx","mesh"),("Tomcat","ports"),("JVM","chip"),("CPU","chip"),("GIL","chip"),
    ("I/O","disk"),("IOPS","disk"),("磁盘","disk"),("端口","ports"),("连接数","ports"),("RPC","ports"),
    ("网络","mesh"),("WebSocket","stream"),("MQ","stream"),("HTTP","ports"),("JSON","schema"),("YAML","schema"),
    ("ORM","database"),("SQL","database"),("数据库","database"),("序列化","schema"),("JWT","shield"),("鉴权","shield"),
    ("表单","browser"),("登录","shield"),("注册","profile"),("路由","mesh"),("过滤","retrieval"),("CSS","blueprint"),
    ("Vue","browser"),("React","browser"),("Scrapy","crawl"),("爬取","crawl"),("抓包","stream"),
    ("截图","focus"),("图像","focus"),("报告","dashboard"),("数据驱动","database"),("参数化","schema"),
    ("日志","stream"),("队列","stream"),("进程","mesh"),("并发","mesh"),("线程","mesh"),("协程","flow"),
    ("闭包","tree"),("装饰器","tree"),("迭代","flow"),("排序","graph"),("查找","retrieval"),("算法","tree"),
    ("Django","browser"),("Flask","ports"),("Python","terminal"),("Java","terminal"),
    ("SSE","stream"),("MCP","ports"),("RAG","retrieval"),("Agent","tree"),("App","phone"),("IOS","phone"),
    ("Shell","terminal"),("H5","browser"),("Chrome","browser"),("Excel","schema"),("Obsidian","note"),
    ("接口","ports"),("工作流","flow"),("通知","stream"),("音频","stream"),("设备","phone"),("实战","blueprint"),
]
GENERIC = {
    "自动化测试":"browser", "测试平台与工具":"dashboard", "质量工程":"shield", "性能与监控":"graph",
    "Agent 与工作流":"tree", "MCP 与 Skills":"ports", "RAG 与知识库":"retrieval", "AI 编程与研发":"flow",
    "模型与本地部署":"chip", "Python 编程":"terminal", "后端开发":"ports", "前端与应用":"browser",
    "项目实战":"blueprint", "爬虫与数据采集":"crawl", "效率工具":"terminal", "系统与调试工具":"stream",
    "Git 与代码协作":"diff", "持续集成":"flow", "写作与图解":"papers", "职业与实践":"note",
}
GENERIC_TITLES = re.compile(r"^(?:《流畅的Python》第.{1,4}章学习笔记|Git基础知识[（(].+|Jenkins[（(].+|ARTS.{1,8}|Django学习_简易博客.+|PC端自动化测试[（(].+)$")
NOISE = re.compile(r"^(?:上一篇|下一篇|参考|总结|简介|前言|小结|写在前面|延伸阅读|参考链接|推荐阅读|概述|环境准备|欢迎关注|推荐|项目介绍|结语|文章目录|视频|原文|代码示例|截图|示例|安装|什么是|说明|步骤)\s*[：:。！!？?]*$")
HEX = re.compile(r"#[0-9A-Fa-f]{6}")


def clean(t):
    t = re.sub(r"https?://[^\s）]+|[\w.+-]+@[\w.-]+\.[a-z]{2,}|[\x00-\x1f]|[\U00010000-\U0010ffff]", " ", t)
    return " ".join(t.strip(" #「」“”|，。　").split())


def body_headings(entry):
    from bs4 import BeautifulSoup
    source = ROOT / entry["path"].lstrip("/")
    doc = BeautifulSoup(source.read_text(encoding="utf-8"), "lxml").select_one(".post-body")
    out = []
    for h in doc.find_all(["h1", "h2", "h3", "h4", "strong"], limit=38):
        if h.find_parent(["pre", "code", "table"]): continue
        v = clean(h.get_text(" ", strip=True))
        v = re.sub(r"^(?:第[一二三四五六七八九十\d]+[章节步部分]|[一二三四五六七八九十\d]+[.、．:：])\s*", "", v)
        if 3 <= len(v) <= 28 and not NOISE.fullmatch(v) and not any(s in v for s in ("公众号","http","目录","密钥","密码：","token=")) and v not in out:
            out.append(v)
    return out


def brief(entry, rules):
    title = clean(entry["title"])
    chapter = re.match(r"^(.+?) · 第 (\d+) 篇[｜|](.*)$", title)
    base = chapter[3] if chapter else title
    topics = entry.get("topics", [])
    label = f"{chapter[1]}  /  {chapter[2]}" if chapter else (topics[1] if len(topics)>1 else topics[0] if topics else "测试游记")
    for pat, kind, msg, chips in rules:
        if re.search(pat, title, re.I):
            return msg, kind, chips.split("、"), label
    heads = body_headings(entry)
    if GENERIC_TITLES.fullmatch(base) and heads:
        if base.startswith("《流畅的Python》"):
            n = re.search(r"第(.+?)章",base)
            if n: label = "流畅的 Python  /  第" + n[1] + "章"
        elif base.startswith("Jenkins"): label = "Jenkins  /  流水线"
        elif base.startswith("Git"): label = "Git  /  基础知识"
        base = heads[0] + ("与" + heads[1] if len(heads)>1 and len(heads[0]+heads[1])<15 else "")
    elif ":" in base and re.match(r"^\d+\.",base):
        base = re.sub(r"^\d+\.", "", base)
    matched = [(term,g) for term,g in KEYWORDS if term.casefold() in base.casefold()]
    broad = {"JMeter","Git","Selenium","WebDriver","Chrome","Vue","React","Django","Flask","Python","Java","pytest","App","接口","Agent","实战"}
    more_specific = [pair for pair in matched if pair[0] not in broad]
    kind = next((g for _,g in (more_specific or matched)), GENERIC.get(topics[1] if len(topics)>1 else "", "diagram"))
    related = [term for term,_ in KEYWORDS if term.casefold() in base.casefold()]
    for h in heads:
        if h not in base and base not in h and len(h)<=12 and not any(h in r or r in h for r in related):
            related.append(h)
        if len(related)>=3: break
    if not related:
        words = re.findall(r"(?<![\w-])(?:[A-Z]{2,7}|[a-zA-Z]{3,16})(?![\w-])",entry.get("text","")[:700])
        related += [w for w in dict.fromkeys(words) if w.casefold() not in {"the","and","with","from","class","function","test","root","none","false","true","return","name","this","print","null","const","https","http","html","python","com","www"}][:2]
    return base, kind, related[:3], label


def mix(a,b,p):
    a,b=tuple(bytes.fromhex(a[1:])),tuple(bytes.fromhex(b[1:]))
    return "#" + "".join(f"{round(x*(1-p)+y*p):02x}" for x,y in zip(a,b))


def font(n,bold=False,mono=False):
    return ImageFont.truetype(str(MONO if mono else CJK),n,index=int(bold))


def lines(draw, line, f, maxw):
    pieces = re.findall(r"[\x21-\x7e]+|\s+|[^\x00-\x7f]",line)
    ret, cur = [], ""
    for p in pieces:
        if draw.textlength(p,font=f)>maxw:
            if cur: ret.append(cur.strip()); cur=""
            while len(p)>1 and draw.textlength(p,font=f)>maxw:
                cut = max(i for i in range(1,len(p)) if draw.textlength(p[:i],font=f)<=maxw)
                ret.append(p[:cut]);p=p[cut:]
        if cur and draw.textlength(cur+p,font=f)>maxw:
            ret.append(cur.strip());cur=p.lstrip()
        else:cur+=p
    if cur.strip():ret.append(cur.strip())
    return ret


def art(d,k,box,a,b,f,s,seed):
    x,y,w,h=box
    def pos(p):return (x+p[0]*w/100,y+p[1]*h/100)
    def rec(x1,y1,x2,y2,fill=s,stroke=a,r=3,n=3):
        p=pos((x1,y1));q=pos((x2,y2));d.rounded_rectangle((p,q),radius=r,fill=fill,outline=stroke,width=n)
    def circ(x1,y1,r=4,fill=a,stroke=None):
        u,v=pos((x1,y1));d.ellipse((u-r,v-r,u+r,v+r),fill=fill,outline=stroke,width=3)
    def L(p,col=a,width=4):
        d.line([pos(i) for i in p],fill=col,width=width,joint="curve")
    def arrow(x1,y1,x2,y2,col=a):
        L([(x1,y1),(x2,y2)],col)
        ang=math.atan2(y2-y1,x2-x1)
        L([(x2-3.1*math.cos(ang-.56),y2-4.4*math.sin(ang-.56)),(x2,y2),(x2-3.1*math.cos(ang+.56),y2-4.4*math.sin(ang+.56))],col)
    def card(x1,y1,x2,y2,col=a,n=3):
        rec(x1,y1,x2,y2,s,col,7,3)
        for j in range(n):
            yy=y1+(y2-y1)*(.28+.2*j); L([(x1+5,yy),(x2-5-(j%2)*6,yy)],col,3)
    def check(x1,y1,col=b):L([(x1-4,y1),(x1-1,y1+5),(x1+6,y1-6)],col,5)
    def stack(x1,y1,x2,y2,col=a,n=3):
        for i in range(n-1,-1,-1):
            rec(x1+i*3,y1+i*7,x2+i*3,y2+i*7,s,col,8,3)
        L([(x1+6,y1+6),(x2-6,y1+6)],col,3)
    def window(x1=10,y1=14,x2=89,y2=86,col=a):
        rec(x1,y1,x2,y2,s,col,12,4); L([(x1,y1+13),(x2,y1+13)],col,3)
        for i in range(3):circ(x1+6+i*5,y1+6.5,3,col)
    if k == "editor":
        stack(7,24,38,68,a)
        for v in (35,42,49):L([(13,v),(32,v)],a,3)
        arrow(42,51,52,51,b)
        window(54,16,93,85,b)
        L([(60,62),(68,49),(75,58),(86,41)],a,4)
        for u,v in [(60,62),(68,49),(75,58),(86,41)]:circ(u,v,4,a)
        L([(61,73),(87,73)],b,3); circ(78,73,8,b)
    elif k == "branch":
        L([(10,67),(91,67)],a,4)
        L([(24,67),(37,37),(67,37),(80,67)],b,5)
        for u,v in [(12,67),(24,67),(48,67),(65,67),(81,67),(90,67)]: circ(u,v,7,a)
        for u in (36,51,67): circ(u,37,7,b)
        arrow(72,28,85,28,b)
    elif k == "snapshot":
        for u,v,co in [(7,36,a),(35,26,b),(64,16,a)]:
            stack(u,v,u+22,v+37,co,3)
            L([(u+4,v+15),(u+17,v+15)],co,4)
            L([(u+4,v+23),(u+13,v+23)],co,3)
        arrow(13,87,88,87,b)
    elif k == "load":
        L([(10,18),(10,84),(91,84)],a,4)
        vals=[(12,70),(26,70),(26,59),(42,59),(42,48),(57,48),(57,31),(71,31),(71,20),(88,20)]
        L(vals,b,5)
        for u,v in vals[1::2]:circ(u,v,5,b)
        L([(11,43),(90,43)],f,2)
    elif k in {"tree","diagram","mesh","map"}:
        if k=="mesh":
            for u,v in [(77,15),(82,52),(74,85),(30,16),(29,84)]:
                L([(51,50),(u,v)],a,4);rec(u-8,v-6,u+8,v+6,s,b)
            rec(43,42,60,59,a,None,9)
        else:
            ys=[20,49,78] if seed%2==0 else [16,49,82]
            rec(9,37,30,62,a,None,10)
            for j,v in enumerate(ys):
                col=b if j==1 else a
                L([(30,49),(40,49),(40,v),(56,v)],col,4);rec(56,v-7,78,v+7,s,col,9)
                circ(88,v,6,col);L([(78,v),(87,v)],col,3)
    elif k in {"flow","compare","diff","review","papers","note","profile","blueprint"}:
        if k=="flow":
            coords=[(10,55),(30,40),(53,66),(79,35)]
            for i,(u,v) in enumerate(coords):
                if i: arrow(*coords[i-1],u-7,v,b if i==2 else a)
                rec(u-6,v-10,u+8,v+10,s,b if i==2 else a,5)
                circ(u+1,v,4,b if i==2 else a)
            L([(9,85),(89,85)],a,3)
        elif k=="review":
            card(13,10,61,86,a,3);card(47,21,89,72,b,2);check(67,60,b)
            circ(27,69,5,a);circ(38,69,5,b)
        elif k in {"compare","diff"}:
            card(8,18,44,83,a);card(56,18,92,83,b)
            L([(45,53),(55,53)],f,3);circ(50,53,5,f)
            L([(18,64),(27,64)],a,4);check(71,63,b)
        elif k=="profile":
            window();circ(38,49,21,a);rec(29,61,48,70,a,None,8);card(53,36,78,76,b,3)
        elif k in {"papers","note"}:
            stack(16,17,69,75,a);rec(18,14,69,75,s,a,6,4)
            for i in range(4):L([(26,30+i*10),(61-i%3*6,30+i*10)],a,3)
            circ(72,65,29,b);check(72,65,s)
        else:
            window();rec(23,38,62,75,s,a,5);rec(63,49,79,73,s,b,5)
            L([(31,65),(42,48),(53,60)],b);circ(42,48,5,b)
    elif k in {"browser","focus","terminal","phone","crawl","shield"}:
        if k=="phone":
            rec(30,7,69,92,s,a,16,4);L([(43,17),(56,17)],a,4)
            rec(37,27,62,67,a,None,8);check(49,47,s);circ(49,80,6,b)
            L([(69,42),(82,42),(90,33)],b,3);circ(90,33,5,b)
        elif k=="terminal":
            window();L([(24,45),(33,54),(24,63)],b,5);L([(40,64),(62,64)],a,4);circ(76,75,6,b)
        elif k=="focus":
            window();rec(28,42,59,73,s,b,5);L([(60,70),(78,85)],b,5);circ(43,57,11,a)
        elif k=="crawl":
            window(6,13,76,76);L([(16,40),(57,40)],a);L([(16,54),(45,54)],a)
            arrow(60,62,71,78,b);stack(69,76,87,85,b,2)
        elif k=="shield":
            window(7,14,55,86);L([(18,38),(43,38)],a);L([(18,53),(36,53)],a)
            d.polygon([pos(p) for p in [(51,39),(72,30),(91,39),(89,64),(72,88),(54,67)]], fill=s,outline=b,width=4);check(71,57,b)
        else:
            window();rec(17,40,39,74,s,a,6);rec(45,40,81,55,s,b,6)
            rec(45,61,81,74,s,a,6);circ(74,48,4,b)
    elif k in {"database","disk","packages","schema","chip","ports"}:
        if k=="database":
            stack(15,27,54,72,a);L([(58,50),(74,50)],b);arrow(65,66,75,66,b)
            card(74,33,92,78,b,2)
        elif k=="disk":
            rec(18,13,81,86,s,a,13,4);circ(46,49,h*.27,a);circ(46,49,19,s)
            L([(75,70),(60,59),(52,50)],b,7);circ(75,70,7,b)
        elif k=="chip":
            rec(27,23,73,78,s,a,11,5);rec(35,34,65,67,a,None,6);circ(50,50,14,s)
            for z in range(36,67,7):
                L([(z,10),(z,22)],a);L([(z,78),(z,90)],b)
            for z in range(35,68,10):
                L([(13,z),(27,z)],a);L([(73,z),(87,z)],b)
        elif k=="schema":
            card(13,16,70,82,a);L([(39,21),(39,78)],a,3);rec(55,47,87,76,s,b,7);check(70,61,b)
        elif k=="packages":
            stack(11,29,47,70,a);stack(50,17,84,66,b);L([(13,85),(91,85)],a)
        else:
            card(7,26,29,76,a,2);card(70,26,93,76,b,2)
            for i,z in enumerate([38,50,63]): arrow(30,z,69,z,a if i!=1 else b)
    elif k in {"graph","dashboard","stream","retrieval"}:
        if k=="retrieval":
            stack(12,25,46,69,a);circ(67,47,h*.22,b);circ(67,47,h*.17,s);L([(74,62),(89,86)],b,8)
        else:
            window(6,10,94,89)
            L([(18,38),(18,76),(82,76)],a,3)
            seq = [(19,64),(31,59),(40,66),(50,44),(56,54),(64,37),(78,47),(83,38)]
            if k=="stream":
                seq=[(19,60),(27,60),(33,42),(41,70),(47,51),(58,51),(66,38),(72,62),(84,56)]
            L(seq,b,5)
            for u,v in seq[::2]:circ(u,v,4,b)
            if k=="dashboard":
                # Three status tiles and a waveform distinguish a dashboard from a single chart.
                for j in range(3):
                    xx=21+j*22
                    rec(xx,33,xx+15,41,s,a,3,2)
                    circ(xx+5,37,2,b)
    else:
        card(11,20,55,79,a);arrow(55,50,68,50,b);rec(68,35,91,65,b,None,8)


def cover(task):
    entry, brief_record = task
    title,k,chips,label=brief_record
    key=Path(entry["path"]).stem
    seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],"big")
    primary=entry.get("topics",["写作与复盘"])[0]
    bg,fg,a,b=STYLES.get(primary,STYLES["工程工具"])
    panel=mix(bg,fg,.075); outline=mix(bg,fg,.16); small=mix(bg,fg,.69)
    im=Image.new("RGB",SIZE,bg)
    d=ImageDraw.Draw(im)
    # Avoid placing important marks outside the crops used by the article list and series cards.
    for xx in range(22,1200,24):
        for yy in range(16,556,24):
            level=.065 + .035*(1+math.sin((xx+yy+(seed%31)*23)/160))
            col=mix(bg,fg,level)
            d.point((xx,yy),fill=col)
    d.line((72,108,1128,108),fill=outline,width=2)
    d.text((73,69),"测试游记  /  "+label,font=font(22,True),fill=small,anchor="ls")
    d.ellipse((1095,53,1107,65),fill=b)
    d.ellipse((1115,53,1127,65),fill=a)
    x=681
    shift=9*(seed%3)
    d.rounded_rectangle((x+shift,139,1128,454),radius=21,fill=panel,outline=outline,width=2)
    for i in range(5):d.line((x+26+shift,174+i*55,1103,174+i*55),fill=outline,width=1)
    art(d,k,(x+33+shift,168,377-shift,258),a,b,small,panel,seed)
    chosen=None
    for n in (56,52,48,44,40,37,34,31,27):
        f=font(n,True)
        rows=lines(d,title,f,565)
        if len(rows)<=3 and len(rows)*(n+15)<=209:
            chosen=f,rows,n
            break
    if chosen is None:
        raise ValueError(f"Cover title does not fit: {key}")
    f,rows,n=chosen
    start=285-(len(rows)-1)*(n+15)/2
    for i,l in enumerate(rows):
        d.text((72,start+i*(n+15)),l,font=f,fill=fg,anchor="lm")
    blend=mix(bg,a,.24)
    left=72
    for chip in dict.fromkeys(chips):
        cf=font(20,True)
        ws=d.textlength(chip,font=cf)
        if left+ws+25>637:continue
        d.rounded_rectangle((left,402,left+ws+24,439),radius=9,fill=blend)
        d.text((left+12,421),chip,font=cf,fill=fg,anchor="lm")
        left+=ws+36
    d.line((72,487,1128,487),fill=outline,width=2)
    d.text((73,514),entry.get("date","")[:10].replace("-","."),font=font(15,mono=True),fill=small,anchor="ls")
    d.text((1128,514),"ARTICLE NOTE",font=font(15,mono=True),fill=small,anchor="rs")
    OUT.mkdir(parents=True,exist_ok=True)
    im.save(OUT / f"{key}.webp","WEBP",quality=86,method=5)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids",nargs="+")
    parser.add_argument("--jobs",type=int,default=6)
    args=parser.parse_args()
    p=json.loads((ROOT/"search.json").read_text())
    rules=[line.split("|",3) for line in (ROOT/"scripts/cover_briefs.tsv").read_text().splitlines() if line and not line.startswith("#")]
    if args.ids:
        p=[x for x in p if Path(x["path"]).stem in args.ids]
    assert p
    tasks=[(entry,brief(entry,rules)) for entry in p]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        tuple(pool.map(cover,tasks,chunksize=4))
    print(f"Rendered {len(tasks)} article covers")


if __name__=="__main__":
    main()
