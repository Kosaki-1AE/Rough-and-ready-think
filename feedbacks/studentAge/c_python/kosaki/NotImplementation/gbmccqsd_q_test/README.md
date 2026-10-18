# GBMCCQSD Q推定プロトタイプ

1次元スカラー系の最小実装です。

## 中心式

R_self = -alpha_s * grad_m + beta_s * d * lap_b

H = (beta_s*d*lap_b - R_self)/alpha_s - c1

Q = H + (R_env - beta_e*Q)/(alpha_e + gamma_e*Q)

したがって各時刻で次の二次方程式を解きます。

gamma_e*Q^2
+ (alpha_e + beta_e - gamma_e*H)*Q
- (alpha_e*H + R_env) = 0

その後、

Q_t = Q_habit + Q_context(x_t,t) + epsilon_t

として分解します。

## 注意
synthetic_example.csv は式が成立するよう生成した人工データです。
そのため、ここで確認できるのは「実装可能性」と「既知条件でQを回収できること」であり、
実世界で理論が正しいことの証明ではありません。

## 実データCSV必須列
d, lap_b, R_self, c1, R_env

Q_context 用の任意列も追加できます。

## 実行例
python gbmccqsd_q_infer.py data.csv --alpha-s 1.3 --beta-s 0.7 --alpha-e 1.1 --beta-e 0.45 --gamma-e 0.18 --context-cols x,time_sin --out-prefix result
