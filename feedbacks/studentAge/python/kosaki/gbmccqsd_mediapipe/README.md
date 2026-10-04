# GBMCCQSD × MediaPipe（教師データ不要の最小実装）

これは、現在の仮説

\[
G \to B \to M \to C_1 \to C_2 \to Q \to S \to D
\]

を、**MediaPipe Pose の時系列だけから一旦動かすためのプロトタイプ**です。

教師ラベルは使いません。

## 何をしているか

動画
→ MediaPipe Pose 33点
→ 平行移動・スケール正規化
→ 関節角度 + 座標 + 速度特徴
→ PCA で1次元 latent state \(x_t\)
→ delay embedding
→ 過去の似た状態をKNNで検索
→ その後に実際どう動いたかを候補集合として取得
→ GBMCCQSD各変数の観測代理量を作る
→ 状態遷移方程式の係数を教師なし回帰
→ Q を habit / context / noise に分解

## 現在の「観測代理量」

- G = 過去の類似状態から得られる有効候補数（memory availability）
- B = 類似状態の「次の遷移」のばらつき（余白）
- M = 1次元 latent state（試行状態）
- C1 = 過去の類似状態から予測した次の遷移
- C2 = 実際に観測された次の遷移
- Q = \(\nabla M - C_2\) の1次元代理量
- S = C1から予測した次状態
- D = 類似状態までの局所距離（自己参照範囲）

**ここは理論上の真値ではなく、実装可能にするための operational definition です。**
結果を見ながら差し替える前提です。

## 当てはめる式

\[
g\frac{Db}{Dt}
=
-\alpha_s\nabla m
+\beta_s d\nabla^2 b
+\alpha_e\Delta C
+\beta_e Q
+\gamma_e\Delta C Q
\]

\[
\Delta C=C_1-C_2
\]

この式は係数について線形なので、

\[
\alpha_s,\beta_s,\alpha_e,\beta_e,\gamma_e
\]

を動画時系列から Ridge 回帰で推定できます。
クラスラベルや教師データは不要です。

## 癖

最後に

\[
Q_t = Q_{\rm habit}+Q_{\rm context}(t)+\epsilon_t
\]

として、

- `Q_habit` = 全時系列で残るロバスト中心
- `Q_context` = 状態クラスタごとの偏り
- `epsilon` = 残差

へ分解します。

現段階では `Q_habit` を **癖候補** と呼ぶのが安全です。
別動画・別曲でも同じ値や方向が再現されるかを検証して初めて「癖」と主張できます。

## インストール

Python 3.9+ を想定。

```bash
python -m pip install -r requirements.txt
```

## 実行

動画1本:

```bash
python mediapipe_gbmccqsd.py input.mp4 --output out
```

同じ人物の動画をフォルダにまとめて:

```bash
python mediapipe_gbmccqsd.py ./videos --output out
```

## 出力

- `landmarks.csv` : MediaPipe 33点
- `pose_features.csv` : 正規化特徴
- `q_timeseries.csv` : G,B,M,C1,C2,Q,S,D と式の残差
- `habit_summary.csv` : Q_habit / context / noise の要約
- `model_summary.json` : 推定された5係数、train/test R²、RMSE

## 重要な読み方

### 1. 最初に見る
`model_summary.json`

特に

- `test_r2`
- `test_rmse`

を見る。

test R² が負なら、現在の式または operational definition がデータを説明できていない。

### 2. 次に見る
`habit_summary.csv`

`Q_habit` が得られる。

ただし1本の動画だけでは「その動画の平均偏り」と「人物固有の癖」を分離しきれない。
同じ人の複数動画、できれば曲・ジャンル・日を変えたデータで再現性を見る。

### 3. q_timeseries.csv
各フレームの

`G,B,M,C1,C2,Q,S,D`

を全部残すので、後から定義を差し替えられる。

## 現時点の弱点

1. 1次元PCAへ落としている。
2. \(\nabla\) を「観測軌道に沿った微分」として近似している。
3. Q の operational definition はまだ仮説。
4. 複数動画を単純結合しているので、動画境界の扱いは次版で分離する方が良い。
5. MediaPipeの誤検出がそのままノイズに入る。

なのでこの版の目的は「理論の正しさを証明する」ことではなく、

**MediaPipeだけでGBMCCQSDを観測可能な時系列に落とし、式を反証可能にする**

ことです。
