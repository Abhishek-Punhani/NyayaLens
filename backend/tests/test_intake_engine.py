import datetime as dt
import pytest

from app.intake_engine.engine import (
    Extraction,
    MergeError,
    NewPerson,
    Update,
    apply_derivations,
    derive_flags,
    get_field,
    merge,
    new_intake,
    next_question,
    process_turn,
    project_facts,
    project_profile,
    register_failed_turn,
)
from app.intake_engine.questions import CLARIFY_CAP, QUESTIONS


def test_new_intake_initialization():
    intake = new_intake()
    assert intake["emergency"] is False
    assert intake["turns"] == 0
    assert len(intake["people"]) == 0
    
    # First question should be the opening narrative
    q = next_question(intake, lang="hi")
    assert q is not None
    assert q["key"] == "how_accident_happened"
    assert q["stage"] == "narrative"


def test_merge_quote_validation():
    intake = new_intake()
    text = "Mera accident ring road par hua tha."
    
    # Valid quote
    ext = Extraction(updates=[
        Update(
            field="accident_location",
            value="Ring Road",
            status="answered",
            quote="ring road par",
        )
    ])
    out = merge(intake, ext, "m1", text)
    f = get_field(out, "accident_location")
    assert f["status"] == "answered"
    assert f["value"] == "Ring Road"
    
    # Invalid quote (hallucinated string not in text)
    bad_ext = Extraction(updates=[
        Update(
            field="accident_location",
            value="Mumbai Highway",
            status="answered",
            quote="mumbai highway",
        )
    ])
    with pytest.raises(MergeError):
        merge(intake, bad_ext, "m2", text)


def test_unknown_does_not_erase_established_fact():
    intake = new_intake()
    text1 = "Location Connaught Place thi."
    ext1 = Extraction(updates=[
        Update(
            field="accident_location",
            value="Connaught Place",
            status="answered",
            quote="Connaught Place",
        )
    ])
    intake = merge(intake, ext1, "m1", text1)
    assert get_field(intake, "accident_location")["status"] == "answered"
    
    # Client later says "I don't know the exact location"
    text2 = "Mujhe ab exact location nahi pata."
    ext2 = Extraction(updates=[
        Update(
            field="accident_location",
            value=None,
            status="unknown",
            quote="nahi pata",
        )
    ])
    intake2 = merge(intake, ext2, "m2", text2)
    f = get_field(intake2, "accident_location")
    # Must NOT erase established fact!
    assert f["status"] == "answered"
    assert f["value"] == "Connaught Place"


def test_explicit_correction_updates_fact():
    intake = new_intake()
    text1 = "Date thi 2026-08-10."
    ext1 = Extraction(updates=[
        Update(field="accident_datetime", value="2026-08-10", status="answered", quote="2026-08-10")
    ])
    intake = merge(intake, ext1, "m1", text1)
    
    text2 = "Sorry galti se bol diya, actually 2026-08-12 ko hua tha."
    ext2 = Extraction(updates=[
        Update(
            field="accident_datetime",
            value="2026-08-12",
            status="answered",
            quote="2026-08-12",
            correction=True,
        )
    ])
    intake = merge(intake, ext2, "m2", text2)
    f = get_field(intake, "accident_datetime")
    assert f["value"] == "2026-08-12"
    assert f["status"] == "answered"


def test_conflict_detection_without_correction():
    intake = new_intake()
    text1 = "Gadi thi Honda City DL1C1234."
    ext1 = Extraction(updates=[
        Update(field="vehicle_details", value="Honda City DL1C1234", status="answered", quote="Honda City")
    ])
    intake = merge(intake, ext1, "m1", text1)
    
    text2 = "Gadi Creta DL2C5678 thi."
    ext2 = Extraction(updates=[
        Update(field="vehicle_details", value="Creta DL2C5678", status="answered", quote="Creta")
    ])
    intake = merge(intake, ext2, "m2", text2)
    f = get_field(intake, "vehicle_details")
    assert f["status"] == "conflicting"
    assert len(f["history"]) == 2


def test_clarification_cap_advances_question():
    intake = new_intake()
    text = "Bas thodi chot aayi thi."
    ext = Extraction(updates=[
        Update(
            field="how_accident_happened",
            value="Thodi chot",
            status="partial",
            quote="thodi chot",
        )
    ])
    
    asked = {"key": "how_accident_happened", "stage": "narrative"}
    intake = process_turn(intake, ext, "m1", text, asked)
    assert get_field(intake, "how_accident_happened")["clarifications"] == 1
    
    # Asked second time
    intake = process_turn(intake, ext, "m2", text, asked)
    assert get_field(intake, "how_accident_happened")["clarifications"] == 2
    
    # Should move to next question, not get stuck
    nq = next_question(intake)
    assert nq is not None
    assert nq["key"] != "how_accident_happened"


def test_multi_person_scoping():
    intake = new_intake()
    text = "Meri wife Anita bhi sath mein thi aur unke haath mein fracture hua."
    ext = Extraction(
        people=[NewPerson(id="p1", label="Wife Anita", quote="wife Anita")],
        updates=[
            Update(
                field="injuries_and_medical_treatment",
                person_id="p1",
                value="Haath mein fracture",
                status="answered",
                quote="haath mein fracture",
            )
        ]
    )
    intake = merge(intake, ext, "m1", text)
    assert "p1" in intake["people"]
    f = get_field(intake, "injuries_and_medical_treatment", "p1")
    assert f["status"] == "answered"
    assert f["value"] == "Haath mein fracture"


def test_limitation_derivation():
    intake = new_intake()
    text = "Date thi 2026-08-01."
    ext = Extraction(updates=[
        Update(field="accident_datetime", value="2026-08-01", status="answered", quote="2026-08-01")
    ])
    today = dt.date(2026, 9, 1)
    intake = process_turn(intake, ext, "m1", text, {"key": "accident_datetime"}, today=today)
    
    lim = get_field(intake, "limitation_check")
    assert lim["status"] == "answered"
    assert "open" in lim["value"]
    
    # Expired date (> 6 months)
    intake_old = new_intake()
    text_old = "Date thi 2025-01-01."
    ext_old = Extraction(updates=[
        Update(field="accident_datetime", value="2025-01-01", status="answered", quote="2025-01-01")
    ])
    intake_old = process_turn(intake_old, ext_old, "m1", text_old, {"key": "accident_datetime"}, today=today)
    lim_old = get_field(intake_old, "limitation_check")
    assert lim_old["status"] == "answered"
    assert "EXPIRED" in lim_old["value"]


def test_projections_and_flag_derivations():
    intake = new_intake()
    text = "Mera naam Ramesh Kumar hai aur umar 45 saal hai."
    ext = Extraction(updates=[
        Update(field="full_name", value="Ramesh Kumar", status="answered", quote="Ramesh Kumar"),
        Update(field="age", value="45", status="answered", quote="45"),
    ])
    intake = merge(intake, ext, "m1", text)
    
    facts = project_facts(intake)
    fact_fields = {f.field: f.value for f in facts}
    assert fact_fields.get("full_name") == "Ramesh Kumar"
    assert fact_fields.get("age") == "45"
    
    profile = project_profile(intake)
    assert profile.get("full_name") == "Ramesh Kumar"
    assert profile.get("age") == 45
    
    flags = derive_flags(intake, [])
    # No conflict or expired limitation, so no unresolved blocking flags
    blocking = [f for f in flags if not f.resolved and f.blocks_handoff]
    assert len(blocking) == 0
