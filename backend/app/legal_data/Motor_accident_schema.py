"""
Motor Accident Case Schema — NyayaLens v3
Fields are ordered by interview phase following the PEACE model + Sarla Verma / Pranay Sethi
MACT compensation framework.

Phase 1 — Client & Victim Profiling (Sarla Verma 2009, Pranay Sethi 2017, Raj Kumar 2011, BSA §149)
Phase 2 — Accident Mechanics & Liability (§166 MV Act negligence proof)
Phase 3 — Police & Regulatory Audit (FIR/DAR/MLC/Limitation §166(3))
Phase 4 — Multiplier Quantum Profiling (Sarla Verma 2009, Pranay Sethi 2017)
Phase 5 — Defense Audit (contributory negligence, DL validity, helmet, intoxication)
"""
from typing import Optional, Any


class ProfileFieldList(list):
    """
    List of profile field schema dicts supporting both dict iteration and
    'field_name in PHASE_1_PROFILE_FIELDS' string membership testing.
    """
    def __contains__(self, item: Any) -> bool:
        if super().__contains__(item):
            return True
        if isinstance(item, str):
            return any(
                (isinstance(f, dict) and f.get("field_name") == item)
                or f == item
                for f in self
            )
        return False


# ────────────────────────────────────────────────────────────────────────
# PHASE 1 — Client & Victim Profiling (Indian MACT Legal Entities)
# ────────────────────────────────────────────────────────────────────────
PHASE_1_PROFILE_FIELDS = ProfileFieldList([
    {
        "field_name": "full_name",
        "legal_anchor": "CPC Order VII R. 1; MV Act §166(1): Claimant/victim identity for memo of parties; prevents misnomer defense.",
        "why_asked": "Establish party standing, legal identity, and locus standi before the Tribunal.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": [],
    },
    {
        "field_name": "age",
        "legal_anchor": "Sarla Verma v. DTC (2009) para 42: Multiplier selection (18 down to 5) strictly anchored to completed age.",
        "why_asked": "Foundational variable for multiplier-based pecuniary loss computation.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["how_accident_happened"],
    },
    {
        "field_name": "dob",
        "legal_anchor": "Sarla Verma (2009); Juvenile Justice Act: Primary age verification against matriculation/birth certificate.",
        "why_asked": "Corroborate exact date of birth to fix precise multiplier bracket at accident date.",
        "priority": "high",
        "phase": "profile",
        "ask_before_fields": ["age"],
    },
    {
        "field_name": "education_qualification",
        "legal_anchor": "State Minimum Wage notification tiers (unskilled vs graduate) and career progression trajectory.",
        "why_asked": "Determine baseline educational attainment and benchmark earning capacity.",
        "priority": "high",
        "phase": "profile",
        "ask_before_fields": ["how_accident_happened"],
    },
    {
        "field_name": "occupation",
        "legal_anchor": "Pranay Sethi (2017); Sarla Verma (2009): Determines baseline earning capacity and future prospects additions.",
        "why_asked": "Understand professional trade/vocation to evaluate economic multiplicand.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["how_accident_happened"],
    },
    {
        "field_name": "employer_name",
        "legal_anchor": "BSA §63 / IEA §65B; salary certificate proof to summon employer records in MACT.",
        "why_asked": "Verify employer identity, permanence of employment, and wage records.",
        "priority": "high",
        "phase": "profile",
        "ask_before_fields": ["occupation"],
    },
    {
        "field_name": "employment_type",
        "legal_anchor": "Pranay Sethi (2017) para 59.3-59.4: Future prospects bracket (+50%/+30%/+15% salaried vs +40%/+25%/+10% self-employed).",
        "why_asked": "Determine future prospects percentage addition (permanent salaried vs self-employed/fixed wage).",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["occupation"],
    },
    {
        "field_name": "monthly_income",
        "legal_anchor": "MV Act §166/§168; Pranay Sethi (2017): Base multiplicand for dependency and income loss calculations.",
        "why_asked": "The primary financial metric determining overall claim quantum.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["occupation"],
    },
    {
        "field_name": "income_proof_type",
        "legal_anchor": "V. Subbulakshmi v. S. Lakshmi: Pre-accident ITRs (3 consecutive years) or salary slips / minimum wage notification.",
        "why_asked": "Verify documentary evidentiary proof to support claimed income and withstand cross-examination.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["monthly_income"],
    },
    {
        "field_name": "dependents",
        "legal_anchor": "Sarla Verma (2009) para 30-32; Magma General Insurance (2018): Personal living expense deduction & consortium.",
        "why_asked": "Census of financial dependents fixes personal expense deduction fraction (1/2, 1/3, 1/4, 1/5) and consortium claims.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["occupation"],
    },
    {
        "field_name": "driving_license_number",
        "legal_anchor": "MV Act §3, §5, §180, §181: Driver licensing verification on SARATHI database.",
        "why_asked": "Identity and license number to verify endorsement and defeat insurer defenses.",
        "priority": "high",
        "phase": "profile",
        "ask_before_fields": ["vehicle_details"],
    },
    {
        "field_name": "driving_license_validity",
        "legal_anchor": "National Insurance v. Swaran Singh (2004); Pappu v. Vinod Kumar (2018): Valid driving license at accident date.",
        "why_asked": "Audit against fundamental breach of policy condition and pay-and-recover orders.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["vehicle_details"],
    },
    {
        "field_name": "criminal_history",
        "legal_anchor": "BSA §149(3) [IEA §146(3)]: Cross-examination on credit, prior convictions, traffic challans, pending FIRs.",
        "why_asked": "Uncover credibility liabilities and prior challans in private before adverse counsel exploits them.",
        "priority": "medium",
        "phase": "profile",
        "ask_before_fields": ["how_accident_happened"],
    },
    {
        "field_name": "pre_existing_conditions",
        "legal_anchor": "Eggshell skull rule vs defense of pre-existing pathology or non-accident infirmity.",
        "why_asked": "Inoculate against defense claiming injuries or disability were pre-existing.",
        "priority": "medium",
        "phase": "profile",
        "ask_before_fields": ["injuries_and_medical_treatment"],
    },
    {
        "field_name": "disability_percentage",
        "legal_anchor": "Rights of Persons with Disabilities Act; Medical Board Disability Certificate (Form IV).",
        "why_asked": "Baseline anatomical / physical impairment percentage issued by Medical Board.",
        "priority": "high",
        "phase": "profile",
        "ask_before_fields": ["injuries_and_medical_treatment"],
    },
    {
        "field_name": "functional_disability_impact",
        "legal_anchor": "Raj Kumar v. Ajay Kumar (2011) 1 SCC 343: Functional disability vs earning capacity loss in victim's specific trade.",
        "why_asked": "Translate medical disability percentage into real vocational earning capacity loss.",
        "priority": "critical",
        "phase": "profile",
        "ask_before_fields": ["disability_percentage", "occupation"],
    },
])

PHASE_1_PROFILE_FIELD_NAMES = [f["field_name"] for f in PHASE_1_PROFILE_FIELDS]

MOTOR_ACCIDENT_FIELDS = list(PHASE_1_PROFILE_FIELDS) + [
    # ────────────────────────────────────────────────────────────────────────
    # PHASE 2 — Accident Mechanics & Liability
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
]


def get_missing_fields(facts: list, client_profile: Optional[dict] = None) -> list[str]:
    """Return schema field names not yet covered by any collected fact or client_profile."""
    collected_fields = set()
    for fact in facts:
        if hasattr(fact, "field"):
            collected_fields.add(fact.field)
        elif isinstance(fact, dict) and "field" in fact:
            collected_fields.add(fact["field"])

    if client_profile:
        for k, v in client_profile.items():
            if v is not None and v != "" and v != [] and v != {}:
                collected_fields.add(k)

    return [
        field["field_name"]
        for field in MOTOR_ACCIDENT_FIELDS
        if field["field_name"] not in collected_fields
    ]


def get_missing_fields_by_phase(facts: list, client_profile: Optional[dict] = None) -> dict[str, list[str]]:
    """
    Return missing fields grouped by interview phase.
    Prioritizes Phase 1 Profile fields at the very top before mechanics,
    regulatory/statute, quantum, and defense audit fields.
    Checks for profile fields collected in either facts or client_profile.
    """
    collected_fields = set()
    for fact in facts:
        if hasattr(fact, "field"):
            collected_fields.add(fact.field)
        elif isinstance(fact, dict) and "field" in fact:
            collected_fields.add(fact["field"])

    if client_profile:
        for k, v in client_profile.items():
            if v is not None and v != "" and v != [] and v != {}:
                collected_fields.add(k)

    # Phase order ensures the accident event is heard first before investigating personal standing and regulatory details
    phase_order = ["mechanics", "profile", "regulatory", "quantum", "defense_audit"]
    result: dict[str, list[str]] = {p: [] for p in phase_order}

    for field in MOTOR_ACCIDENT_FIELDS:
        fname = field["field_name"]
        if fname not in collected_fields:
            phase = field.get("phase", "unknown")
            result.setdefault(phase, []).append(fname)

    # Filter out empty phases while strictly preserving prioritized phase ordering
    return {p: fields for p, fields in result.items() if fields}


def get_next_priority_field(facts: list, client_profile: Optional[dict] = None) -> Optional[str]:
    """
    Return the highest-priority missing field, respecting natural investigative phase ordering.
    Natural investigative order: mechanics (the accident event) → profile (human impact/standing) → regulatory → quantum → defense_audit
    Within a phase, priority order: critical → high → medium → low
    Also checks ask_before_fields gates.
    """
    collected_fields = set()
    for fact in facts:
        if hasattr(fact, "field"):
            collected_fields.add(fact.field)
        elif isinstance(fact, dict) and "field" in fact:
            collected_fields.add(fact["field"])

    if client_profile:
        for k, v in client_profile.items():
            if v is not None and v != "" and v != [] and v != {}:
                collected_fields.add(k)

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

    phase_order = {
        "mechanics": 0,
        "profile": 1,
        "regulatory": 2,
        "quantum": 3,
        "defense_audit": 4,
    }
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    gated.sort(key=lambda x: (
        phase_order.get(x.get("phase", "unknown"), 99),
        priority_order.get(x.get("priority", "low"), 99),
    ))
    return gated[0]["field_name"]



def get_schema_field_info(field_name: str) -> Optional[dict]:
    """Return the full schema dict for a given field name, dynamically enriched from statute_db."""
    for f in MOTOR_ACCIDENT_FIELDS:
        if f["field_name"] == field_name:
            field_dict = dict(f)
            import re
            mva_match = re.search(r"(?:MV Act\s*)?(?:Section|§)\s*(\d+[A-Za-z]?)", f.get("legal_anchor", ""))
            if mva_match:
                try:
                    from app.legal_data.statute_db import get_section
                    sec_clean = mva_match.group(1)
                    sec_info = get_section("MVA", sec_clean)
                    if sec_info:
                        field_dict["statute_section_title"] = sec_info.get("section_title")
                        field_dict["statute_section_desc"] = sec_info.get("section_desc")
                except Exception:
                    pass
            return field_dict
    return None