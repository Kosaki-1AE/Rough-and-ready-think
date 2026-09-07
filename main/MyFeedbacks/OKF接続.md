# Obsidian VaultとOKFの接続

## 構成

KQIリポジトリのルートがVaultです。.git、.obsidian、README.md、MyFeedbacksなどが同じ階層にあります。既存ノートのサブフォルダ構成は維持します。

- スマホ：KQIフォルダそのものをObsidianのVaultとして開きます。
- PC：独立したOKFディレクトリの vault/KQI から、KQIルートへのシンボリックリンクで接続します。
- ノートの正本はKQIのみです。OKFへコピーして二重に編集しません。
- スマホにはOKFやシンボリックリンクは不要です。端末間の反映には通常のGit同期が必要です。

## PCで接続する

OKFはKQIの外、例えば隣のディレクトリに置きます。OKFディレクトリは src/reference_agent がある階層です。

```sh
python3 /path/to/KQI/tools/connect_okf.py --okf /path/to/okf
python3 /path/to/KQI/tools/connect_okf.py --okf /path/to/okf --check
```

Windowsでは python3 の代わりに python を使用できます。シンボリックリンク作成には、Windowsの設定・実行権限が必要な場合があります。

接続後、OKF側の vault/KQI/MyFeedbacks はKQI本体の MyFeedbacks を指します。リンク経由の書き込みも本体に反映されます。KQIを移動した場合は接続先の見直しが必要です。

既存の vault/KQI がある場合、スクリプトは上書きせず停止します。未同期ノートを照合・退避してから、その旧ディレクトリを別名へ移して再実行してください。

リンクは端末固有のためOKF側のGitにはコミットしません。OKFのローカル除外設定（.git/info/exclude）に /vault/KQI を追加できます。ただし既に追跡中の旧Vaultには除外が効かないため、旧構成の整理が別途必要です。

## OKF本体を取り出し直す場合

削除前のコードはこのリポジトリの backup-before-vault-root-20260907 ブランチに残っています。KQIルートで次を実行すると、当時のOKFコードだけを隣のディレクトリへ取り出せます。旧Vaultは含めません。

```sh
git fetch origin backup-before-vault-root-20260907
git archive origin/backup-before-vault-root-20260907 -- okf ':(exclude)okf/vault' | tar -x -C ..
```

実行前に、親ディレクトリに既存の okf がないことを確認してください。コードのインストール方法は取り出したOKFのREADME.mdを参照します。

## 接続と形式変換の違い

これは同じMarkdownをOKF側から参照するためのファイル接続です。既存ノートを一括変換する処理ではありません。

退避されているOKF v0.2仕様では、概念文書にYAML frontmatterの type が必要です。通常のObsidianノートがすべてその仕様を満たすとは限りません。可視化・取り込みで厳密なOKF形式を要求する場合は、別途変換やメタデータ補完が必要です。生成物の出力先には原本Vaultと別のディレクトリを指定してください。
