# figgen を新しいPCで使えるようにする

```bash
pip install pyyaml pillow
python knowledge/tools/figgen/doctor.py
```

`doctor.py` は足りないものを挙げたうえで、**見本を1枚実際に描いて確かめる**。
「入っているか」を数えるだけでは足りない（入っていても Chrome が無ければ図は出ない）。
最後に `figgen は使える。` と出れば本当に使える。

使い方そのものは [README.md](README.md)、書くときの禁じ手は [CLAUDE.md](CLAUDE.md)。

## 要るもの

| | 無いとどうなるか |
|---|---|
| Python 3.9 以上 | 動かない |
| PyYAML | 動かない |
| Pillow | PNG が出ない（`--html` だけなら動く） |
| Chrome か Edge | PNG が出ない。既定の場所に無ければ環境変数 `FIGGEN_CHROME` で実行ファイルを指す |

`pip` 以外は要らない。npm もビルドも無い。

## なぜ knowledge の中にあるのか

**2026-08-11 に `Life/tools/figgen` からここへ移した。**

元の場所はバージョン管理外だったので、別のPCで knowledge を clone しても
figgen だけが無い状態になった（実際になった）。knowledge 側は AGENTS.md・
`skills/` の3本・`assets/figgen-theme.md` から figgen を参照していて、
**依存だけがあって実体が無い**という形だった。

ここに置けば clone した時点で揃う。`assets/figgen-theme.md` の `source_path` も
ここを指している（コピーではなく実体への参照）。

## 描画は別ファイル・ただし中にある

「HTML を Chrome で撮って PNG にする」は図とは別の関心事なので、
[`src/figgen/html2png.py`](src/figgen/html2png.py) に分けてある。figgen はそれを使う側。

`tools/design_hub` も同じものを使う。以前は figgen を丸ごと import していたが、
実際に呼ぶのは67行で、引きずり込む867行のうち661行（`blocks.py` の図のDSL）は
1つも使っていなかった。今も design_hub が読むのは `html2png` だけで、`blocks.py` は
読み込まない。**関心事の分離はファイルを分けることで保たれていて、
置き場所を離すことが条件ではなかった。**

> ### 2026-08-14 変更: `../html2png.py` → `figgen/html2png.py`
>
> 元は1つ上（`tools/html2png.py`）に置いていたが、**figgen 側が親ディレクトリを
> import する形になっていた**（`sys.path.insert(..., parent)`）。この1行があると
> figgen をディレクトリごとコピーしても動かず、**単体のリポジトリとして公開できない**。
> OSSとして出す前提に変えたので、実体を figgen の中へ移した。
>
> **写しは作っていない**（`html2png.py` 自身が「写して使わないこと」と書いている）。
> 実体は1つのまま、`design_hub/paths.py` が新しい場所を sys.path に通している。
> 移動後、figgen 単体・design_hub の両方が動くことを確認済み。
