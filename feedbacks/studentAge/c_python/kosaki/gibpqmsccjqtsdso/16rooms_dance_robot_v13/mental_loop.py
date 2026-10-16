# -*- coding: utf-8 -*-
"""16Rooms v1.2: observation -> replay -> simulated prediction -> reobserve.

Simulation is a deliberately modest first-order joint tracking model. It is NOT
rigid-body physics, collision checking, robot control, or imagined experience.
No motor commands, no network requests, no external dependencies.
"""
import argparse
import copy
import json
import math
import os
from rooms_v11 import (read_csv, csv_write, get_json, put_json, finite,
                       mapping_config, extract_urdf, learning_memory,
                       nearest_reference, evaluate, FEATURES)


def reference_frames(rows, chunk):
    frames = []
    for row in rows:
        if row.get('chunk_id') != chunk:
            continue
        phase = finite(row.get('phase'))
        if phase is None or not 0 <= phase <= 1:
            continue
        features = {k: finite(row.get(k)) for k in FEATURES}
        features = {k: v for k, v in features.items() if v is not None}
        if features:
            frames.append({'phase': phase, 'features': features})
    return sorted(frames, key=lambda r: r['phase'])


def replay(rows, chunk, phase, n=9):
    """Interpolate the *recorded* reference, never invent missing observations.

    The returned sample carries 'observed' and 'interpolated' flags; interpolation
    is a display/processing convenience, not a new measurement.
    """
    frames = reference_frames(rows, chunk)
    if not frames:
        return [], 'missing_reference'
    if len(frames) < 2:
        return [], 'insufficient_reference_frames'
    if phase < frames[0]['phase'] or phase > frames[-1]['phase']:
        return [], 'phase_outside_observed_range'
    end = frames[-1]['phase']
    times = [phase + (end - phase) * i / float(max(1, n - 1)) for i in range(max(2, n))]
    out = []
    for t in times:
        before = max((f for f in frames if f['phase'] <= t), key=lambda f:f['phase'])
        after = min((f for f in frames if f['phase'] >= t), key=lambda f:f['phase'])
        width = after['phase'] - before['phase']
        alpha = (t-before['phase']) / width if width > 0 else 0.0
        common = set(before['features']) & set(after['features'])
        values = {k: before['features'][k]*(1-alpha) + after['features'][k]*alpha for k in common}
        out.append({'phase': round(t, 6), 'features': values,
                    'interpolated': int(width > 1e-9), 'observed': int(width <= 1e-9)})
    return out, 'ok'


def mapped_targets(features, config, urdf, residuals):
    """Upper-body demo proposals only. Missing calibration or limits -> reject."""
    targets = {}
    for item in config:
        joint = item.get('joint')
        source = item.get('feature')
        if source not in features:
            continue
        if joint not in urdf:
            return {}, 'unknown_joint:' + str(joint)
        model = urdf[joint]
        if model['type'] != 'revolute':
            return {}, 'unsupported_joint_type:' + str(joint)
        neutral = finite(item.get('neutral_rad'))
        scale = finite(item.get('scale_rad_per_deg'))
        if neutral is None or scale is None:
            return {}, 'missing_mapping_calibration'
        bias = finite(residuals.get(joint, {}).get('bias', 0))
        if bias is None:
            return {}, 'invalid_learned_bias'
        target = neutral + scale*(features[source]-90) + bias
        low, high = model['lower'], model['upper']
        if low is None or high is None or not low <= target <= high:
            return {}, 'joint_limit_or_missing_limits:' + str(joint)
        targets[joint] = target
    if not targets:
        return {}, 'no_mapped_features'
    return targets, 'ok'


def simulate(replayed, config, urdf, memory, initial_joints=None, response=0.4):
    """One-step lagged *kinematic approximation*: q_next=q+response*(goal-q).

    response is a demo parameter, not identified physical dynamics. No balance,
    contact, torque, velocity or collision model. No updates to memory.
    """
    if not 0 < response <= 1:
        raise ValueError('response must be in (0,1]')
    state = dict(initial_joints or {})
    predictions = []
    for frame in replayed:
        targets, reason = mapped_targets(frame['features'], config, urdf, memory.get('residuals', {}))
        if reason != 'ok':
            return predictions, reason
        for joint, target in targets.items():
            current = finite(state.get(joint))
            if current is None:
                # Explicit assumption, not a sensor reading.
                current = target
            predicted = current + response*(target-current)
            state[joint] = predicted
            predictions.append({'phase': frame['phase'], 'joint': joint,
                                'target_rad': round(target, 6),
                                'predicted_rad': round(predicted, 6),
                                'predicted_tracking_error_rad': round(abs(target-predicted), 6),
                                'model': 'FIRST_ORDER_APPROXIMATION_NOT_PHYSICS'})
    return predictions, 'ok'


def reobserve_requests(chunk, phase, reason, reference, replayed, observations):
    """Select what to look at again; never claim the camera was actually used."""
    requests = []
    if reason != 'ok':
        requests.append({'chunk_id':chunk, 'phase':phase, 'reason':reason,
                         'request':'REOBSERVE_REFERENCE_AND_BODY'})
    elif not observations:
        requests.append({'chunk_id':chunk, 'phase':phase, 'reason':'missing_current_observation',
                         'request':'REOBSERVE_BODY'})
    else:
        # Disagreement is logged descriptively; no arbitrary quality cutoff.
        ref = nearest_reference(reference, chunk, phase)
        if ref is not None:
            for key in FEATURES:
                a = finite(observations.get(key))
                b = finite(ref.get(key))
                if a is None and b is not None:
                    requests.append({'chunk_id':chunk, 'phase':phase, 'reason':'missing:'+key,
                                     'request':'REOBSERVE_BODY'})
    return requests


def plan_event(row, references, config, urdf, memory, replay_points=9, response=0.4):
    """Evaluate a candidate, replay its teacher, predict motion, request observation.

    No experience counter increments: imagined outcomes are not measurements.
    """
    before = copy.deepcopy(memory)
    # evaluate() mutates chunk metadata even without feedback; isolate it.
    decision, trace, proposals = evaluate(row, references, config, copy.deepcopy(memory), None, urdf)
    chunk = str(row.get('chunk_id') or '')
    phase = finite(row.get('phase'))
    if phase is None:
        phase = 0.0
    replayed, replay_reason = replay(references, chunk, phase, replay_points)
    if decision['status'] != 'PROPOSED':
        reason = decision['reason']
        predicted = []
    elif replay_reason != 'ok':
        reason = replay_reason
        predicted = []
    else:
        predicted, reason = simulate(replayed, config, urdf, memory, response=response)
    requests = reobserve_requests(chunk, phase, reason, references, replayed, row)
    action = 'REOBSERVE' if requests or reason != 'ok' else 'SIMULATED_NOT_EXECUTED'
    assert memory == before, 'mental simulation must not train from imagined feedback'
    summary = {'event_id':row.get('event_id'), 'chunk_id':chunk, 'phase':phase,
               'decision':decision['status'], 'next_action':action,
               'reason':reason, 'replay_frames':len(replayed),
               'prediction_rows':len(predicted), 'reobserve_requests':len(requests),
               'room_visits':len(trace)}
    return summary, replayed, predicted, requests, trace


def run(args):
    references = read_csv(args.reference)
    observations = read_csv(args.input)
    config = mapping_config(args.mapping)
    urdf = extract_urdf(args.urdf)
    memory = learning_memory(args.memory)
    summaries, replays, predictions, requests, traces = [], [], [], [], []
    for row in observations:
        s, r, p, q, t = plan_event(row, references, config, urdf, memory,
                                    args.replay_points, args.response)
        summaries.append(s)
        for item in r:
            replays.append(dict(event_id=s['event_id'], chunk_id=s['chunk_id'],
                                phase=item['phase'], interpolated=item['interpolated'],
                                observed=item['observed'], **item['features']))
        for item in p:
            predictions.append(dict(event_id=s['event_id'], chunk_id=s['chunk_id'], **item))
        for item in q:
            requests.append(dict(event_id=s['event_id'], **item))
        traces += t
    os.makedirs(args.out, exist_ok=True)
    csv_write(os.path.join(args.out, 'mental_loop.csv'), summaries,
              ['event_id','chunk_id','phase','decision','next_action','reason',
               'replay_frames','prediction_rows','reobserve_requests','room_visits'])
    csv_write(os.path.join(args.out, 'refrain.csv'), replays,
              ['event_id','chunk_id','phase','interpolated','observed']+FEATURES)
    csv_write(os.path.join(args.out, 'SIMULATED_NOT_FOR_HARDWARE.csv'), predictions,
              ['event_id','chunk_id','phase','joint','target_rad','predicted_rad',
               'predicted_tracking_error_rad','model'])
    csv_write(os.path.join(args.out, 'reobserve_requests.csv'), requests,
              ['event_id','chunk_id','phase','reason','request'])
    csv_write(os.path.join(args.out, 'room_history.csv'), traces,
              ['event_id','chunk_id','room_id','room','register_hex','stage','reason'])
    # Persist no simulated results into Backrooms. Existing memory stays untouched.
    for s in summaries:
        print('%s %s -> %s (%s)' % (s['event_id'],s['decision'],s['next_action'],s['reason']))
    print('Wrote: ' + os.path.abspath(args.out))


def main():
    p = argparse.ArgumentParser(description='16Rooms v1.2 mental rehearsal; NO MOTOR COMMANDS')
    p.add_argument('--input', required=True)
    p.add_argument('--reference', required=True)
    p.add_argument('--mapping', required=True)
    p.add_argument('--urdf', required=True)
    p.add_argument('--memory', default='output/backrooms.json')
    p.add_argument('--out', default='output/mental')
    p.add_argument('--replay-points', type=int, default=9)
    p.add_argument('--response', type=float, default=0.4)
    run(p.parse_args())

if __name__ == '__main__':
    main()
