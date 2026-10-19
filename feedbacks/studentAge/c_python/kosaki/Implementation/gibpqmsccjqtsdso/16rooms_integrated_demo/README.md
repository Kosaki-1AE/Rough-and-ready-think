# 16Rooms × Music × Dance Robot 統合デモ

既存の `gbmc_music_v04`、`rooms_v11`、`mental_loop`、`pipeline_v13` を利用したオフライン統合デモです。

## 実行方法

Python 3.10以上推奨。

```bash
python -m pip install -r requirements.txt
python integrated_demo.py --out demo_output
```

このコマンドは **人工音声・人工姿勢**を生成して実行します。実音源・実動画の検証結果ではありません。

実音源と、`extract_pose.py` が生成したMediaPipe CSVを利用する場合:

```bash
python integrated_demo.py --wav music.wav --pose-csv pose_csv/sample_pose.csv --bpm 120 --out real_output
```

**重要:** `--pose-csv` のみではお手本の参照データが存在しないため、ロボット側は `HOLD` となります。参照姿勢を別途測定した場合は以下を使ってください。

```bash
python integrated_demo.py --wav music.wav --pose-csv pose_csv/sample_pose.csv --reference-csv reference.csv --bpm 120 --out real_output
```

参照CSVには `chunk_id`, `phase`, および8種の関節角度列（`hip_left_deg` など）が必要です。入力CSVのチャンクは `dance_chunk` に固定しているため、参照側も `dance_chunk` としてください。現状、時刻原点は `--start-ms`、1エイト長は `8*60000/BPM` で設定します。自動的な楽曲とダンスの時刻合わせではありません。

ドラム・メロディ分離を省略する場合は `--no-layers` を追加できます。

## 生成ファイル

- `integrated_timeline.csv` : 音楽全体、ドラム、メロディ、ダンス、Robot v1.3の判断を時刻で結合
- `integrated_summary.json` : 統合処理の集計
- `timeline.png` : Room推移の簡易図
- `music/` : GBMC Music v0.4のCSV・JSON
- `robot/` : Dance Robot v1.3のCSV・JSON、Room履歴、予測、再観測要求

## 重要な制約

- G1 URDFは関節定義の参照用で、**モーターへの命令送信はありません**。
- MediaPipeの人体角度からG1の関節角度への較正・逆運動学・バランス制御は未実装です。
- ロボットのマッピングは空にしており、`PROPOSED` は「判断段階の候補」であり、実機用関節目標の存在を意味しません。
- HPSSは曲全体を処理する非因果的なオフライン解析です。30msは観測間隔で、30ms以内のリアルタイム計算保証ではありません。
- 実データでは、音声と映像の時間原点、BPM、参照チャンクを明示的に合わせる必要があります。
- 人工データの結果は研究性能の証明ではありません。
- 認証情報・YouTube動画本体は同梱していません。
