#/Mine研究 
何か分かったんだけどさ。世の中には俺みたいに「場における認証」が確定で必要になる人間がいるはずだわ。

#/git 
gitに登録したんすけど。多分これでWindowsでもできるようになったはずでな。できてるんかなぁ。まぁしばらく書き続ける必要はある気がするけどね。
fetchやらpushやらやらなあかんのクソ面倒くさいw これならいけるんかなぁ
色々変更中です。最終変更版だけこっちに記載するけどね。

終わったっぽい。あえてWindowsの方で書いてるんだけどさぁw 多分大丈夫かなぁってw
あ...ちな、ps1じゃないとWinsowsの変更はできないので....。気を付ける必要がございますww
でも今のところ何もエラーないところを見ると.....合ってるんだろうねww

Obsidian + Git + GitHub 同期構築手順（Mac / Windows / iPhone）
環境構築
- GitHub Repository
- Obsidian
- Obsidian Git Plugin
- Mac
- Windows11 (WSL)
- iPhone

1. MacでGitHubを正常化
リポジトリへ移動
```bash
cd ~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/knowledge-catalog
```
確認
```bash
git status
git branch -vv
git remote -v
```
期待結果
```
origin https://github.com/Kosaki-1AE/KQI.git
```
remote修正（必要なら）
```bash
git remote set-url origin https://github.com/Kosaki-1AE/KQI.git
```
branch追跡設定
```bash
git push -u origin main
```
確認
```bash
git status
working tree clean
```

2. .gitignore設定
追加
```gitignore
# macOS
.DS_Store

# Python
.venv/

# node
node_modules/

# Obsidian
.obsidian/workspace.json
.obsidian/workspace-mobile.json

# Windows ADS
*Zone.Identifier

# askpass
**/obsidian_askpass.sh
```
コミット
```bash
git add .gitignore
git commit -m "ignore obsidian temporary files"
git push
```

3. Windows (WSL)
リポジトリへ
```bash
cd /mnt/c/Users/<ユーザー名>/Documents/KQI
```
確認
```bash
git status
git branch -vv
git remote -v
```
最新取得
```bash
git fetch
```
pull
```bash
git pull
```
conflictが出たら
```
<<<<<<< HEAD
=======
>>>>>>>
```
を消す。
内容だけ残す。
保存
```
Ctrl+O
Enter
Ctrl+X
```
反映
```bash
git add ファイル名
git commit -m "Merge xxxx"
git push
```

4. Zone.Identifier掃除
Windows特有
- 削除
```bash
find . -name "*Zone.Identifier" -delete
```
- .gitignoreへ追加
```
*Zone.Identifier
```
- コミット
```bash
git add .
git commit -m "Ignore Zone.Identifier"
git push
```

5. Windows Proxy問題
学校
```
http://wwwproxy1.kanazawa-it.ac.jp:8080
```
学外ではOFFにする。

PowerShell
- Proxy ON
```powershell
$env:http_proxy="http://wwwproxy1.kanazawa-it.ac.jp:8080"
$env:https_proxy="http://wwwproxy1.kanazawa-it.ac.jp:8080"
```
- Proxy OFF
```powershell
Remove-Item Env:http_proxy
Remove-Item Env:https_proxy
```
自動化
- kit-proxy.ps1
```powershell
$ssid=(netsh wlan show interfaces |
Select-String "^ *SSID").ToString().Split(":")[1].Trim()

if($ssid -eq "KIT-WLAP2"){
    $env:http_proxy="http://wwwproxy1.kanazawa-it.ac.jp:8080"
    $env:https_proxy="http://wwwproxy1.kanazawa-it.ac.jp:8080"
    Write-Host "Proxy ON"
}
else{
    Remove-Item Env:http_proxy -ErrorAction Ignore
    Remove-Item Env:https_proxy -ErrorAction Ignore
    Write-Host "Proxy OFF"
}
```
実行
```powershell
.\kit-proxy.ps1
```

6. iPhone
Obsidian Git
同期失敗したら
```
wwwproxy1.kanazawa-it.ac.jp:8080
```
になっていないか確認。
Proxy設定を削除。

7. 日常運用
Mac
```bash
git pull
```
↓
編集
↓
```bash
git add .
git commit -m "内容"
git push
```

Windows
```bash
git pull
```
↓
編集
↓
```bash
git add .
git commit -m "内容"
git push
```

iPhone
Obsidian Git：Sync または Auto Sync
確認コマンド
```bash
git status
working tree clean
git branch -vv
git remote -v
git log --oneline --decorate -5
```

トラブル
 "failed to connect to wwwproxy" → Proxy OFF
"working tree clean" → 正常
"Your branch is ahead" → pushすればOK
merge conflict → 「<<<<<<<=======>>>>>>>」を消して内容だけ残す。
Zone.Identifier → Windowsの付加情報。削除して問題なし。

GitHubのPATとして使ってくれ(有効期限は一年後の今日！！)⬇️
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

無理っぽい、なぜだぁぁぁぁ.......。
⬆️出来てましたごめんw

#人間関係/愛情 
女子においても「単純」と「複雑」っていう分けられる部分があるっぽくてな。
つまりは「肌感」とかその類なんだけどねw この単純と複雑とを分けるのが「肌感」っていうねw
