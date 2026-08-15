"""figgen — YAMLの仕様1枚から説明図を出す。

mermaid や PlantUML は配置をエンジンが決める。figgen は配置をこちらが決める。
レイアウトは HTML/CSS で持ち、文字は焼かずにテキストのまま置き、描画だけ Chrome に任せる。

    from figgen import render_spec
    render_spec(Path("図.yaml"))            # 図.png と 図.html を出す

コマンドとして使うときは `figgen 図.yaml`（または `python -m figgen 図.yaml`）。

**ここで `cli` を import しないこと（下の `__getattr__` は飾りではない）。**
`html2png` は「HTMLを撮る」だけの原始関数で、図のDSL（`blocks.py` 661行）とは無関係。
design_hub はスクリーンショットのためだけにこれを使う。ここで素直に
`from .cli import ...` と書くと、`from figgen import html2png` がパッケージの
`__init__` を経由する際に `cli` → `blocks` まで巻き込み、**分離した意味が消える**。
実際に一度そう書いて戻している（2026-08-15）。
"""

from typing import TYPE_CHECKING

__all__ = ["build_html", "render_spec", "main", "__version__"]
__version__ = "0.1.0"

_LAZY = {"build_html", "render_spec", "main"}


def __getattr__(name: str):
    """使われた時に初めて `cli` を読む（PEP 562）。"""
    if name in _LAZY:
        from . import cli

        return getattr(cli, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    return sorted(__all__)


if TYPE_CHECKING:  # 型検査と補完のためだけ。実行時には読み込まれない
    from .cli import build_html, main, render_spec
