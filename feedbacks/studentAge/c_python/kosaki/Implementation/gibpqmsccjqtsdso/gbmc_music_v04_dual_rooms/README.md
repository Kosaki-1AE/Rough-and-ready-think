# GBMC Music v0.4 — Dual 16-Room runtimes (drum-like / melody-like)

実験用ソフトウェア。神経科学・音楽理論で検証された16状態モデルではありません。

## 新機能

- v0.3までの **全曲GBMC**（16 Rooms, Genesis再始動, 履歴CSV）・拍推定・HPSS分離とイベント時刻を維持
- HPSSで抽出した **ドラム寄り / メロディ寄り成分**から独立の30ms特徴量を計算
- **それぞれ独立したMusicGBMC 16 Roomsインスタンス**を実行。現在Room、基準ID、履歴は相互に干渉しない
- 各成分のOnset時刻を±100ms以内で**1対1の最近傍マッチング**し、符号付き時間差をCSV化
- 音声の全体GBMC・ドラムGBMC・メロディGBMCは別々の観測器。ドラム/メロディ解析の追加は従来全体GBMCを変更しない

## インストール・実行（Windows）

展開した `gbmc_music_v04` フォルダ内で:

```bat
python -m pip install -r requirements.txt
python gbmc_music.py demo.wav --out output_demo --change-threshold 3.2 --transition-threshold 0.2
```

`demo.wav` は付属の**人工的なテスト音**です。購入済み曲を試す場合は自分のWAVを同じフォルダに置き:

```bat
python gbmc_music.py "doppelganger.wav" --out output_doppel_v04 --change-threshold 3.2 --transition-threshold 0.2
python gbmc_music.py "mazy_metroplex.wav" --out output_mazy_v04 --change-threshold 3.2 --transition-threshold 0.2
```

入力は非圧縮PCM WAV。ファイル名は実際のものに置き換えてください。例の2曲のWAVはZIPには入っていません。

`--pair-tolerance-ms 100` を変えると時刻マッチングの許容幅を変更できます。

## 主要CSV（新機能）

| 名前 | 内容 |
|---|---|
| `layer_rooms_timeline.csv` | 共通の観測時刻・ドラムRoom・メロディRoom・それぞれの判定と基準ID |
| `layer_room_events.csv` | ドラム/メロディ側の独立した遷移とG再始動の全イベント（保持は省略） |
| `drum_melody_offsets.csv` | 対応付けたドラム時刻とメロディ時刻、`offset_ms = melody_time - drum_time`、先行/遅延 |
| `summary.json` | 全体GBMC、拍、2レイヤーの独立Room遷移回数、マッチング集計 |

### 維持する旧出力

`events.csv`, `beat_times.csv`, `beat_comparison.csv`, `drum_melody_events.csv`, `drum_melody_timeline.csv`。

## 注意・制限

1. HPSSの打楽器的成分 ≠ ドラム音源そのもの。持続音成分 ≠ メロディそのもの（歌声・ベースも含み得る）。
2. Onset最近傍1対1対応は**時刻の近さ**であり、音楽的に対応する音符や意図されたズレの証明ではありません。該当範囲に相手がないイベントは未対応として集計します。
3. HPSSは曲全体を見て処理する**非因果的オフライン解析**です。実時間30msの処理速度は保証しません。
4. 独立ランタイムのRoom遷移規則は以前と同じ仮説的な閾値+線形遷移。各Roomに固有の意味的機能は未実装です。
5. 分離レイヤーは11025Hzにリサンプリングするため、30ms hopが整数サンプルに丸められ、元音源の時刻とわずかにずれます。タイムラインの対応は実時刻の最近傍で行っています。
6. ビート推定は半テンポ/倍テンポや位相誤差があり得ます。

## テスト

```bat
python -m unittest discover -v
```
