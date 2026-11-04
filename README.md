# Colorful-dictionary

[ColorfulTalk](https://github.com/ukagaka-irono/ColorfulTalk) シリーズの言語処理エンジン **ColorfulYomi** が使う、
読み・アクセント付きの日本語辞書と、その作成ツールです。

> **状態: 設計中。** 仕様は [docs/spec.md](docs/spec.md) で検討しています。

## 内容（予定）

| ファイル | 内容 |
|---|---|
| `colorful_talk.dic` | 辞書（約 48 万語、約 26MB）。リポジトリには入れず、リリースに添付する |
| `NOTICE` | 元データの著作権表示とライセンス |
| `tools/build_dic.py` | 元データから辞書を作るツール |

## ライセンス

- 作成ツールなど、このリポジトリのソースコード: MIT License（[LICENSE](LICENSE)）
- 辞書ファイル: 元データ（Open JTalk 同梱の mecab-naist-jdic）のライセンス BSD 3-Clause に従います。
  辞書を配布するときは `NOTICE` を同梱してください
