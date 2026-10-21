# YouTube Hybrid Research Collector

自分で管理するYouTubeプレイリストと、YouTube全体の「踊ってみた」検索結果を一つのCSVに統合します。Python 3.9以降推奨。

## セットアップ

```bash
python3 -m pip install -U yt-dlp
```

## 1. 設定

- `playlists.txt` に**自分の**プレイリストURLを1行1つ記入（先頭 `#` はコメント）。
- `queries.txt` に「踊ってみた」関連の検索語を1行1つ記入。

## 2. 収集

```bash
python3 youtube_hybrid.py collect --mode all --search-limit 100
```

検索のみ: `--mode search` / プレイリストのみ: `--mode playlist`

`--search-limit` は**検索語あたり**の上限です。実際の取得件数は検索結果や環境に左右されます。検索結果は網羅的ではありません。

## 3. CSV

`youtube_metadata.csv` に動画ID、タイトル、URL、チャンネル、再生時間、収集経路などを保存。`source_type` は `my_playlist` と `odottemita_search`、両方で見つかった場合は `|` 区切り。重複は動画IDで統合。CSVを編集しても、再収集時に `download_permission` と `review_status` は保持します。

検索結果には無関係の動画も含まれる可能性があるため、人手で対象を選別してください。自分のプレイリストにあることは、動画の著作権を持つことを意味しません。

## 4. 動画の保存（任意）

動画本体を保存する場合は、権利者の許諾等を確認し、利用規約に従ってください。CSVの `download_permission` を確認済みの対象に限って `yes` としてください。

```bash
python3 youtube_hybrid.py download --input youtube_metadata.csv --directory videos
```

保存は最大480pを指定。既に保存したIDは `videos/archive.txt` に記録し再取得を避けます。利用許可のない動画はダウンロード対象にしないでください。

## 留意点

- YouTubeの検索・取得には変更や制限があり、一定件数の収集は保証されません。
- `--flat-playlist` により軽量に一覧を取得するため、再生時間・チャンネル・投稿日などは空欄になることがあります。
- YouTube Data APIを用いる方式へ移行する場合はAPIキー・クォータ管理が別途必要です。
- 自分の投稿動画だけに限定する自動判定は行っていません。プレイリストを自分で管理する前提です。
