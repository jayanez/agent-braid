#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate docs/assets/agent-braid-overview.svg (README hero diagram).

Usage: python3 docs/assets/agent-braid-overview.py docs/assets/agent-braid-overview.svg
"""
import sys
from xml.sax.saxutils import escape as E
W=1200; M=40; BW=W-2*M; PAD=28
out=[]
def a(s): out.append(s)
def text(x,y,s,cls,anchor='middle'): a(f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{E(s)}</text>')
def band(y,h,title,sub,cls='band'):
    a(f'<rect x="{M}" y="{y}" width="{BW}" height="{h}" rx="18" class="{cls}"/>')
    text(M+PAD,y+34,title,'bt','start')
    if sub: text(W-M-PAD,y+34,sub,'bs','end')
def card(x,y,w,h,title,lines,cls='card',pill=None,pcls='pill'):
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" class="{cls}"/>')
    cx=x+w/2; n=len(lines)+(1 if pill else 0)
    ty=y+h/2-(n*17)/2+4
    text(cx,ty,title,'ct'); yy=ty+20
    for l in lines: text(cx,yy,l,'cs'); yy+=17
    if pill:
        pw=len(pill)*6.6+22
        a(f'<rect x="{cx-pw/2}" y="{yy-11}" width="{pw}" height="20" rx="10" class="{pcls}"/>'); text(cx,yy+3,pill,'pt')
def row(n,w,gap,y0=None):
    total=n*w+(n-1)*gap; x0=M+(BW-total)/2
    return [x0+i*(w+gap) for i in range(n)]
def arrow(x1,y1,x2,y2,cls='ar',label=None,lx=None,ly=None):
    a(f'<path d="M{x1} {y1} L{x2} {y2}" class="{cls}" marker-end="url(#m)"/>')
    if label:
        lx=lx if lx is not None else (x1+x2)/2; ly=ly if ly is not None else (y1+y2)/2
        lw=len(label)*6.4+18
        a(f'<rect x="{lx-lw/2}" y="{ly-11}" width="{lw}" height="22" rx="11" class="lab"/>'); text(lx,ly+4,label,'lt')

# Title
text(W/2,46,'Agent Braid: the algebraic concurrency layer for multi-agent AI development','title')
text(W/2,70,'Agents work in parallel; Agent Braid decides, with evidence, which work commutes. Only an operator grant executes.','subtitle')

# Band 1: AIDLC
y1=96; h1=150
band(y1,h1,'01  Multi-agent AI development lifecycle (AIDLC)','Claude Code · Codex · subagents')
xs=row(5,190,22)
for x,(t,s) in zip(xs,[('Plan agent','breaks work into tasks'),('Build agents','edit code in parallel'),('Test agent','runs and fixes checks'),('Review agent','reviews and merges'),('Shared codebase','files, branches, effects')]):
    card(x,y1+60,190,66,t,[s],'card db' if t=='Shared codebase' else 'card host')

# Band 2: hero
y2=y1+h1+44; h2=330
arrow(W/2,y1+h1+2,W/2,y2-4,'ar','declare tasks (AIM effects or Git commits)')
band(y2,h2,'02  Algebraic concurrency layer  ·  System 2 (shipped)','via native plugin, MCP tools or CLI','hero')
cy=y2+64
card(M+PAD+8,cy+40,250,150,'Declared effects',['what each task reads,','writes and creates,','and under which conditions'],'card in',pill='AIM · Git commits',pcls='pill v')
ax=M+PAD+8+250+56; aw=290
a(f'<rect x="{ax}" y="{cy+20}" width="{aw}" height="190" rx="14" class="card core"/>')
text(ax+aw/2,cy+52,'Commutation analysis','ct big')
text(ax+aw/2,cy+74,'effect graph over shared resources','cs')
text(ax+aw/2,cy+92,'Git replay of every admissible order','cs')
# braid motif
bx=ax+40; by=cy+112; bw=aw-80
cols=['s1','s2','s3']
ys=[by,by+30,by+60]
import math
for i,c in enumerate(cols):
    pts=[]
    for k in range(0,101):
        t=k/100; x=bx+bw*t
        # simple braid: strands swap
        ph=[0,2*math.pi/3,4*math.pi/3][i]
        y=by+30+28*math.sin(2*math.pi*t*1.5+ph)
        pts.append(f'{x:.1f},{y:.1f}')
    a(f'<polyline points="{" ".join(pts)}" class="strand {c}"/>')
arrow(M+PAD+8+250+4,cy+115,ax-6,cy+115,'ar')
# outcomes
ox=ax+aw+56; ow=W-M-PAD-8-ox
outs=[('independent-candidate','can run in parallel','ok'),('ordered','follow the dependency order','ord'),('conflicting','serialize or isolate','bad'),('unknown','keep exclusive ownership','unk')]
oh=42; og=12; oy0=cy+20+(190-(4*oh+3*og))/2
arrow(ax+aw+4,cy+115,ox-6,cy+115,'ar')
for i,(k,v,c) in enumerate(outs):
    y=oy0+i*(oh+og)
    a(f'<rect x="{ox}" y="{y}" width="{ow}" height="{oh}" rx="10" class="out {c}"/>')
    a(f'<circle cx="{ox+20}" cy="{y+oh/2}" r="5" class="dot {c}"/>')
    text(ox+34,y+oh/2+4,k,'ok','start'); text(ox+ow-16,y+oh/2+4,v,'ov','end')
text(W/2,y2+h2-22,'Every report states its inputs, method and limits, and carries executionAuthorization: false.','foot')

# Band 3: authority and execution
y3=y2+h2+44; h3=150
arrow(W/2,y2+h2+2,W/2,y3-4,'ar','verified plan')
band(y3,h3,'03  Authority and execution','the only path that changes anything')
xs=row(4,220,64)
specs=[('Verified plan',['exact plan digest'],'card core'),('Operator grant',['one use, exact digest'],'card auth'),('Owned Git runtime',['isolated prep, serial publish'],'card core'),('Private result',['checkpoints + journal','verify · recover'],'card db')]
for x,(t,l,c) in zip(xs,specs): card(x,y3+58,220,70,t,l,c)
for i in range(3):
    arrow(xs[i]+222,y3+93,xs[i+1]-6,y3+93,'ar auth' if i==0 else 'ar')

# Band 4: layers
y4=y3+h3+28; h4=170
band(y4,h4,'04  Opt-in, experimental and in-development layers','none of them can authorize execution','side')
xs=row(4,238,32)
L=[('Local telemetry',['numeric counts, local only'],'off by default','pill'),('System One',['decision layer in shadow mode','no learned model yet'],'opt-in · S1.5','pill v'),('Braid Harness lab',['offline variant evaluation'],'experimental · HAR','pill a'),('Loom viewer',['event stream + 3D braid'],'in development · VIS','pill s')]
for x,(t,l,p,pc) in zip(xs,L): card(x,y4+56,238,94,t,l,'card side',pill=p,pcls=pc)
H=y4+h4+30

css='''
:root{--bg:#ffffff;--band:#f6f8fb;--bandb:#e2e8f0;--hero:#f5f3ff;--herob:#c4b5fd;--side:#fafafa;--card:#ffffff;--cardb:#cbd5e1;--tx:#0f172a;--mu:#475569;--vi:#6d28d9;--vibg:#ede9fe;--ok:#15803d;--okbg:#ecfdf5;--ord:#1d4ed8;--ordbg:#eff6ff;--bad:#b91c1c;--badbg:#fef2f2;--unk:#475569;--unkbg:#f1f5f9;--auth:#be123c;--authbg:#fff1f2;--amb:#b45309;--ambbg:#fffbeb;--sky:#0369a1;--skybg:#f0f9ff;--ar:#64748b}
@media (prefers-color-scheme: dark){:root{--bg:#0d1117;--band:#161b22;--bandb:#30363d;--hero:#1c1530;--herob:#6d28d9;--side:#12161c;--card:#0f141b;--cardb:#3b4250;--tx:#f0f6fc;--mu:#9da7b3;--vi:#c4b5fd;--vibg:#2e1f55;--ok:#4ade80;--okbg:#0f2a1a;--ord:#93c5fd;--ordbg:#10213f;--bad:#fca5a5;--badbg:#3a1414;--unk:#cbd5e1;--unkbg:#1e2530;--auth:#fda4af;--authbg:#3b1220;--amb:#fcd34d;--ambbg:#33260a;--sky:#7dd3fc;--skybg:#0b2537;--ar:#8b949e}}
svg{font-family:ui-sans-serif,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.bg{fill:var(--bg)}
.title{font-size:22px;font-weight:700;fill:var(--tx)}
.subtitle{font-size:13.5px;fill:var(--mu)}
.band{fill:var(--band);stroke:var(--bandb)}
.hero{fill:var(--hero);stroke:var(--herob);stroke-width:1.5}
.side{fill:var(--side);stroke:var(--bandb);stroke-dasharray:6 5}
.bt{font-size:14px;font-weight:700;fill:var(--tx);letter-spacing:.2px}
.bs{font-size:12.5px;fill:var(--mu)}
.card{fill:var(--card);stroke:var(--cardb)}
.card.core{stroke:var(--vi);stroke-width:1.5}
.card.in{stroke:var(--vi);stroke-dasharray:4 3}
.card.auth{fill:var(--authbg);stroke:var(--auth);stroke-width:2;stroke-dasharray:6 4}
.card.db{fill:var(--skybg);stroke:var(--sky)}
.ct{font-size:14.5px;font-weight:650;fill:var(--tx)}
.ct.big{font-size:17px;font-weight:700;fill:var(--vi)}
.cs{font-size:12px;fill:var(--mu)}
.pill{fill:var(--unkbg)} .pill.v{fill:var(--vibg)} .pill.a{fill:var(--ambbg)} .pill.s{fill:var(--skybg)}
.pt{font-size:11px;font-weight:600;fill:var(--tx)}
.out{stroke-width:1.2} .out.ok{fill:var(--okbg);stroke:var(--ok)} .out.ord{fill:var(--ordbg);stroke:var(--ord)} .out.bad{fill:var(--badbg);stroke:var(--bad)} .out.unk{fill:var(--unkbg);stroke:var(--unk)}
.dot.ok{fill:var(--ok)} .dot.ord{fill:var(--ord)} .dot.bad{fill:var(--bad)} .dot.unk{fill:var(--unk)}
.ok{font-size:13px;font-weight:650;fill:var(--tx);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.ov{font-size:12.5px;fill:var(--mu)}
.foot{font-size:12px;fill:var(--mu);font-style:italic}
.ar{stroke:var(--ar);stroke-width:1.6;fill:none} .ar.auth{stroke:var(--auth)}
.lab{fill:var(--bg);stroke:var(--bandb)} .lt{font-size:11.5px;fill:var(--mu)}
.strand{fill:none;stroke-width:3;stroke-linecap:round;opacity:.9} .s1{stroke:#8b5cf6} .s2{stroke:#06b6d4} .s3{stroke:#f59e0b}
#m path{fill:var(--ar)}
'''
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">',
 '<title id="t">Agent Braid: the algebraic concurrency layer for multi-agent AI development</title>',
 '<desc id="d">Parallel agents in the AI development lifecycle declare tasks; Agent Braid computes which operations commute (parallel), are ordered, conflict (serialize or isolate) or are unknown (exclusive ownership); a verified plan runs only after a one-use operator grant on the exact digest; telemetry, System One shadow mode, the Harness lab and the Loom viewer are opt-in, experimental or in development and never authorize execution.</desc>',
 f'<style>{css}</style>',
 '<defs><marker id="m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z"/></marker></defs>',
 f'<rect width="{W}" height="{H}" class="bg"/>']+out+['</svg>']
open(sys.argv[1],'w').write('\n'.join(svg)+'\n')
