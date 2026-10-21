"""Minimal structure/history experiment; Python standard library only.
Run: python perceptron_structure_experiment.py
"""
from itertools import product

class Perceptron:
    def __init__(self, n_features, lr=0.2):
        self.w = [0.0] * n_features
        self.b = 0.0
        self.lr = lr

    def predict(self, x):
        return int(sum(w * v for w, v in zip(self.w, x)) + self.b >= 0)

    def fit(self, samples, epochs=100):
        for _ in range(epochs):
            mistakes = 0
            for x, label in samples:
                error = label - self.predict(x)
                mistakes += (error != 0)
                for j, value in enumerate(x):
                    self.w[j] += self.lr * error * value
                self.b += self.lr * error
            if not mistakes:
                break
        return self

def accuracy(model, samples):
    return sum(model.predict(x) == y for x, y in samples) / len(samples)

# Four states: same current room (0 or 1), but two different entry histories (0 or 1).
# A valid next-route decision is determined by where the agent arrived FROM.
full_samples = [((current, history), history)
                for current, history in product((0, 1), repeat=2)]
current_only = [((x[0],), y) for x, y in full_samples]
with_history = [(x, y) for x, y in full_samples]

for label, samples in [('Current state only', current_only),
                       ('Current + history', with_history)]:
    model = Perceptron(len(samples[0][0])).fit(samples)
    print(f'{label}: accuracy={accuracy(model, samples):.0%}, weights={model.w}, bias={model.b:.2f}')

# Same example for XOR: needs a hidden layer or nonlinear feature representation.
xor_samples = [((a, b), a ^ b) for a, b in product((0, 1), repeat=2)]
model = Perceptron(2).fit(xor_samples)
print(f'XOR with a single perceptron: accuracy={accuracy(model, xor_samples):.0%}')
print('Note: toy training-set demonstrations, not independent generalization tests.')
