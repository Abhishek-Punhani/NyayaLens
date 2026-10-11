"""
Motor-accident (claimant side) question bank.

Design (ported from Nyaya-Lens-2.0): the *code* decides what to ask next; the LLM
only extracts facts. Every key that appears in MOTOR_ACCIDENT_FIELDS is a key here,
so downstream readiness/completeness scoring keeps working. Extra keys (suffix noted
below) exist only to gate follow-ups.

Question text is fixed Hinglish (text_hi) / English (text_en) so the voice agent can
speak it verbatim and the stored transcript always matches what the client heard.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

CLARIFY_CAP = 2  # max asks per field before we move on and leave it for the lawyer


@dataclass(frozen=True)
class Question:
    key: str
    stage: str            # interview_stage label exposed to the UI
    text_hi: str
    text_en: str
    kind: str = "text"    # text | bool | date
    parent: Optional[str] = None
    person: bool = False
    # Extra applicability rule over the *global* fields dict; None means always.
    gate: Optional[Callable[[dict], bool]] = None


def _val(fields: dict, key: str) -> str:
    f = fields.get(key) or {}
    v = f.get("value")
    return str(v).lower() if v is not None else ""


_NON_EARNING = (
    "student", "vidyarthi", "homemaker", "housewife", "grihini", "ghar",
    "retired", "pension", "unemployed", "bekaar", "berozgar", "child", "bachcha",
)


def _earning(fields: dict) -> bool:
    occ = _val(fields, "occupation")
    return bool(occ) and not any(tok in occ for tok in _NON_EARNING)


def _date_unresolved(fields: dict) -> bool:
    return (fields.get("accident_datetime") or {}).get("status") != "answered"


Q = Question
QUESTIONS: list[Question] = [
    # ── Narrative ──────────────────────────────────────────────────────────
    Q("how_accident_happened", "narrative",
      "Aap advocate Sahab se kis mamle ke silsile mein appointment schedule karna chahte hain? Kripya thoda batayein.",
      "What matter would you like the advocate's appointment for? Please tell me what happened."),
    # ── Mechanics / liability ──────────────────────────────────────────────
    Q("accident_datetime", "timeline_liability",
      "Yeh haadsa kis tareekh ko hua tha? Saal ke saath bataiye, aur yaad ho to samay bhi.",
      "On what date did the accident happen? Please include the year, and the time if you remember.", kind="date"),
    Q("accident_location", "timeline_liability",
      "Haadsa kahan hua tha? Shehar, sadak aur aas-paas ka koi landmark bataiye.",
      "Where did it happen? Please give the city, road and a nearby landmark."),
    Q("vehicle_details", "timeline_liability",
      "Haadse ke samay aap kis vehicle mein ya kis tarah sadak par the? Vehicle ka type aur number bataiye.",
      "At the time, what vehicle were you in or how were you on the road? Please give the vehicle type and number."),
    Q("was_driving", "timeline_liability",
      "Kya haadse ke samay aap khud vehicle chala rahe the?",
      "Were you driving the vehicle yourself at the time?", kind="bool"),
    Q("other_party_vehicle_and_identity", "timeline_liability",
      "Doosri taraf kaun sa vehicle tha? Uska number ya driver ki koi jaankari yaad hai?",
      "What was the other vehicle? Do you remember its number or anything about its driver?"),
    Q("people_involved", "timeline_liability",
      "Is haadse mein kaun-kaun ghayal hua ya shaamil tha? Har vyakti ka naam ya rishta bataiye.",
      "Who was injured or involved in the accident? Please give each person's name or relationship."),
    Q("immediate_actions_taken", "timeline_liability",
      "Haadse ke turant baad kya-kya kiya gaya? Jaise police ko bulaya, aspatal le gaye, ya kisi ko khabar ki.",
      "What was done right after the accident? For example calling police, going to hospital, or informing someone."),
    Q("witnesses_available", "timeline_liability",
      "Kya kisi ne haadsa dekha ya madad ki?",
      "Did anyone see the accident or help afterwards?", kind="bool"),
    Q("witness_details", "timeline_liability",
      "Unka naam ya contact aur unhone kya dekha, yeh bataiye.",
      "What are their names or contacts, and what did they see?", parent="witnesses_available"),
    Q("property_or_vehicle_damage", "timeline_liability",
      "Vehicle ya saman ko kitna nuksan hua? Koi repair estimate ya bill hai?",
      "How much damage was done to the vehicle or property? Is there a repair estimate or bill?"),
    # ── Injuries (per injured person) ──────────────────────────────────────
    Q("injuries_and_medical_treatment", "timeline_liability",
      "{person} ko kaun si chotein aayi aur ilaaj kahan hua?",
      "What injuries did {person} suffer and where was the treatment?", person=True),
    Q("medical_bills_available", "timeline_liability",
      "{person} ke ilaaj ke bills ya medical records kya-kya available hain?",
      "What medical bills or records are available for {person}?", person=True),
    # ── Police / regulatory ────────────────────────────────────────────────
    Q("police_reported", "regulatory",
      "Kya is haadse ki police ko report ki gayi?",
      "Was the accident reported to the police?", kind="bool"),
    Q("fir_or_police_report_status", "regulatory",
      "FIR darj hui? Thane ka naam, FIR number aur saal bataiye.",
      "Was an FIR registered? Please give the police station, FIR number and year.", parent="police_reported"),
    Q("insurance_and_documents_available", "regulatory",
      "Vehicle ke kaunse kagaz aapke paas hain — RC, insurance, driving licence?",
      "Which vehicle documents do you have — RC, insurance, driving licence?"),
    Q("limitation_check", "regulatory",
      "Yeh haadsa lagbhag kitne mahine pehle hua tha?",
      "Roughly how many months ago did the accident happen?", gate=_date_unresolved),
    # ── Client / victim profile (Sarla Verma / Pranay Sethi inputs) ────────
    Q("full_name", "quantum_profiling",
      "Aur main aapko kis naam se bulaun? Poora naam bataiye.",
      "What name should I use for you? Please give your full name."),
    Q("age", "quantum_profiling",
      "Aapki — ya agar claim kisi aur ke liye hai to unki — umar kitni hai?",
      "What is your age — or the injured person's age, if the claim is for someone else?"),
    Q("dob", "quantum_profiling",
      "Janm tithi yaad hai?", "Do you remember the date of birth?", gate=lambda f: (f.get("age") or {}).get("status") != "answered"),
    Q("education_qualification", "quantum_profiling",
      "Padhai kitni ki hai?", "How far did you study?"),
    Q("occupation", "quantum_profiling",
      "Kaam-dhandha kya karte hain?", "What work do you do?"),
    Q("employment_type", "quantum_profiling",
      "Naukri permanent hai, apna kaam hai, ya dihadi?",
      "Is the job permanent, self-employed, or daily wage?", parent="occupation", gate=_earning),
    Q("employer_name", "quantum_profiling",
      "Kis employer ya company mein kaam karte hain?",
      "Which employer or company do you work for?", parent="occupation", gate=_earning),
    Q("monthly_income", "quantum_profiling",
      "Mahine ki kamai lagbhag kitni hai?", "What is the approximate monthly income?",
      parent="occupation", gate=_earning),
    Q("income_proof_type", "quantum_profiling",
      "Income ka koi saboot hai — ITR, salary slip ya bank statement?",
      "Is there proof of income — ITR, salary slip or bank statement?", parent="monthly_income"),
    Q("dependents", "quantum_profiling",
      "Aap par kitne log nirbhar hain? Parivaar mein kaun-kaun hai?",
      "How many people depend on you? Who is in the family?"),
    Q("pre_existing_conditions", "quantum_profiling",
      "Haadse se pehle koi bimari ya purani chot thi?",
      "Was there any illness or old injury before the accident?"),
    Q("disability_percentage", "quantum_profiling",
      "Doctor ne koi disability certificate ya percentage bataya hai?",
      "Has a doctor given a disability certificate or percentage?"),
    Q("functional_disability_impact", "quantum_profiling",
      "Chot ki wajah se kaam ya roz ki zindagi par kya asar pada hai?",
      "How have the injuries affected work or daily life?", parent="disability_percentage"),
    # ── Defence audit ──────────────────────────────────────────────────────
    Q("driving_license_number", "defense_audit",
      "Aapke driving licence ka number yaad hai?",
      "Do you remember your driving licence number?", parent="was_driving"),
    Q("driving_license_validity", "defense_audit",
      "Haadse ke din licence valid tha?",
      "Was the licence valid on the day of the accident?", parent="was_driving"),
    Q("criminal_history", "defense_audit",
      "Kya aapke khilaf koi challan ya police case pending hai ya pehle raha hai?",
      "Is there any challan or police case pending or in the past against you?"),
]

INDEX: dict[str, Question] = {q.key: q for q in QUESTIONS}
GLOBAL_KEYS = [q.key for q in QUESTIONS if not q.person]
PERSON_KEYS = [q.key for q in QUESTIONS if q.person]
