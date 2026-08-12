"""figgen — YAMLの仕様から、説明図を1枚のPNG/SVG付きHTMLとして出す道具。

なぜこれを作ったか（2026-07-26）:
  画像生成モデルは日本語の文字を崩す。逆に mermaid や PlantUML は正確だがレイアウトを
  自分で決められない（グラフ配置エンジンが勝手に置く）。スライドに貼る説明図は
  「どこに何を置くか」をこちらが決めたいので、レイアウトはHTML/CSSで持ち、
  文字はテキストのまま焼かずに置き、描画だけを Chrome に任せる。

使い方:
    python figgen.py spec.yaml                 # spec.yaml と同じ場所に .png と .html を出す
    python figgen.py spec.yaml -o out.png
    python figgen.py spec.yaml --html          # HTMLだけ作って描画しない（速い。確認用）
    python figgen.py spec.yaml --scale 3       # 3倍解像度
    python figgen.py spec/*.yaml               # まとめて

必要なもの: Python（PyYAML, Pillow）と Chrome か Edge。npm も pip install も要らない。
Chromeの場所を変えたいときは環境変数 FIGGEN_CHROME。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import blocks as B  # noqa: E402

# 「HTMLを撮る」は図とは別の関心事なので隣（tools/html2png.py）に出してある。
# design_hub もそれを直接使う（以前はここを丸ごと import していた）。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from html2png import crop_to_content, find_chrome, render  # noqa: E402,F401

HERE = Path(__file__).parent

PAGE = """<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><title>{title}</title>
<style>
:root {{ --w: {width}px; }}
{css}
{extra_css}
</style></head>
<body class="{body_class}"><div id="fig">
{head}
{body}
{foot}
</div></body></html>
"""


def build_html(spec: dict, base: Path) -> str:
    css = (HERE / "theme.css").read_text(encoding="utf-8")
    ctx = {"base": base, "spec": spec}

    head = ""
    if spec.get("title") or spec.get("subtitle"):
        sub = f'<div class="sub">{B.rich(spec["subtitle"])}</div>' if spec.get("subtitle") else ""
        head = (f'<div class="fig-head"><h1>{B.rich(spec.get("title"))}</h1>{sub}'
                f'<div class="rule"></div></div>')

    foot = ""
    if spec.get("footer") or spec.get("source"):
        left = B.rich(spec.get("footer", ""))
        right = B.rich(spec.get("source", ""))
        foot = f'<div class="fig-foot"><div>{left}</div><div>{right}</div></div>'

    body_class = f'accent-{spec.get("accent", "blue")}'
    return PAGE.format(
        title=B.esc(spec.get("title", "figure")),
        width=int(spec.get("width", 1600)),
        css=css,
        extra_css=spec.get("css", ""),
        body_class=body_class,
        head=head,
        body=B.render_blocks(spec.get("blocks"), ctx),
        foot=foot,
    )


def one(spec_path: Path, args) -> None:
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise SystemExit(f"{spec_path.name}: 中身が辞書になっていない")
    width = int(spec.get("width", 1600))
    scale = float(args.scale or spec.get("scale", 2))

    out_png = (Path(args.out) if args.out else spec_path.with_suffix(".png")).resolve()
    out_html = out_png.with_suffix(".html")
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(build_html(spec, spec_path.parent), encoding="utf-8")
    print(f"  html  {out_html}")
    if args.html:
        return

    tall = int(spec.get("height", 0)) or 4200
    render(out_html, out_png, width, scale, tall)
    if not spec.get("height"):
        w, h, overflowed = crop_to_content(out_png, pad_px=int(40 * scale))
        if overflowed:
            print(f"  ⚠ 内容が縦にあふれている（描画枠 {tall}px を超えた）。"
                  f"中身を減らすか、spec に height を書く")
        print(f"  png   {out_png}  ({w}x{h})")
    else:
        print(f"  png   {out_png}")


def main() -> None:
    ap = argparse.ArgumentParser(description="YAMLの仕様から説明図を出す")
    ap.add_argument("specs", nargs="+", help="spec の .yaml")
    ap.add_argument("-o", "--out", help="出力先の .png（specが1つのときだけ）")
    ap.add_argument("--scale", type=float, help="解像度の倍率。既定は spec の scale か 2")
    ap.add_argument("--html", action="store_true", help="HTMLだけ作って描画しない")
    args = ap.parse_args()

    paths = []
    for s in args.specs:
        p = Path(s)
        paths.extend(sorted(p.parent.glob(p.name)) if "*" in p.name else [p])
    if args.out and len(paths) > 1:
        raise SystemExit("-o は spec が1つのときだけ")
    for p in paths:
        if not p.exists():
            raise SystemExit(f"見つからない: {p}")
        print(p.name)
        one(p, args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
