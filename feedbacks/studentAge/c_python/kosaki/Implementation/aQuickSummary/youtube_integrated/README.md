# 統合版（自分のプレイリスト＋踊ってみた検索）

## 準備
Python 3.9以降推奨。`python3 -m pip install -U yt-dlp` を実行。

## 設定
- プレイリストを利用する場合: `playlists.txt` に自分のプレイリストURLを1行ずつ記載。
- 検索を利用する場合: `queries.txt` に「踊ってみた」などの検索語を1行ずつ記載。

## 実行
`python3 run.py` でこの版の標準収集を実行。`python3 run.py collect --search-limit 100 --output youtube_metadata.csv` で検索上限等を指定。
`python3 youtube_hybrid.py collect --mode all` でも実行可能。

## 保存
CSVの `download_permission` に、利用権限を確認できた動画のみ `yes` を入力。
`python3 run.py download` で許可確認済み動画だけ保存。

検索結果の全件取得は保証されません。自分のプレイリスト内にも第三者の動画があり得るため、保存・研究利用の権利は別途確認してください。
