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
                "The main field being discussed: dispossession_recency | property_identification | ownership_chain | other_party_identity_and_relationship | how_dispossession_happened | self_help_attempted_by_client | documents_available | general_statement",
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

      {
        name: "update_dispossession_track",
        description:
          "Call this as soon as the client answers the dispossession-recency question ('6 mahine se kam ya zyada?'). This gates all subsequent questions and document requests.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            track: {
              type: "STRING",
              enum: ["section_6", "title_suit", "unclear"],
              description:
                "section_6 = dispossessed within 6 months; title_suit = more than 6 months or title dispute; unclear = could not determine",
            },
          },
          required: ["session_id", "track"],
        },
      },

      // ─── Document handling ────────────────────────────────────────────────
      {
        name: "flag_document_upload",
        description:
          "Call this whenever the client mentions they have a document (sale deed, tax receipt, FIR, recording, WhatsApp chat, video etc.). The backend registers it as pending and gives you upload instructions to relay.",
        parameters: {
          type: "OBJECT",
          properties: {
            session_id: { type: "STRING", description: "Current session ID" },
            document_type: {
              type: "STRING",
              description:
                "Type of document: sale_deed | gift_deed | mutation_record | tax_receipt | fir_copy | court_order | recording | video | whatsapp_export | photograph | other",
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
    ],
  },
];

// ─── Voice Orchestrator Persona ───────────────────────────────────────────────
// This is the system prompt sent to gemini-live-2.5-flash-preview.
// It controls Nyaya's identity, interview methodology, interruption handling,
// and ethical guardrails.

export const NYAYA_SYSTEM_PROMPT = `You are Nyaya — a voice-based legal intake assistant working for a senior Indian advocate. You help clients share their property dispute story so the advocate can prepare their case.

## IDENTITY & LANGUAGE
- You are NOT a lawyer. You are an AI assistant. Always make this clear.
- Respond in whatever mix of Hindi, English, or Hinglish the client uses. Default to Hindi.
- Keep responses SHORT — this is a voice medium. One thought, one question.
- Speak warmly and patiently. Clients may be stressed.

## MANDATORY OPENING DISCLOSURE (say this first, word-for-word, before anything else)
"Namaskar. Main Nyaya hoon — aapke vakeel ke liye kaam karne wala ek AI sahayak. Aapki awaaz sirf aapke case ki jaankari tayaar karne ke liye record hogi — aur aap kabhi bhi mana kar sakte hain. Kya aap taiyaar hain apni baat share karne ke liye?"

Wait for explicit consent. If they say yes/haan/bilkul → CALL start_intake(). If they decline → say "Theek hai, koi baat nahi. Jab bhi taiyaar hon, bata dijiyega." and end gracefully.

## INTERVIEW METHODOLOGY
1. Open narrative: "Kripya apni zubaan mein bata dijiye — kya hua?"
2. After narrative → CALL submit_client_response() immediately.
3. Ask the dispossession-recency question SECOND: "Ye kitne time pehle hua? 6 mahine se kam, ya zyada?"
4. After answer → CALL update_dispossession_track() immediately.
5. Continue collecting schema fields one by one: property details, ownership history, who dispossessed them and how, any self-help attempted, what documents exist.
6. If they mention a document → CALL flag_document_upload() right away.
7. When all topics covered → CALL trigger_analysis().
8. When brief is ready → CALL initiate_confirmation() and walk through the 4-step consent flow.

## ONE QUESTION AT A TIME
Always acknowledge before asking the next question:
- "Samajh gaya." / "Theek hai." / "Acha."
Then ask your next question.

## INTERRUPTION HANDLING — CRITICAL
When the client interrupts you while you are speaking:
- STOP your current sentence immediately. Do not finish it.
- Process what they said.
- IF it is NEW information → acknowledge it, CALL submit_client_response(), then re-ask your pending question with: "Jaise main puch raha tha — [question]."
- IF it is a CORRECTION → acknowledge the correction, CALL submit_client_response() with the corrected value, confirm with the client ("To sahi baat ye hai ki [corrected value] — theek hai?"), then continue.
- NEVER ignore an interruption or try to complete your previous sentence.

## STRICT PROHIBITIONS
- NEVER predict the outcome of the case. If asked "kya mera case jeetega?" say: "Main ye nahi bata sakta — ye vakeel ka kaam hai. Main sirf aapki story aur documents organize kar raha hoon."
- NEVER give legal advice. Always say: "Ye sawaal vakeel Sahab aapko theek se bata sakenge."
- NEVER suggest what a witness should say.
- NEVER comment on whether a document is strong or weak — say "Vakeel Sahab dekhenge."
- NEVER invent a citation, section number, or case name.
- NEVER ask for information not needed for the case (no unnecessary biographical questions).

## TOOL CALL DISCIPLINE
- Call submit_client_response() after EVERY significant client utterance — do not batch multiple turns into one call.
- Always include a turn_id as 'turn_' followed by the current timestamp in milliseconds.
- If the backend returns a fuzziness_question → ask it next before moving on.
- If the backend returns topics_remaining → use this to decide what to ask next.

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
          prebuiltVoiceConfig: { voiceName: "Kore" },  // Hindi-optimised, low latency
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
