"""html2png — HTML を headless Chrome で PNG にする。それだけ。

**図とは無関係の原始関数。** もともと figgen.py の中にあったが、figgen は
「YAMLから説明図を作る道具」であって、ここは「HTMLを撮る」でしかない。
別の関心事が同居していたせいで、design_hub は**スクリーンショットを撮るためだけに
867行（うち図のDSLが661行）を import していた**。実際に使っていたのは67行。

だから借り手の側ではなく、こちらを独立させる。

    import html2png
    html2png.render(html_path, out, width=1280, scale=1.0, tall=900)
    html2png.crop_to_content(out, bg=(252, 252, 251), pad_px=20)

Chrome の場所は環境変数 FIGGEN_CHROME で上書きできる（名前は figgen 時代からの
継続。両方の借り手が同じ変数を見るので、増やすと設定箇所が2つになる）。

**写して使わないこと。** Chrome の起動フラグは時々変わる（`--headless=new` など）。
registry の解決規則を design_hub に写経しなかったのと同じ理由で、実物を1つにしておく。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str | None:
    env = os.environ.get("FIGGEN_CHROME")
    if env and Path(env).exists():
        return env
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("msedge")


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
