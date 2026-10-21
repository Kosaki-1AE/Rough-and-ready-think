# YouTube研究収集ツール：OAuth＋URL＋踊ってみた検索

## 1. インストール
Python 3.9以上を推奨。

```bash
python3 -m pip install -r requirements.txt
```

## 2. 自分のYouTubeアカウントでログインする準備
1. Google Cloud Consoleでプロジェクトを作成し **YouTube Data API v3** を有効化。
2. Google Auth Platform のOAuth同意画面を設定。テスト公開状態なら自分のGoogleアカウントをテストユーザーに追加。
3. OAuthクライアントIDを **デスクトップアプリ** として作成し、JSONをダウンロード。
4. JSONをこのフォルダに `client_secret.json` として置く。
5. 以下のコマンドでブラウザログイン。読み取り専用権限のみ要求します。

```bash
python3 run.py collect --mode all --oauth --search-limit 100
```

初回ログイン後、認証情報は `.youtube_oauth_token.json` に保存されます。**この2つのJSONを他人に送ったりGitHubに公開しないでください。**

OAuthは自分のプレイリスト一覧をAPIで自動取得します。公開・非公開プレイリストの取得は、アカウント権限とAPI応答に依存します。自分の「高く評価した動画」や「後で見る」は通常のプレイリストとして取得できるとは限りません。

## 3. 手動URL指定（OAuthなしでも動作）
`playlists.txt` にプレイリストURLを1行ずつ追加。OAuthと同時に使ってもOK。URL収集は `yt-dlp` を利用。

```bash
python3 run.py collect --mode playlist
```

## 4. 「踊ってみた」をYouTube全体から検索
`queries.txt` に検索キーワードを1行ずつ記入。`--search-limit` は**キーワードごと**の上限。

```bash
python3 run.py collect --mode search --search-limit 100
```

## 5. 全機能まとめて実行

```bash
python3 run.py collect --mode all --oauth --search-limit 100
```

結果は `youtube_metadata.csv`。同じ動画IDは統合され、収集元 `oauth_my_playlist` / `my_playlist` / `odottemita_search` と元のプレイリスト名・検索語を記録します。既存CSVの権利確認状況を維持します。OAuthで取得したプレイリスト内にも他人の動画が含まれ得ます。

## 6. 権利確認済み動画のみ保存
CSVの `download_permission` 列を権利確認済みの動画だけ `yes` に変更してから実行。

```bash
python3 run.py download
```

YouTube検索の全件取得は保証されません。Google APIにはクォータがあり、取得可能な動画やプレイリストは権限・公開状態によって変わります。動画本体の取得・研究利用はYouTubeの規約と著作権等を確認してください。OAuthはメタデータ取得専用で、非公開動画のダウンロード認証には使いません。
