# figgen を新しいPCで使えるようにする

```bash
pip install pyyaml pillow
python knowledge/tools/figgen/setup.py
```

`setup.py` は足りないものを挙げたうえで、**見本を1枚実際に描いて確かめる**。
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

`tools/design_hub` もサムネイル生成で figgen を import している。
場所は `paths.figgen_dir()` の1か所だけが知っているので、
移動するときはそこを直す。
