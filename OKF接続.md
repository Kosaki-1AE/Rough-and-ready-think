# Obsidian VaultとOKFの更新・接続

## ノートの本体

KQIリポジトリのルートをObsidian Vaultとして使います。既存ノートのサブフォルダは維持します。スマホもこのルートを開きます。

OKF本体はKQIの外にある GoogleCloudPlatform/knowledge-catalog の独立したGitチェックアウトで管理します。外部チェックアウトの okf/vault/KQI がKQI本体を参照します。スマホにはOKF本体もリンクも不要です。

## OKFを使う前に更新する

PCでKQIルートから実行します（Python 3.9以降、Gitが必要）。

```sh
python3 tools/update_okf.py
```

初回は隣の knowledge-catalog-upstream に元リポジトリを取得し、次回以降は origin/main をfast-forwardで更新します。OKFへの接続も同時に確認します。配置先を変える場合：

```sh
python3 tools/update_okf.py --checkout /path/to/knowledge-catalog-upstream
```

- 更新元：https://github.com/GoogleCloudPlatform/knowledge-catalog
- 変更前後の okf/SPEC.md を比較し、変わっていれば差分URLを表示します。
- ローカル編集や独自コミット、異なるoriginがある場合は停止します。強制リセットしません。
- 端末固有リンクは外部チェックアウトのローカルGit除外設定に登録します。
- OKFの依存ライブラリの更新は、取得したOKFのREADME・pyproject.tomlに従って行います。
- バックグラウンドで自動実行する仕組みではありません。OKF利用前にこのコマンドを実行して最新版を取得する運用です。

仕様書の変更検出とコードの取得までを行います。破壊的な仕様変更に対するKQIの変換処理の修正や、全ノートの自動変換を保証するものではありません。SPEC CHANGEDと出たら差分を確認してから利用します。生成・変換したファイルは原本Vaultとは別の出力先に置きます。

既存の独立OKFに接続だけする場合は従来どおり：

```sh
python3 tools/connect_okf.py --okf /path/to/okf
```

Windowsでは python3 を python に置き換えられます。シンボリックリンク作成にはWindows側の設定・権限が必要な場合があります。

## 入れ子のVaultが端末に残っている場合

2026-09-07の確認時点でGitHub mainには okf/ はありません。スマホの表示に残っていても、端末内の未同期ファイルや異なるチェックアウトの可能性があるため、一括削除はしません。Vaultの表示名だけでは接続先リポジトリは判断できません。

旧 okf/vault/KQI がある実際のローカルVaultで、PCから以下を実行できます。

```sh
python3 tools/clean_duplicate_vault.py --vault /path/to/actual-vault
python3 tools/clean_duplicate_vault.py --vault /path/to/actual-vault --apply
```

最初は比較のみです。--apply は直下の同じ相対パスとバイト単位で一致するコピーだけを削除します。片側にしかないファイル、内容が異なるノート、隠しファイル、リンクは削除しません。空になったフォルダだけ取り除きます。OKF本体が残っていればそれも保持します。

スマホ上でこのPython処理は実行していません。端末固有の残存ファイルをGitHubから直接消すことはできません。端末側の差分を取り込んだ後に整理が必要です。

## 過去のOKF

削除前の構成・独自ファイルは backup-before-vault-root-20260907 ブランチに保持されています。これは復元用であり、更新元としては使いません。過去の独自変更は上流チェックアウトへ自動移植しません。

ノートは通常のMarkdownのままです。OKF消費側がtypeなどのメタデータを必須とする場合は、別途補完・変換が必要です。
