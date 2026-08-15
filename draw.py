#!/usr/bin/env python
"""figgen の入口（pip で入れずに、この場で動かすとき用）。実体は `src/figgen/`。

    python draw.py 図.yaml

pip で入れたなら `figgen 図.yaml` が使える。この入口は clone しただけで動かせる
ようにするためのもので、中身は持たずパッケージを呼ぶだけ。

**`figgen.py` という名前にしてはいけない（2026-08-15 に改名した）。**
リポジトリ直下に `figgen.py` があると、cwd が sys.path の先頭に入る都合で
インストール済みの `figgen` パッケージを覆い隠し、`import figgen` が
「'figgen' is not a package」で落ちる。実際に venv へ入れて踏んだ。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from figgen.cli import main  # noqa: E402

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
