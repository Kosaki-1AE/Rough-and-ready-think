# GBMCCQSD × Obsidian / Text

教師データなしで Markdown 時系列から GBMCCQSD の代理変数を構成するプロトタイプです。

## 実行

```bash
python -m pip install -r requirements.txt
```

GitHub clone済みなら:

```bash
python text_gbmccqsd.py \
  ~/Documents/Programs/Rough-and-ready-think/MyFeedbacks \
  --output out
```

修士1年だけ:

```bash
python text_gbmccqsd.py \
  ~/Documents/Programs/Rough-and-ready-think/MyFeedbacks \
  --include-regex "GraduateAge/1stGrade" \
  --output out_grad1
```

## 出力

- `q_timeseries.csv`
- `habit_summary.csv`
- `habit_examples.md`
- `model_summary.json`
- `REPORT.md`

## 現在の operational definition

- G = 過去類似状態の有効数
- B = 類似状態の次遷移候補のばらつき
- M = 現在の文章 latent state
- C1 = 過去の類似状態から予測される次遷移
- C2 = 実際に観測された次遷移
- Q = grad(M) - C2
- S = M + C1
- D = 過去類似状態までの参照半径

## 式

```text
g * Db/Dt =
    -alpha_s * grad_m
    + beta_s * d * lap_b
    + alpha_e * DeltaC
    + beta_e * Q
    + gamma_e * DeltaC * Q
```

教師ラベルは使わず、係数をRidge回帰で推定します。

## 最初に見るもの

`REPORT.md` の `test R2`。

次に `habit_examples.md` を読んで、Q_habit付近の原文が本当に同じ思考遷移の癖に見えるか確認してください。

現段階のQ_habitは「癖候補」です。期間・話題を変えても安定するかを確認すると、論文としてかなり強くなります。
