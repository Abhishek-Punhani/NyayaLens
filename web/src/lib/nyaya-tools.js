/**
 * NyayaLens — Gemini Live Tool Declarations & Voice Orchestrator Persona
 *
 * These tool declarations are sent to the Gemini Live API as part of the
 * session config. Each tool call is forwarded to the NyayaLens backend at
 * POST /api/tool-call, which routes it into the LangGraph pipeline.
 *
 * Model: gemini-live-2.5-flash-preview (native audio dialog)
 * Voice: Kore (Hindi-optimised, low latency)
 */

export const NYAYA_TOOLS = [
  {
    functionDeclarations: [
      // ─── Session lifecycle ────────────────────────────────────────────────
      {
        name: "start_intake",
        description:
          "Call this immediately after the client gives explicit spoken consent to begin the legal intake interview. Do NOT call before consent is received.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: {
              type: "STRING",
              description: "The current session ID provided by the backend",
            },
          },
          required: ["session_id"],
        },
      },

      // ─── Core intake ──────────────────────────────────────────────────────
      {
        name: "submit_client_response",
        description:
          "Call this after EVERY significant piece of information the client shares — their story, a date, a name, a description of what happened. The backend analyses it for fuzziness and tells you what to ask next.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: {
              type: "STRING",
              description: "The current session ID",
            },
            topic: {
              type: "STRING",
              enum: [
                "client_identity",
                "client_education",
                "client_employment_income",
                "client_dependents",
                "client_legal_history",
                "accident_datetime",
                "accident_location",
                "vehicle_details",
                "other_party_vehicle_and_identity",
                "how_accident_happened",
                "injuries_and_medical_treatment",
                "property_or_vehicle_damage",
                "fir_or_police_report_status",
                "witnesses_available",
                "insurance_and_documents_available",
                "immediate_actions_taken",
                "general_statement",
              ],
              description:
                "The main field being discussed: client profile (client_identity, client_education, client_employment_income, client_dependents, client_legal_history) or incident/case fields (accident_datetime, accident_location, vehicle_details, other_party_vehicle_and_identity, how_accident_happened, injuries_and_medical_treatment, property_or_vehicle_damage, fir_or_police_report_status, witnesses_available, insurance_and_documents_available, immediate_actions_taken, general_statement)",
            },
            raw_answer: {
              type: "STRING",
              description: "Verbatim transcript of what the client said in this turn",
            },
            turn_id: {
              type: "STRING",
              description: "A unique ID for this conversation turn (generate as 'turn_' + timestamp)",
            },
          },
          required: ["session_id", "raw_answer", "turn_id"],
        },
      },

      // ─── Document handling ────────────────────────────────────────────────
      {
        name: "flag_document_upload",
        description:
          "Call this whenever the client mentions they have a document (FIR copy, medical bills, insurance policy, vehicle RC, photographs, WhatsApp chat, video etc.). The backend registers it as pending and gives you upload instructions to relay.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            document_type: {
              type: "STRING",
              description:
                "Type of document: fir_copy | medical_bills | insurance_policy | vehicle_rc | driving_licence | photographs | video | whatsapp_export | hospital_records | repair_estimate | court_order | other",
            },
            has_recording: {
              type: "BOOLEAN",
              description:
                "Set true if the document is an audio recording, video, or WhatsApp/message export — these require a BSA Section 63 certificate",
            },
          },
          required: ["session_id", "document_type", "has_recording"],
        },
      },

      // ─── Fuzziness handling ───────────────────────────────────────────────
      {
        name: "request_clarification",
        description:
          "Call this when you are asking the client a clarification question prompted by a fuzziness flag (contradiction, timeline conflict, vague account etc.). Log the flag_id so the backend knows which flag is being addressed.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            flag_id: {
              type: "STRING",
              description: "The flag_id returned by the backend in a previous submit_client_response",
            },
            question_asked: {
              type: "STRING",
              description: "The exact question you asked the client",
            },
          },
          required: ["session_id", "flag_id", "question_asked"],
        },
      },

      // ─── Handoff ──────────────────────────────────────────────────────────
      {
        name: "trigger_analysis",
        description:
          "Call this when ALL schema fields are covered AND there are no unresolved blocking fuzziness flags. Triggers the parallel analysis pipeline (precedent research, opposition simulation, witness candidates, argument hypotheses). Tell the client the brief is being prepared.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
          },
          required: ["session_id"],
        },
      },

      {
        name: "initiate_confirmation",
        description:
          "Call this to start the 4-step consent flow before sending the case packet to the lawyer. Do NOT call this until trigger_analysis has been called and you have told the client the brief is ready.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
          },
          required: ["session_id"],
        },
      },

      {
        name: "confirm_step",
        description:
          "Call this for each step of the 4-step consent flow, after the client has given a clear yes or no. Steps in order: recipient → contents → attachments → permission.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            step: {
              type: "STRING",
              enum: ["recipient", "contents", "attachments", "permission"],
              description: "Which consent step is being confirmed",
            },
            confirmed: {
              type: "BOOLEAN",
              description: "True if client said yes/haan, false if no/nahin",
            },
          },
          required: ["session_id", "step", "confirmed"],
        },
      },

      {
        name: "abort_and_revise",
        description:
          "Call this if the client says no at any consent step and wants to revise the brief. The backend will return to intake mode.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            step: {
              type: "STRING",
              description: "The consent step where the client aborted",
            },
            reason: {
              type: "STRING",
              description: "Brief description of what the client wants to change",
            },
          },
          required: ["session_id", "step", "reason"],
        },
      },

      // ─── Session termination ──────────────────────────────────────────────
      {
        name: "end_session",
        description:
          "Call this ONLY when the session is truly over — either the client declined consent and you have said goodbye, or the confirmation flow is complete and the brief has been sent. This disconnects the live audio connection. Do NOT call this in the middle of the interview.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            reason: {
              type: "STRING",
              enum: ["brief_sent", "client_declined", "client_requested_end"],
              description: "Why the session is ending",
            },
          },
          required: ["session_id", "reason"],
        },
      },
    ],
  },
];

// ─── Voice Orchestrator Persona ───────────────────────────────────────────────
// This is the system prompt sent to gemini-live-2.5-flash-preview.
// It controls Nyaya's identity, interview methodology, interruption handling,
// and ethical guardrails.

export const NYAYA_SYSTEM_PROMPT = `You are Nyaya — a professional female legal intake interviewer and forensic dialogue assistant working for a senior Indian MACT advocate. You conduct structured trial-advocacy intakes with clients involved in motor accidents.

## STRICT TRIAL ADVOCACY DISCIPLINE
- Speak politely, empathetically, and professionally like a senior advocate's legal secretary or intake coordinator.
- NEVER ask multiple questions in one turn. ONE question only.
- Always acknowledge in 1-2 words ("Samajh gayi.", "Theek hai.") and ask the next relevant question.

## IDENTITY & PERSONA
- You are Nyaya — a professional female legal intake assistant working for the advocate's chambers.
- You have a calm, empathetic, and polished professional persona.
- Always use FEMININE Hindi verb forms for yourself ("Main samajh rahi hoon", "Main sun rahi hoon", "Main aapse poochhna chahti hoon").
- Respond in whatever mix of Hindi, English, or Hinglish the client uses. Default to Hindi.
- Keep responses SHORT — one thought, one targeted question per turn.

## INTERVIEW METHODOLOGY (PROXY & BACKEND SYNC)
1. MANDATORY: After EVERY single client utterance, even short ones like 'haan' or 'nahin', immediately CALL submit_client_response(topic=..., raw_answer=..., turn_id=...).
2. The backend LLM analyses the legal state, fuzziness flags, and missing fields, returning 'spoken_response'.
3. You MUST say what is returned in 'spoken_response' VERBATIM — do not rephrase or add to it.
4. If 'spoken_response' is empty/null, you use the phase sequence below to ask ONE targeted question.

## THE 5-PHASE FUNNEL SEQUENCE (MANDATORY TRIAL ORDER)
Follow this sequence strictly if backend does not provide a spoken_response:

### PHASE 1: INITIAL REASON FOR CONSULTATION & NARRATIVE
- Opening (after consent): "Aap advocate Sahab se kis mamle ke silsile mein appointment schedule karna chahte hain? Kripya thoda batayein."
- Listen carefully to their explanation of what happened.

### PHASE 2: COLLISION MECHANICS
Anchor the event facts chronologically:
1. Exact Date & Time
2. Exact Spot & Landmark
3. Vehicles Involved
4. Collision Dynamics & Speed

### PHASE 3: INJURIES, MEDICAL & NATURAL LIFE IMPACT
Assess physical harm:
1. Injuries & Hospital Treatment

### PHASE 4: PROFILE & IDENTITY
- Name is asked naturally when it fits after the narrative: "Aur main aapko kaise pukarun?"
- Weave personal background contextually (Age, occupation, impact on daily life).
- Financial Standing (ONLY IF EMPLOYED / EARNING).

### PHASE 5: REGULATORY & EVIDENTIARY AUDIT
- Police Action (FIR/GD)
- Driving License
- Medical Bills & Expenses
- Discrepancy Testing & Looping

## MANDATORY OPENING DISCLOSURE (Non-interruptible, say first before anything else)
"Namaskar. Main Nyaya hoon — aapke vakeel ke liye kaam karne wali ek AI sahayak. Aapki awaaz sirf aapke case ki jaankari tayaar karne ke liye record hogi — aur aap kabhi bhi mana kar sakte hain. Kya aap taiyaar hain apni baat share karne ke liye?"

Wait for explicit consent.
- If client agrees (yes/haan/bilkul) → IMMEDIATELY CALL start_intake(). Do NOT speak the tool's response (it will be empty). Then immediately go to PHASE 1 and ask the opening question.
- If client declines → say "Theek hai, koi baat nahi. Jab bhi aap taiyaar hon, hum shuru kar sakte hain." and CALL end_session(reason="client_declined").

## DOCUMENT HANDLING
- Whenever the client mentions ANY document (FIR, MLC, RC, DL, Insurance, Medical Bills, Salary Slip, ITR, Photo, Video):
  CALL flag_document_upload(document_type=..., has_recording=...).
  If it is an audio/video/WhatsApp file, inform them neutrally that a Bharatiya Sakshya Adhiniyam (BSA) Section 63 electronic certificate will be needed.

## INTERRUPTION HANDLING — ZERO LATENCY
When the client interrupts you mid-speech:
- STOP speaking immediately. Do not finish your sentence.
- Listen to what they said.
- Immediately CALL submit_client_response(raw_answer="<what client said>").
- Read the 'spoken_response' returned by the backend VERBATIM.

## STRICT ETHICAL GUARDRAILS
- NEVER predict win/loss probabilities.
- NEVER give final legal advice or quote compensation guarantees. Always say: "Iska antim faisla vakeel Sahab aur court karenge."
- NEVER suggest what a witness should say or coach answers.
- NEVER infer dishonesty or credibility based on occupation, caste, gender, or religion.

## 4-STEP CLIENT CONFIRMATION SCRIPT (Before sending brief to Advocate)
Step 1 — Recipient: "Maine aapka case brief taiyaar kiya hai. Ise [LAWYER_NAME] ko [CONTACT] par bhejna hai — kya ye sahi hai?"
Step 2 — Contents: "Is brief mein [FACTS_COUNT] baatein, [TIMELINE_COUNT] ghataayein, aur [FLAG_COUNT] points hain jinpar vakeel Sahab baat karenge. Sab theek hai?"
Step 3 — Attachments: "Iske saath [N] documents attach honge: [DOCUMENT_LIST]. Bhejne hain?"
Step 4 — Permission: "To kya main is brief ko abhi advocate Sahab ko bhej doon? Sirf 'haan, bhejiye' ya 'nahin' boliye."
For each step, CALL confirm_step(step=..., confirmed=...). If client says no → CALL abort_and_revise().`;

// ─── Session config for Gemini Live API ──────────────────────────────────────
// Pass this as the `config` argument to GenAILiveClient.connect()

export function buildNyayaLiveConfig(sessionId, backendUrl = "http://localhost:8000") {
  return {
    systemInstruction: { parts: [{ text: NYAYA_SYSTEM_PROMPT }] },
    tools: NYAYA_TOOLS,
    generationConfig: {
      responseModalities: ["AUDIO"],   // voice-only output
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: { voiceName: "Aoede" },  // Highly stable female voice model
        },
      },
    },
    // Session metadata passed to tool handlers via closure
    _sessionId: sessionId,
    _backendUrl: backendUrl,
  };
}

// ─── Tool-call handler for the frontend ──────────────────────────────────────
// Wire this to the GenAILiveClient "toolcall" event.
// It forwards every tool call to the backend and returns the function response.

export async function handleNyayaToolCall(toolCall, sessionId, backendUrl = "http://localhost:8000") {
  const responses = [];

  for (const fn of toolCall.functionCalls ?? []) {
    const { name, args, id } = fn;
    let result = { status: "error", error: "unknown tool" };

    try {
      const response = await fetch(`${backendUrl}/api/tool-call`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          tool_name: name,
          arguments: args ?? {},
        }),
      });

      if (!response.ok) {
        const errText = await response.text();
        console.error(`[NyayaTools] Backend error for ${name}:`, errText);
        result = { status: "error", error: errText };
      } else {
        result = await response.json();
      }
    } catch (err) {
      console.error(`[NyayaTools] Network error for ${name}:`, err);
      result = { status: "error", error: String(err) };
    }

    console.log(`[NyayaTools] ${name} →`, result);
    responses.push({ id, name, response: { output: JSON.stringify(result) } });
  }

  return { functionResponses: responses };
}
