# Colorful-dictionary

[ColorfulTalk](https://github.com/ukagaka-irono/ColorfulTalk) シリーズの言語処理エンジン
[ColorfulYomi](https://github.com/ukagaka-irono/ColorfulYomi) が使う、読み・アクセント付きの日本語辞書と、その作成ツールです。

- 約 48 万語（481,977 語）。発音・アクセント型・アクセント結合規則・連接コスト・未知語の扱いを 1 つのファイル（26MB）にまとめたもの
- 元データは Open JTalk に同梱の mecab-naist-jdic（BSD 3-Clause）。作成ツールは元データを固定した版から取得し、毎回同じ辞書を作る
- 辞書ファイルはリポジトリには入れず、リリースに添付する

## 辞書を作る

Python 3（標準ライブラリのみ）があれば作れます。

```bash
python tools/build_dic.py --fetch -o colorful_talk.dic
```

元データ（約 66MB）を `naist-jdic/` に取得し、SHA-256 を確かめてから辞書を書き出します。

## 中身

| 場所 | 内容 |
|---|---|
| [tools/build_dic.py](tools/build_dic.py) | 辞書の作成ツール |
| [docs/spec.md](docs/spec.md) | 仕様書（元データ、ライセンス、ファイル形式） |
| [NOTICE](NOTICE) | 元データの著作権表示とライセンス |

## ライセンス

- 作成ツールなど、このリポジトリのソースコード: MIT License（[LICENSE](LICENSE)）
- 辞書ファイル `colorful_talk.dic`: 元データのライセンス BSD 3-Clause に従います。辞書を配布するときは [NOTICE](NOTICE) を同梱してください
