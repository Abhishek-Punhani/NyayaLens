"""
Motor Accident Case Schema — NyayaLens v3
Fields are ordered by interview phase following the PEACE model + Sarla Verma / Pranay Sethi
MACT compensation framework.

Phase 1 — Accident Mechanics & Liability (§166 MV Act negligence proof)
Phase 2 — Police & Regulatory Audit (FIR/DAR/MLC/Limitation §166(3))
Phase 3 — Multiplier Quantum Profiling (Sarla Verma 2009, Pranay Sethi 2017)
Phase 4 — Defense Audit (contributory negligence, DL validity, helmet, intoxication)
"""
from typing import Optional

MOTOR_ACCIDENT_FIELDS = [
    # ────────────────────────────────────────────────────────────────────────
    # PHASE 1 — Accident Mechanics & Liability
    # ────────────────────────────────────────────────────────────────────────
    {
        "field_name": "accident_datetime",
        "legal_anchor": "MV Act §166(3): 6-month limitation window — exact date is foundational. "
                         "Also anchors every other chronological cross-check (MLC, FIR, treatment).",
        "why_asked": "Anchor the incident in time before anything else can be sequenced.",
        "priority": "critical",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "accident_location",
        "legal_anchor": "Determines territorial jurisdiction of the police station and MACT "
                         "under MV Act §166(2): place of accident, claimant's residence, or insurer's office.",
        "why_asked": "Cannot identify jurisdiction or the FIR/GD entry without a clear location.",
        "priority": "critical",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "how_accident_happened",
        "legal_anchor": "Establishes prima facie rashness/negligence under §166. Road geometry, "
                         "signals, lane discipline, speed, impact points — all determine negligence "
                         "apportionment and rebut contributory negligence defenses.",
        "why_asked": "Core liability narrative — must be established via free chronological TED narration "
                     "before any category-specific facts are drilled.",
        "priority": "critical",
        "phase": "mechanics",
        "ask_before_fields": ["accident_datetime", "accident_location"]
    },
    {
        "field_name": "vehicle_details",
        "legal_anchor": "MV Act requires identification of the vehicle involved (registration, "
                         "insurance) to proceed against the correct insurer/owner under §147-§150.",
        "why_asked": "Establish which vehicle and driver the client was in control of or riding.",
        "priority": "critical",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "other_party_vehicle_and_identity",
        "legal_anchor": "Necessary-party identification for a §166 MACT claim petition. "
                         "Registration number enables VAHAN verification of insurance coverage.",
        "why_asked": "Know who/what the claim or complaint will be filed against.",
        "priority": "high",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "injuries_and_medical_treatment",
        "legal_anchor": "Basis for compensation quantum under §166 (medical expenses, loss of income, "
                         "pain and suffering). Grievous hurt classification under BNS §116 determines "
                         "criminal angle. Medical bills anchor Sarla Verma actual loss calculation.",
        "why_asked": "Determine severity and type of injury — drives both quantum and criminal strategy.",
        "priority": "critical",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "property_or_vehicle_damage",
        "legal_anchor": "Relevant to own-damage insurance claim and quantum of compensation "
                         "claimed for repair/replacement under the policy.",
        "why_asked": "Establish the extent of physical/financial loss to the vehicle or property.",
        "priority": "medium",
        "phase": "mechanics",
        "ask_before_fields": []
    },
    {
        "field_name": "witnesses_available",
        "legal_anchor": "Witness testimony is key evidence under the Bharatiya Sakshya Adhiniyam 2023 "
                         "(BSA) where documentary proof is incomplete or disputed.",
        "why_asked": "Identify corroborating evidence beyond the client's own account. "
                     "A disinterested eyewitness is the most powerful evidence before MACT.",
        "priority": "medium",
        "phase": "mechanics",
        "ask_before_fields": ["how_accident_happened"]
    },
    {
        "field_name": "immediate_actions_taken",
        "legal_anchor": "Delay or omission in reporting/seeking treatment can affect claim "
                         "credibility and any limitation-related explanation required under §166(3).",
        "why_asked": "Understand what the client did right after the accident — police, hospital, insurer.",
        "priority": "medium",
        "phase": "mechanics",
        "ask_before_fields": []
    },

    # ────────────────────────────────────────────────────────────────────────
    # PHASE 2 — Police & Regulatory Audit
    # ────────────────────────────────────────────────────────────────────────
    {
        "field_name": "fir_or_police_report_status",
        "legal_anchor": "FIR/GD/FAR is the primary contemporaneous official record relied on in "
                         "MACT proceedings and any criminal complaint under BNS rash driving provisions. "
                         "FAR (Form I) must be filed by police within 48 hrs; DAR (Form VII) within 90 days "
                         "(SC directions in Gohar Mohammed, 2022).",
        "why_asked": "Know whether police involvement has begun, what the official record says, "
                     "and whether the FIR narrative matches the client's version.",
        "priority": "high",
        "phase": "regulatory",
        "ask_before_fields": ["accident_datetime", "accident_location"]
    },
    {
        "field_name": "insurance_and_documents_available",
        "legal_anchor": "RC, DL, insurance policy, PUC are primary documentary proof. "
                         "Active Third-Party insurance on the date of accident is mandatory for MACT "
                         "proceedings under MV Act §§145-150.",
        "why_asked": "Know what proofs already exist before requesting more — avoids duplicate requests.",
        "priority": "high",
        "phase": "regulatory",
        "ask_before_fields": ["vehicle_details"]
    },
    {
        "field_name": "limitation_check",
        "legal_anchor": "MV Act §166(3) (effective 01.04.2022): claim petition must be filed within "
                         "6 months of the accident. Delay must be explained and condoned by tribunal. "
                         "Critical gate — if expired, legal strategy changes entirely.",
        "why_asked": "Determine if the 6-month window is still open or if delay needs to be explained.",
        "priority": "critical",
        "phase": "regulatory",
        "ask_before_fields": ["accident_datetime"]
    },

    # ────────────────────────────────────────────────────────────────────────
    # PHASE 3 — Multiplier Quantum Profiling (Sarla Verma / Pranay Sethi)
    # ────────────────────────────────────────────────────────────────────────
    {
        "field_name": "victim_age_and_dob",
        "legal_anchor": "Sarla Verma v. DTC (2009): multiplier selection is entirely determined by "
                         "victim age at accident date. Gold standard proof: Class 10 certificate > "
                         "birth certificate > passport/PAN. Aadhaar increasingly rejected by courts.",
        "why_asked": "Every rupee of compensation depends on the multiplier — wrong age = wrong quantum.",
        "priority": "critical",
        "phase": "quantum",
        "ask_before_fields": []
    },
    {
        "field_name": "victim_occupation_and_employer",
        "legal_anchor": "Pranay Sethi (2017): future prospects addition = +50% for permanent salaried "
                         "employee under 40, +40% for self-employed/fixed salary under 40. "
                         "Employment type (Govt/Corporate/Self-employed/Daily wager) determines this.",
        "why_asked": "Determines the correct future-prospects enhancement percentage.",
        "priority": "critical",
        "phase": "quantum",
        "ask_before_fields": []
    },
    {
        "field_name": "victim_income_and_proof",
        "legal_anchor": "Baseline loss-of-dependency calculation. Last 3 years ITR filed before the "
                         "accident date (ITR filed after the accident date cannot be used per V. Subbulakshmi "
                         "ruling). For unorganized workers: State Minimum Wage Notification for skill level.",
        "why_asked": "The single biggest determinant of total compensation quantum.",
        "priority": "critical",
        "phase": "quantum",
        "ask_before_fields": ["victim_occupation_and_employer"]
    },
    {
        "field_name": "dependents_roster",
        "legal_anchor": "Sarla Verma personal expense deduction: 50% for bachelor, 33.3% for 2-3 "
                         "dependents, 25% for 4-6, 20% for more than 6. Magma General Insurance (2018): "
                         "loss of consortium payable to each surviving spouse, each minor child, each parent.",
        "why_asked": "Full dependency census determines the deduction bracket and consortium multiplier.",
        "priority": "critical",
        "phase": "quantum",
        "ask_before_fields": ["victim_income_and_proof"]
    },
    {
        "field_name": "disability_and_functional_impact",
        "legal_anchor": "Raj Kumar v. Ajay Kumar (2011): disability % on medical certificate ≠ "
                         "loss of earning capacity. Must establish functional impact on the victim's "
                         "specific occupation (e.g., 25% finger amputation = 100% loss for a typist).",
        "why_asked": "In injury cases — determines loss of earning capacity (not just physical disability %).",
        "priority": "high",
        "phase": "quantum",
        "ask_before_fields": ["injuries_and_medical_treatment"]
    },

    # ────────────────────────────────────────────────────────────────────────
    # PHASE 4 — Contributory Negligence & Defense Audit
    # ────────────────────────────────────────────────────────────────────────
    {
        "field_name": "contributory_negligence_audit",
        "legal_anchor": "MV Act §129 (helmet), §194B (triple-riding). Insurer's standard defenses: "
                         "invalid DL, intoxication at time of accident (check MLC for 'smell of alcohol'), "
                         "overloading, no valid fitness certificate/PUC. Each reduces or eliminates claim.",
        "why_asked": "Proactively identify and address every statutory defense the insurer will raise "
                     "before the advocate is surprised in tribunal.",
        "priority": "high",
        "phase": "defense_audit",
        "ask_before_fields": ["vehicle_details", "fir_or_police_report_status"]
    },
]


def get_missing_fields(facts: list) -> list[str]:
    """Return schema field names not yet covered by any collected fact."""
    collected_fields = {fact.field for fact in facts}
    return [
        field["field_name"]
        for field in MOTOR_ACCIDENT_FIELDS
        if field["field_name"] not in collected_fields
    ]


def get_missing_fields_by_phase(facts: list) -> dict[str, list[str]]:
    """Return missing fields grouped by interview phase."""
    collected_fields = {fact.field for fact in facts}
    result: dict[str, list[str]] = {}
    for field in MOTOR_ACCIDENT_FIELDS:
        if field["field_name"] not in collected_fields:
            phase = field.get("phase", "unknown")
            result.setdefault(phase, []).append(field["field_name"])
    return result


def get_next_priority_field(facts: list) -> Optional[str]:
    """
    Return the highest-priority missing field, respecting phase ordering.
    Phase order: mechanics → regulatory → quantum → defense_audit
    Within a phase, priority order: critical → high → medium → low
    Also checks ask_before_fields gates.
    """
    collected_fields = {fact.field for fact in facts}
    missing = [f for f in MOTOR_ACCIDENT_FIELDS if f["field_name"] not in collected_fields]
    if not missing:
        return None

    # Filter to only fields whose prerequisites are already collected
    gated = [
        f for f in missing
        if all(pre in collected_fields for pre in f.get("ask_before_fields", []))
    ]
    if not gated:
        # All remaining fields are gated — return first missing from the ungated list
        return missing[0]["field_name"]

    phase_order = {"mechanics": 0, "regulatory": 1, "quantum": 2, "defense_audit": 3}
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    gated.sort(key=lambda x: (
        phase_order.get(x.get("phase", "unknown"), 99),
        priority_order.get(x.get("priority", "low"), 99),
    ))
    return gated[0]["field_name"]


def get_schema_field_info(field_name: str) -> Optional[dict]:
    """Return the full schema dict for a given field name."""
    for f in MOTOR_ACCIDENT_FIELDS:
        if f["field_name"] == field_name:
            return f
    return None