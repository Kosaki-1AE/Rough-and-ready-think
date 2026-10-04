```python
"""
Responsibility Room Theory / GBMC Reference Implementation v0.2
===============================================================

STATUS
------
This file is intentionally both:
1) an executable Python reference implementation,
2) a memory capsule for the theory,
3) a falsifiable specification whose invariants can be attacked by tests,
4) a staging point for a future Python library.

It is NOT a claim that the mathematical theory is finished or empirically
validated.  Every formula explicitly marked "provisional" is allowed to
change.  The stable target is the architecture: change, local scope, history,
unresolved consequence, responsibility routing, settlement, and closure.

ORIGIN / RESEARCH PROVENANCE
----------------------------
The project did not begin with the instruction "define responsibility".
Responsibility emerged while repeatedly using AI as an external wall for
self-analysis: lived experience and questions were externalized, rewritten,
challenged, compared across domains, and fed back into the next observation.

A compact description of the process is:

    self-observation
        -> AI wall-bouncing / externalization
        -> re-description
        -> contradiction / counterexample
        -> re-observation
        -> repeated stable structure

Across apparently different topics -- dance feedback, freedom, trust, Git,
rollback, Backrooms, Room boundaries, organizations, worldview -- the same
question kept reappearing:

    "A change happened.  What remains unresolved, who can recover it,
     and what has to happen before the local scope is allowed to close?"

So responsibility is treated here as an emergent attractor of the analysis,
not as an assumption that was inserted at the beginning.

Role split in that process:
    Human: experience, questions, selection, rejection, theory judgment.
    AI:    externalization, recombination, adversarial examples, reflection.
    Theory: what survives repeated human/AI revision and implementation tests.

CORE IDEA
---------
The top-level primitive is CHANGE, not responsibility.

    x_t --action--> x_(t+1)

The theory asks:
- What possibilities were generated?
- What was held in memory/context?
- Which possibility was committed?
- What was predicted?
- What actually happened?
- What deviation appeared?
- Who/what caused the change?
- What consequence remains unresolved?
- Who currently holds recovery/settlement responsibility?
- Who owns the Room, who has authority, and who guarantees the transition?
- Can the system return?
- If it cannot return, can it still settle forward?
- When may the local scope close?
- How do repeated settlements become credit, trust, freedom, attractors,
  depth, and worldview?
- How does direction/orientation affect perceived freedom and responsibility?
- Under what conditions can x_t != x_(t+1) while the system still preserves
  enough history/continuity to count as the "same" actor/system?
- Can an actor recursively observe itself and the Room without replacing
  action with permanent self-monitoring?

CURRENT LAYERING
----------------
[WORLD]
    Worldview / Attractor
        ^
[EMERGENT / DERIVED]
    NoriEntropy / Freedom / SmoothFreedom / Trust / Credit / Depth
        ^
[RESPONSIBILITY]
    Responsibility / Guarantee / Insurance / Return / Handoff / Settlement
    ResponsibilityDirection / ResponsibilityCoherence
        ^
[EVALUATION]
    Deviation(T/S/P) / prediction error epsilon / Coherence
        ^
[DYNAMICS]
    Genesys -> Buffer -> Motion -> Coherence -> Genesys'
        ^
[BOUNDARY]
    Room / History / Context / Orientation
        ^
[BASE]
    State / Change / Actor / Time

GBMC
----
GBMC is the local change loop:

    Genesys -> Buffer -> Motion -> Coherence -> Genesys'

Interpretation:
- Genesys: generate candidates / possible next states.
- Buffer: hold history, context, guarantees and relevant memory.
- Motion: commit one candidate as an actual change.
- Coherence: compare prediction vs observation and integrate/recover the result.

A mechanical analogy that helped generate the theory (NOT a formal identity):
- engine            = self-motion / self-generated activity,
- Buffer            = slack that preserves rotation,
- responsibility    = clutch coupling change to consequences,
- credit            = accumulated friction/reliability,
- meaning           = load,
- real-world impact = drive transmitted to the environment.

ROOM
----
A Room is NOT another GBMC stage.
A Room is a local boundary/responsibility scope around one or more GBMC cycles.

    OPEN ROOM
        GBMC cycles...
    SETTLE
    CLOSE ROOM

A Room can remain open after responsibility is handed off.  Structural
closure and semantic settlement are separate operations.

RESPONSIBILITY
--------------
Working computational definition:

    Responsibility = a live reference from an unresolved change/consequence
                     to the actor(s) currently expected/authorized to recover,
                     integrate, hand off, or settle it.

A shorter intuition is:

    responsibility = pointer to unresolved change

Responsibility is NOT identical to cause, blame, ownership, authority,
guarantee, success, or returnability.

Cause graph:
    actor/action -> change

Responsibility graph:
    unresolved consequence -> current holder(s)

A cause can remain with actor A while responsibility is formally handed off to
actor B.  This separation is a core feature, not an implementation detail.

RESPONSIBILITY KINDS / QUESTIONS
--------------------------------
The current vocabulary distinguishes at least:
- genesis/opening responsibility: who opened the Room / created scope,
- directional responsibility: who changed the option distribution or direction,
- decision responsibility: who committed the actual transition,
- guarantee responsibility: who said the transition was sufficiently safe,
- maintenance responsibility: who preserves context/history/return references,
- recovery responsibility: who can recover from an error or consequence,
- handoff responsibility: who must make transfer explicit and valid,
- closure responsibility: who decides/establishes that settlement is enough.

Not every implementation needs eight independent numbers.  These are semantic
questions that must not be silently collapsed into "who caused it?".

RESPONSIBILITY CONSERVATION (WORKING AXIOM)
-------------------------------------------
For every OPEN obligation:

    sum(responsibility shares) == 1.0

Responsibility may be split, merged, handed off, or settled, but while the
obligation remains OPEN it must not silently disappear.

IMPORTANT:
    returnable == False
DOES NOT imply:
    responsibility == 0

This conservation rule is intentionally attackable.  If a counterexample
shows that a different algebra is required, change the axiom and its tests.

ROLLBACK AND SETTLEMENT
-----------------------
Rollback is only one settlement mechanism:

    Rollback ⊂ Settlement

An irreversible change may still settle through:
- compensation,
- correction,
- acceptance,
- integration,
- formal handoff,
- another forward action.

SUCCESS != SETTLEMENT.
A transition can succeed while leaving unresolved consequences, and a failed
transition can still be fully settled.

CLOSURE
-------
A Room may close only after its unresolved obligations are settled:

    unresolved(room) == empty
        -> room may become SETTLED
        -> room may become CLOSED

"Close" is structural.
"Settle" is semantic/accounting.

BACKROOM
--------
A Backroom is not modeled as a supernatural/special class.  It is a normal
Room whose responsibility-management references are damaged or insufficient.
Examples include:
- owner missing,
- parent/history reference missing,
- responsibility conservation broken,
- responsibility points to unknown actor,
- context missing,
- no valid settlement path.

    Normal Room --reference loss--> Backroom-like state

This is a failure-mode interpretation: "Backroom" is a diagnostic condition.

8-BIT LOCAL INTERFACE
---------------------
The earlier compact interface is deliberately preserved:

    [ Real: 5 bit ][ Virtual: 3 bit ]

Real 5 bit:
    hierarchy(2) + skill_guarantee(1) + insurance(1) + option(1)
Virtual 3 bit:
    local room pointer 0..7

The byte is NOT the entire world model.  It is a fast local/current interface
into the larger graph.

DIRECTIONALITY / ORIENTATION
----------------------------
Some experiences depend on direction, not only position.  The same location
facing forward vs looking back can be a different state:

    z = (x, theta)

This motivated two provisional additions:
1) oriented/boundary state for "smooth freedom",
2) responsibility field/coherence for the felt direction of responsibility.

Responsibility Coherence is not "who is right".  It is a descriptive measure
of alignment among directional signals such as cause, decision, current
settlement responsibility, and explicit expectation.

SMOOTH FREEDOM (PROVISIONAL)
----------------------------
Freedom is not simply the number of choices.  Current intuition:

    Freedom = recoverable exploration range/budget

Smooth Freedom adds continuity through a boundary: possibility space may
contract at entry and expand at exit while direction/orientation remains
continuous.  The implementation below exposes a deliberately provisional
metric combining NoriEntropy continuity and orientation continuity.

META-OBSERVATION
----------------
Responsibility sensitivity is treated as potentially trainable through repeated
questions such as: what changed, whose option space changed, what remains
unresolved, who currently holds it, can we return, and what would close it?
It is never inferred from demographic identity.

An actor may need to alternate between immersion/action and brief recursive
observation:

    Motion <-> Meta

Permanent self-monitoring can paralyze action; therefore meta-observation is
modeled as an explicit operation/event, not as an always-on replacement for
Motion.  A meta-observation can inspect self, Room, unresolved obligations,
responsibility flow, integrity issues, and the current option space.

DERIVED CONCEPTS (PROVISIONAL)
------------------------------
Deviation:
    temporal / spatial / predictive deviation; descriptive, not responsibility.
Credit:
    historical settlement reliability.
Trust:
    extrapolated expectation of settlement in a less-known context; not credit.
Capacity:
    ability to absorb/settle change; kept independent from credit.
Freedom:
    recoverable exploration budget/range.
NoriEntropy:
    diversity of futures that remain meaningfully recoverable.
SmoothFreedom:
    directional/continuous recoverable freedom across a boundary.
Depth:
    accumulated traversed/settled history (operational definition provisional).
Attractor:
    repeatedly reinforced transitions.
Worldview:
    weighted transition structure produced by accumulated history.

APPLICATION HYPOTHESES (NOT YET GENERAL EMPIRICAL CLAIMS)
---------------------------------------------------------
Git:
    branch   = Room opening
    commit   = local responsibility boundary
    history  = Buffer
    diff     = delta-x
    revert   = rollback
    merge    = Coherence/integration
    conflict = predictive/spatial deviation
    blame    = responsibility/cause trace (not moral blame)
    tag      = guarantee marker
    HEAD     = current state

Organizations / Agile:
    organization ~= network that generates, routes, guarantees and settles
                    unresolved changes
    management   ~= responsibility-flow control
    agile        ~= shorter responsibility/settlement cycle through smaller
                    scopes (hypothesis, not a full definition of Agile)
    design target (conceptual, not an equation of law):
        Authority ~= Responsibility ~= SettlementCapacity
    Large mismatch cases are candidates for failure analysis:
        high authority / low settlement capacity,
        high responsibility / low authority.
    Shared responsibility should remain explicit rather than becoming
    undefined "everyone is responsible" language.

AI:
    preferred first experimental domain because agents, logs and controlled
    scenarios allow responsibility-aware vs ordinary multi-agent systems to be
    compared before imposing the model on human organizations.
    Candidate measurements:
        unresolved task count,
        responsibility handoff count,
        settlement time,
        rollback rate,
        exploration range.

Education / entrepreneurship:
    opening a world/scope is only half the learning task; maintaining,
    handing off, reconciling, cleaning up and closing it are also observable.

Dance:
    GBMC, orientation, option generation, meta/immersion switching and
    responsibility/turn-taking may be test domains, but these mappings remain
    hypotheses until operationalized.

RESEARCH / PRODUCT STRATEGY
---------------------------
Near-term artifact:
    a reviewed reference implementation, then possibly a Python library.
The desired loop is:

    definition
        -> invariant
        -> code
        -> counterexample / unit test
        -> revised definition

Unit tests therefore function as executable claims about the theory.  They do
NOT prove that the theory describes reality; they prove that the implementation
obeys the currently chosen formal rules.

DO NOT DO
---------
- Do not force every concept into the 8-bit byte.
- Do not equate cause with responsibility.
- Do not equate responsibility with blame.
- Do not equate success with settlement.
- Do not equate failure with responsibility.
- Do not delete obligations because rollback became impossible.
- Do not infer responsibility sensitivity from sex/gender or other identity.
- Do not turn responsibility visibility into punishment scoring.
- Do not silently present provisional formulas as validated science.
- Do not add concepts without labeling them primitive, operation, invariant,
  derived quantity, observable phenomenon, analogy, or application hypothesis.

THEORY REVIEW TARGETS
---------------------
Before calling the theory "frozen", attack at least these cases:
- Can a non-causal actor legitimately hold 100% recovery responsibility?
- Can responsibility be shared without becoming undefined?
- What happens when no actor can settle an obligation?
- What happens when a holder disappears/dies/leaves the system?
- What makes a handoff valid vs merely forced/claimed?
- Who has authority to declare settlement sufficient?
- Can a Room close if consequences remain outside its boundary?
- Can two different decompositions of the same situation produce contradictory
  responsibility routing?
- Does conservation need a scalar 1.0, a vector, or a richer measure?

VERSION
-------
    THEORY_VERSION = "0.2-reference"

This file is a working formalization, not a final theory and not a paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import json
import math
import time
import uuid


# ============================================================
# 0. HELPERS
# ============================================================

RoomPath = Tuple[int, ...]


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def now() -> float:
    return time.monotonic()


def room_binary(path: RoomPath) -> str:
    if not path:
        return "ε"
    return "/".join(format(code, "03b") for code in path)


def room_octal(path: RoomPath) -> str:
    if not path:
        return "ε"
    return "".join(format(code, "o") for code in path)


THEORY_VERSION = "0.2-reference"
EPS = 1e-12


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def normalize_distribution(values: Mapping[str, float]) -> Dict[str, float]:
    """Normalize non-negative actor weights; empty/zero input stays empty."""
    cleaned = {k: max(0.0, float(v)) for k, v in values.items() if float(v) > 0}
    total = sum(cleaned.values())
    if total <= EPS:
        return {}
    return {k: v / total for k, v in cleaned.items()}


def cosine_similarity_maps(
    a: Mapping[str, float],
    b: Mapping[str, float],
) -> Optional[float]:
    """
    Cosine similarity across named actor dimensions.

    Returns None when either signal has no magnitude.  This matters because
    "no signal" should not be silently interpreted as disagreement.
    """
    keys = set(a) | set(b)
    if not keys:
        return None
    dot = sum(float(a.get(k, 0.0)) * float(b.get(k, 0.0)) for k in keys)
    na = math.sqrt(sum(float(a.get(k, 0.0)) ** 2 for k in keys))
    nb = math.sqrt(sum(float(b.get(k, 0.0)) ** 2 for k in keys))
    if na <= EPS or nb <= EPS:
        return None
    return max(-1.0, min(1.0, dot / (na * nb)))


def angular_alignment(theta_a: float, theta_b: float) -> float:
    """Map heading agreement to [0,1], where same=1 and opposite=0."""
    delta = float(theta_a) - float(theta_b)
    return (1.0 + math.cos(delta)) / 2.0


# ============================================================
# 1. ENUMS
# ============================================================

class RoomStatus(str, Enum):
    OPEN = "OPEN"
    SETTLED = "SETTLED"
    CLOSED = "CLOSED"


class ObligationStatus(str, Enum):
    OPEN = "OPEN"
    SETTLED = "SETTLED"


class ResponsibilityKind(str, Enum):
    GENESIS = "GENESIS"
    DIRECTION = "DIRECTION"
    DECISION = "DECISION"
    GUARANTEE = "GUARANTEE"
    MAINTENANCE = "MAINTENANCE"
    RECOVERY = "RECOVERY"
    HANDOFF = "HANDOFF"
    CLOSURE = "CLOSURE"


class EventKind(str, Enum):
    ROOM_OPEN = "ROOM_OPEN"
    ROOM_SETTLE = "ROOM_SETTLE"
    ROOM_CLOSE = "ROOM_CLOSE"
    ROOM_ROLLBACK = "ROOM_ROLLBACK"

    OBLIGATION_CREATE = "OBLIGATION_CREATE"
    OBLIGATION_HANDOFF = "OBLIGATION_HANDOFF"
    OBLIGATION_SETTLE = "OBLIGATION_SETTLE"

    TRANSITION = "TRANSITION"
    CAUSE_LINK = "CAUSE_LINK"
    RESPONSIBILITY_LINK = "RESPONSIBILITY_LINK"

    RETURN_LOCK = "RETURN_LOCK"

    GENESYS = "GENESYS"
    BUFFER = "BUFFER"
    MOTION = "MOTION"
    COHERENCE = "COHERENCE"

    META_OBSERVE = "META_OBSERVE"
    EXPECTATION_SET = "EXPECTATION_SET"
    BOUNDARY_PASS = "BOUNDARY_PASS"


# ============================================================
# 2. PRIMITIVES
# ============================================================

@dataclass
class Actor:
    """
    Primitive causal/responsibility-capable entity.

    capacity:
        Provisional ability to absorb/settle change.  Independent of credit.
    authority:
        Permission/power to make or ratify decisions.  Independent of cause.
    responsibility_sensitivity:
        Declared/model parameter for sensitivity to responsibility-flow cues.
        It is NOT inferred from identity or demographics.
    meta_awareness:
        Declared/model parameter for ability/willingness to enter Meta mode.
    """
    id: str
    name: str
    capacity: float = 1.0
    authority: float = 1.0
    responsibility_sensitivity: float = 1.0
    meta_awareness: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrientedState:
    """
    Optional state wrapper for position + direction.

    heading is in radians.  position is intentionally generic: 1D, 2D, 3D or
    symbolic coordinates can all be stored as a tuple.
    """
    position: Tuple[float, ...] = field(default_factory=tuple)
    heading: float = 0.0
    label: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoundaryPassage:
    """
    Provisional representation of directional continuity through a boundary.
    """
    approach_heading: float
    entry_heading: float
    exit_heading: float
    forward_heading: float
    freedom_before: float
    freedom_after: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def directional_continuity(self) -> float:
        return (
            angular_alignment(self.approach_heading, self.entry_heading)
            + angular_alignment(self.exit_heading, self.forward_heading)
        ) / 2.0

    @property
    def freedom_continuity(self) -> float:
        scale = max(1.0, abs(self.freedom_before), abs(self.freedom_after))
        return clamp01(1.0 - abs(self.freedom_after - self.freedom_before) / scale)

    @property
    def smooth_freedom(self) -> float:
        # Explicitly provisional: continuity, not raw freedom magnitude.
        return self.directional_continuity * self.freedom_continuity


@dataclass
class Candidate:
    """
    A possible next action/state generated by Genesys.
    """
    id: str
    label: str
    probability: float = 1.0
    recoverability: float = 1.0
    exploration_cost: float = 0.0
    target_heading: Optional[float] = None
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Deviation:
    """
    The three deviation dimensions previously discussed.

    They are descriptive magnitudes, NOT responsibility values.
    """
    temporal: float = 0.0
    spatial: float = 0.0
    predictive: float = 0.0

    @property
    def magnitude(self) -> float:
        return math.sqrt(
            self.temporal ** 2 +
            self.spatial ** 2 +
            self.predictive ** 2
        )


@dataclass
class Obligation:
    """
    An unresolved change that must be settled.

    Responsibility is represented as shares:
        {"actor_A": 0.7, "actor_B": 0.3}

    Invariant while OPEN:
        sum(shares) == 1.0
    """
    id: str
    room: RoomPath
    description: str
    created_by: str

    # Cause and responsibility are intentionally separate.
    causal_actors: List[str] = field(default_factory=list)
    responsibility: Dict[str, float] = field(default_factory=dict)

    guarantee_by: List[str] = field(default_factory=list)
    responsibility_kind: ResponsibilityKind = ResponsibilityKind.RECOVERY
    closure_authority: List[str] = field(default_factory=list)
    status: ObligationStatus = ObligationStatus.OPEN

    created_at: float = field(default_factory=now)
    settled_at: Optional[float] = None
    settled_by: Optional[str] = None
    settlement_note: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def responsibility_sum(self) -> float:
        return sum(self.responsibility.values())

    def is_conserved(self, tol: float = 1e-9) -> bool:
        if self.status == ObligationStatus.SETTLED:
            return True
        return abs(self.responsibility_sum() - 1.0) <= tol


@dataclass
class Transition:
    """
    Actual committed change.

    This records cause and prediction/observation information.
    The obligation created from a transition is a separate object.
    """
    id: str
    room: RoomPath
    actor_id: str

    from_state: Any
    to_state: Any

    prediction: Any = None
    observation: Any = None
    deviation: Deviation = field(default_factory=Deviation)

    candidate_id: Optional[str] = None
    obligation_id: Optional[str] = None
    heading_before: Optional[float] = None
    heading_after: Optional[float] = None

    created_at: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HistoryEntry:
    """
    Traversal history for room entry.

    returnable is a route property, not a responsibility property.
    """
    id: str
    memory_hex: str
    from_room: RoomPath
    to_room: RoomPath
    entered_at: float

    actor_id: str
    obligation_id: Optional[str]

    returnable: bool = True
    locked_reason: Optional[str] = None
    success: bool = False


@dataclass
class Room:
    """
    Responsibility scope.

    A Room may be OPEN while its opener no longer holds responsibility
    if responsibility has been formally handed off.
    """
    path: RoomPath
    parent: Optional[RoomPath]
    via: Optional[int]

    opened_by: Optional[str]
    owner: Optional[str]

    context: Optional[str] = None
    status: RoomStatus = RoomStatus.OPEN
    entry_heading: Optional[float] = None
    exit_heading: Optional[float] = None

    refs: Dict[int, RoomPath] = field(default_factory=dict)
    obligation_ids: List[str] = field(default_factory=list)
    transition_ids: List[str] = field(default_factory=list)

    candidates: Dict[str, Candidate] = field(default_factory=dict)

    opened_at: float = field(default_factory=now)
    settled_at: Optional[float] = None
    closed_at: Optional[float] = None

    # Provisional settlement rule; later this should become formal.
    settlement_rule: str = "all_obligations_settled"

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponsibilityFieldSnapshot:
    """
    Descriptive directional signals over actor dimensions.

    Values are non-negative weights, usually normalized before comparison.
    No moral judgment is encoded here.
    """
    room: RoomPath
    cause: Dict[str, float] = field(default_factory=dict)
    decision: Dict[str, float] = field(default_factory=dict)
    settlement: Dict[str, float] = field(default_factory=dict)
    expectation: Dict[str, float] = field(default_factory=dict)

    def normalized(self) -> "ResponsibilityFieldSnapshot":
        return ResponsibilityFieldSnapshot(
            room=self.room,
            cause=normalize_distribution(self.cause),
            decision=normalize_distribution(self.decision),
            settlement=normalize_distribution(self.settlement),
            expectation=normalize_distribution(self.expectation),
        )

    def pairwise_alignment(self) -> Dict[str, Optional[float]]:
        n = self.normalized()
        return {
            "cause_decision": cosine_similarity_maps(n.cause, n.decision),
            "cause_settlement": cosine_similarity_maps(n.cause, n.settlement),
            "decision_settlement": cosine_similarity_maps(n.decision, n.settlement),
            "settlement_expectation": cosine_similarity_maps(n.settlement, n.expectation),
        }

    def coherence(self) -> Optional[float]:
        vals = [v for v in self.pairwise_alignment().values() if v is not None]
        if not vals:
            return None
        # Signals are non-negative, so cosine should normally be [0,1].
        return sum(vals) / len(vals)


@dataclass
class MetaObservation:
    id: str
    actor_id: str
    room: RoomPath
    room_status: RoomStatus
    unresolved_obligation_ids: List[str]
    responsibility_field: ResponsibilityFieldSnapshot
    integrity_issues: List[str]
    recoverable_candidate_ids: List[str]
    self_capacity: float
    self_authority: float
    notes: Optional[str] = None
    created_at: float = field(default_factory=now)


@dataclass
class Event:
    id: str
    kind: EventKind
    room: RoomPath
    actor_id: Optional[str]
    payload: Dict[str, Any]
    created_at: float = field(default_factory=now)


# ============================================================
# 3. ORIGINAL 5-BIT REAL STATE
# ============================================================

LABELS_RELEASE = [
    "S/CM(Release)",
    "O/GL(Release)",
    "C/DO(Release)",
    "V/BO(Release)",
]

LABELS_OTHER = [
    "Scalar(S)",
    "Off(D)",
    "CM(Absorb)",
    "Set(G)",
    "Hit(B)",
    "GL(Absorb)",
    "Shoot(M)",
    "Pop(C1)",
    "DO(Absorb)",
    "Pop(C2)",
    "Arrow(Q)",
    "BO(Absorb)",
]


def encode_real(
    hierarchy: int,
    skill_guarantee: int,
    insurance: int,
    option: int,
) -> str:
    value = (
        (int(hierarchy) << 3)
        | (int(skill_guarantee) << 2)
        | (int(insurance) << 1)
        | int(option)
    )
    return format(value, "02X")


def decode_real(hex_value: str) -> Dict[str, Any]:
    value = int(hex_value, 16)

    if not 0 <= value <= 0x1F:
        raise ValueError("Real State must be 5bit (0x00..0x1F)")

    hierarchy = (value >> 3) & 0b11
    skill_guarantee = (value >> 2) & 0b1
    insurance = (value >> 1) & 0b1
    option = value & 0b1
    col = insurance * 2 + option
    row = hierarchy

    label = (
        LABELS_RELEASE[row]
        if col == 3
        else LABELS_OTHER[row * 3 + col]
    )

    return {
        "hex": format(value, "02X"),
        "value": value,
        "bits": format(value, "05b"),
        "hierarchy": hierarchy,
        "skill_guarantee": skill_guarantee,
        "insurance": insurance,
        "option": option,
        "row": row,
        "col": col,
        "label": label,
    }


# ============================================================
# 4. 8-BIT LOCAL INTERFACE
# ============================================================

class EightBitInterface:
    """
    Fast local/current interface.

    [Real 5bit][Virtual 3bit]

    It deliberately does NOT store:
    - full responsibility graph,
    - full history,
    - trust,
    - worldview,
    - all Room data.

    Those belong to TheoryWorld.
    """

    ROOM_BRANCH_COUNT = 8

    def __init__(
        self,
        viscosity_threshold: int = 2,
        skill_success_threshold: int = 2,
    ) -> None:
        self.viscosity_threshold = viscosity_threshold
        self.skill_success_threshold = skill_success_threshold

        self.skill_success_count = 0
        self.current_real = encode_real(0, 0, 0, 0)
        self.current_virtual: Optional[int] = None

        self.real_candidates: set[str] = {
            encode_real(0, 0, 0, 0),
            encode_real(0, 0, 0, 1),
        }
        self.virtual_candidates: set[int] = set()

        self._viscosity: Dict[Tuple[int, int, int], float] = defaultdict(float)

    def calc_skill_guarantee(self) -> int:
        return int(self.skill_success_count >= self.skill_success_threshold)

    def mark_skill_success(self) -> None:
        self.skill_success_count += 1
        self.sync_skill_guarantee()

    def sync_skill_guarantee(self) -> None:
        info = decode_real(self.current_real)
        self.current_real = encode_real(
            info["hierarchy"],
            self.calc_skill_guarantee(),
            info["insurance"],
            info["option"],
        )

    def reset_real(self, hierarchy: int = 0) -> None:
        skill = self.calc_skill_guarantee()
        self.current_real = encode_real(hierarchy, skill, 0, 0)
        self.current_virtual = None
        self.virtual_candidates.clear()
        self.real_candidates = {
            encode_real(hierarchy, skill, 0, 0),
            encode_real(hierarchy, skill, 0, 1),
        }

    def set_real_candidates(self, *hex_values: str) -> None:
        candidates = set()
        for value in hex_values:
            value = str(value).upper().zfill(2)
            try:
                decode_real(value)
            except ValueError:
                continue
            candidates.add(value)
        self.real_candidates = candidates

    def set_io_candidates(
        self,
        insurance: int,
        *options: int,
        hierarchy: Optional[int] = None,
    ) -> None:
        if hierarchy is None:
            hierarchy = decode_real(self.current_real)["hierarchy"]

        skill = self.calc_skill_guarantee()
        self.set_real_candidates(
            *[
                encode_real(hierarchy, skill, insurance, option)
                for option in options
            ]
        )

    def set_virtual_candidates(self, *room_codes: int) -> None:
        self.virtual_candidates = {
            int(code)
            for code in room_codes
            if 0 <= int(code) < self.ROOM_BRANCH_COUNT
        }

    def open_all_virtual_candidates(self) -> None:
        self.set_virtual_candidates(*range(self.ROOM_BRANCH_COUNT))

    def select_virtual_pointer(self, room_code: int) -> bool:
        room_code = int(room_code)
        if not 0 <= room_code < self.ROOM_BRANCH_COUNT:
            return False
        if self.virtual_candidates and room_code not in self.virtual_candidates:
            return False
        self.current_virtual = room_code
        return True

    def pointer_is_active(self) -> bool:
        info = decode_real(self.current_real)
        return info["insurance"] == 1 and self.current_virtual is not None

    def effective_virtual(self) -> int:
        return self.current_virtual if self.pointer_is_active() else 0

    def pack_current_byte(self) -> int:
        return (int(self.current_real, 16) << 3) | self.effective_virtual()

    def byte_binary(self) -> str:
        return format(self.pack_current_byte(), "08b")

    def byte_hex(self) -> str:
        return format(self.pack_current_byte(), "02X")

    def observe(
        self,
        hex_value: str,
        *,
        on_absorb: Optional[Callable[[int], None]] = None,
        on_release: Optional[Callable[[int], None]] = None,
    ) -> str:
        """
        Returns one of:
            UNKNOWN
            OUTSIDE_CANDIDATES
            NEED_VIRTUAL_POINTER
            HOLD
            COMMIT
        """
        hex_value = str(hex_value).upper().zfill(2)

        try:
            state = decode_real(hex_value)
        except ValueError:
            return "UNKNOWN"

        if hex_value not in self.real_candidates:
            return "OUTSIDE_CANDIDATES"

        if state["insurance"] == 1 and self.current_virtual is None:
            if not self.virtual_candidates:
                self.open_all_virtual_candidates()
            return "NEED_VIRTUAL_POINTER"

        skill = state["skill_guarantee"]
        row = state["row"]
        col = state["col"]

        key = (skill, row, col)
        self._viscosity[key] += 1

        if self._viscosity[key] < self.viscosity_threshold:
            return "HOLD"

        self.current_real = hex_value
        self._viscosity[key] = 0

        if state["insurance"] == 0:
            self.current_virtual = None

        if state["insurance"] == 1 and state["option"] == 0:
            if on_absorb is not None and self.current_virtual is not None:
                on_absorb(self.current_virtual)

        elif state["insurance"] == 1 and state["option"] == 1:
            if on_release is not None and self.current_virtual is not None:
                on_release(self.current_virtual)

        return "COMMIT"


# ============================================================
# 5. THEORY WORLD
# ============================================================

class TheoryError(RuntimeError):
    pass


class TheoryWorld:
    """
    Main reference engine.

    This class stores the graph that the 8-bit interface points into.
    """

    ROOT: RoomPath = ()

    def __init__(self, return_window: float = 10.0) -> None:
        self.return_window = return_window

        self.actors: Dict[str, Actor] = {}
        self.rooms: Dict[RoomPath, Room] = {
            self.ROOT: Room(
                path=self.ROOT,
                parent=None,
                via=None,
                opened_by=None,
                owner=None,
                context="ROOT",
                status=RoomStatus.OPEN,
            )
        }

        self.current_room: RoomPath = self.ROOT
        self.obligations: Dict[str, Obligation] = {}
        self.transitions: Dict[str, Transition] = {}
        self.events: List[Event] = []
        self.history: List[HistoryEntry] = []
        self.meta_observations: List[MetaObservation] = []
        self.boundary_passages: List[BoundaryPassage] = []

        # Explicit expected responsibility/attention signal per Room.
        # This is separate from actual current responsibility ownership.
        self.room_expectations: Dict[RoomPath, Dict[str, float]] = {}

        # Operational counters for AI/multi-agent experiments.
        self.rollback_attempts: int = 0
        self.rollback_successes: int = 0

        # Weighted graph of actual room-to-room traversals.
        self.room_edge_weights: Counter[Tuple[RoomPath, RoomPath]] = Counter()

        self.byte = EightBitInterface()

    # --------------------------------------------------------
    # Event log
    # --------------------------------------------------------

    def _event(
        self,
        kind: EventKind,
        *,
        actor_id: Optional[str] = None,
        room: Optional[RoomPath] = None,
        **payload: Any,
    ) -> Event:
        event = Event(
            id=uid("evt"),
            kind=kind,
            room=self.current_room if room is None else room,
            actor_id=actor_id,
            payload=payload,
        )
        self.events.append(event)
        return event

    # --------------------------------------------------------
    # Actors
    # --------------------------------------------------------

    def add_actor(
        self,
        name: str,
        *,
        actor_id: Optional[str] = None,
        capacity: float = 1.0,
        authority: float = 1.0,
        responsibility_sensitivity: float = 1.0,
        meta_awareness: float = 1.0,
        **metadata: Any,
    ) -> str:
        actor_id = actor_id or uid("actor")
        if actor_id in self.actors:
            raise TheoryError(f"Actor already exists: {actor_id}")

        self.actors[actor_id] = Actor(
            id=actor_id,
            name=name,
            capacity=float(capacity),
            authority=float(authority),
            responsibility_sensitivity=float(responsibility_sensitivity),
            meta_awareness=float(meta_awareness),
            metadata=metadata,
        )
        return actor_id

    def _require_actor(self, actor_id: str) -> Actor:
        if actor_id not in self.actors:
            raise TheoryError(f"Unknown actor: {actor_id}")
        return self.actors[actor_id]

    # --------------------------------------------------------
    # Room helpers
    # --------------------------------------------------------

    def current(self) -> Room:
        return self.rooms[self.current_room]

    def set_context(self, context: str) -> None:
        self.current().context = context

    def ensure_room(
        self,
        path: RoomPath,
        *,
        parent: Optional[RoomPath] = None,
        via: Optional[int] = None,
        opened_by: Optional[str] = None,
        owner: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Room:
        if path not in self.rooms:
            self.rooms[path] = Room(
                path=path,
                parent=parent,
                via=via,
                opened_by=opened_by,
                owner=owner,
                context=context,
            )
        return self.rooms[path]

    # --------------------------------------------------------
    # Obligations / responsibility
    # --------------------------------------------------------

    def create_obligation(
        self,
        description: str,
        *,
        actor_id: str,
        room: Optional[RoomPath] = None,
        causal_actors: Optional[Sequence[str]] = None,
        guarantee_by: Optional[Sequence[str]] = None,
        responsibility: Optional[Mapping[str, float]] = None,
        responsibility_kind: ResponsibilityKind = ResponsibilityKind.RECOVERY,
        closure_authority: Optional[Sequence[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> str:
        """
        Creating an unresolved consequence creates responsibility.

        Default:
            creator gets 100% responsibility.

        NOTE:
            Cause can contain multiple actors and does not need to equal
            the responsibility holder.
        """
        self._require_actor(actor_id)
        room = self.current_room if room is None else room

        if room not in self.rooms:
            raise TheoryError(f"Unknown room: {room}")

        if causal_actors is None:
            causal_actors = [actor_id]

        for a in causal_actors:
            self._require_actor(a)

        if guarantee_by is None:
            guarantee_by = []
        for a in guarantee_by:
            self._require_actor(a)

        if responsibility is None:
            responsibility = {actor_id: 1.0}

        if closure_authority is None:
            closure_authority = []
        for a in closure_authority:
            self._require_actor(a)

        for a in responsibility:
            self._require_actor(a)

        ob = Obligation(
            id=uid("obl"),
            room=room,
            description=description,
            created_by=actor_id,
            causal_actors=list(causal_actors),
            responsibility=dict(responsibility),
            guarantee_by=list(guarantee_by),
            responsibility_kind=responsibility_kind,
            closure_authority=list(closure_authority),
            metadata=dict(metadata or {}),
        )

        if not ob.is_conserved():
            raise TheoryError(
                "Responsibility conservation violated at creation: "
                f"sum={ob.responsibility_sum():.6f}"
            )

        self.obligations[ob.id] = ob
        self.rooms[room].obligation_ids.append(ob.id)

        self._event(
            EventKind.OBLIGATION_CREATE,
            actor_id=actor_id,
            room=room,
            obligation_id=ob.id,
            description=description,
            responsibility=dict(ob.responsibility),
        )

        for causal_actor in ob.causal_actors:
            self._event(
                EventKind.CAUSE_LINK,
                actor_id=causal_actor,
                room=room,
                obligation_id=ob.id,
            )

        for holder, share in ob.responsibility.items():
            self._event(
                EventKind.RESPONSIBILITY_LINK,
                actor_id=holder,
                room=room,
                obligation_id=ob.id,
                share=share,
            )

        return ob.id

    def handoff(
        self,
        obligation_id: str,
        *,
        from_actor: str,
        to_actor: str,
        share: float = 1.0,
    ) -> None:
        """
        Transfer responsibility without changing cause.

        This is one of the most important operations in the theory.
        """
        self._require_actor(from_actor)
        self._require_actor(to_actor)

        ob = self.obligations[obligation_id]
        if ob.status != ObligationStatus.OPEN:
            raise TheoryError("Cannot handoff a settled obligation")

        share = float(share)
        if share <= 0:
            raise TheoryError("share must be > 0")

        available = ob.responsibility.get(from_actor, 0.0)
        if share > available + 1e-9:
            raise TheoryError(
                f"{from_actor} holds {available}, cannot transfer {share}"
            )

        ob.responsibility[from_actor] = available - share
        if abs(ob.responsibility[from_actor]) <= 1e-12:
            del ob.responsibility[from_actor]

        ob.responsibility[to_actor] = (
            ob.responsibility.get(to_actor, 0.0) + share
        )

        if not ob.is_conserved():
            raise TheoryError("Responsibility conservation violated by handoff")

        self._event(
            EventKind.OBLIGATION_HANDOFF,
            actor_id=from_actor,
            room=ob.room,
            obligation_id=ob.id,
            to_actor=to_actor,
            share=share,
            responsibility=dict(ob.responsibility),
        )

    def settle_obligation(
        self,
        obligation_id: str,
        *,
        actor_id: str,
        note: str,
        allow_nonholder: bool = False,
    ) -> None:
        """
        Settle one unresolved consequence.

        By default, the settling actor must currently hold some responsibility.
        This can later be expanded to explicit settlement authority.
        """
        self._require_actor(actor_id)
        ob = self.obligations[obligation_id]

        if ob.status == ObligationStatus.SETTLED:
            return

        if (
            not allow_nonholder
            and ob.responsibility.get(actor_id, 0.0) <= 0
        ):
            raise TheoryError(
                f"{actor_id} does not currently hold responsibility "
                f"for {obligation_id}"
            )

        ob.status = ObligationStatus.SETTLED
        ob.settled_at = now()
        ob.settled_by = actor_id
        ob.settlement_note = note

        self._event(
            EventKind.OBLIGATION_SETTLE,
            actor_id=actor_id,
            room=ob.room,
            obligation_id=ob.id,
            note=note,
        )

    def unresolved_obligations(
        self,
        room: Optional[RoomPath] = None,
    ) -> List[Obligation]:
        room = self.current_room if room is None else room
        r = self.rooms[room]
        return [
            self.obligations[oid]
            for oid in r.obligation_ids
            if self.obligations[oid].status == ObligationStatus.OPEN
        ]

    # --------------------------------------------------------
    # Room opening / release / absorb
    # --------------------------------------------------------

    def absorb_reference(self, pointer: int) -> RoomPath:
        """
        Internalize/remember a possible external room reference
        without entering it.
        """
        pointer = int(pointer)
        if not 0 <= pointer < 8:
            raise TheoryError("Virtual pointer must be 0..7")

        source = self.current_room
        target = source + (pointer,)

        self.ensure_room(
            target,
            parent=source,
            via=pointer,
            context=None,
        )
        self.rooms[source].refs[pointer] = target
        return target

    def release(
        self,
        pointer: int,
        *,
        actor_id: str,
        context: Optional[str] = None,
        obligation_description: Optional[str] = None,
    ) -> RoomPath:
        """
        Externalize a possibility as a new Room and enter it.

        Opening a Room automatically creates an obligation:
        the opener must eventually settle the Room or formally hand off
        the responsibility.
        """
        self._require_actor(actor_id)

        pointer = int(pointer)
        if not 0 <= pointer < 8:
            raise TheoryError("Virtual pointer must be 0..7")

        source = self.current_room
        target = source + (pointer,)

        room = self.ensure_room(
            target,
            parent=source,
            via=pointer,
            opened_by=actor_id,
            owner=actor_id,
            context=context,
        )

        # If a placeholder was created earlier by absorb_reference,
        # fill in missing semantic ownership.
        if room.opened_by is None:
            room.opened_by = actor_id
        if room.owner is None:
            room.owner = actor_id
        if context is not None:
            room.context = context

        room.status = RoomStatus.OPEN
        self.rooms[source].refs[pointer] = target

        description = (
            obligation_description
            or f"Settle Room R{room_octal(target)} opened from R{room_octal(source)}"
        )

        obligation_id = self.create_obligation(
            description,
            actor_id=actor_id,
            room=target,
            causal_actors=[actor_id],
            responsibility={actor_id: 1.0},
            responsibility_kind=ResponsibilityKind.GENESIS,
            closure_authority=[actor_id],
            metadata={"type": "room_open"},
        )

        entry = HistoryEntry(
            id=uid("hist"),
            memory_hex=self.byte.byte_hex(),
            from_room=source,
            to_room=target,
            entered_at=now(),
            actor_id=actor_id,
            obligation_id=obligation_id,
        )
        self.history.append(entry)

        self.room_edge_weights[(source, target)] += 1
        self.current_room = target

        self._event(
            EventKind.ROOM_OPEN,
            actor_id=actor_id,
            room=target,
            from_room=source,
            to_room=target,
            pointer=pointer,
            obligation_id=obligation_id,
        )

        self.byte.reset_real(hierarchy=0)
        return target

    # --------------------------------------------------------
    # Return / rollback
    # --------------------------------------------------------

    def invalidate_return(self, reason: str) -> None:
        if not self.history:
            return

        last = self.history[-1]
        if last.to_room != self.current_room:
            return

        last.returnable = False
        last.locked_reason = reason

        self._event(
            EventKind.RETURN_LOCK,
            actor_id=last.actor_id,
            room=self.current_room,
            reason=reason,
        )

    def rollback(
        self,
        *,
        actor_id: str,
        settlement_note: str = "Settled by rollback/reversion",
    ) -> RoomPath:
        """
        Rollback is a settlement mechanism, not the definition of settlement.

        Reference behavior:
        - route must still be returnable,
        - current Room must match history,
        - actor must own the Room OR hold responsibility in every unresolved
          obligation,
        - unresolved obligations are settled as reverted,
        - Room becomes SETTLED then CLOSED,
        - current Room moves to parent.

        Later versions may model partial rollback.
        """
        self._require_actor(actor_id)
        self.rollback_attempts += 1

        if not self.history:
            raise TheoryError("Return failed: no history")

        last = self.history[-1]

        if self.current_room != last.to_room:
            raise TheoryError("Return failed: route mismatch")

        elapsed = now() - last.entered_at

        if elapsed > self.return_window:
            last.returnable = False
            last.locked_reason = "timeout"

        if not last.returnable:
            raise TheoryError(
                f"Return permanently locked: {last.locked_reason}"
            )

        room = self.current()

        for ob in self.unresolved_obligations(room.path):
            is_owner = room.owner == actor_id
            is_holder = ob.responsibility.get(actor_id, 0.0) > 0

            if not (is_owner or is_holder):
                raise TheoryError(
                    "Rollback cannot settle all unresolved obligations: "
                    f"{actor_id} lacks responsibility/ownership for {ob.id}"
                )

        # A rollback is treated as one valid form of settlement.
        for ob in list(self.unresolved_obligations(room.path)):
            self.settle_obligation(
                ob.id,
                actor_id=actor_id,
                note=settlement_note,
                allow_nonholder=(room.owner == actor_id),
            )

        self.settle_room(actor_id=actor_id)
        parent = room.parent

        if parent is None:
            raise TheoryError("Root Room cannot rollback")

        self.close_room(actor_id=actor_id, move_to_parent=False)

        self.history.pop()
        self.current_room = parent
        self.byte.reset_real(hierarchy=0)

        self.rollback_successes += 1
        self._event(
            EventKind.ROOM_ROLLBACK,
            actor_id=actor_id,
            room=room.path,
            elapsed=elapsed,
            returned_to=parent,
        )

        return parent

    # --------------------------------------------------------
    # Settlement / closure
    # --------------------------------------------------------

    def settle_room(self, *, actor_id: str) -> None:
        """
        Room settlement is allowed only when no OPEN obligations remain.
        """
        self._require_actor(actor_id)
        room = self.current()

        unresolved = self.unresolved_obligations(room.path)
        if unresolved:
            raise TheoryError(
                "Room cannot settle while obligations remain open: "
                + ", ".join(ob.id for ob in unresolved)
            )

        room.status = RoomStatus.SETTLED
        room.settled_at = now()

        self._event(
            EventKind.ROOM_SETTLE,
            actor_id=actor_id,
            room=room.path,
        )

    def close_room(
        self,
        *,
        actor_id: str,
        move_to_parent: bool = True,
    ) -> None:
        """
        Structural close.

        Success is NOT required.
        Settlement IS required.
        """
        self._require_actor(actor_id)
        room = self.current()

        if room.path == self.ROOT:
            raise TheoryError("Root Room cannot close")

        if room.status != RoomStatus.SETTLED:
            raise TheoryError("Room must be SETTLED before it can CLOSE")

        if self.unresolved_obligations(room.path):
            raise TheoryError("Invariant violation: settled Room has open obligations")

        room.status = RoomStatus.CLOSED
        room.closed_at = now()

        self._event(
            EventKind.ROOM_CLOSE,
            actor_id=actor_id,
            room=room.path,
        )

        if move_to_parent:
            if room.parent is None:
                raise TheoryError("Closed Room has no parent")
            self.current_room = room.parent
            self.byte.reset_real(hierarchy=0)

    # --------------------------------------------------------
    # Success (kept separate from settlement)
    # --------------------------------------------------------

    def mark_success(self) -> None:
        """
        Success is an outcome label, not settlement.

        This only updates the old skill-guarantee mechanism.
        """
        if not self.history:
            raise TheoryError("No history to mark success")

        self.history[-1].success = True
        self.byte.mark_skill_success()

    # --------------------------------------------------------
    # GBMC
    # --------------------------------------------------------

    def genesys(
        self,
        candidates: Sequence[Candidate],
        *,
        actor_id: Optional[str] = None,
    ) -> List[Candidate]:
        """
        Generate/register candidates for the current Room.
        """
        room = self.current()
        room.candidates = {c.id: c for c in candidates}

        self._event(
            EventKind.GENESYS,
            actor_id=actor_id,
            candidates=[asdict(c) for c in candidates],
        )
        return list(candidates)

    def buffer_snapshot(
        self,
        *,
        actor_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Buffer is treated as retained local context/history,
        not a single scalar variable.
        """
        room = self.current()

        snapshot = {
            "room": room_octal(room.path),
            "context": room.context,
            "status": room.status.value,
            "open_obligations": [
                ob.id for ob in self.unresolved_obligations(room.path)
            ],
            "history_depth": len(self.history),
            "local_byte": self.byte.byte_binary(),
        }

        self._event(
            EventKind.BUFFER,
            actor_id=actor_id,
            snapshot=snapshot,
        )
        return snapshot

    @staticmethod
    def calculate_deviation(
        *,
        predicted_time: float = 0.0,
        observed_time: float = 0.0,
        predicted_space: float = 0.0,
        observed_space: float = 0.0,
        predicted_value: float = 0.0,
        observed_value: float = 0.0,
    ) -> Deviation:
        return Deviation(
            temporal=abs(observed_time - predicted_time),
            spatial=abs(observed_space - predicted_space),
            predictive=abs(observed_value - predicted_value),
        )

    def motion(
        self,
        *,
        actor_id: str,
        candidate_id: Optional[str],
        from_state: Any,
        to_state: Any,
        prediction: Any = None,
        observation: Any = None,
        deviation: Optional[Deviation] = None,
        create_obligation_if_deviation_above: Optional[float] = None,
    ) -> str:
        """
        Commit an actual state transition.

        Optional reference behavior:
        if deviation magnitude exceeds a threshold, create an obligation
        assigned to the actor who committed the Motion.
        """
        self._require_actor(actor_id)

        if candidate_id is not None and candidate_id not in self.current().candidates:
            raise TheoryError(f"Unknown candidate in current Room: {candidate_id}")

        deviation = deviation or Deviation()

        transition = Transition(
            id=uid("tr"),
            room=self.current_room,
            actor_id=actor_id,
            from_state=from_state,
            to_state=to_state,
            prediction=prediction,
            observation=observation,
            deviation=deviation,
            candidate_id=candidate_id,
        )

        self.transitions[transition.id] = transition
        self.current().transition_ids.append(transition.id)

        self._event(
            EventKind.MOTION,
            actor_id=actor_id,
            transition_id=transition.id,
            candidate_id=candidate_id,
            from_state=from_state,
            to_state=to_state,
        )

        self._event(
            EventKind.TRANSITION,
            actor_id=actor_id,
            transition_id=transition.id,
            deviation=asdict(deviation),
        )

        if (
            create_obligation_if_deviation_above is not None
            and deviation.magnitude > create_obligation_if_deviation_above
        ):
            obligation_id = self.create_obligation(
                description=(
                    f"Resolve deviation from transition {transition.id} "
                    f"(magnitude={deviation.magnitude:.4f})"
                ),
                actor_id=actor_id,
                causal_actors=[actor_id],
                responsibility={actor_id: 1.0},
                metadata={
                    "type": "deviation",
                    "transition_id": transition.id,
                    "deviation": asdict(deviation),
                },
            )
            transition.obligation_id = obligation_id

        return transition.id

    def coherence(
        self,
        transition_id: str,
        *,
        actor_id: str,
        settlement_note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare/integrate an actual Motion.

        If a transition has an obligation and a settlement note is supplied,
        this reference implementation settles it here.

        Coherence is broader than settlement in the full theory; this is only
        a minimal executable behavior.
        """
        self._require_actor(actor_id)
        tr = self.transitions[transition_id]

        result = {
            "transition_id": transition_id,
            "deviation": asdict(tr.deviation),
            "deviation_magnitude": tr.deviation.magnitude,
            "obligation_id": tr.obligation_id,
            "settled_now": False,
        }

        if tr.obligation_id and settlement_note is not None:
            ob = self.obligations[tr.obligation_id]
            if ob.status == ObligationStatus.OPEN:
                self.settle_obligation(
                    ob.id,
                    actor_id=actor_id,
                    note=settlement_note,
                )
                result["settled_now"] = True

        self._event(
            EventKind.COHERENCE,
            actor_id=actor_id,
            transition_id=transition_id,
            result=result,
        )
        return result

    def gbmc_cycle(
        self,
        *,
        actor_id: str,
        candidates: Sequence[Candidate],
        selected_candidate_id: str,
        from_state: Any,
        to_state: Any,
        deviation: Optional[Deviation] = None,
        prediction: Any = None,
        observation: Any = None,
        deviation_obligation_threshold: Optional[float] = None,
    ) -> str:
        """
        Convenience wrapper:

            Genesys -> Buffer -> Motion -> Coherence

        It does not auto-settle the resulting obligation.
        """
        self.genesys(candidates, actor_id=actor_id)
        self.buffer_snapshot(actor_id=actor_id)

        transition_id = self.motion(
            actor_id=actor_id,
            candidate_id=selected_candidate_id,
            from_state=from_state,
            to_state=to_state,
            prediction=prediction,
            observation=observation,
            deviation=deviation,
            create_obligation_if_deviation_above=deviation_obligation_threshold,
        )

        self.coherence(
            transition_id,
            actor_id=actor_id,
            settlement_note=None,
        )
        return transition_id

    # --------------------------------------------------------
    # Derived quantities
    # --------------------------------------------------------

    def credit(self, actor_id: str) -> float:
        """
        Provisional historical settlement reliability.

        numerator:
            obligations settled by this actor

        denominator:
            obligations this actor has ever been responsible for
            at creation or via handoff, approximated from event log.

        This is intentionally simple and should be replaced by a richer model.
        """
        self._require_actor(actor_id)

        ever_responsible: set[str] = set()
        settled_by_actor: set[str] = set()

        for event in self.events:
            if event.kind == EventKind.RESPONSIBILITY_LINK and event.actor_id == actor_id:
                ever_responsible.add(event.payload["obligation_id"])

            if event.kind == EventKind.OBLIGATION_HANDOFF:
                if event.payload.get("to_actor") == actor_id:
                    ever_responsible.add(event.payload["obligation_id"])

        for ob in self.obligations.values():
            if ob.settled_by == actor_id:
                settled_by_actor.add(ob.id)

        if not ever_responsible:
            return 0.0

        return len(settled_by_actor & ever_responsible) / len(ever_responsible)

    def freedom_budget(
        self,
        actor_id: str,
        *,
        insurance: float = 0.0,
    ) -> float:
        """
        Working hypothesis:

            freedom budget = capacity + external insurance

        Credit is intentionally NOT automatically substituted for capacity.
        """
        actor = self._require_actor(actor_id)
        return max(0.0, actor.capacity + float(insurance))

    def recoverable_candidates(
        self,
        actor_id: str,
        *,
        insurance: float = 0.0,
    ) -> List[Candidate]:
        """
        Candidate is currently considered explorable when:
            exploration_cost <= freedom_budget

        This is a provisional operationalization.
        """
        budget = self.freedom_budget(actor_id, insurance=insurance)
        return [
            c for c in self.current().candidates.values()
            if c.exploration_cost <= budget
        ]

    @staticmethod
    def norientropy(
        candidates: Sequence[Candidate],
    ) -> float:
        """
        Provisional NoriEntropy.

        Weighted probability:
            p*_i ∝ probability_i * recoverability_i

        Then:
            N = H(p*) * mean(recoverability)

        Interpretation:
            diversity of futures that remain meaningfully recoverable.

        This formula is explicitly provisional.
        """
        if not candidates:
            return 0.0

        weighted = [
            max(0.0, c.probability) * max(0.0, c.recoverability)
            for c in candidates
        ]
        total = sum(weighted)

        if total <= 0:
            return 0.0

        p = [w / total for w in weighted if w > 0]
        entropy = -sum(x * math.log2(x) for x in p)

        mean_recoverability = (
            sum(max(0.0, min(1.0, c.recoverability)) for c in candidates)
            / len(candidates)
        )

        return entropy * mean_recoverability

    def attractors(
        self,
        *,
        min_weight: int = 2,
    ) -> Dict[Tuple[RoomPath, RoomPath], int]:
        """
        Repeated room transitions are treated as candidate attractor edges.
        """
        return {
            edge: weight
            for edge, weight in self.room_edge_weights.items()
            if weight >= min_weight
        }

    def worldview(self) -> Dict[str, Any]:
        """
        Minimal weighted transition view.

        This is not yet a full worldview model; it is the graph skeleton.
        """
        return {
            "rooms": {
                room_octal(path): {
                    "status": room.status.value,
                    "context": room.context,
                    "owner": room.owner,
                }
                for path, room in self.rooms.items()
            },
            "edges": [
                {
                    "from": room_octal(src),
                    "to": room_octal(dst),
                    "weight": weight,
                }
                for (src, dst), weight in self.room_edge_weights.items()
            ],
        }

    # --------------------------------------------------------
    # Directionality / responsibility field / meta-observation
    # --------------------------------------------------------

    def set_expectation(
        self,
        expectation: Mapping[str, float],
        *,
        room: Optional[RoomPath] = None,
        actor_id: Optional[str] = None,
    ) -> None:
        """
        Store an explicit expectation signal for a Room.

        Expectation is descriptive: who participants/system currently expect to
        pick up or settle the consequence.  It does not automatically transfer
        actual responsibility.
        """
        room = self.current_room if room is None else room
        if room not in self.rooms:
            raise TheoryError(f"Unknown room: {room}")
        for aid in expectation:
            self._require_actor(aid)
        self.room_expectations[room] = normalize_distribution(expectation)
        self._event(
            EventKind.EXPECTATION_SET,
            actor_id=actor_id,
            room=room,
            expectation=dict(self.room_expectations[room]),
        )

    def responsibility_field(
        self,
        room: Optional[RoomPath] = None,
    ) -> ResponsibilityFieldSnapshot:
        """
        Build a descriptive field from OPEN obligations and transitions.

        cause:
            causal actors of unresolved obligations (equal share per obligation)
        decision:
            actors who committed transitions in this Room (count weighted)
        settlement:
            current responsibility shares for unresolved obligations
        expectation:
            explicit Room expectation if supplied; otherwise empty
        """
        room = self.current_room if room is None else room
        if room not in self.rooms:
            raise TheoryError(f"Unknown room: {room}")

        cause: Dict[str, float] = defaultdict(float)
        decision: Dict[str, float] = defaultdict(float)
        settlement: Dict[str, float] = defaultdict(float)

        for ob in self.unresolved_obligations(room):
            if ob.causal_actors:
                share = 1.0 / len(ob.causal_actors)
                for aid in ob.causal_actors:
                    cause[aid] += share
            for aid, share in ob.responsibility.items():
                settlement[aid] += float(share)

        for tid in self.rooms[room].transition_ids:
            tr = self.transitions.get(tid)
            if tr is not None:
                decision[tr.actor_id] += 1.0

        return ResponsibilityFieldSnapshot(
            room=room,
            cause=dict(cause),
            decision=dict(decision),
            settlement=dict(settlement),
            expectation=dict(self.room_expectations.get(room, {})),
        )

    def responsibility_coherence(
        self,
        room: Optional[RoomPath] = None,
    ) -> Optional[float]:
        """Provisional mean alignment among responsibility-related signals."""
        return self.responsibility_field(room).coherence()

    def meta_observe(
        self,
        actor_id: str,
        *,
        room: Optional[RoomPath] = None,
        insurance: float = 0.0,
        notes: Optional[str] = None,
    ) -> MetaObservation:
        """
        Explicitly enter Meta mode for one observation.

        This does not change responsibility or settle anything.  It records a
        structured snapshot for later comparison with action/Motion.
        """
        actor = self._require_actor(actor_id)
        room = self.current_room if room is None else room
        if room not in self.rooms:
            raise TheoryError(f"Unknown room: {room}")

        old = self.current_room
        try:
            self.current_room = room
            recoverable = [
                c.id for c in self.recoverable_candidates(actor_id, insurance=insurance)
            ]
        finally:
            self.current_room = old

        obs = MetaObservation(
            id=uid("meta"),
            actor_id=actor_id,
            room=room,
            room_status=self.rooms[room].status,
            unresolved_obligation_ids=[ob.id for ob in self.unresolved_obligations(room)],
            responsibility_field=self.responsibility_field(room),
            integrity_issues=self.room_integrity_issues(room),
            recoverable_candidate_ids=recoverable,
            self_capacity=actor.capacity,
            self_authority=actor.authority,
            notes=notes,
        )
        self.meta_observations.append(obs)
        self._event(
            EventKind.META_OBSERVE,
            actor_id=actor_id,
            room=room,
            meta_observation_id=obs.id,
            unresolved=list(obs.unresolved_obligation_ids),
            responsibility_coherence=obs.responsibility_field.coherence(),
        )
        return obs

    def record_boundary_passage(
        self,
        passage: BoundaryPassage,
        *,
        actor_id: Optional[str] = None,
        room: Optional[RoomPath] = None,
    ) -> float:
        room = self.current_room if room is None else room
        self.boundary_passages.append(passage)
        self._event(
            EventKind.BOUNDARY_PASS,
            actor_id=actor_id,
            room=room,
            directional_continuity=passage.directional_continuity,
            freedom_continuity=passage.freedom_continuity,
            smooth_freedom=passage.smooth_freedom,
        )
        return passage.smooth_freedom

    def trust(
        self,
        actor_id: str,
        *,
        context_similarity: float = 0.5,
        prior: float = 0.5,
        prior_strength: float = 2.0,
    ) -> float:
        """
        Provisional extrapolated settlement expectation.

        Credit is observed history.  Trust extrapolates that history into a
        target context using externally supplied context_similarity [0,1].
        A Beta-like prior avoids claiming certainty from tiny histories.

        This is an operational placeholder, not a validated trust equation.
        """
        self._require_actor(actor_id)
        context_similarity = clamp01(context_similarity)
        prior = clamp01(prior)
        prior_strength = max(0.0, float(prior_strength))

        ever: set[str] = set()
        settled: set[str] = set()
        for event in self.events:
            if event.kind == EventKind.RESPONSIBILITY_LINK and event.actor_id == actor_id:
                ever.add(event.payload["obligation_id"])
            elif event.kind == EventKind.OBLIGATION_HANDOFF and event.payload.get("to_actor") == actor_id:
                ever.add(event.payload["obligation_id"])
        for ob in self.obligations.values():
            if ob.settled_by == actor_id and ob.id in ever:
                settled.add(ob.id)

        successes = len(settled)
        trials = len(ever)
        posterior = (
            successes + prior * prior_strength
        ) / max(EPS, trials + prior_strength)

        # Unknown context regresses toward prior; similar context uses history.
        return clamp01(
            context_similarity * posterior
            + (1.0 - context_similarity) * prior
        )

    def depth(self, actor_id: Optional[str] = None) -> float:
        """
        Provisional history/settlement depth.

        World depth counts traversal history + settled obligations.
        Actor depth counts entries made by actor + obligations settled by actor.
        """
        if actor_id is None:
            return float(
                len(self.history)
                + sum(ob.status == ObligationStatus.SETTLED for ob in self.obligations.values())
            )
        self._require_actor(actor_id)
        traversals = sum(h.actor_id == actor_id for h in self.history)
        settlements = sum(ob.settled_by == actor_id for ob in self.obligations.values())
        return float(traversals + settlements)

    @staticmethod
    def smooth_freedom(
        *,
        freedom_before: float,
        freedom_after: float,
        approach_heading: float,
        entry_heading: float,
        exit_heading: float,
        forward_heading: float,
    ) -> float:
        """Convenience wrapper around BoundaryPassage.smooth_freedom."""
        return BoundaryPassage(
            approach_heading=approach_heading,
            entry_heading=entry_heading,
            exit_heading=exit_heading,
            forward_heading=forward_heading,
            freedom_before=freedom_before,
            freedom_after=freedom_after,
        ).smooth_freedom

    def experiment_metrics(self) -> Dict[str, float]:
        """
        Metrics intended for responsibility-aware AI / multi-agent experiments.
        """
        open_obligations = [
            ob for ob in self.obligations.values()
            if ob.status == ObligationStatus.OPEN
        ]
        handoffs = sum(
            e.kind == EventKind.OBLIGATION_HANDOFF for e in self.events
        )
        settled_durations = [
            ob.settled_at - ob.created_at
            for ob in self.obligations.values()
            if ob.settled_at is not None
        ]
        avg_settlement_time = (
            sum(settled_durations) / len(settled_durations)
            if settled_durations else 0.0
        )
        rollback_rate = (
            self.rollback_successes / self.rollback_attempts
            if self.rollback_attempts else 0.0
        )
        exploration_range = sum(
            len(room.candidates) for room in self.rooms.values()
        )
        return {
            "unresolved_task_count": float(len(open_obligations)),
            "responsibility_handoff_count": float(handoffs),
            "average_settlement_time": float(avg_settlement_time),
            "rollback_rate": float(rollback_rate),
            "exploration_range": float(exploration_range),
        }

    # --------------------------------------------------------
    # Integrity / Backroom detection
    # --------------------------------------------------------

    def room_integrity_issues(
        self,
        room_path: Optional[RoomPath] = None,
    ) -> List[str]:
        """
        Return reasons why a Room is "Backroom-like".

        Backroom is treated as loss of responsibility-management references,
        not as a separate type.
        """
        room_path = self.current_room if room_path is None else room_path

        if room_path not in self.rooms:
            return ["room_missing"]

        room = self.rooms[room_path]
        issues: List[str] = []

        if room.path != self.ROOT:
            if room.parent is None or room.parent not in self.rooms:
                issues.append("parent_reference_missing")

            if room.owner is None or room.owner not in self.actors:
                issues.append("owner_missing")

            if room.opened_by is None or room.opened_by not in self.actors:
                issues.append("opener_missing")

            if room.context is None:
                issues.append("context_missing")

        for oid in room.obligation_ids:
            if oid not in self.obligations:
                issues.append(f"obligation_reference_missing:{oid}")
                continue

            ob = self.obligations[oid]

            if not ob.is_conserved():
                issues.append(
                    f"responsibility_not_conserved:{oid}:"
                    f"{ob.responsibility_sum():.6f}"
                )

            for actor_id in ob.responsibility:
                if actor_id not in self.actors:
                    issues.append(
                        f"responsibility_holder_missing:{oid}:{actor_id}"
                    )

            for actor_id in ob.closure_authority:
                if actor_id not in self.actors:
                    issues.append(
                        f"closure_authority_missing:{oid}:{actor_id}"
                    )

        if (
            room.status in {RoomStatus.SETTLED, RoomStatus.CLOSED}
            and self.unresolved_obligations(room.path)
        ):
            issues.append("closed_or_settled_with_open_obligations")

        return issues

    def is_backroom_like(
        self,
        room_path: Optional[RoomPath] = None,
    ) -> bool:
        return bool(self.room_integrity_issues(room_path))

    def assert_invariants(self) -> None:
        """
        Hard integrity checks for development/testing.
        """
        for ob in self.obligations.values():
            if not ob.is_conserved():
                raise AssertionError(
                    f"Responsibility conservation broken: {ob.id}"
                )

        for room in self.rooms.values():
            if room.status in {RoomStatus.SETTLED, RoomStatus.CLOSED}:
                if self.unresolved_obligations(room.path):
                    raise AssertionError(
                        f"{room.path} is {room.status} but has open obligations"
                    )

    # --------------------------------------------------------
    # Status / serialization
    # --------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        info = decode_real(self.byte.current_real)

        return {
            "real_bits": info["bits"],
            "real_hex": self.byte.current_real,
            "hierarchy": info["hierarchy"],
            "skill_guarantee": info["skill_guarantee"],
            "insurance": info["insurance"],
            "option": info["option"],
            "virtual": self.byte.current_virtual,
            "byte_binary": self.byte.byte_binary(),
            "byte_hex": self.byte.byte_hex(),
            "room_octal": room_octal(self.current_room),
            "room_binary": room_binary(self.current_room),
            "context": self.current().context,
            "room_status": self.current().status.value,
            "open_obligations": [
                ob.id for ob in self.unresolved_obligations()
            ],
            "history_depth": len(self.history),
            "backroom_like": self.is_backroom_like(),
            "integrity_issues": self.room_integrity_issues(),
            "responsibility_coherence": self.responsibility_coherence(),
            "meta_observation_count": len(self.meta_observations),
            "theory_version": THEORY_VERSION,
        }

    def to_jsonable(self) -> Dict[str, Any]:
        """
        JSON-friendly snapshot.

        Persistent load/restore is intentionally left for v0.2.
        """
        return {
            "actors": {
                aid: asdict(actor)
                for aid, actor in self.actors.items()
            },
            "rooms": {
                room_binary(path): {
                    **asdict(room),
                    "path": room_binary(room.path),
                    "parent": (
                        None if room.parent is None
                        else room_binary(room.parent)
                    ),
                    "status": room.status.value,
                    "refs": {
                        str(k): room_binary(v)
                        for k, v in room.refs.items()
                    },
                    "candidates": {
                        cid: asdict(c)
                        for cid, c in room.candidates.items()
                    },
                }
                for path, room in self.rooms.items()
            },
            "obligations": {
                oid: {
                    **asdict(ob),
                    "room": room_binary(ob.room),
                    "status": ob.status.value,
                }
                for oid, ob in self.obligations.items()
            },
            "transitions": {
                tid: {
                    **asdict(tr),
                    "room": room_binary(tr.room),
                    "deviation": asdict(tr.deviation),
                }
                for tid, tr in self.transitions.items()
            },
            "events": [
                {
                    **asdict(event),
                    "kind": event.kind.value,
                    "room": room_binary(event.room),
                }
                for event in self.events
            ],
            "meta_observations": [
                {
                    **asdict(obs),
                    "room": room_binary(obs.room),
                    "room_status": obs.room_status.value,
                    "responsibility_field": {
                        **asdict(obs.responsibility_field),
                        "room": room_binary(obs.responsibility_field.room),
                    },
                }
                for obs in self.meta_observations
            ],
            "boundary_passages": [asdict(p) for p in self.boundary_passages],
            "room_expectations": {
                room_binary(path): dict(weights)
                for path, weights in self.room_expectations.items()
            },
            "experiment_metrics": self.experiment_metrics(),
            "status": self.status(),
        }

    def save_snapshot(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                self.to_jsonable(),
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )


# ============================================================
# 6. EXAMPLE / SELF-TEST
# ============================================================

def demo() -> None:
    """
    Comprehensive executable scenario.

    1. A opens a Room.
    2. A runs GBMC and creates a deviation obligation.
    3. Cause stays with A while opening responsibility is handed to B.
    4. An explicit expectation signal is set.
    5. A enters Meta mode and observes the responsibility field.
    6. B settles the opening obligation; A settles prediction deviation.
    7. The Room settles/closes.
    8. Smooth freedom is measured across a directional boundary.
    9. Invariants are checked.
    """
    world = TheoryWorld(return_window=999.0)

    A = world.add_actor(
        "A",
        actor_id="A",
        capacity=1.5,
        authority=1.0,
        responsibility_sensitivity=1.2,
        meta_awareness=1.2,
    )
    B = world.add_actor(
        "B",
        actor_id="B",
        capacity=1.0,
        authority=1.0,
    )

    world.byte.open_all_virtual_candidates()
    world.byte.select_virtual_pointer(3)

    room = world.release(
        3,
        actor_id=A,
        context="Prototype theory discussion / AI wall-bouncing",
    )
    opening_obligation = world.rooms[room].obligation_ids[0]

    candidates = [
        Candidate(
            id="c0",
            label="stay",
            probability=0.4,
            recoverability=1.0,
            exploration_cost=0.2,
            target_heading=0.0,
        ),
        Candidate(
            id="c1",
            label="explore",
            probability=0.6,
            recoverability=0.7,
            exploration_cost=1.2,
            target_heading=0.15,
        ),
    ]

    deviation = Deviation(
        temporal=0.2,
        spatial=0.3,
        predictive=0.9,
    )

    transition_id = world.gbmc_cycle(
        actor_id=A,
        candidates=candidates,
        selected_candidate_id="c1",
        from_state=OrientedState(position=(0.0,), heading=0.0, label="S0"),
        to_state=OrientedState(position=(1.0,), heading=0.15, label="S1"),
        prediction="expected",
        observation="different",
        deviation=deviation,
        deviation_obligation_threshold=0.5,
    )

    deviation_obligation = world.transitions[transition_id].obligation_id
    assert deviation_obligation is not None

    # Cause remains A.  Recovery responsibility for the opening scope moves.
    world.handoff(
        opening_obligation,
        from_actor=A,
        to_actor=B,
        share=1.0,
    )

    world.set_expectation({A: 0.3, B: 0.7}, actor_id=A)
    meta = world.meta_observe(A, notes="Brief Meta pass before settlement")

    world.settle_obligation(
        opening_obligation,
        actor_id=B,
        note="B formally accepted and completed room-opening responsibility.",
    )
    world.settle_obligation(
        deviation_obligation,
        actor_id=A,
        note="A integrated the prediction error into the next model state.",
    )

    world.settle_room(actor_id=A)
    world.close_room(actor_id=A)

    smooth = world.record_boundary_passage(
        BoundaryPassage(
            approach_heading=0.0,
            entry_heading=0.05,
            exit_heading=0.10,
            forward_heading=0.12,
            freedom_before=world.norientropy(candidates),
            freedom_after=world.norientropy(candidates),
            metadata={"intuition": "forward-facing entry/exit continuity"},
        ),
        actor_id=A,
        room=room,
    )

    world.assert_invariants()

    print("=== Responsibility Room Theory v0.2 demo ===")
    print("Theory version:", THEORY_VERSION)
    print("Current room:", room_octal(world.current_room))
    print("Closed child:", room_octal(room))
    print("A credit:", round(world.credit(A), 3))
    print("B credit:", round(world.credit(B), 3))
    print("A trust(similarity=.7):", round(world.trust(A, context_similarity=0.7), 3))
    print("NoriEntropy:", round(world.norientropy(candidates), 4))
    print("SmoothFreedom:", round(smooth, 4))
    print("Meta unresolved:", meta.unresolved_obligation_ids)
    print("Responsibility coherence:", meta.responsibility_field.coherence())
    print("Metrics:", json.dumps(world.experiment_metrics(), ensure_ascii=False))
    print("Worldview:", json.dumps(world.worldview(), ensure_ascii=False))
    print("All invariants: OK")


def run_self_tests() -> None:
    """
    Executable theory checks.

    Passing these tests means the implementation obeys the current axioms.
    It does NOT prove the axioms are true in the real world.
    """
    # 1) Cause and responsibility can diverge without losing history.
    w = TheoryWorld(return_window=999.0)
    A = w.add_actor("A", actor_id="A")
    B = w.add_actor("B", actor_id="B")
    w.byte.select_virtual_pointer(1)
    room = w.release(1, actor_id=A, context="self-test")
    oid = w.rooms[room].obligation_ids[0]
    assert w.obligations[oid].causal_actors == [A]
    w.handoff(oid, from_actor=A, to_actor=B, share=1.0)
    assert w.obligations[oid].causal_actors == [A]
    assert w.obligations[oid].responsibility == {B: 1.0}

    # 2) Return lock does not delete responsibility.
    w.invalidate_return("irreversible external effect")
    assert w.obligations[oid].status == ObligationStatus.OPEN
    assert abs(w.obligations[oid].responsibility_sum() - 1.0) <= 1e-9

    # 3) An open obligation blocks semantic Room settlement.
    blocked = False
    try:
        w.settle_room(actor_id=A)
    except TheoryError:
        blocked = True
    assert blocked

    # 4) Forward settlement is possible even when rollback is locked.
    w.settle_obligation(oid, actor_id=B, note="forward compensation/integration")
    w.settle_room(actor_id=A)
    w.close_room(actor_id=A)
    w.assert_invariants()

    # 5) Meta observation is descriptive and does not mutate obligation state.
    w2 = TheoryWorld(return_window=999.0)
    A2 = w2.add_actor("A2", actor_id="A2")
    w2.byte.select_virtual_pointer(2)
    room2 = w2.release(2, actor_id=A2, context="meta-test")
    oid2 = w2.rooms[room2].obligation_ids[0]
    before = dict(w2.obligations[oid2].responsibility)
    _ = w2.meta_observe(A2)
    after = dict(w2.obligations[oid2].responsibility)
    assert before == after

    # 6) Backroom-like diagnostic fires on deliberate reference damage.
    saved_parent = w2.rooms[room2].parent
    w2.rooms[room2].parent = (7, 7, 7)  # unknown path on purpose
    assert w2.is_backroom_like(room2)
    w2.rooms[room2].parent = saved_parent

    # 7) Smooth freedom is direction-sensitive.
    forward = TheoryWorld.smooth_freedom(
        freedom_before=1.0,
        freedom_after=1.0,
        approach_heading=0.0,
        entry_heading=0.0,
        exit_heading=0.0,
        forward_heading=0.0,
    )
    looking_back = TheoryWorld.smooth_freedom(
        freedom_before=1.0,
        freedom_after=1.0,
        approach_heading=0.0,
        entry_heading=0.0,
        exit_heading=math.pi,
        forward_heading=0.0,
    )
    assert forward > looking_back

    print("Self-tests: ALL PASS")


if __name__ == "__main__":
    run_self_tests()
    demo()
```