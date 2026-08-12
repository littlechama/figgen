# figgen — YAMLから説明図を出す

スライドや報告に貼る説明図を、YAMLの仕様1枚から作る。文字は画像として焼かず、
レイアウトはHTML/CSSで持ち、描画だけを Chrome に任せる。

```
python figgen.py 図.yaml          # 同じ場所に 図.png と 図.html を出す
python figgen.py 図.yaml --html   # HTMLだけ（速い。中身の確認用）
python figgen.py fig*.yaml        # まとめて
```

必要なもの: Python（PyYAML・Pillow）と Chrome か Edge。npm も pip install も要らない。
Chromeの場所を変えたいときは環境変数 `FIGGEN_CHROME`。

## なぜ作ったか

画像生成モデルは日本語の文字を崩す。一方 mermaid・PlantUML・Graphviz 系は文字は正確だが、
**どこに何を置くかを自分で決められない**（配置エンジンが勝手に置く）。既存のYAML→図のOSSを
一通り見たが（drawthe.net / diagrams-as-code / yml2dot / infrastructure-diagrams 等）、
どれもインフラ構成図の生成が目的で、Graphviz にレイアウトを任せる作りだった。

説明図でこちらが決めたいのは、まさにその配置のほう。だから配置はCSSグリッドで持ち、
図の中身はYAMLで持ち、描画をChromeに任せる薄い道具にした。

- 文字が崩れない。テキストのまま置くので、解像度も自由（`scale`）
- 直せる。1行直して再実行すれば1秒で出る。画像生成のように全部描き直しにならない
- 数字が嘘にならない。散布図などはデータのJSONから描くので、手で置いた点にならない
- 見た目が揃う。色・余白・字は `theme.css` の1枚に集約してある

## 仕様（YAML）の書き方

```yaml
title: 図の見出し
subtitle: 小見出し
footer: 左下に出る文字
source: 右下に出る文字（出典）
width: 1600        # 内部の設計幅。既定 1600
scale: 2           # PNGの倍率。既定 2（=3200px幅）
height: 900        # 書くと固定キャンバス。省くと内容の高さに合わせて切る
accent: blue       # blue | orange
blocks:
  - type: ...
```

本文で使える記法は3つだけ。`**太字**` ／ `` `コード` `` ／ `[[アクセント色]]`。改行はそのまま改行になる。
Markdownを全部通すと図の中で崩れるので、意図的にこれだけにしてある。

## ブロック一覧

| type | 何を出すか | 主なキー |
|---|---|---|
| `banner` | 全幅の帯。転回点や結論を1行で | `text` `note` `tone: plain` |
| `steps` | 番号付きの横フロー | `items[].text` `.body` `.note` |
| `chain` | 横並びの連鎖。矢印つき | `items[]` `emphasis: [3]` `bypass` `tight` |
| `columns` | N列のパネル | `columns[].title` `.badge` `.items` `.ft` `between` |
| `callout` | 強調の1枚 | `text` `body` `label_in` `tone: warn/plain` |
| `metrics` | 大きな数字の並び | `items[].value` `.label` `.caption` |
| `table` | 表 | `headers` `rows` `align` |
| `note` | 小さい注記 | `text` |
| `swimlane` | 担当（レーン）を行、作業の順序を列に置く | `lanes[]` `items[].lane` `loops[]` `row_h` `label_width` `numbered` |
| `boxgraph` | 層に並べた箱と、箱をつなぐ辺 | `layers[].nodes[]` `edges[]` `node_w` `col_gap` `bottom_pad` |
| `graph_pair` | 2つのグラフ（ノード＋辺）を並べる | `data` `left.panel` `right.panel` `center` `field_width` `field_height` |
| `scatter_pair` | 同じ点集合を2通りに囲う | `data` `left` `right` `center` |
| `spacer` | 余白 | `h` |

共通で `label`（ブロックの上に出る小見出し）が使える。

### chain の矢印

- `items[i].arrow_label` … その矢印の上に出るラベル
- `emphasis: [3]` … 3番目の右の矢印を太くアクセント色にする（1始まり）
- `bypass: {from: 2, to: 5, label: "..."}` … 下を迂回する点線の矢印
- `items[i].tone` … `accent`（強調）／ `dim`（破線・スコープ外）／ `soft`

### swimlane

担当を行に、作業の順序を列に置く。`items[i].lane` でどの行かを決め、`lanes` で行の順を決める。
矢印は隣り合う作業の間に自動で引かれ、**レーンをまたぐときは直角に折れる**。

```yaml
- type: swimlane
  lanes: [学生, システム]
  numbered: true
  row_h: 152            # 1レーンの高さ
  label_width: 116      # 左のレーン名の幅
  items:
    - {lane: 学生, text: 資料を出す, body: "[[段1]] 手元の資料をテキストで置く"}
  loops:
    - {from: 6, to: 5, label: 別の材料を見る, side: below}   # 1始まり。side は below（既定）か above
```

- **⚠ `note` は出ない。** `_node()` が描画するのは `n` / `text` / `body` / `arrow_label` だけ。`.node-note` の
  CSS はあるが `chain` と `swimlane` の項目では使われない。**書いても黙って消える。**
  ラベルを添えたいときは `body` の頭に `[[...]]`（アクセント色）を入れる
- **⚠ 1項目＝1列。列幅 = 1000/n。** 項目を増やすと横に潰れる。`width: 1900` で10項目のとき
  1列 ≈178px、ノード実幅 ≈143px で、**本文は20字以内でないと箱からはみ出す**。10項目が上限の目安

### boxgraph

構造そのものを描くとき（設計図の箱と、その継ぎ目）。`graph_pair` と違い、ノードに名前と説明文が付き、
辺にラベルが付く。**箱と辺の両方に `badge` を載せられる**ので、あとから件数や判定を重ねられる。

```yaml
- type: boxgraph
  layers:
    - id: 背景
      nodes:
        - {id: 意義, text: 意義, body: なぜ重要とされているか, badge: "14件"}
  edges:
    - {from: 意義, to: 欠落, label: 重要なのに解けていないか, badge: "0件", tone: accent}
```

- 層は左から右へ並び、層の中のノードは縦に積む。座標は自動
- 辺は3通りに自動で描き分ける。**前へ進む**（曲線）／**同じ層の中**（縦の直線）／**戻る**（下を回る点線状の弧）
- `tone` は `accent`（強調）／ `dim`（破線・外す候補）
- 端点に無いIDを書くとエラーで止まる（黙って消えない）

### graph_pair のデータ

グラフをそのまま描く。ノードは番号つきの丸、辺は線で、濃さは重み。どこにも繋がらないノードは
灰色の輪郭になる。左右で座標系が違ってよい（枠ごとに別のレイアウトで置いた場合）。番号が
枠をまたいで共通なら、同じ論文を左右で追える。

```json
{ "papers": {"p3": {"num": 4, "title": "..."}},
  "panels": {
    "significance": {
      "title": "①意義",
      "nodes":    [{"id": "p3", "x": 0.42, "y": 0.10}],   // x,y は 0〜1 に正規化済み
      "edges":    [["p3", "p7", 0.31]],                    // [端, 端, 重み]
      "clusters": [["p3","p7"], ["p1"]],
      "n": 37, "n_edges": 33, "n_clusters": 13, "n_singleton": 7, "sizes": [20, 2, ...]
    }}}
```

`caption` を省くと `37本・33辺・13かたまり（最大20本、…単独が7本）` を自動で出す。数え直しの
手間と食い違いを避けるため、**数えられるものは仕様に書かずデータから出す**。

**凸包の囲い（`hulls: true`）は既定で切ってある。** 凸包はそのかたまりに属さないノードまで
囲ってしまい、「この袋の中は同じかたまり」という誤読を生むため。かたまりは辺で読ませる。

### scatter_pair のデータ

グラフの構造が要らず、点と囲いだけでよいとき。

```json
{ "points":    [{"id": "p0", "x": 0.1, "y": -0.4}, ...],
  "groupings": {"significance": {"clusters": [["p0","p3"], ["p1"], ...]}} }
```

点の位置は左右で共通で、`clusters` だけが違う前提。上の誤読の問題があるので、使う前に
「囲いに入っていない点が袋の中に来ないか」を必ず出力で確かめること。

作る側の例: `research/survey_thema/analysis/theme_box_analysis/scripts/export_grouping.py`。
分析スクリプトの関数をそのまま呼んでJSONにしているので、分析を直せば図も変わる。

## 色

`theme.css` の先頭にまとまっている。カテゴリ色は blue → orange の順で固定で、順番を入れ替えない。
値は dataviz の検証済みパレットで、`validate_palette.js` の6項目（明度帯・彩度下限・色覚特性下での分離・
通常視での分離・地色とのコントラスト）を全部通したもの。色を足すときは同じ検証を通すこと。

## 制約・分かっている穴

- **横にあふれても警告しない。** 縦のあふれだけは検知して警告する（`height` を省いたとき）
- **1枚に詰めすぎると読めなくなる。** ブロック7つを超えたら2枚に割ることを考える
- 矢印は隣どうしと `bypass` だけ。任意のノード間を結ぶ線は引けない。要るようになったら足す
- フォントは環境依存（游ゴシック→Noto→Meiryo の順）。他のPCで出すと字幅が変わる
- ダークモードは持っていない。スライドに貼る前提で明るい地色だけ

## 置き場所の約束

道具はここ（`tools/figgen/`）に置き、**図の仕様は使う側のプロジェクトに置く**。
仕様はプロジェクトの資料であって、道具の一部ではないため。

例: `research/survey_thema/verbalization/0727/figures/*.yaml`
