"""GBMC/CQSD attractor toy experiment (standard library only).

This extends the supplied single-layer perceptron demo with a *recurrent*
continuous neuron. It tests symmetry and attraction, not dance or GBMC truth.

Run:
    python3 perceptron_attractor_experiment.py
    python3 perceptron_attractor_experiment.py --w 1.6 --bias 0 --steps 120
    python3 perceptron_attractor_experiment.py --w 0.6 --bias 0.2 --out my_run
    python3 perceptron_attractor_experiment.py --legacy
"""

import argparse
import csv
import math
from itertools import product
from pathlib import Path


class Perceptron:
    """Original non-recurrent classifier, retained for comparison."""
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


def legacy_demo():
    """Reproduce the uploaded classifier/history and XOR baseline."""
    full = [((current, history), history)
            for current, history in product((0, 1), repeat=2)]
    for name, data in [
        ('Current state only', [((x[0],), y) for x, y in full]),
        ('Current + history', full),
        ('XOR, single perceptron', [((a, b), a ^ b)
                                    for a, b in product((0, 1), repeat=2)]),
    ]:
        model = Perceptron(len(data[0][0])).fit(data)
        rate = sum(model.predict(x) == y for x, y in data) / len(data)
        print(f'{name}: training accuracy={rate:.0%}, weights={model.w}, bias={model.b:.2f}')
    print('These are training-set demonstrations, not generalization tests.')


class RecurrentNeuron:
    """x(t+1) = tanh(w*x(t) + b): no history array needed for decisions."""
    def __init__(self, weight, bias):
        self.weight = float(weight)
        self.bias = float(bias)

    def step(self, x):
        return math.tanh(self.weight * x + self.bias)

    def slope_at(self, x):
        return self.weight * (1.0 - self.step(x) ** 2)


def transform(x):
    """Involution T(x)=-x; T(T(x))=x."""
    return -x


def paired_model(g):
    """C = T o G o T; this is *conjugacy*, not a time-reversed inverse."""
    return RecurrentNeuron(g.weight, -g.bias)


def trace(model, seed, steps):
    values = [float(seed)]
    for _ in range(steps):
        values.append(model.step(values[-1]))
    return values


def assess(trace_values, model, tolerance=1e-8):
    """End-state residual is a numerical fixed-point diagnostic."""
    x = trace_values[-1]
    residual = abs(model.step(x) - x)
    slope = abs(model.slope_at(x))
    return x, residual, slope, (residual < tolerance and slope < 1.0)


def max_symmetry_error(g, c, samples=201):
    # Verify C(Tx) == T(G(x)) on a dense grid in [-1, 1].
    return max(abs(c.step(transform(-1 + 2 * i / (samples - 1)))
                   - transform(g.step(-1 + 2 * i / (samples - 1))))
               for i in range(samples))


def check_interval_invariance(model, bound, samples=1001):
    """Sampling check only; not a rigorous proof of robust invariance."""
    values = [-bound + 2 * bound * i / (samples - 1)
              for i in range(samples)]
    maximum = max(abs(model.step(x)) for x in values)
    return maximum <= bound + 1e-12, maximum


def run_case(case, g, c, seeds, steps, writer, summary_writer):
    sym_error = max_symmetry_error(g, c)
    print(f'\n[{case}] GBMC: w={g.weight:.3f}, b={g.bias:.3f}; '
          f'CQSD: w={c.weight:.3f}, b={c.bias:.3f}')
    print(f'  equivariance error max |F_C(Tx)-T(F_G(x))| = {sym_error:.3e}')
    for name, model in [('GBMC', g), ('CQSD', c)]:
        invariant, max_abs = check_interval_invariance(model, 0.5)
        print(f'  {name} candidate K=[-0.5,0.5]: sampled invariant={invariant} '
              f'(max |F(x)|={max_abs:.5f})')
        for seed in seeds:
            values = trace(model, seed, steps)
            x, residual, abs_slope, converged = assess(values, model)
            print(f'  {name:4} x0={seed:+.2f} -> x={x:+.6f} '
                  f'residual={residual:.2e} |slope|={abs_slope:.4f} '
                  f'stable_fixed_point={converged}')
            summary_writer.writerow([case, name, seed, x, residual, abs_slope,
                                     int(converged), sym_error, int(invariant)])
            for i, val in enumerate(values):
                writer.writerow([case, name, seed, i, val])
    print('  Note: a finite-step residual is not proof of attraction or global convergence.')


def main():
    parser = argparse.ArgumentParser(description='Recurrent one-neuron attractor and GBMC/CQSD symmetry toy test')
    parser.add_argument('--w', type=float, default=None, help='Use a single custom GBMC weight')
    parser.add_argument('--bias', type=float, default=0.0, help='GBMC bias for custom test')
    parser.add_argument('--steps', type=int, default=160)
    parser.add_argument('--out', default='attractor_results', help='Output CSV filename prefix')
    parser.add_argument('--legacy', action='store_true', help='Also run original classification demo')
    args = parser.parse_args()
    if args.steps < 1:
        parser.error('--steps must be positive')
    if args.legacy:
        legacy_demo()
    if args.w is not None and not math.isfinite(args.w):
        parser.error('--w must be finite')
    if not math.isfinite(args.bias):
        parser.error('--bias must be finite')
    seeds = [-0.95, -0.55, 0.0, 0.2, 0.9]
    if args.w is None:
        cases = [
            ('contracting', RecurrentNeuron(0.6, 0.0), None),
            ('two_basins', RecurrentNeuron(1.6, 0.0), None),
            ('asymmetric_bias_but_symmetric_pair', RecurrentNeuron(1.4, 0.25), None),
            ('deliberately_broken_symmetry', RecurrentNeuron(1.4, 0.25),
             RecurrentNeuron(1.4, 0.25)),
        ]
    else:
        cases = [('custom', RecurrentNeuron(args.w, args.bias), None)]
    trace_path = Path(f'{args.out}_traces.csv')
    summary_path = Path(f'{args.out}_summary.csv')
    with trace_path.open('w', newline='', encoding='utf-8') as trace_file, \
         summary_path.open('w', newline='', encoding='utf-8') as summary_file:
        writer = csv.writer(trace_file)
        summary_writer = csv.writer(summary_file)
        writer.writerow(['case', 'model', 'initial_x', 'step', 'x'])
        summary_writer.writerow(['case', 'model', 'initial_x', 'final_x',
                                 'fixed_point_residual', 'local_abs_slope',
                                 'numerical_stable_fixed_point',
                                 'symmetry_error', 'K_half_sampled_invariant'])
        for name, g, c in cases:
            run_case(name, g, c if c is not None else paired_model(g),
                     seeds, args.steps, writer, summary_writer)
    print(f'\nSaved {trace_path} and {summary_path}')
    print('Interpretation: these are toy update maps, NOT validated GBMC/CQSD semantics.')
    print('No past-state history is supplied to the updater; x_t itself carries state.')


if __name__ == '__main__':
    main()
