"""figgen-mcp — エージェントに図を描かせるための MCP サーバー。

figgen の弱点は「独自YAML方言を13ブロックぶん覚えないと書けない」ことだった。
MCP 越しに使うなら、覚えるのは人ではなくエージェントなので、その弱点が消える。
人は「こういう図が欲しい」と言うだけでよくなる。

    figgen-mcp                      # stdio で待つ

**`figgen_blocks` を独立した道具にしてあるのは飾りではない。** 方言を渡す経路が
無いと、エージェントは YAML を幻覚して失敗し、「使えない」で終わる。サーバーの
instructions と `figgen_render` の説明の両方から、先に呼ぶよう指している。
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from mcp.server import MCPServer

from . import __version__

HERE = Path(__file__).resolve().parent

INSTRUCTIONS = """\
figgen は YAML の仕様1枚から説明図（PNG）を出す。mermaid と違い、**配置をこちらが決める**。
スイムレーン・層構造・強調矢印・迂回矢印など、「人に見せる図」で効く。

手順:
  1. **まず `figgen_blocks` を呼んで方言を読む。** 記憶で YAML を書かない
  2. どのブロックを使うか決めて YAML を書く
  3. `figgen_render` で PNG にする
  4. **出た PNG を必ず画像として開いて見る。** CSS は検証されないので、
     はみ出し・重なり・文字切れは見ないと分からない（横のあふれは警告も出ない）

図に書く数字は、確かめたものだけにする。
"""


def _blocks_reference() -> str:
    """YAML 方言の正本。README ではなくここが単一の出所。"""
    return (HERE / "BLOCKS.md").read_text(encoding="utf-8")


server = MCPServer(
    name="figgen",
    title="figgen — 説明図を描く",
    version=__version__,
    instructions=INSTRUCTIONS,
)


@server.tool(
    name="figgen_blocks",
    title="figgen の YAML 方言を読む",
    description=(
        "figgen の仕様の書き方（全13ブロックのキー・記法・落とし穴）を返す。"
        "**図を書く前に必ず1回呼ぶこと。** 記憶で書くと、存在しないキーを"
        "使って黙って無視されるか、エラーで止まる。"
    ),
)
def figgen_blocks() -> str:
    return _blocks_reference()


@server.tool(
    name="figgen_render",
    title="YAMLの仕様を図(PNG)にする",
    description=(
        "figgen の YAML 仕様から PNG を出す。仕様は `.yaml` として隣に保存され、"
        "図の正本になる（直すときは YAML を直して呼び直す）。"
        "方言を知らないなら先に figgen_blocks を呼ぶこと。"
        "返り値には出力先と画像の実寸が入る。**縦にあふれた場合は警告が出るが、"
        "横のあふれは検出できない**ので、返ってきた PNG は必ず開いて目で見ること。"
    ),
)
def figgen_render(spec: str, out_path: str, scale: float | None = None) -> str:
    """spec: YAML本文 / out_path: 出力する .png のパス / scale: 解像度の倍率（既定2）"""
    from .cli import render_spec  # 遅延: サーバー起動を図のDSLの読み込みで遅らせない

    out_png = Path(out_path).expanduser().resolve()
    if out_png.suffix.lower() != ".png":
        out_png = out_png.with_suffix(".png")
    out_png.parent.mkdir(parents=True, exist_ok=True)

    # 仕様を残す。figgen は「YAMLが正本、PNGは生成物」という道具なので、
    # 本文だけ受け取って捨てると、次に直すときに書き直しになる
    spec_file = out_png.with_suffix(".yaml")
    spec_file.write_text(spec, encoding="utf-8")

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            render_spec(spec_file, out=out_png, scale=scale)
    # 失敗は例外のまま上げる。SDK が isError: true にしてくれるので、
    # 文字列で返すと「成功した」と読まれかねない。SystemExit は BaseException
    # なので `except Exception` では捕まらない（figgen は Chrome 不在などで
    # SystemExit を投げる）。両方を明示的に拾う
    except SystemExit as e:
        raise RuntimeError(
            f"描けなかった: {e}\n仕様は {spec_file} に残してある。") from e
    except Exception as e:
        raise RuntimeError(
            f"描けなかった: {type(e).__name__}: {e}\n"
            f"仕様は {spec_file} に残してある。") from e

    report = buf.getvalue().strip()
    return (
        f"{report}\n\n"
        f"仕様: {spec_file}\n"
        "**この PNG を画像として開いて確かめること。** はみ出し・重なり・文字切れは"
        "実際に見ないと分からない（横のあふれは警告が出ない）。"
    )


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
