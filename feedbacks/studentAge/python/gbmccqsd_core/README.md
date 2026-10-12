# GBMCCQSD Python Core v0.1

資料「261004_理論がガチで、完成したぁぁぁ.md」の最後に示された構造を、
分野に依存しないPythonコアとして実装しました。
Python 3.9以上向け。外部ライブラリ不要です。

これは状態遷移の記述・実行用の骨格です。理論の実証や、映像から人間の意図を
自動推定するモデルを提供するものではありません。

## まず動かす

ZIPを展開し、`README.md`がある`gbmccqsd_core`フォルダで実行します。
Windowsで`python`が使えない場合は`py`、Mac/Linuxでは`python3`でも実行できます。

```bash
python -m examples.basic
python -m examples.dance
python -m unittest discover -s tests -v
```

`basic`は下位4bitの全16通り、`dance`は手動指定した4例を実行します。
動作中にファイルを書き出す処理やネットワーク通信はありません。

## コアと分野別ファイルの分け方

| ファイル | 役割 | 分野追加時の扱い |
| --- | --- | --- |
| `gbmccqsd/model.py` | Room、判断、操作結果、遷移、記録の共通型 | 基本は共通利用 |
| `gbmccqsd/codec.py` | Roomと下位4bitの符号化・復号 | 基本は共通利用 |
| `gbmccqsd/router.py` | 資料のO/S/J/T判定 | 将来変更するならRouterを差し替え |
| `gbmccqsd/engine.py` | 1サイクルの実行と状態更新 | 基本は共通利用 |
| `domains/template.py` | 新しい分野を作るための実行可能な雛形 | コピーして編集 |
| `examples/basic.py` | 全16通りの実行例 | 実行方法の参考 |
| `examples/dance.py` | ダンスへの接続例 | 分野実装の参考 |
| `tests/test_core.py` | 判定・符号化・状態保持などの検証 | コア変更時に実行 |
| `DESIGN.md` | 資料との対応と未定義部分の扱い | 意味を確認するために参照 |

依存方向は「分野別ファイル → コア」です。コアはダンスや他の分野をimportしません。

## 固定した部分

毎回、次の順序で処理します。

1. `observe`：入力と前回のFeedbackを観測する。
2. `choose`：Responsibility 2bitとOperation 2bitを選ぶ。
3. `operate`：現在のRoomで局所操作を実行する。資料のΦに対応。
4. `route_decision`：下位4bitからO/S/J/Tを判定する。資料のDに対応。
5. `transition`：操作結果・判定・時刻を使って次のRoomを決める。資料のΓに対応。
6. 次の状態とFeedbackを保持し、次回の`observe`へ渡す。

観測する処理`observe`はすべてのサイクルで実行します。
Routerの結果`Route.OBSERVE`はそれとは別の分類です。

| 責任 `b3b2` | 操作 `b1b0` | 判定 | 下位4bitの16進値 |
| --- | --- | --- | --- |
| 00 / 01 | 00 / 01 | Observe | 0, 1, 4, 5 |
| 00 / 01 | 10 / 11 | Straight | 2, 3, 6, 7 |
| 10 / 11 | 00 / 01 | Jab | 8, 9, C, D |
| 10 / 11 | 10 / 11 | Twist | A, B, E, F |

| 操作 | 値 | ビット | 資料の複素単位対応 |
| --- | --- | --- | --- |
| `Operation.HIT`（打つ） | 0 | 00 | 1 |
| `Operation.SHOOT`（弾く） | 1 | 01 | i |
| `Operation.OFF`（外す） | 2 | 10 | -1 |
| `Operation.SET`（置く） | 3 | 11 | -i |

「止める」「当てる」は資料と同じくSET=11に属します。
細かい違いは分野別の入力payloadで表現します。
責任の00/01/10/11の具体的名称は、分野側で定義してください。

## 最小の使用例

```python
from gbmccqsd import Engine, State
from domains.template import TemplateDomain

engine = Engine(TemplateDomain(), State(room=0))

record = engine.step(
    {"responsibility": 2, "operation": 2, "payload": "読み替えたい対象"},
    timestamp=0.03,
)

print(record.route.value)   # Twist
print(record.before.room)   # 0
print(record.after.room)    # 3（テンプレートが決めた移動先）
print(record.address)       # 10 = 0x0A
print(engine.state.data)    # 次の状態
```

Roomが0xA、責任が10、操作が10ならアドレスは`0xAA`です。
既定では上位4bitがRoom、下位4bitが責任と操作で、全体は8bitです。
資料にあるRoom幅2/3bitも`Engine(..., room_bits=2)`などで選べます。
Roomはそれぞれ0..3 / 0..7 / 0..15です。

## 分野を追加する

`domains/template.py`を`domains/my_domain.py`などにコピーし、4つのメソッドを書き換えます。

| メソッド | 受け取るもの | 戻り値 | 分野側が決めること |
| --- | --- | --- | --- |
| `observe` | 状態・外部入力・時刻・前回Feedback | `Observation` | 観測データ、前処理 |
| `choose` | 状態・観測 | `Decision` | 責任と操作の選択方法 |
| `operate` | 状態・観測・判断 | `OperationResult` | 局所操作Φ |
| `transition` | 状態・観測・判断・結果・判定 | `Transition` | 次Room、状態、Feedbackを決めるΓ |

戻り値を作る最小例：

```python
Observation(timestamp, {"features": [0.1, 0.2]})
Decision(responsibility=2, operation=2)
OperationResult(value={"action": "example"}, result_code=None)
Transition(next_room=3, data={"memory": []}, feedback={"status": "updated"})
```

`Transition.data`は次の状態全体です。以前のデータを残すならテンプレートのように
`data = dict(state.data)`から作ってください。
Observeで同じRoomに留まる規則や、JabでRoom 2へ行く規則は**サンプルの設定**です。
コアは移動先、待ち時間、未回収情報の扱いを固定していません。

## 記録・時刻・結果4bit

`step()`は`StepRecord`を返し、観測・責任・操作・結果・ルート・前後Room・Feedbackを記録します。
直近の記録は`engine.last_record`でも参照できます。全履歴が必要なら、呼び出し側で
返り値をリストやファイルへ保存してください。コアは全履歴を溜めません。

`timestamp`は呼び出し側が指定する有限の数値です。秒など、同じ単位・基準を使ってください。
前回より小さい値はエラー、同じ値は許可します。Observeは指定時刻を保持します。
経過時間を使ったTwist判定、待機、タイムアウトの意味は分野側に置いています。

資料の「結果4bit」は符号の意味が未定義なので、任意の`result_code`（0..15）で保持します。
Router判定を結果4bitとして自動符号化したり、Roomアドレスへ追加したりはしません。

状態と記録はdeepcopyで分離します。コールバックや検証が失敗した場合、Engine内の状態、
直近Feedback、時刻、カウンタを更新しません。分野オブジェクト自身の変更、外部への出力、
カメラなどの副作用は巻き戻せません。データはdeepcopy可能な通常の値にしてください。
同じEngineへの再帰的なstepはエラーになります。スレッド間で同じEngineを共有しないでください。

デモの選択は手動指定です。音・骨格から責任や操作を推定したい場合は、別ファイルの
`choose`に推定器を接続します。その推定の正しさは別途検証する必要があります。
