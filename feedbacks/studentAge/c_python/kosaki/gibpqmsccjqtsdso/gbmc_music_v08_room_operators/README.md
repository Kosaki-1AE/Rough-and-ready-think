# GBMC Music v0.8 — Room Operator Isolation Test

目的は **16 Rooms の演算処理を追加しても、Normal/Bypass の「いつ保持・遷移・再評価するか」の判断が同じか** だけを検証することです。v0.7 の既存機能・CSVを保持します。

## 追加機能

- 各 Room `0..F` に *異なる純粋な数値演算* を仮置きしました（例：Input=音量、Motion=音量とFluxの差、Stillness=音量の逆数的スコア）。
- 各30ms観測において、**従来のゲート判定が終わった後** に、到達 Room の演算を実行します。
- `gated_layer_timeline.csv` に従来列を残して `room_operator`, `room_output` を追加しています。
- **演算値は判定・履歴・閾値・再始動にフィードバックしません**。独立性を意図的に保つ検証設計です。
- `compare_routes.py` で Normal/Bypass の判定行・遷移時刻・Room・演算出力を比較します。

⚠️ 演算関数は単なるテスト用の代理演算であり、GBMCCQSD の正式なRoom機能や音楽的判断の正解ではありません。判定の独立性はこの実装で構造的に保証されており、実データから自然法則として発見したわけではありません。音楽的な性能改善も未検証です。

## セットアップ

```powershell
python -m pip install -r requirements.txt
```

WAV ファイル（非圧縮PCM）をこのフォルダに置くか、フルパスで指定します。

## 同じ曲を二経路で処理

```powershell
python gbmc_music.py doppelganger.wav --out output_normal --transition-threshold 0.2 --route normal --repeat-limit 3
python gbmc_music.py doppelganger.wav --out output_bypass --transition-threshold 0.2 --route bypass --repeat-limit 3
python compare_routes.py output_normal/gated_layer_timeline.csv output_bypass/gated_layer_timeline.csv --out route_comparison.json
```

Mazy Metroplexでも同様のコマンドで試せます（WAVファイル名だけ変更）。

## 検証基準

- `gate_decisions_identical: true` … 全観測で `source`, `time_s`, `event`, `reason`, `novelty`, `reference_id` が一致
- `different_room_rows > 0` … 通過した Room が異なる
- `different_operator_output_rows > 0` … Room 演算値が異なる

Room `F` への経路上の通常一周と、G再始動は異なる概念として従来どおり保持します。

## 動作確認

```powershell
python -m unittest discover -p "test*.py" -v
```

2026-10-14時点で全16テスト通過。付属 demo.wav では Normal/Bypass 各268観測、ゲート判定268件一致、Room値差124件、演算値差124件。

これは機能分離を確認した結果です。各Roomの演算結果を *次の判定へ戻す* 場合の独立性は別の実験になります。
