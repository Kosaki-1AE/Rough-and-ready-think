```python
import numpy as np


class Perceptron:
    """
    prgrms_v4.1 experimental

    追加した観測層:
    - Q       : 候補ごとの責任重み
    - Depth   : Qから実効候補集合を作る
    - N_eff   : 実効候補数（entropy/perplexity）
    - viscosity(nu): 同じ経路を保持してきた長さから作る「変わりにくさ」

    NOTE:
    学習則そのものを大きく変えず、まずは「観測可能にする」ための実装。
    """

    def __init__(
        self,
        n_features=2,
        learning_rate=0.1,
        q_temperature=1.0,
        depth_threshold=0.15,
        viscosity_alpha=0.35,
    ):
        self.lr = learning_rate

        self.w = np.zeros(n_features)
        self.b = 0.0

        self.w_main = [0.0]
        self.b_main = [0.0]

        self.w_backup = [np.zeros(2)]
        self.b_backup = [0.0]

        self.memory = []

        self.backup_states = [
            np.array([0, 0]),
            np.array([0, 1]),
            np.array([1, 0]),
            np.array([1, 1]),
        ]
        self.backup_index = 0

        # ---------- GBMCCQSD観測用 ----------
        self.q_temperature = q_temperature
        self.depth_threshold = depth_threshold
        self.viscosity_alpha = viscosity_alpha

        self.route_stats = {
            "main": {"attempts": 0, "success": 0},
            "backup": {"attempts": 0, "success": 0},
        }

        self.last_selected = None
        self.route_streak = 0

    def next_backup(self):
        backup = self.backup_states[self.backup_index]
        self.backup_index += 1
        if self.backup_index >= len(self.backup_states):
            self.backup_index = 0
        return backup

    def activation(self, z):
        return 1 if z >= 0 else 0

    def logical_or(self, a, b):
        return int(bool(a) or bool(b))

    # ============================================================
    # Q（責任重み）
    # ============================================================

    def responsibility_score(self, route_name):
        """
        現時点では最小構成として、
        「その経路が過去どれだけ成功したか」を責任重みの観測量にする。

        Beta(1,1) の平滑化:
            q = (success + 1) / (attempts + 2)

        これはQの最終定義ではなく、実験用の推定量。
        """
        s = self.route_stats[route_name]
        return (s["success"] + 1.0) / (s["attempts"] + 2.0)

    def q_distribution(self):
        q_main = self.responsibility_score("main")
        q_backup = self.responsibility_score("backup")

        q = np.array([q_main, q_backup], dtype=float)
        z = q / max(self.q_temperature, 1e-9)
        z = z - np.max(z)
        p = np.exp(z)
        p = p / np.sum(p)

        return {
            "q_main": q_main,
            "q_backup": q_backup,
            "p_main": p[0],
            "p_backup": p[1],
        }

    # ============================================================
    # Depth（実効候補集合）
    # ============================================================

    def depth_filter(self, p_main, p_backup):
        candidates = {
            "main": p_main,
            "backup": p_backup,
        }

        active = {
            name: prob
            for name, prob in candidates.items()
            if prob >= self.depth_threshold
        }

        if not active:
            name = max(candidates, key=candidates.get)
            active = {name: candidates[name]}

        return active

    # ============================================================
    # 実効候補数 N_eff
    # ============================================================

    def effective_candidate_count(self, probs):
        p = np.asarray(probs, dtype=float)
        p = p[p > 0]
        if len(p) == 0:
            return 0.0

        p = p / np.sum(p)
        H = -np.sum(p * np.log(p))
        return float(np.exp(H))

    # ============================================================
    # 粘性 nu
    # ============================================================

    def update_viscosity(self, selected):
        if selected == self.last_selected:
            self.route_streak += 1
        else:
            self.route_streak = 1
            self.last_selected = selected

        nu = 1.0 - np.exp(-self.viscosity_alpha * self.route_streak)
        return float(nu)

    # ============================================================
    # 学習
    # ============================================================

    def train_one(self, x, y_main, y_backup, epoch, sample_id):
        x_main = int(x[0])
        x_backup = int(x[1])
        x_total = self.logical_or(x_main, x_backup)

        main_score = self.w_main[-1] * x_main + self.b_main[-1]
        main_pred = self.activation(main_score)
        error_main = y_main - main_pred

        # Q / Depth / N_eff は「選択前」に観測
        q_state = self.q_distribution()
        active_candidates = self.depth_filter(
            q_state["p_main"],
            q_state["p_backup"],
        )
        N_eff = self.effective_candidate_count([
            q_state["p_main"],
            q_state["p_backup"],
        ])

        self.route_stats["main"]["attempts"] += 1

        if main_pred == y_main:
            selected = "main"
            self.route_stats["main"]["success"] += 1

            backup = None
            backup_score = None
            backup_pred = None
            error_backup = 0
        else:
            backup = self.next_backup()
            selected = "backup"

            self.route_stats["backup"]["attempts"] += 1

            backup_score = np.dot(self.w_backup[-1], backup) + self.b_backup[-1]
            backup_pred = self.activation(backup_score)
            error_backup = y_backup - backup_pred

            if backup_pred == y_backup:
                self.route_stats["backup"]["success"] += 1

        viscosity = self.update_viscosity(selected)

        old_w_main = self.w_main[-1]
        old_b_main = self.b_main[-1]
        old_w_backup = self.w_backup[-1].copy()
        old_b_backup = self.b_backup[-1]

        new_b_main = self.b_main[-1] + self.lr * error_main
        new_w_main = self.w_main[-1] + new_b_main * x_main
        new_b_backup = self.b_backup[-1] + self.lr * error_backup

        if backup is not None:
            new_w_backup = self.w_backup[-1] + new_b_backup * backup
        else:
            new_w_backup = self.w_backup[-1].copy()

        self.b_main.append(new_b_main)
        self.w_main.append(new_w_main)
        self.b_backup.append(new_b_backup)
        self.w_backup.append(new_w_backup)

        self.memory.append({
            "epoch": epoch,
            "sample_id": sample_id,
            "x_main": x_main,
            "x_backup": x_backup,
            "x": x_total,
            "y_main": y_main,
            "y_backup": y_backup,
            "main_score": main_score,
            "main_pred": main_pred,
            "error_main": error_main,
            "backup_state": None if backup is None else backup.copy(),
            "backup_score": backup_score,
            "backup_pred": backup_pred,
            "error_backup": error_backup,
            "selected": selected,

            # 新規観測
            "q_main": q_state["q_main"],
            "q_backup": q_state["q_backup"],
            "p_main": q_state["p_main"],
            "p_backup": q_state["p_backup"],
            "active_candidates": list(active_candidates.keys()),
            "N_eff": N_eff,
            "history_length": self.route_streak,
            "viscosity": viscosity,

            # 既存
            "old_w_main": old_w_main,
            "old_b_main": old_b_main,
            "old_w_backup": old_w_backup,
            "old_b_backup": old_b_backup,
            "w_main": self.w_main[-1],
            "b_main": self.b_main[-1],
            "w_backup": self.w_backup[-1].copy(),
            "b_backup": self.b_backup[-1],
        })

        return error_main, error_backup, selected

    def fit(self, X, y_main, y_backup, epochs=10):
        for epoch in range(epochs):
            errors = 0

            for sample_id, (xi, ym, yb) in enumerate(zip(X, y_main, y_backup)):
                error_main, error_backup, selected = self.train_one(
                    xi, ym, yb, epoch + 1, sample_id
                )

                if error_main != 0 or error_backup != 0:
                    errors += 1

            last = self.memory[-1]
            print(
                f"epoch={epoch + 1}, "
                f"errors={errors}, "
                f"w_main={self.w_main[-1]:.2f}, "
                f"b_main={self.b_main[-1]:.2f}, "
                f"w_backup={self.w_backup[-1]}, "
                f"b_backup={self.b_backup[-1]:.2f}, "
                f"N_eff={last['N_eff']:.3f}, "
                f"nu={last['viscosity']:.3f}"
            )

    def show_memory(self):
        print("\n===== MEMORY =====")

        for m in self.memory:
            print(
                f"epoch={m['epoch']} "
                f"sample={m['sample_id']} | "
                f"x_main={m['x_main']} "
                f"x_backup={m['x_backup']} "
                f"-> x={m['x']} | "
                f"selected={m['selected']} | "
                f"Q=({m['q_main']:.3f},{m['q_backup']:.3f}) | "
                f"P=({m['p_main']:.3f},{m['p_backup']:.3f}) | "
                f"active={m['active_candidates']} | "
                f"N_eff={m['N_eff']:.3f} | "
                f"L={m['history_length']} | "
                f"nu={m['viscosity']:.3f} | "
                f"error_main={m['error_main']} "
                f"error_backup={m['error_backup']}"
            )


X = np.array([
    [0, 0],
    [0, 1],
    [1, 0],
    [1, 1],
])

y_main = np.array([0, 1, 1, 1])
y_backup = np.array([1, 1, 1, 1])

model = Perceptron(
    n_features=2,
    learning_rate=0.1,
    q_temperature=1.0,
    depth_threshold=0.15,
    viscosity_alpha=0.35,
)

model.fit(X, y_main, y_backup, epochs=10)
model.show_memory()
```
