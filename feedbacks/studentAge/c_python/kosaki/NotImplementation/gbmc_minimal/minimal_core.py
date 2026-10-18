"""Minimal candidate narrowing and commitment experiment, no LLM/dependencies."""
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Optional

@dataclass
class MinimalCore:
    universe: FrozenSet[str]
    candidates: FrozenSet[str] = field(init=False)
    committed: Optional[str] = None
    history: list = field(default_factory=list)

    def __post_init__(self):
        if not self.universe:
            raise ValueError('universe must be nonempty')
        self.candidates = self.universe

    def observe(self, possible: Iterable[str]):
        evidence = frozenset(possible)
        if not evidence <= self.universe:
            raise ValueError('unknown candidate in evidence')
        narrowed = self.candidates & evidence
        if not narrowed:
            event = 'CONFLICT'  # no silent rollback or arbitrary decision
        elif self.committed is not None and narrowed != frozenset({self.committed}):
            event = 'CONFLICT'
        else:
            self.candidates = narrowed
            if len(narrowed) == 1 and self.committed is None:
                self.committed = next(iter(narrowed))
                event = 'COMMIT'
            else:
                event = 'HOLD'
        record = {'evidence': sorted(evidence), 'candidates': sorted(self.candidates),
                  'committed': self.committed, 'event': event}
        self.history.append(record)
        return record


def experiment():
    rows = []
    for n in [2,4,8,16,32,64,128,256]:
        labels = [f'C{i:03d}' for i in range(n)]
        target = labels[0]
        # deterministic binary partitions, each answer halves remaining candidates
        state = MinimalCore(frozenset(labels))
        remaining = labels
        decisions = 0
        while len(remaining) > 1:
            half = (len(remaining)+1)//2
            remaining = remaining[:half]
            result = state.observe(remaining)
            decisions += 1
        rows.append({'candidates':n,'binary_observations_to_commit':decisions,
                     'final_event':state.history[-1]['event'] if state.history else 'INITIAL',
                     'committed':state.committed})
    return rows

if __name__ == '__main__':
    import csv, json
    from pathlib import Path
    output = Path(__file__).parent
    results = experiment()
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=results[0].keys()); writer.writeheader(); writer.writerows(results)
    (output/'sample_history.json').write_text(json.dumps(
        MinimalCore(frozenset({'A','B','C','D'})).observe({'A','B'}),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))
