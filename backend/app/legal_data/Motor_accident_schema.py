from typing import Optional

MOTOR_ACCIDENT_FIELDS = [
    {
        "field_name": "accident_datetime",
        "legal_anchor": "Limitation Act 1963 / MV Act §166 proviso — claim petitions have no "
                         "strict limitation but delay must be explained; exact date fixes this.",
        "why_asked": "Anchor the incident in time before anything else can be sequenced.",
        "priority": "critical",
        "gates_which_agent": ["legal_strategy", "drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "accident_location",
        "legal_anchor": "Determines territorial jurisdiction of the police station and the "
                         "Motor Accident Claims Tribunal (MACT) under MV Act §166(2).",
        "why_asked": "Cannot identify jurisdiction or the FIR/GD entry without a clear location.",
        "priority": "critical",
        "gates_which_agent": ["legal_strategy", "drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "vehicle_details",
        "legal_anchor": "MV Act requires identification of the vehicle involved (registration, "
                         "insurance) to proceed against the correct insurer/owner.",
        "why_asked": "Establish which vehicle and driver the client was in control of or riding.",
        "priority": "critical",
        "gates_which_agent": ["drafting", "document_review"],
        "ask_before_fields": []
    },
    {
        "field_name": "other_party_vehicle_and_identity",
        "legal_anchor": "Necessary-party identification for a §166 MV Act claim petition or a "
                         "criminal complaint under BNS rash/negligent-driving provisions.",
        "why_asked": "Know who/what the claim or complaint will be filed against.",
        "priority": "high",
        "gates_which_agent": ["drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "how_accident_happened",
        "legal_anchor": "Determines negligence/contributory negligence apportionment under "
                         "MV Act and applicable BNS provisions (rash driving, causing hurt).",
        "why_asked": "Understand the sequence of events causing the accident.",
        "priority": "high",
        "gates_which_agent": ["legal_strategy"],
        "ask_before_fields": ["accident_datetime", "accident_location"]
    },
    {
        "field_name": "injuries_and_medical_treatment",
        "legal_anchor": "Basis for compensation quantum under MV Act §166 (medical expenses, "
                         "loss of income, pain and suffering) and for grievous-hurt classification "
                         "under BNS if criminal proceedings are relevant.",
        "why_asked": "Determine severity and the compensation/criminal angle.",
        "priority": "critical",
        "gates_which_agent": ["legal_strategy", "document_review"],
        "ask_before_fields": []
    },
    {
        "field_name": "property_or_vehicle_damage",
        "legal_anchor": "Relevant to own-damage insurance claim and to quantum of compensation "
                         "claimed for repair/replacement.",
        "why_asked": "Establish the extent of physical/financial loss to the vehicle or property.",
        "priority": "medium",
        "gates_which_agent": ["document_review"],
        "ask_before_fields": []
    },
    {
        "field_name": "fir_or_police_report_status",
        "legal_anchor": "FIR/GD entry is often the primary contemporaneous record relied on in "
                         "MACT proceedings and any criminal complaint.",
        "why_asked": "Know whether police involvement has already begun and what it records.",
        "priority": "high",
        "gates_which_agent": ["legal_strategy", "document_review"],
        "ask_before_fields": ["accident_datetime", "accident_location"]
    },
    {
        "field_name": "witnesses_available",
        "legal_anchor": "Witness testimony is key evidence under the Bharatiya Sakshya "
                         "Adhiniyam where documentary proof is incomplete or disputed.",
        "why_asked": "Identify corroborating evidence beyond the client's own account.",
        "priority": "medium",
        "gates_which_agent": ["legal_strategy"],
        "ask_before_fields": ["how_accident_happened"]
    },
    {
        "field_name": "insurance_and_documents_available",
        "legal_anchor": "RC, DL, insurance policy and PUC are primary documentary proof under "
                         "the Evidence Act and are required to process any insurance claim.",
        "why_asked": "Know what proofs already exist before requesting more.",
        "priority": "high",
        "gates_which_agent": ["document_review"],
        "ask_before_fields": ["vehicle_details"]
    },
    {
        "field_name": "immediate_actions_taken",
        "legal_anchor": "Delay or omission in reporting/seeking treatment can affect claim "
                         "credibility and any limitation-related explanation required.",
        "why_asked": "Understand what the client already did right after the accident.",
        "priority": "medium",
        "gates_which_agent": ["legal_strategy"],
        "ask_before_fields": []
    },
]


def get_missing_fields(facts: list) -> list[str]:
    collected_fields = {fact.field for fact in facts}
    return [field["field_name"] for field in MOTOR_ACCIDENT_FIELDS if field["field_name"] not in collected_fields]


def get_next_priority_field(facts: list) -> Optional[str]:
    missing = get_missing_fields(facts)
    if not missing:
        return None
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    missing_schema = [f for f in MOTOR_ACCIDENT_FIELDS if f["field_name"] in missing]
    missing_schema.sort(key=lambda x: priority_order.get(x["priority"], 99))
    return missing_schema[0]["field_name"]