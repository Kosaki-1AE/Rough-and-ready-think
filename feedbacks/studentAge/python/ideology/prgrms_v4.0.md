```python
import numpy as np

class Perceptron:

    def __init__(self, n_features=2, learning_rate=0.1):
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
            np.array([1, 1])
        ]
        self.backup_index = 0
    
    def next_backup(self):
        backup = self.backup_states[
            self.backup_index
        ]
        self.backup_index += 1
        if self.backup_index >= len(self.backup_states):
            self.backup_index = 0
        return backup
    
    def activation(self, z):
        return 1 if z >= 0 else 0

    def logical_or(self, a, b):
        return int(bool(a) or bool(b))

    def train_one(self, x, y_main, y_backup, epoch, sample_id):
        x_main = int(x[0])
        x_backup = int(x[1])
        x_total = self.logical_or(x_main, x_backup)
        main_score = (self.w_main[-1] * x_main + self.b_main[-1])
        main_pred = self.activation(main_score)
        error_main = (y_main - main_pred)

        if main_pred == y_main:
            selected = "main"
            backup = None
            backup_score = None
            backup_pred = None
            error_backup = 0

        else:
            backup = self.next_backup()
            selected = "backup"
            backup_main = backup[0]
            backup_sub = backup[1]
            backup_score = np.dot(self.w_backup[-1], backup) + self.b_backup[-1]
            backup_pred = self.activation(backup_score)
            error_backup = y_backup - backup_pred

        old_w_main = self.w_main[-1]
        old_b_main = self.b_main[-1]
        old_w_backup = self.w_backup[-1].copy()
        old_b_backup = self.b_backup[-1]
        new_b_main = (self.b_main[-1] + self.lr * error_main)
        new_w_main = (self.w_main[-1] + new_b_main * x_main)
        new_b_backup = (self.b_backup[-1] + self.lr * error_backup)
        if backup is not None:
            new_w_backup = (self.w_backup[-1] + new_b_backup * backup)
        else:
            new_w_backup = (self.w_backup[-1].copy())
        self.b_main.append(new_b_main)
        self.w_main.append(new_w_main)
        self.b_backup.append(new_b_backup)
        self.w_backup.append(new_w_backup)

        self.memory.append({
            "epoch": epoch,
            "sample_id": sample_id, # 時間
            
            "x_main": x_main,
            "x_backup": x_backup, # OR前
            "x": x_total, # OR後
            
            "y_main": y_main,
            "y_backup": y_backup, # 教師
            
            "main_score": main_score,
            "main_pred": main_pred, # 予測
            "error_main": error_main,
            
            "backup_state":
                None
                if backup is None
                else backup.copy(),
            "backup_score": backup_score,
            "backup_pred": backup_pred,
            "error_backup": error_backup, # 誤差
            
            "selected": selected, # 選択経路
            
            "old_w_main": old_w_main, # 更新前
            "old_b_main": old_b_main,
            "old_w_backup": old_w_backup,
            "old_b_backup": old_b_backup,

            "w_main": self.w_main[-1], # 更新後
            "b_main": self.b_main[-1],
            "w_backup": self.w_backup[-1].copy(),
            "b_backup": self.b_backup[-1]
        })

        return (error_main, error_backup, selected)

    def fit(self, X, y_main, y_backup, epochs=10):
        for epoch in range(epochs):
            errors = 0

            for sample_id, (xi, ym, yb) in enumerate(zip(X, y_main, y_backup)):
                (error_main, error_backup, selected) = self.train_one(xi, ym, yb, epoch + 1, sample_id)

                if (error_main != 0 or error_backup != 0):
                    errors += 1

            print(
                f"epoch={epoch + 1}, "
                f"errors={errors}, "
                f"w_main={self.w_main[-1]:.2f}, "
                f"b_main={self.b_main[-1]:.2f}, "
                f"w_backup={self.w_backup[-1]}, "
                f"b_backup={self.b_backup[-1]:.2f}"
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
                f"backup_state={m['backup_state']} | "
                f"error_main={m['error_main']} "
                f"error_backup={m['error_backup']}"
            )

X = np.array([
    [0, 0],
    [0, 1],
    [1, 0],
    [1, 1]
])

y_main = np.array([0, 1, 1, 1])
y_backup = np.array([1, 1, 1, 1])

model = Perceptron(
    n_features=2,
    learning_rate=0.1
)

model.fit(
    X,
    y_main,
    y_backup,
    epochs=10
)

model.show_memory()
```
