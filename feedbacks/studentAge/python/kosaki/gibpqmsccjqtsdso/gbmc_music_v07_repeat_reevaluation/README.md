# GBMC Music v0.7 — 同じRoom 2〜3連で再評価

v0.6の全機能（音声WAV・30ms観測、全体GBMC、Beat、HPSSによるドラム寄り／メロディ寄りの抽出、独立Room、時間差CSV、通常経路／バイパス経路）を保持。新たに、**音の立ち上がり候補が検出されたときの判断**を1回として数え、同じRoomの判断が指定回数続いたら再評価を記録する。

- `--repeat-limit 3`（標準）または `--repeat-limit 2` を指定。
- **30msの通常観測は連続回数に含めない**。検出されたOnsetのみカウント。
- 再評価は `gated_layer_timeline.csv` に `event=reevaluate` として残す。理由は `repeat_limit_reached_keep_familiar` または `repeat_limit_reached_keep_insufficient_evidence`。
- 「2連／3連だから必ず遷移」ではない。既知のパターンや証拠不足なら現在Roomを保持する。再評価後は連続カウンタをリセットして、再び次の判断群を観測する。
- 通常のRoom遷移・Genesis再始動が生じた場合もカウンタをリセット。再始動時も従来の履歴を保持。
- 新しい `summary.json` の `gated_layer_runtimes.{drum,melody}.reevaluations` に回数を記録。
- `normal`: `F0123456789ABCDE` (`9→A`)、`bypass`: `F14679BC` (`9→B`)。

## インストール

```powershell
python -m pip install -r requirements.txt
```

## まずDoppelgängerで比較

```powershell
python gbmc_music.py doppelganger.wav --out output_normal_3 --transition-threshold 0.2 --route normal --repeat-limit 3
python gbmc_music.py doppelganger.wav --out output_bypass_3 --transition-threshold 0.2 --route bypass --repeat-limit 3
```

2連も比較する場合：

```powershell
python gbmc_music.py doppelganger.wav --out output_normal_2 --transition-threshold 0.2 --route normal --repeat-limit 2
```

テスト： `python -m unittest discover -p "test*.py" -v`

## 出力

既存の `events.csv`, `beat_times.csv`, `beat_comparison.csv`, `drum_melody_timeline.csv`, `drum_melody_events.csv`, `drum_melody_offsets.csv`, `layer_rooms_timeline.csv`, `layer_room_events.csv`, `gated_layer_timeline.csv`, `summary.json` を維持。

`gated_layer_timeline.csv` の `event=reevaluate` は **Room遷移でもG再始動でもない**。`held_frames` は `hold` と `reevaluate` を合算した保持区間数。

## 限界・研究上の解釈

これは「空気を読む」ことを証明したものではない。音響のOnset候補を意思決定イベントの代理にしており、既知判定も拍への相対位置を量子化した簡易規則。何を「同じRoomの判断」と呼ぶか、2〜3連の閾値が妥当かは要検証。音楽の時間軸と人間の即興判断は別。

同じRoom連続という条件だけでは新しい選択肢を生成しない（Qは未実装）。再評価でも新証拠が無ければ保持。既存の通常／バイパス経路選択は実行時の手動選択であり、自動切替は行わない。
