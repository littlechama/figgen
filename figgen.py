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
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
import blocks as B  # noqa: E402

HERE = Path(__file__).parent
CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]

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


def find_chrome() -> str | None:
    env = os.environ.get("FIGGEN_CHROME")
    if env and Path(env).exists():
        return env
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("msedge")


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


def crop_to_content(png: Path, bg=(252, 252, 251), pad_px: int = 0) -> tuple[int, int, bool]:
    """下側の余白を切る。返り値は (幅, 高さ, あふれたか)。

    注意: 地色 #fcfcfb とパネルの白 #ffffff の差はわずか3しかない。許容差を広く取ると
    白パネルの中の文字が無い帯まで「余白」と判定してしまい、画面外へあふれた内容を
    黙って切り落とす。だから許容差は1に絞り、地色そのものの行だけを余白とみなす。
    あふれの判定も、切り取り後の高さではなく「下端の行が地色か」で見る。
    """
    from PIL import Image

    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    step = max(1, w // 400)

    def is_bg_row(y: int) -> bool:
        for x in range(0, w, step):
            r, g, b = px[x, y]
            if abs(r - bg[0]) > 1 or abs(g - bg[1]) > 1 or abs(b - bg[2]) > 1:
                return False
        return True

    last = 0
    for y in range(h - 1, -1, -1):
        if not is_bg_row(y):
            last = y
            break
    overflowed = not is_bg_row(h - 1)

    if last and last < h - 2:
        im.crop((0, 0, w, min(h, last + 1 + pad_px))).save(png)
        return w, min(h, last + 1 + pad_px), overflowed
    return w, h, overflowed


def render(html_path: Path, out: Path, width: int, scale: float, tall: int) -> None:
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("Chrome も Edge も見つからない。FIGGEN_CHROME で場所を指定する。")
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--no-sandbox", "--disable-lcd-text",
            f"--user-data-dir={tmp}",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{tall}",
            f"--screenshot={out}",
            "--virtual-time-budget=3000",
            html_path.as_uri(),
        ]
        # Chrome の出力は cp932 で読めないことがあるので、明示的に utf-8 で受ける
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    if not out.exists():
        raise SystemExit(f"描画に失敗した:\n{p.stderr[-1200:]}")


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
