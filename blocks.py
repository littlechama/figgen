"""ブロックの描画。1ブロック＝1関数で、HTMLの断片を返す。

新しいブロックを足すときは、関数を1つ書いて RENDERERS に登録するだけ。
CSSは theme.css 側に置く（見た目とデータを混ぜない）。
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

# ---------------------------------------------------------------- 文字まわり


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def rich(s) -> str:
    """図の中で使う最小限の記法だけ通す。

    **太字** ／ `コード` ／ [[強調]]（アクセント色）／ 改行。
    Markdownを全部通すと図の中で崩れるので、意図的にこれだけ。

    制約（承知の上で残している）: 開始と終了の記号が同じ（`**` と `` ` ``）なので、
    記号が交差する書き方（`**あ` + `` `い** `` のような並び）は入れ子が壊れ、装飾が
    後ろへ漏れる。素の `**` を本文に書いた場合も同じ。仕様のYAMLを書くときは
    記号を交差させない。閉じ忘れは素通しになるだけなので害はない。
    HTMLは先に esc() でエスケープするので、タグが混ざることはない。
    """
    if s is None:
        return ""
    out = esc(s)
    for a, b, tag in (("**", "**", "b"), ("`", "`", "code"), ("[[", "]]", 'span class="mark"')):
        parts, i = [], 0
        close = tag.split()[0]
        while True:
            p = out.find(a, i)
            q = out.find(b, p + len(a)) if p >= 0 else -1
            if p < 0 or q < 0:
                parts.append(out[i:])
                break
            parts.append(out[i:p])
            parts.append(f"<{tag}>{out[p + len(a):q]}</{close}>")
            i = q + len(b)
        out = "".join(parts)
    return out.replace("\n", "<br/>")


def _cls(*names) -> str:
    got = [n for n in names if n]
    return f' class="{" ".join(got)}"' if got else ""


def _label(b: dict) -> str:
    return f'<div class="block-label">{rich(b["label"])}</div>' if b.get("label") else ""


# ---------------------------------------------------------------- ブロック


def banner(b: dict, ctx: dict) -> str:
    note = f'<div class="note">{rich(b["note"])}</div>' if b.get("note") else ""
    tone = "plain" if b.get("tone") == "plain" else ""
    return (f'{_label(b)}<div class="banner {tone}">'
            f'<div class="t">{rich(b.get("text"))}</div>{note}</div>')


def _node(it: dict, arrow: str = "", numbered: bool = False, idx: int = 0) -> str:
    """ノード1つ。arrow は右側に出す矢印の種類（"" / normal / strong）。"""
    tone = it.get("tone") or ""
    cls = ["node", tone]
    if arrow:
        cls.append("arrow")
        if arrow == "strong":
            cls.append("arrow-strong")
    n = ""
    if it.get("n"):
        n = f'<div class="n">{rich(it["n"])}</div>'
    elif numbered:
        n = f'<div class="n">{idx}</div>'
    body = f'<div class="b">{rich(it["body"])}</div>' if it.get("body") else ""
    lab = ""
    if it.get("arrow_label"):
        wide = " wide" if len(str(it["arrow_label"])) > 12 else ""
        lab = f'<div class="arrow-label{wide}">{rich(it["arrow_label"])}</div>'
    inner = f'{n}<div class="t">{rich(it.get("text"))}</div>{body}{lab}'
    return f'<div{_cls(*cls)}>{inner}</div>'


def _bypass_svg(n: int, frm: int, to: int, label: str, color: str = "var(--ink-3)") -> str:
    """ノード frm から to へ、下を迂回する点線の矢印。frm/to は1始まり。

    等幅グリッドなのでノード中心は (i-0.5)/n。gap の分だけずれるが、
    図として読める範囲なので割り切る。
    """
    x1 = (frm - 0.5) / n * 100
    x2 = (to - 0.5) / n * 100
    d = f"M {x1:.2f} 0 V 62 H {x2:.2f} V 26"
    # 矢頭は preserveAspectRatio="none" だと潰れるので、SVGではなくCSSの三角で置く
    head = (f'<div style="position:absolute;left:{x2:.2f}%;top:4px;'
            f'transform:translateX(-50%);width:0;height:0;'
            f'border:6px solid transparent;border-bottom-color:{color}"></div>')
    lab = f'<div class="lab">{rich(label)}</div>' if label else ""
    return (f'<div class="bypass"><svg viewBox="0 0 100 100" preserveAspectRatio="none">'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" '
            f'stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/></svg>'
            f"{head}{lab}</div>")


def chain(b: dict, ctx: dict) -> str:
    """横並びの連鎖。items の間に矢印を出す。

    emphasis: [3] のように書くと、3番目のノードの右の矢印が太くなる（1始まり）。
    items[i].arrow_label を書くと、その矢印の上にラベルが出る。
    bypass: {from: 2, to: 5, label: "..."} で下を迂回する点線。
    """
    items = b.get("items") or []
    n = len(items)
    emph = set(b.get("emphasis") or [])
    gap = "tight" if b.get("tight") else ""
    if any(it.get("arrow_label") for it in items):
        gap += " has-labels"
    cells = []
    for i, it in enumerate(items, 1):
        arrow = "" if i == n else ("strong" if i in emph else "normal")
        cells.append(_node(it, arrow, numbered=bool(b.get("numbered")), idx=i))
    # ノードを1行目、注記を2行目に置く。同じグリッドに並べると高さが自動で揃う
    if any(it.get("note") for it in items):
        for it in items:
            note_html = rich(it["note"]) if it.get("note") else ""
            cells.append(f'<div class="node-note">{note_html}</div>')
    grid = (f'<div class="row {gap}" style="grid-template-columns:repeat({n},1fr)">'
            + "".join(cells) + "</div>")
    by = ""
    if b.get("bypass"):
        p = b["bypass"]
        by = _bypass_svg(n, int(p["from"]), int(p["to"]), p.get("label", ""))
    return f"{_label(b)}{grid}{by}"


def steps(b: dict, ctx: dict) -> str:
    """番号付きの流れ。chain の numbered 版。"""
    b = {**b, "numbered": True}
    return chain(b, ctx)


def columns(b: dict, ctx: dict) -> str:
    """N列のパネル。between に文字列を並べると、列と列の間に入る。"""
    cols = b.get("columns") or []
    between = b.get("between") or []
    parts, widths = [], []
    for i, c in enumerate(cols):
        badge = f'<span class="badge">{rich(c["badge"])}</span>' if c.get("badge") else ""
        head = ""
        if c.get("title"):
            head = (f'<div class="hd"><div class="t">{rich(c["title"])}{badge}</div></div>')
        lis = []
        for it in (c.get("items") or []):
            if isinstance(it, str):
                it = {"text": it}
            lis.append(f'<li{_cls(it.get("tone"))}>{rich(it.get("text"))}</li>')
        ft = f'<div class="ft">{rich(c["ft"])}</div>' if c.get("ft") else ""
        body = f'<div class="bd"><ul>{"".join(lis)}</ul>{ft}</div>' if (lis or ft) else ""
        parts.append(f'<div{_cls("col", c.get("tone"))}>{head}{body}</div>')
        widths.append(c.get("width", 1))
        if i < len(cols) - 1 and i < len(between) and between[i]:
            bt = between[i]
            if isinstance(bt, dict):
                v = f'<div class="v">{rich(bt.get("value"))}</div>' if bt.get("value") else ""
                inner = f'<div>{rich(bt.get("text"))}{v}</div>'
            else:
                inner = rich(bt)
            parts.append(f'<div class="col-between">{inner}</div>')
            widths.append("between")
    tpl = " ".join("auto" if w == "between" else f"{w}fr" for w in widths)
    return (f'{_label(b)}<div class="cols" style="grid-template-columns:{tpl}">'
            + "".join(parts) + "</div>")


def callout(b: dict, ctx: dict) -> str:
    lb = f'<div class="lb">{rich(b["label_in"])}</div>' if b.get("label_in") else ""
    body = f'<div class="b">{rich(b["body"])}</div>' if b.get("body") else ""
    return (f'{_label(b)}<div{_cls("callout", b.get("tone"))}>'
            f'{lb}<div class="t">{rich(b.get("text"))}</div>{body}</div>')


def metrics(b: dict, ctx: dict) -> str:
    items = b.get("items") or []
    cells = []
    for m in items:
        c = f'<div class="c">{rich(m["caption"])}</div>' if m.get("caption") else ""
        cells.append(f'<div{_cls("metric", m.get("tone"))}>'
                     f'<div class="v">{rich(m.get("value"))}</div>'
                     f'<div class="l">{rich(m.get("label"))}</div>{c}</div>')
    return (f'{_label(b)}<div class="metrics" '
            f'style="grid-template-columns:repeat({len(items)},1fr)">' + "".join(cells) + "</div>")


def table(b: dict, ctx: dict) -> str:
    heads = b.get("headers") or []
    align = b.get("align") or []

    def a(i):
        return ' class="num"' if i < len(align) and align[i] == "num" else ""

    th = "".join(f"<th{a(i)}>{rich(h)}</th>" for i, h in enumerate(heads))
    rows = []
    for r in (b.get("rows") or []):
        tds = []
        for i, cell in enumerate(r):
            cls = a(i)
            if isinstance(cell, dict):
                if cell.get("em"):
                    cls = f' class="{"num em" if "num" in cls else "em"}"'
                cell = cell.get("text", "")
            tds.append(f"<td{cls}>{rich(cell)}</td>")
        rows.append(f"<tr>{''.join(tds)}</tr>")
    return (f"{_label(b)}<table><thead><tr>{th}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def note(b: dict, ctx: dict) -> str:
    return f'{_label(b)}<div class="note-block">{rich(b.get("text"))}</div>'


def spacer(b: dict, ctx: dict) -> str:
    return f'<div style="height:{int(b.get("h", 10))}px"></div>'


# ---------------------------------------------------------------- 散布＋囲い


def _hull(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """凸包（Andrew monotone chain）。2点以下はそのまま返す。"""
    p = sorted(set(pts))
    if len(p) <= 2:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo = []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    up = []
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def _field_svg(points: list[dict], clusters: list[list[int]], color: str,
               w: int = 430, h: int = 300, pad: int = 26) -> str:
    """同じ点の並びに、クラスタごとの囲いを描く。

    囲いは凸包を太い丸継ぎの線で描くだけ。これだけで丸みのある袋になる。
    2点・1点のクラスタでも線幅で潰れずに出る。
    """
    xs = [p["x"] for p in points] or [0]
    ys = [p["y"] for p in points] or [0]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    sx = (w - 2 * pad) / (x1 - x0 or 1)
    sy = (h - 2 * pad) / (y1 - y0 or 1)
    s = min(sx, sy)
    ox = pad + ((w - 2 * pad) - (x1 - x0) * s) / 2
    oy = pad + ((h - 2 * pad) - (y1 - y0) * s) / 2
    P = [(ox + (p["x"] - x0) * s, oy + (p["y"] - y0) * s) for p in points]

    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="display:block">']
    for cl in clusters:
        if len(cl) < 2:
            continue
        hull = _hull([P[i] for i in cl])
        d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in hull) + " Z"
        out.append(f'<path d="{d}" fill="{color}" fill-opacity="0.10" stroke="{color}" '
                   f'stroke-opacity="0.55" stroke-width="30" stroke-linejoin="round" '
                   f'stroke-linecap="round"/>')
        out.append(f'<path d="{d}" fill="{color}" fill-opacity="0.10" stroke="none"/>')
    for i, (x, y) in enumerate(P):
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0b0b0b" fill-opacity="0.72" '
                   f'stroke="#fcfcfb" stroke-width="1.5"/>')
    out.append("</svg>")
    return "".join(out)


def scatter_pair(b: dict, ctx: dict) -> str:
    """同じ点の集合を、2通りの束ね方で囲って並べる。

    data: JSONへのパス（spec からの相対）。
      {"points":[{"id":..,"x":..,"y":..}], "groupings":{"key":{"clusters":[[id,..],..]}}}
    """
    data = b.get("data")
    if isinstance(data, str):
        p = (ctx["base"] / data).resolve()
        data = json.loads(p.read_text(encoding="utf-8"))
    pts = data["points"]
    index = {p["id"]: i for i, p in enumerate(pts)}
    colmap = {"blue": "#2a78d6", "orange": "#eb6834", "c1": "#2a78d6", "c2": "#eb6834"}

    def side(cfg, dflt_color):
        g = data["groupings"][cfg["grouping"]]
        cl = [[index[x] for x in c if x in index] for c in g["clusters"]]
        color = colmap.get(cfg.get("color", dflt_color), dflt_color)
        cap = f'<div class="c">{rich(cfg["caption"])}</div>' if cfg.get("caption") else ""
        klass = "c1" if color == "#2a78d6" else "c2"
        return (f'<div class="field {klass}"><div class="t">{rich(cfg.get("title"))}</div>{cap}'
                + _field_svg(pts, cl, color) + "</div>")

    mid = b.get("center") or {}
    pin = ""
    if mid.get("pin") is not None:
        pin = f'<div class="pin" style="left:calc({float(mid["pin"]) * 100:.1f}% - 1.5px)"></div>'
    gauge = ""
    if mid.get("pin") is not None:
        gauge = (f'<div class="gauge">{pin}'
                 f'<div class="end" style="left:0">{rich(mid.get("lo", "0"))}</div>'
                 f'<div class="end" style="right:0">{rich(mid.get("hi", "1.0"))}</div></div>')
    cap = f'<div class="c">{rich(mid["caption"])}</div>' if mid.get("caption") else ""
    center = (f'<div class="mid"><div class="v">{rich(mid.get("value"))}</div>'
              f'<div class="l">{rich(mid.get("label"))}</div>{gauge}{cap}</div>')
    return (f'{_label(b)}<div class="scatter" style="grid-template-columns:1fr 190px 1fr">'
            + side(b["left"], "blue") + center + side(b["right"], "orange") + "</div>")


# ---------------------------------------------------------------- 実際のグラフ


def _graph_svg(nodes: list[dict], edges: list, clusters: list[list[str]],
               meta: dict, color: str, w: int, h: int, hulls: bool = False) -> str:
    """ノードと辺をそのまま描く。

    座標は 0〜1 に正規化済みのものを受け取る（正規化は書き出し側の仕事）。

    hulls は既定で描かない。凸包はかたまりに属さないノードまで囲んでしまい、
    「この袋の中は同じかたまり」という誤読を生むため。かたまりは辺で読む。
    """
    pad = 30
    P = {n["id"]: (pad + n["x"] * (w - 2 * pad), pad + n["y"] * (h - 2 * pad)) for n in nodes}
    deg = {n["id"]: 0 for n in nodes}
    for a, b_, _ in edges:
        deg[a] = deg.get(a, 0) + 1
        deg[b_] = deg.get(b_, 0) + 1

    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="display:block;overflow:visible">']

    # 1. かたまりの袋（いちばん後ろ）。既定では描かない
    if hulls:
        for cl in clusters:
            pts = [P[i] for i in cl if i in P]
            if len(pts) < 2:
                continue
            hull = _hull(pts)
            d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in hull) + " Z"
            out.append(f'<path d="{d}" fill="{color}" fill-opacity="0.09" stroke="{color}" '
                       f'stroke-opacity="0.09" stroke-width="38" stroke-linejoin="round" '
                       f'stroke-linecap="round"/>')

    # 2. 辺。濃さは類似の強さ
    for a, b_, wt in edges:
        if a not in P or b_ not in P:
            continue
        op = 0.22 + 0.68 * min(float(wt) / 0.5, 1.0)
        (x1, y1), (x2, y2) = P[a], P[b_]
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                   f'stroke="{color}" stroke-opacity="{op:.2f}" stroke-width="2"/>')

    # 3. ノード。どこにも繋がらなかったものは灰色の輪郭にする
    for n in nodes:
        x, y = P[n["id"]]
        m = meta.get(n["id"], {})
        alone = deg.get(n["id"], 0) == 0
        ring = "#c3c2b7" if alone else color
        ink = "#898781" if alone else "#0b0b0b"
        out.append(
            f'<g><title>{esc(m.get("title", ""))}</title>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#fcfcfb" stroke="{ring}" '
            f'stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{y + 4.2:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" fill="{ink}">{esc(m.get("num", ""))}</text></g>')
    out.append("</svg>")
    return "".join(out)


def graph_pair(b: dict, ctx: dict) -> str:
    """2つの枠の実際のグラフを並べる。

    data は export_grouping.py が書き出した JSON。
      {"papers": {"p3": {"num":4,"title":".."}},
       "panels": {"significance": {"nodes":[..],"edges":[..],"clusters":[..], ...}}}
    座標は枠ごとに別々に置かれている前提（同じ位置ではない）。
    """
    data = b.get("data")
    if isinstance(data, str):
        data = json.loads((ctx["base"] / data).resolve().read_text(encoding="utf-8"))
    meta = data.get("papers", {})
    colmap = {"blue": "#2a78d6", "orange": "#eb6834", "c1": "#2a78d6", "c2": "#eb6834"}
    w = int(b.get("field_width", 620))
    h = int(b.get("field_height", 460))

    def side(cfg, dflt):
        pan = data["panels"][cfg["panel"]]
        color = colmap.get(cfg.get("color", dflt), colmap[dflt])
        klass = "c1" if color == "#2a78d6" else "c2"
        title = cfg.get("title") or pan.get("title")
        auto = (f'{pan["n"]}本・{pan["n_edges"]}辺・{pan["n_clusters"]}かたまり'
                f'（最大{pan["sizes"][0]}本、どこにも繋がらない単独が{pan["n_singleton"]}本）')
        cap = cfg.get("caption", auto)
        return (f'<div class="field {klass}"><div class="t">{rich(title)}</div>'
                f'<div class="c">{rich(cap)}</div>'
                + _graph_svg(pan["nodes"], pan["edges"], pan["clusters"], meta, color, w, h,
                             hulls=bool(b.get("hulls")))
                + "</div>")

    mid = b.get("center") or {}
    val = mid.get("value", data.get("ari"))
    gauge = ""
    # pin が無いときは value から位置を導くが、value は文字列でもよい（"0.418" 以外もありうる）。
    # 数に読めなければゲージを出さない。調整ランド指数は負にもなる（下限 -0.5）ので 0〜1 に丸める。
    raw = mid.get("pin", val)
    try:
        pin = min(1.0, max(0.0, float(raw)))
    except (TypeError, ValueError):
        pin = None
    if pin is not None:
        gauge = (f'<div class="gauge">'
                 f'<div class="pin" style="left:calc({pin * 100:.1f}% - 1.5px)"></div>'
                 f'<div class="end" style="left:0">{rich(mid.get("lo", "0"))}</div>'
                 f'<div class="end" style="right:0">{rich(mid.get("hi", "1.0"))}</div></div>')
    cap = f'<div class="c">{rich(mid["caption"])}</div>' if mid.get("caption") else ""
    center = (f'<div class="mid"><div class="v">{rich(val)}</div>'
              f'<div class="l">{rich(mid.get("label"))}</div>{gauge}{cap}</div>')

    mw = int(b.get("center_width", 190))
    return (f'{_label(b)}<div class="scatter" style="grid-template-columns:1fr {mw}px 1fr">'
            + side(b["left"], "blue") + center + side(b["right"], "orange") + "</div>")



def swimlane(b: dict, ctx: dict) -> str:
    """スイムレーン図。担当（レーン）を行に、作業の順序を列に置く。

    items[i].lane にレーン名を書くと、その行に配置される。lanes で順番を決める。
    矢印は隣り合う作業の間に自動で引かれ、レーンをまたぐときは直角に折れる。
    loops: [{from, to, label, side}] で戻りの点線。side は below（既定）か above。

    chain と同じく、x はパーセント・y はピクセルの混在なので
    preserveAspectRatio="none" で伸ばし、矢頭だけ CSS の三角で置く（_bypass_svg と同じ作法）。
    """
    items = b.get("items") or []
    lanes = b.get("lanes") or []
    if not items:
        return _label(b)
    if not lanes:
        seen = []
        for it in items:
            if it.get("lane") and it["lane"] not in seen:
                seen.append(it["lane"])
        lanes = seen
    n, L = len(items), max(1, len(lanes))
    row_h = int(b.get("row_h", 116))          # 1レーンの高さ
    lab_w = int(b.get("label_width", 128))    # 左のレーン名の幅
    pad_below = 64 if any((l.get("side") or "below") == "below" for l in (b.get("loops") or [])) else 8
    pad_above = 46 if any((l.get("side") or "") == "above" for l in (b.get("loops") or [])) else 0
    H = L * row_h

    idx_of = {name: i for i, name in enumerate(lanes)}
    col_w = 1000.0 / n
    cx = lambda i: (i + 0.5) * col_w                     # 列の中心（0..1000）
    hw = col_w * 0.40                                    # ノードの半幅
    cy = lambda k: k * row_h + row_h / 2                 # レーンの中心（px）

    # --- レーンの帯と名前
    bands = "".join(
        f'<div class="swim-band{" alt" if k % 2 else ""}" '
        f'style="top:{k*row_h}px;height:{row_h}px"></div>'
        f'<div class="swim-name" style="top:{k*row_h}px;height:{row_h}px;width:{lab_w}px">'
        f'{rich(name)}</div>'
        for k, name in enumerate(lanes)
    )

    # --- ノード
    cells = []
    for i, it in enumerate(items):
        k = idx_of.get(it.get("lane"), 0)
        cells.append(
            f'<div class="swim-node-wrap" style="left:{(cx(i) - hw)/10:.3f}%;'
            f'width:{hw*2/10:.3f}%;top:{k*row_h + 14}px;height:{row_h - 28}px">'
            + _node(it, "", numbered=bool(b.get("numbered")), idx=i + 1)
            + "</div>"
        )

    # --- 進む矢印
    paths, heads = [], []
    for i in range(n - 1):
        ka = idx_of.get(items[i].get("lane"), 0)
        kb = idx_of.get(items[i + 1].get("lane"), 0)
        x1, x2 = cx(i) + hw, cx(i + 1) - hw
        if ka == kb:
            paths.append(f"M {x1:.2f} {cy(ka):.2f} H {x2:.2f}")
        else:
            xm = (cx(i) + cx(i + 1)) / 2
            paths.append(f"M {x1:.2f} {cy(ka):.2f} H {xm:.2f} V {cy(kb):.2f} H {x2:.2f}")
        heads.append((x2, cy(kb), "right"))

    # --- 戻りの点線
    loops = []
    for lp in (b.get("loops") or []):
        f, t = int(lp["from"]) - 1, int(lp["to"]) - 1
        above = (lp.get("side") or "below") == "above"
        y = -pad_above / 2 if above else H + pad_below / 2
        kf, kt = idx_of.get(items[f].get("lane"), 0), idx_of.get(items[t].get("lane"), 0)
        d = (f"M {cx(f):.2f} {cy(kf) + (-40 if above else 40):.2f} V {y:.2f} "
             f"H {cx(t):.2f} V {cy(kt) + (-40 if above else 40):.2f}")
        loops.append(
            f'<path d="{d}" fill="none" stroke="var(--ink-3)" stroke-width="1.6" '
            f'stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/>'
        )
        heads.append((cx(t), cy(kt) + (-40 if above else 40), "up" if not above else "down"))
        if lp.get("label"):
            loops.append(
                f'<text x="{(cx(f)+cx(t))/2:.2f}" y="{y + (-8 if above else 14):.2f}" '
                f'class="swim-loop-lab" text-anchor="middle">{esc(lp["label"])}</text>'
            )

    head_html = "".join(
        f'<div class="swim-head {d}" style="left:calc({lab_w}px + '
        f'(100% - {lab_w}px) * {x/1000:.5f});top:{y + pad_above:.2f}px"></div>'
        for x, y, d in heads
    )
    svg = (f'<svg class="swim-svg" viewBox="0 -{pad_above} 1000 {H + pad_above + pad_below}" '
           f'preserveAspectRatio="none" style="left:{lab_w}px;width:calc(100% - {lab_w}px);'
           f'height:{H + pad_above + pad_below}px;top:-{pad_above}px">'
           + "".join(f'<path d="{d}" fill="none" stroke="var(--rule)" stroke-width="1.8" '
                     f'vector-effect="non-scaling-stroke"/>' for d in paths)
           + "".join(loops) + "</svg>")

    inner = (f'<div class="swim-grid" style="height:{H}px;padding-left:{lab_w}px">'
             f'{bands}<div class="swim-cells" style="left:{lab_w}px;'
             f'width:calc(100% - {lab_w}px);height:{H}px">{"".join(cells)}</div>'
             f"{svg}{head_html}</div>")
    return (f'{_label(b)}<div class="swim" style="padding-top:{pad_above}px;'
            f'padding-bottom:{pad_below}px">{inner}</div>')



def boxgraph(b: dict, ctx: dict) -> str:
    """層に並べた箱と、箱をつなぐ辺を描く。

    箱と辺のどちらにも badge を載せられる（後から件数を重ねるため）。
    座標はここで計算し、辺は SVG、箱は絶対配置の div で描く。

      layers: [{id: 背景, nodes: [{id, text, body, badge, tone}]}]
      edges:  [{from, to, label, badge, tone}]   tone: accent / dim / back
    """
    layers = b.get("layers") or []
    edges = b.get("edges") or []
    NW = int(b.get("node_w", 250))
    NH = int(b.get("node_h", 96))
    CG = int(b.get("col_gap", 118))
    RG = int(b.get("row_gap", 34))
    PAD = 26                      # 層の帯の内側の余白
    BOT = int(b.get("bottom_pad", 96))   # 戻りの辺を通す下の帯

    rows = max((len(l.get("nodes") or []) for l in layers), default=1)
    band_h = rows * NH + (rows - 1) * RG + PAD * 2
    W = len(layers) * NW + (len(layers) - 1) * CG + PAD * 2 * len(layers)
    H = band_h + BOT

    pos, bands, nodes_html = {}, [], []
    x = 0
    for li, lay in enumerate(layers):
        ns = lay.get("nodes") or []
        bw = NW + PAD * 2
        bands.append(f'<div class="bg-band" style="left:{x}px;top:0;width:{bw}px;height:{band_h}px">'
                     f'<div class="bl">{rich(lay.get("id"))}</div></div>')
        inner_h = len(ns) * NH + (len(ns) - 1) * RG
        y0 = PAD + (band_h - PAD * 2 - inner_h) / 2
        for ni, n in enumerate(ns):
            nx, ny = x + PAD, y0 + ni * (NH + RG)
            pos[n["id"]] = (nx, ny, NW, NH)
            badge = f'<div class="bg-badge">{rich(n["badge"])}</div>' if n.get("badge") else ""
            body = f'<div class="b">{rich(n["body"])}</div>' if n.get("body") else ""
            tone = n.get("tone") or ""
            nodes_html.append(
                f'<div class="bg-node {tone}" style="left:{nx}px;top:{ny:.0f}px;'
                f'width:{NW}px;height:{NH}px">{badge}'
                f'<div class="t">{rich(n.get("text", n["id"]))}</div>{body}</div>')
        x += bw + CG

    paths, labels = [], []
    back_i = 0
    for e in edges:
        a, z = pos.get(e["from"]), pos.get(e["to"])
        if not a or not z:
            raise SystemExit(f"boxgraph: 端点が見つからない辺 {e.get('from')} -> {e.get('to')}")
        ax, ay, aw, ah = a
        zx, zy, zw, zh = z
        cls = "bg-path " + (e.get("tone") or "")
        if zx > ax:                                   # 前へ進む
            x1, y1 = ax + aw, ay + ah / 2
            x2, y2 = zx, zy + zh / 2
            c = (x2 - x1) * 0.5
            d = f"M{x1},{y1:.0f} C{x1 + c:.0f},{y1:.0f} {x2 - c:.0f},{y2:.0f} {x2},{y2:.0f}"
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 9
        elif zx == ax:                                # 同じ層の中（縦）
            up = zy < ay
            x1 = ax + aw * 0.5
            y1 = ay if up else ay + ah
            y2 = (zy + zh) if up else zy
            d = f"M{x1},{y1:.0f} L{x1},{y2:.0f}"
            lx, ly = x1 + 8, (y1 + y2) / 2
        else:                                         # 戻る（下を回す）
            back_i += 1
            base = band_h + 30 + (back_i - 1) * 26
            x1, y1 = ax + aw * 0.5, ay + ah
            x2, y2 = zx + zw * 0.5, zy + zh
            d = (f"M{x1},{y1:.0f} C{x1},{base:.0f} {x2},{base:.0f} {x2},{y2:.0f}")
            lx, ly = (x1 + x2) / 2, base - 6
        paths.append(f'<path class="{cls}" d="{d}" marker-end="url(#bgArrow)"/>')
        txt = e.get("label") or ""
        if e.get("badge"):
            txt = (txt + "  " if txt else "") + str(e["badge"])
        if txt:
            wpx = len(str(txt)) * 7.4 + 12
            labels.append(
                f'<rect class="bg-elab-bg" x="{lx - wpx / 2:.0f}" y="{ly - 12:.0f}" '
                f'width="{wpx:.0f}" height="18" rx="4"/>'
                f'<text class="bg-elab" x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle">{esc(txt)}</text>')

    svg = (f'<svg class="bg-svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs><marker id="bgArrow" viewBox="0 0 10 10" refX="9" refY="5" '
           f'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="var(--rule)"/></marker></defs>'
           + "".join(paths) + "".join(labels) + "</svg>")
    return (f'{_label(b)}<div class="bg-wrap" style="width:{W}px;height:{H}px">'
            + "".join(bands) + svg + "".join(nodes_html) + "</div>")


RENDERERS = {
    "banner": banner, "chain": chain, "steps": steps, "columns": columns,
    "callout": callout, "metrics": metrics, "table": table, "note": note,
    "spacer": spacer, "swimlane": swimlane, "scatter_pair": scatter_pair, "graph_pair": graph_pair, "boxgraph": boxgraph,
}


def render_blocks(blocks: list[dict], ctx: dict) -> str:
    out = []
    for b in blocks or []:
        t = b.get("type")
        fn = RENDERERS.get(t)
        if not fn:
            raise SystemExit(f"知らないブロック: {t!r}（使えるのは {', '.join(sorted(RENDERERS))}）")
        out.append(f'<div class="block">{fn(b, ctx)}</div>')
    return "\n".join(out)
