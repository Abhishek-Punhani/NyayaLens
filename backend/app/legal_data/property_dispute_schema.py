from typing import Optional

PROPERTY_DISPUTE_FIELDS = [
    {
        "field_name": "dispossession_recency",
        "legal_anchor": "Section 6 of Specific Relief Act requires filing within 6 months.",
        "why_asked": "Determine if fast-track Section 6 applies.",
        "priority": "critical",
        "gates_which_agent": ["legal_strategy", "drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "property_identification",
        "legal_anchor": "Order 7 Rule 3 CPC requires exact property boundaries/numbers.",
        "why_asked": "Cannot file suit without clear property identity.",
        "priority": "critical",
        "gates_which_agent": ["drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "ownership_chain",
        "legal_anchor": "Title suits require proving better title than defendant.",
        "why_asked": "Establish client's right to the property.",
        "priority": "high",
        "gates_which_agent": ["legal_strategy", "document_review"],
        "ask_before_fields": []
    },
    {
        "field_name": "other_party_identity_and_relationship",
        "legal_anchor": "Necessary party identification; impacts claims like adverse possession.",
        "why_asked": "Know who we are suing and if any relationship complicates it.",
        "priority": "high",
        "gates_which_agent": ["drafting"],
        "ask_before_fields": []
    },
    {
        "field_name": "how_dispossession_happened",
        "legal_anchor": "Forceful vs peaceful dispossession alters relief types.",
        "why_asked": "Understand the event causing the dispute.",
        "priority": "medium",
        "gates_which_agent": ["legal_strategy"],
        "ask_before_fields": ["dispossession_recency"]
    },
    {
        "field_name": "self_help_attempted_by_client",
        "legal_anchor": "Law frowns upon forceful repossession; impacts equity.",
        "why_asked": "Ensure client hasn't weakened their own case.",
        "priority": "medium",
        "gates_which_agent": ["legal_strategy"],
        "ask_before_fields": []
    },
    {
        "field_name": "documents_available",
        "legal_anchor": "Documentary evidence acts as primary proof under Evidence Act.",
        "why_asked": "Know what proofs we actually have.",
        "priority": "high",
        "gates_which_agent": ["document_review"],
        "ask_before_fields": ["ownership_chain"]
    }
]

def get_missing_fields(facts: list) -> list[str]:
    collected_fields = {fact.field for fact in facts}
    return [field["field_name"] for field in PROPERTY_DISPUTE_FIELDS if field["field_name"] not in collected_fields]

def get_next_priority_field(facts: list) -> Optional[str]:
    missing = get_missing_fields(facts)
    if not missing:
        return None
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    missing_schema = [f for f in PROPERTY_DISPUTE_FIELDS if f["field_name"] in missing]
    missing_schema.sort(key=lambda x: priority_order.get(x["priority"], 99))
    return missing_schema[0]["field_name"]
