#!/usr/bin/env python
"""setup.py — 新しいPCで figgen が動くところまで持っていく。

やること:
  1. 足りない部品を挙げる（PyYAML / Pillow / Chrome）
  2. 例を1枚描いてみて、**実際に PNG が出ることを確かめる**

「入っているか」を数えるだけの点検は当てにならない（入っていても Chrome が
無ければ図は出ない）。だから最後に必ず1枚描かせる。ここが通れば本当に使える。

    python knowledge/tools/figgen/setup.py            # 点検して1枚描く
    python knowledge/tools/figgen/setup.py --quiet    # 結果だけ

Chrome が既定の場所に無いときは環境変数 FIGGEN_CHROME に実行ファイルを指す。
"""

from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 点検の道具が表示で落ちるのは本末転倒。コンソールが出せない文字は諦めて出す
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

# (import名, pip名, 何に要るか, 無いと何ができないか)
PACKAGES = [
    ("yaml", "pyyaml", "YAMLの読み込み", "何も動かない"),
    ("PIL", "pillow", "余白の切り落としとあふれ検出", "PNGが出ない（--html だけなら動く）"),
]


def check_python() -> list[str]:
    v = sys.version_info
    if v < (3, 9):
        return [f"Python {v.major}.{v.minor} は古い。3.9 以上が要る（型注記の書き方が通らない）"]
    return []


def check_packages() -> tuple[list[str], list[str]]:
    missing, notes = [], []
    for mod, pip_name, why, without in PACKAGES:
        try:
            importlib.import_module(mod)
            notes.append(f"  OK   {pip_name:<8} {why}")
        except ImportError:
            missing.append(pip_name)
            notes.append(f"  無い {pip_name:<8} {why} → 無いと{without}")
    return missing, notes


def check_chrome() -> tuple[str | None, str]:
    """探索の実物（tools/html2png.py）をそのまま使う。ここで別に書くと片方だけ直って食い違う。"""
    sys.path.insert(0, str(HERE.parent))
    try:
        import html2png  # noqa: E402
    except ImportError as e:
        return None, f"  ×    tools/html2png.py を読めない — {e}"
    chrome = html2png.find_chrome()
    if not chrome:
        return None, "  無い Chrome / Edge が見つからない → 環境変数 FIGGEN_CHROME で実行ファイルを指す"
    return chrome, f"  OK   Chrome   {chrome}"


def render_example() -> tuple[bool, str]:
    """例を1枚描く。ここが通れば本当に使える。"""
    src = HERE / "examples" / "全ブロック.yaml"
    if not src.exists():
        return False, f"  ×    見本が無い — {src}"
    with tempfile.TemporaryDirectory() as td:
        work = Path(td) / src.name
        work.write_bytes(src.read_bytes())
        # 日本語Windowsでは、子は既定で cp932 を吐き、こちらは utf-8 で読もうとして
        # 文字化けする。**失敗時にこそ本文を見たい**のに、そこで化けたり例外になったり
        # して本文が消える。子に UTF-8 で書かせたうえで UTF-8 で読む
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, str(HERE / "figgen.py"), str(work)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        png = work.with_suffix(".png")
        if r.returncode != 0 or not png.exists():
            # 標準出力を握り潰すと「異常終了(1)」しか残らず原因が追えない
            tail = (r.stderr or r.stdout or "").strip().splitlines()
            return False, "  ×    描けなかった\n" + "\n".join("       " + x for x in tail[-6:])
        return True, f"  OK   見本を描けた（{png.stat().st_size // 1024} KB）"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="結果だけ出す")
    args = ap.parse_args()

    lines, problems = [], []

    problems += check_python()
    missing, notes = check_packages()
    lines += notes
    chrome, note = check_chrome()
    lines.append(note)

    if missing:
        problems.append("pip install " + " ".join(missing))
    if not chrome:
        problems.append("Chrome か Edge を入れる（または FIGGEN_CHROME で場所を指す）")

    # 部品が欠けたまま描かせても、原因の分からない失敗が増えるだけ
    if not problems:
        ok, note = render_example()
        lines.append(note)
        if not ok:
            problems.append("見本が描けない。上の出力を見る")

    if not args.quiet:
        print("figgen の点検")
        print("\n".join(lines))
        print()

    if problems:
        print("足りないもの:")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("figgen は使える。")
    print(f"  python {HERE.as_posix()}/figgen.py 図.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
