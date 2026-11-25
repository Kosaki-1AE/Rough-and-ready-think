/- Four Walls: provisional logical formalization, Lean 4 core only.
   The four obligations are supplied by the caller, not derived from logic.
   No axioms or sorry are introduced by this file. -/
namespace FourWalls

inductive Wall where
  | GL | DO | BO | CM
  deriving DecidableEq, Repr

-- A context is a set of possible worlds; a claim is a predicate on worlds.
def Entails {W : Type} (ctx claim : W → Prop) : Prop :=
  ∀ w, ctx w → claim w

def Pass {W : Type} (ctx claim : W → Prop) : Prop := Entails ctx claim
def Blocked {W : Type} (ctx claim : W → Prop) : Prop :=
  Entails ctx (fun w => ¬ claim w)
def Pending {W : Type} (ctx claim : W → Prop) : Prop :=
  ¬ Pass ctx claim ∧ ¬ Blocked ctx claim

def Consistent {W : Type} (ctx : W → Prop) : Prop := ∃ w, ctx w

-- Under a consistent context, a claim cannot both pass and be blocked.
theorem pass_not_blocked {W : Type} {ctx claim : W → Prop}
    (hc : Consistent ctx) (hp : Pass ctx claim) : ¬ Blocked ctx claim := by
  intro hb
  obtain ⟨w, hw⟩ := hc
  exact hb w hw (hp w hw)

-- Logical trichotomy, not a terminating decision algorithm.
theorem trichotomy {W : Type} (ctx claim : W → Prop) :
    Pass ctx claim ∨ Blocked ctx claim ∨ Pending ctx claim := by
  classical
  by_cases hp : Pass ctx claim
  · exact Or.inl hp
  · by_cases hb : Blocked ctx claim
    · exact Or.inr (Or.inl hb)
    · exact Or.inr (Or.inr ⟨hp, hb⟩)

-- Strengthening the context preserves established conclusions.
theorem strengthen {W : Type} {old new claim : W → Prop}
    (h : ∀ w, new w → old w) (hp : Pass old claim) : Pass new claim := by
  intro w hw
  exact hp w (h w hw)

-- Extension of a verified domain: exactly the new region must be justified.
theorem extension_iff {X : Type} (A B P : X → Prop)
    (hAB : ∀ x, A x → B x) :
    (∀ x, B x → P x) ↔
    ((∀ x, A x → P x) ∧ (∀ x, B x → ¬ A x → P x)) := by
  classical
  constructor
  · intro h
    exact ⟨fun x hx => h x (hAB x hx), fun x hx _ => h x hx⟩
  · intro h x hx
    by_cases ha : A x
    · exact h.1 x ha
    · exact h.2 x hx ha

-- GL: applicability; DO: definition; BO: justification; CM: meaning/scope.
-- These are provisional interpretations, not a theorem of exhaustiveness.
structure Audit (W : Type) where
  context : W → Prop
  obligation : Wall → W → Prop

def Ready {W : Type} (a : Audit W) : Prop :=
  Consistent a.context ∧ ∀ k, Pass a.context (a.obligation k)

theorem pending_prevents_ready {W : Type} (a : Audit W) (k : Wall)
    (h : Pending a.context (a.obligation k)) : ¬ Ready a := by
  intro hr
  exact h.1 (hr.2 k)

theorem blocked_prevents_ready {W : Type} (a : Audit W) (k : Wall)
    (h : Blocked a.context (a.obligation k)) : ¬ Ready a := by
  intro hr
  exact pass_not_blocked hr.1 (hr.2 k) h

-- Concrete example: meaning is unresolved; other obligations are true.
def exampleAudit : Audit Bool where
  context := fun _ => True
  obligation := fun k w => match k with
    | .CM => w = true
    | _ => True

theorem example_cm_pending : Pending exampleAudit.context
    (exampleAudit.obligation .CM) := by
  constructor
  · intro h
    have hf : false = true := h false True.intro
    cases hf
  · intro h
    exact h true True.intro rfl

theorem example_not_ready : ¬ Ready exampleAudit :=
  pending_prevents_ready exampleAudit .CM example_cm_pending

end FourWalls
