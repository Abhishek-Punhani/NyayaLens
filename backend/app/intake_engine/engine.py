"""
Intake engine — field state machine, transactional merge, deterministic scheduler,
and projections into the CaseState shapes the rest of the system already consumes
(facts, fuzziness_flags, client_profile, timeline, entity_graph).

Ported from Nyaya-Lens-2.0's engine with three deliberate changes:
  * `extends_existing` lets an elaboration replace a stored value without being
    mistaken for a contradiction (voice answers elaborate constantly).
  * Quote matching tolerates punctuation/spacing drift from ASR, with a negation
    guard so a fuzzy match can never flip "nahi" into "haan".
  * Extra derivations: limitation (§166(3)) is computed from the accident date.

Everything here is pure and offline-testable — no LLM, no I/O.
"""
from __future__ import annotations

import copy
import datetime as dt
import difflib
import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.intake_engine.questions import CLARIFY_CAP, INDEX, QUESTIONS, Question
from app.legal_data.Motor_accident_schema import MOTOR_ACCIDENT_FIELDS
from app.state import ClientProfile, Fact, FuzzinessFlag

TERMINAL = {"answered", "unknown", "declined", "not_applicable"}
LIMITATION_DAYS = 183  # MV Act §166(3): six months
SAFETY_KEY = "__safety__"
_CRITICAL = {f["field_name"] for f in MOTOR_ACCIDENT_FIELDS if f.get("priority") == "critical"}
_PROFILE_KEYS = {
    "full_name", "age", "dob", "education_qualification", "occupation", "employer_name",
    "employment_type", "monthly_income", "income_proof_type", "dependents",
    "driving_license_number", "driving_license_validity", "criminal_history",
    "pre_existing_conditions", "disability_percentage", "functional_disability_impact",
}


class MergeError(ValueError):
    """An extraction was rejected; the case state is left untouched."""


# ───────────────────────────── LLM output schema ─────────────────────────────
Status = Literal["answered", "partial", "unknown", "declined", "not_applicable"]


class Update(BaseModel):
    field: str
    person_id: Optional[str] = None
    value: Optional[str] = None
    status: Status
    quote: str
    correction: bool = False
    extends_existing: bool = False


class NewPerson(BaseModel):
    id: str
    label: str
    quote: str


class Extraction(BaseModel):
    people: list[NewPerson] = Field(default_factory=list)
    updates: list[Update] = Field(default_factory=list)
    emergency: bool = False
    emergency_quote: Optional[str] = None
    emergency_cleared: bool = False
    emergency_cleared_quote: Optional[str] = None


# ───────────────────────────────── state ─────────────────────────────────────
def empty_field() -> dict:
    return {"value": None, "status": "unanswered", "history": [], "clarifications": 0}


def new_intake() -> dict:
    return {
        "fields": {q.key: empty_field() for q in QUESTIONS if not q.person},
        "people": {},
        "emergency": False,
        "turns": 0,
        "raw_notes": [],
    }


def get_field(intake: dict, key: str, person_id: Optional[str] = None) -> dict:
    return intake["people"][person_id]["fields"][key] if person_id else intake["fields"][key]


# ─────────────────────────── normalisation & quotes ──────────────────────────
_TRUE = {"true", "yes", "haan", "han", "ha", "y", "1"}
_FALSE = {"false", "no", "nahin", "nahi", "na", "n", "0"}
_NEGATIONS = {"no", "not", "never", "nahi", "nahin", "nhi", "nai", "na", "mat", "without", "bina"}


def normalize(q: Question, value: Optional[str], status: str):
    if status in {"unknown", "declined", "not_applicable"}:
        return None, status  # tolerate stray text; unresolved statuses never carry a value
    if value is None or not str(value).strip():
        raise MergeError(f"{q.key}: '{status}' requires a non-empty value")
    v = str(value).strip()
    if q.kind == "bool":
        low = v.lower()
        if low in _TRUE:
            return True, status
        if low in _FALSE:
            return False, status
        raise MergeError(f"{q.key} must be true or false")
    if q.kind == "date":
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", v):
            try:
                dt.date.fromisoformat(v[:10])
            except ValueError as exc:
                raise MergeError(f"{q.key}: invalid date {v!r}") from exc
        else:
            status = "partial"
    return v, status


def _tokens(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


def resolve_quote(quote: Optional[str], text: str) -> Optional[str]:
    """Return a span of `text` supporting `quote`, or None. Exact first, then looser."""
    q = re.sub(r"\s+", " ", quote or "").strip()
    t = re.sub(r"\s+", " ", text or "").strip()
    if not q or not t:
        return None
    if q in t:
        return q
    i = t.lower().find(q.lower())
    if i != -1:
        return t[i:i + len(q)]
    # Punctuation-insensitive contiguous word match (ASR/LLM often drop commas, dandas).
    words = t.split(" ")
    wtoks = [" ".join(_tokens(w)) for w in words]
    qtoks = _tokens(q)
    if not qtoks:
        return None
    flat = [(tok, idx) for idx, w in enumerate(wtoks) for tok in (w.split(" ") if w else [])]
    toks = [tok for tok, _ in flat]
    n = len(qtoks)
    for s in range(len(toks) - n + 1):
        if toks[s:s + n] == qtoks:
            first, last = flat[s][1], flat[s + n - 1][1]
            return " ".join(words[first:last + 1])
    # Fuzzy, word-level, only for substantial quotes and never across a negation flip.
    if len(q) < 12:
        return None
    best, best_span = 0.0, None
    for wlen in range(max(1, n - 1), n + 2):
        for s in range(len(toks) - wlen + 1):
            cand = toks[s:s + wlen]
            ratio = difflib.SequenceMatcher(None, " ".join(qtoks), " ".join(cand), autojunk=False).ratio()
            if ratio > best and (set(qtoks) & _NEGATIONS) == (set(cand) & _NEGATIONS):
                best = ratio
                best_span = " ".join(words[flat[s][1]:flat[s + wlen - 1][1] + 1])
    return best_span if best >= 0.9 else None


def _same_person(a: str, b: str) -> bool:
    ta, tb = set(_tokens(a or "")), set(_tokens(b or ""))
    if not ta or not tb:
        return False
    return ta == tb or ta <= tb or tb <= ta


# ───────────────────────────────── merge ─────────────────────────────────────
def merge(intake: dict, result: Extraction, message_id: str, text: str) -> dict:
    """Transactional: raises MergeError and leaves `intake` unchanged on any problem."""
    out = copy.deepcopy(intake)
    remap: dict[str, str] = {}

    for person in result.people:
        if not re.fullmatch(r"p[1-9]\d*", person.id):
            raise MergeError("Person IDs must look like p1, p2, ...")
        existing = next((pid for pid, p in out["people"].items() if _same_person(p["label"], person.label)), None)
        if existing:
            if person.id != existing:
                remap[person.id] = existing
            continue
        if not person.label.strip() or not resolve_quote(person.quote, text):
            raise MergeError("A new person needs a label and a supporting quote from the latest answer")
        target = person.id
        if target in out["people"]:
            nums = [int(n) for pid in out["people"] for n in re.findall(r"\d+", pid)]
            target = f"p{max(nums + [0]) + 1}"
            remap[person.id] = target
        out["people"][target] = {
            "label": person.label.strip(),
            "source": message_id,
            "fields": {q.key: empty_field() for q in QUESTIONS if q.person},
        }

    seen: set[tuple] = set()
    for u in result.updates:
        q = INDEX.get(u.field)
        if q is None:
            raise MergeError(f"Unknown field {u.field!r}")
        pid = remap.get(u.person_id, u.person_id) if u.person_id else None
        if not q.person:
            pid = None  # lenient: a stray person_id on a global field is ignored
        elif pid is None:
            if len(out["people"]) == 1:
                pid = next(iter(out["people"]))
            else:
                raise MergeError(f"{u.field} is person-scoped and needs a valid person_id")
        if pid is not None and pid not in out["people"]:
            raise MergeError(f"Unknown person id {pid!r}")
        if (pid, u.field) in seen:
            raise MergeError(f"Duplicate update for {u.field}")
        seen.add((pid, u.field))

        quote = resolve_quote(u.quote, text)
        if not quote:
            raise MergeError(f"{u.field}: supporting quote must appear in the latest answer")
        value, status = normalize(q, u.value, u.status)

        f = get_field(out, u.field, pid)
        previous = f["status"]
        f["history"].append({
            "value": value, "status": status, "source": message_id, "quote": quote,
            "correction": u.correction, "extends": u.extends_existing,
        })
        if previous in {"answered", "conflicting"} and status in {"unknown", "declined", "not_applicable"} and not u.correction:
            continue  # "don't know" never erases an established fact
        replace = u.correction or u.extends_existing
        if previous == "answered" and f["value"] != value and not replace:
            f["status"] = "conflicting"
        elif previous == "conflicting" and not replace:
            f["status"] = "conflicting"
        else:
            f["value"], f["status"] = value, status
            f["source"], f["quote"] = message_id, quote
            if status in TERMINAL:
                f["clarifications"] = 0

    if result.emergency:
        if not resolve_quote(result.emergency_quote, text):
            raise MergeError("emergency=true needs a supporting quote")
        out["emergency"] = True
    elif result.emergency_cleared and out["emergency"]:
        if not resolve_quote(result.emergency_cleared_quote, text):
            raise MergeError("emergency_cleared=true needs a supporting quote")
        out["emergency"] = False
    return out


# ─────────────────────────────── scheduler ───────────────────────────────────
def applicable(intake: dict, q: Question, pid: Optional[str]) -> bool:
    if q.gate and not q.gate(intake["fields"]):
        return False
    if not q.parent:
        return True
    parent = get_field(intake, q.parent, pid if INDEX[q.parent].person else None)
    if parent["status"] != "answered":
        return False
    return parent["value"] is True if INDEX[q.parent].kind == "bool" else bool(parent["value"])


def _label(intake: dict, pid: Optional[str]) -> str:
    return intake["people"][pid]["label"] if pid else ""


def _render(q: Question, pid: Optional[str], f: dict, intake: dict, lang: str) -> str:
    base = (q.text_hi if lang == "hi" else q.text_en).format(person=_label(intake, pid) or ("unke" if lang == "hi" else "them"))
    if f["status"] == "partial":
        pre = (f"Aapne bataya: {f['value']}. Thoda aur spasht bataiye. "
               if lang == "hi" else f"You said: {f['value']}. Could you be a little more specific? ")
        return pre + base
    if f["status"] == "conflicting":
        cands = list(dict.fromkeys(str(h["value"]) for h in f["history"] if h["status"] in {"answered", "partial"}))
        pre = (f"Mere paas do alag baatein hain: {' / '.join(cands)}. Sahi kaunsi hai? "
               if lang == "hi" else f"I have two different accounts: {' / '.join(cands)}. Which is correct? ")
        return pre + base
    return base


def next_question(intake: dict, lang: str = "hi") -> Optional[dict]:
    """First applicable, unresolved, under-cap question; None when intake is complete."""
    if intake["emergency"]:
        return None
    for q in QUESTIONS:
        for pid in (list(intake["people"]) if q.person else [None]):
            f = get_field(intake, q.key, pid)
            if f["status"] in TERMINAL or not applicable(intake, q, pid):
                continue
            if f["clarifications"] >= CLARIFY_CAP:
                continue  # left unresolved for the lawyer; never trap the client
            return {
                "key": q.key, "person_id": pid, "stage": q.stage,
                "text": _render(q, pid, f, intake, lang), "status": f["status"],
            }
    return None


def remaining_keys(intake: dict) -> list[str]:
    out: list[str] = []
    for q in QUESTIONS:
        for pid in (list(intake["people"]) if q.person else [None]):
            f = get_field(intake, q.key, pid)
            if f["status"] not in TERMINAL and applicable(intake, q, pid) and f["clarifications"] < CLARIFY_CAP:
                if q.key not in out:
                    out.append(q.key)
    return out


def is_complete(intake: dict) -> bool:
    return not intake["emergency"] and next_question(intake) is None


def safety_question(lang: str = "hi") -> dict:
    text = (
        "Pehle ek zaroori baat — kya aap aur baaki sab log abhi surakshit hain? "
        "Agar madad ki zaroorat hai to turant 112 ya 108 par call kijiye."
        if lang == "hi" else
        "First, something important — are you and everyone else safe right now? "
        "If help is needed, please call 112 or 108 immediately."
    )
    return {"key": SAFETY_KEY, "person_id": None, "stage": "engage", "text": text, "status": "unanswered"}


# ───────────────────────────── turn processing ───────────────────────────────
def _bump_clarification(intake: dict, asked: Optional[dict]) -> None:
    if not asked or asked.get("key") in (None, SAFETY_KEY) or asked["key"] not in INDEX:
        return
    pid = asked.get("person_id")
    if pid and pid not in intake["people"]:
        return
    f = get_field(intake, asked["key"], pid if INDEX[asked["key"]].person else None)
    if f["status"] not in TERMINAL:
        f["clarifications"] += 1


def process_turn(intake: dict, result: Extraction, message_id: str, text: str,
                 asked: Optional[dict], today: Optional[dt.date] = None) -> dict:
    out = merge(intake, result, message_id, text)
    out["turns"] += 1
    _bump_clarification(out, asked)
    apply_derivations(out, today or dt.date.today())
    return out


def register_failed_turn(intake: dict, asked: Optional[dict], message_id: str, text: str, reason: str) -> dict:
    """Extraction unusable: keep the raw words for the lawyer and still make progress."""
    out = copy.deepcopy(intake)
    out["turns"] += 1
    out["raw_notes"].append({"id": message_id, "text": text, "reason": reason,
                             "question_key": (asked or {}).get("key")})
    _bump_clarification(out, asked)
    return out


def apply_derivations(intake: dict, today: dt.date) -> None:
    """limitation_check is computed, not asked, whenever the accident date is known."""
    date_f = intake["fields"]["accident_datetime"]
    lim = intake["fields"]["limitation_check"]
    user_answered = lim["status"] != "unanswered" and lim.get("source") != "derived"
    if date_f["status"] != "answered" or user_answered:
        return
    try:
        accident = dt.date.fromisoformat(str(date_f["value"])[:10])
    except ValueError:
        return
    days = (today - accident).days
    if days < 0:
        return
    window = "open" if days <= LIMITATION_DAYS else "EXPIRED — delay must be explained/condoned"
    value = f"Accident on {accident.isoformat()}; {days} days elapsed; MV Act §166(3) six-month window {window}"
    if lim["value"] == value:
        return
    lim.update(value=value, status="answered", source="derived",
               quote="[derived from accident_datetime]", clarifications=0)
    lim["history"].append({"value": value, "status": "answered", "source": "derived",
                           "quote": "[derived from accident_datetime]", "correction": False, "extends": False})


# ─────────────────────────────── projections ─────────────────────────────────
def _fid(key: str, pid: Optional[str]) -> str:
    return f"E:{key}:{pid or 'g'}"


def _display(q: Question, value) -> str:
    if q.kind == "bool" and isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def _iter_fields(intake: dict):
    for q in QUESTIONS:
        for pid in (list(intake["people"]) if q.person else [None]):
            yield q, pid, get_field(intake, q.key, pid)


def project_facts(intake: dict) -> list[Fact]:
    facts: list[Fact] = []
    for q, pid, f in _iter_fields(intake):
        if f["status"] not in {"answered", "partial", "conflicting"} or f["value"] is None:
            continue
        label = _label(intake, pid)
        main_id = _fid(q.key, pid)
        prefix = f"{label}: " if pid else ""
        derived = f.get("source") == "derived"
        alts: list[Fact] = []
        if f["status"] == "conflicting":
            seen = {_display(q, f["value"])}
            for h in f["history"]:
                if h["status"] in {"answered", "partial"} and h["value"] is not None:
                    d = _display(q, h["value"])
                    if d not in seen:
                        seen.add(d)
                        alts.append(Fact(
                            fact_id=f"{main_id}:alt{len(alts) + 1}", field=q.key, value=prefix + d,
                            evidence_type="CLIENT_STATED", source_ref=h.get("source", ""),
                            confidence=0.4, status="unconfirmed", contradicts=[main_id],
                        ))
        facts.append(Fact(
            fact_id=main_id, field=q.key, value=prefix + _display(q, f["value"]),
            evidence_type="INFERENCE" if derived else "CLIENT_STATED",
            source_ref=f.get("source", ""),
            confidence={"answered": 0.9, "partial": 0.5, "conflicting": 0.4}[f["status"]],
            status="unconfirmed", contradicts=[a.fact_id for a in alts],
        ))
        facts.extend(alts)
    for note in intake.get("raw_notes", []):
        facts.append(Fact(
            fact_id=f"E:raw:{note['id']}", field="unparsed_client_statement", value=note["text"],
            evidence_type="CLIENT_STATED", source_ref=note["id"], confidence=0.3,
            status="unconfirmed", contradicts=[],
        ))
    return facts


def project_profile(intake: dict) -> dict:
    raw: dict = {}
    for key in _PROFILE_KEYS:
        f = intake["fields"].get(key)
        if f and f["status"] in {"answered", "partial", "conflicting"} and f["value"] is not None:
            raw[key] = f["value"]
    if "dependents" in raw:
        raw["dependents"] = [{"description": raw["dependents"]}]
    try:
        prof = ClientProfile(**raw).model_dump(exclude_none=True)
    except Exception:
        prof = raw
    return {k: v for k, v in prof.items() if v not in (None, "", [], {})}


def project_timeline(intake: dict) -> list[dict]:
    f = intake["fields"]["accident_datetime"]
    if f["status"] not in {"answered", "partial", "conflicting"} or f["value"] is None:
        return []
    loc = intake["fields"]["accident_location"]
    place = f" at {loc['value']}" if loc["value"] else ""
    events = [{
        "event": f"Accident{place}", "date": str(f["value"]),
        "fact_refs": [_fid("accident_datetime", None)],
        "certainty": "exact" if f["status"] == "answered" else "approximate",
    }]
    try:
        d = dt.date.fromisoformat(str(f["value"])[:10])
        events.append({
            "event": "MV Act §166(3) limitation window ends (approx. 6 months)",
            "date": (d + dt.timedelta(days=LIMITATION_DAYS)).isoformat(),
            "fact_refs": [_fid("limitation_check", None)], "certainty": "derived",
        })
    except ValueError:
        pass
    return events


def project_entity_graph(intake: dict) -> dict:
    nodes = [{"id": pid, "label": p["label"], "type": "person"} for pid, p in intake["people"].items()]
    edges: list[dict] = []
    mine, other = intake["fields"]["vehicle_details"], intake["fields"]["other_party_vehicle_and_identity"]
    if mine["value"]:
        nodes.append({"id": "client_vehicle", "label": str(mine["value"]), "type": "vehicle"})
    if other["value"]:
        nodes.append({"id": "other_vehicle", "label": str(other["value"]), "type": "vehicle"})
        if mine["value"]:
            edges.append({"from": "client_vehicle", "to": "other_vehicle", "relation": "collided_with"})
    return {"nodes": nodes, "edges": edges}


def derive_flags(intake: dict, previous: list[FuzzinessFlag]) -> list[FuzzinessFlag]:
    """Flags are a pure function of field state; vanished flags are kept as resolved."""
    current: dict[str, FuzzinessFlag] = {}

    def add(key, pid, ftype, severity, refs, why, question, blocks=False):
        fid = f"FZ-{key}-{pid or 'g'}-{ftype}"
        current[fid] = FuzzinessFlag(
            flag_id=fid, flag_type=ftype, severity=severity, fact_refs=refs,
            explanation=why, neutral_clarifying_question=question,
            blocks_handoff=blocks, resolved=False,
        )

    for q, pid, f in _iter_fields(intake):
        main = _fid(q.key, pid)
        who = f" for {_label(intake, pid)}" if pid else ""
        st = f["status"]
        if st == "conflicting":
            vals = list(dict.fromkeys(str(h["value"]) for h in f["history"] if h["status"] in {"answered", "partial"}))
            add(q.key, pid, "contradiction", "high", [main],
                f"Client gave differing accounts of {q.key}{who}: {' / '.join(vals)}.",
                f"You mentioned {' and '.join(vals)}. Which one is correct?",
                blocks=f["clarifications"] < CLARIFY_CAP)
        elif st == "partial" and (f["clarifications"] >= CLARIFY_CAP or q.key in _CRITICAL):
            add(q.key, pid, "vague_account", "high" if q.key in _CRITICAL else "medium", [main],
                f"{q.key}{who} is only partially stated: {f['value']!r}.",
                "Could you give the remaining detail?")
        elif st in {"unknown", "declined"} and q.key in _CRITICAL:
            ftype = "quantum_data_gap" if q.key in _PROFILE_KEYS else "vague_account"
            add(q.key, pid, ftype, "high", [main],
                f"Client could not or would not provide {q.key}{who}.",
                "Is there anyone or any record that could confirm this?")
    lim = intake["fields"]["limitation_check"]
    if lim.get("source") == "derived" and "EXPIRED" in str(lim["value"]):
        add("limitation_check", None, "limitation_risk", "high", [_fid("limitation_check", None)],
            str(lim["value"]), "Why was the claim not filed within six months?")
    out = list(current.values())
    for p in previous or []:
        if p.flag_id not in current and not p.resolved:
            out.append(p.model_copy(update={"resolved": True, "blocks_handoff": False}))
        elif p.flag_id not in current:
            out.append(p)
    return out


def current_stage(intake: dict) -> str:
    if intake["emergency"]:
        return "engage"
    nq = next_question(intake)
    return nq["stage"] if nq else "closure"
