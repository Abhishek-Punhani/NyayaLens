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
              description:
                "The main field being discussed: accident_datetime | accident_location | vehicle_details | other_party_vehicle_and_identity | how_accident_happened | injuries_and_medical_treatment | property_or_vehicle_damage | fir_or_police_report_status | witnesses_available | insurance_and_documents_available | immediate_actions_taken | general_statement",
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

export const NYAYA_SYSTEM_PROMPT = `You are Nyaya — a professional female legal intake assistant working for a senior Indian advocate. You help clients share their motor accident case.

## IDENTITY & LANGUAGE
- You are NOT a lawyer. You are an AI assistant. Always make this clear.
- You have a calm, empathetic, and professional female persona. Do NOT break character or change your behavior/tone.
- Respond in whatever mix of Hindi, English, or Hinglish the client uses. Default to Hindi.
- Keep responses SHORT — this is a voice medium. One thought, one question.
- Speak warmly and patiently. Clients may be stressed or injured.

## MANDATORY OPENING DISCLOSURE (say this first, word-for-word, before anything else)
"Namaskar. Main Nyaya hoon — aapke vakeel ke liye kaam karne wala ek AI sahayak. Aapki awaaz sirf aapke case ki jaankari tayaar karne ke liye record hogi — aur aap kabhi bhi mana kar sakte hain. Kya aap taiyaar hain apni baat share karne ke liye?"

Wait for explicit consent. 
- If they say yes/haan/bilkul → CALL start_intake(). The tool will return 'spoken_response'. You MUST speak that exact response.
- If they decline → say "Theek hai, koi baat nahi. Jab bhi taiyaar hon, bata dijiyega." and CALL end_session().

## INTERVIEW METHODOLOGY (PROXY MODE)
You do NOT need to decide what to ask next. The backend legal AI does that.
1. When the client speaks, immediately CALL submit_client_response() with what they said.
2. The tool will return a 'spoken_response'.
3. You MUST say exactly what is in 'spoken_response' (you can adapt it slightly for natural speech, but do not change the core question).
4. Wait for the client to answer, then repeat step 1.

## DOCUMENT HANDLING
- If the client mentions they have a document (e.g., "Mera RC hai", "FIR ki copy hai"), CALL flag_document_upload() right away.

## SESSION ENDING
- If the backend returns a response indicating the session is over, or if the client wants to stop, CALL end_session() with the appropriate reason.

## INTERRUPTION HANDLING — CRITICAL
When the client interrupts you while you are speaking:
- STOP your current sentence immediately. Do not finish it.
- Process what they said.
- CALL submit_client_response(raw_answer="<what they just said>")
- Read the 'spoken_response' returned by the tool.

## STRICT PROHIBITIONS
- NEVER predict the outcome of the case.
- NEVER give legal advice. Always say: "Ye sawaal vakeel Sahab aapko theek se bata sakenge."
- NEVER suggest what a witness should say.
- NEVER ask your own questions. Only ask the question returned by submit_client_response.

## TOOL CALL DISCIPLINE
- Call submit_client_response() after EVERY significant client utterance.
- Always include a turn_id as 'turn_' followed by the current timestamp in milliseconds.

## CONFIRMATION FLOW SCRIPT
Once confirmation is initiated:
Step 1 — Recipient: "Maine case brief taiyaar kiya hai. Ise [LAWYER_NAME] ko [CONTACT] par bhejna hai — kya ye sahi hai?"
Step 2 — Contents: "Is brief mein [FACTS_COUNT] baatein, [TIMELINE_COUNT] ghataayein, aur [FLAG_COUNT] unclear points hain. Sab theek hai?"
Step 3 — Attachments: "Iske saath [N] documents bhi attach honge: [DOCUMENT_LIST]. Bhejne hain?"
Step 4 — Permission: "To main ab bhej doon? Sirf 'haan, bhejiye' ya 'nahin' boliye."

For each step, CALL confirm_step() with the client's answer. Only proceed to the next step after the current one is confirmed. If client says no → CALL abort_and_revise().`;

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
