VOICE_ORCHESTRATOR_SYSTEM_PROMPT = """You are Nyaya, a voice-based legal intake assistant working for a senior Indian advocate.

Languages: Respond in whatever mix of Hindi/English/Hinglish the client uses. Default to Hindi if unclear.

Opening disclosure (MANDATORY first utterance, non-interruptible): 
Say the client is speaking with an AI assistant. Their voice is being recorded only to build the case brief for the lawyer. They may decline at any time. Get explicit spoken consent before proceeding.

Core interview methodology:
1. Open narrative
2. Dispossession recency branching
3. Schema-driven cross-questioning
4. Document requests
5. Confirmation flow

Interview Rules:
- ONE question at a time. Acknowledge before asking next.
- Interruption handling:
  - If the client interrupts mid-response: STOP immediately, process what they said.
  - Decide: (a) if it's new information → acknowledge, record via tool call, then re-ask pending question with context "Jaise main puch raha tha..."; OR (b) if it's a correction → update the fact, confirm correction, continue.
  - Never ignore an interruption or try to finish the previous sentence.
- Never give legal advice. Never predict outcomes. If asked "kya mera case jeetega?": "Main ye nahi bata sakta — ye advocate ka kaam hai. Main sirf aapki story aur documents organize kar raha hoon."

Tool call discipline:
- After EVERY significant client utterance, call `submit_client_response`.
- After every document mention, call `flag_document_upload`.
- After intake complete, call `trigger_analysis`.

Prohibited: coaching witnesses, inferring credibility from demographic, stating case outcome, inventing legal citations.
"""

VOICE_TOOL_DECLARATIONS = [
    {
        "name": "start_intake",
        "description": "Call when client gives consent to begin",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "submit_client_response",
        "description": "Call after every client utterance with info to submit their response",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "topic": {
                    "type": "STRING",
                    "description": "The topic being discussed"
                },
                "raw_answer": {
                    "type": "STRING",
                    "description": "The raw answer from the client"
                },
                "turn_id": {
                    "type": "STRING",
                    "description": "The current turn ID"
                }
            },
            "required": ["session_id", "topic", "raw_answer", "turn_id"]
        }
    },
    {
        "name": "flag_document_upload",
        "description": "Call when client mentions a document",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "document_type": {
                    "type": "STRING",
                    "description": "The type of document mentioned"
                },
                "has_recording": {
                    "type": "BOOLEAN",
                    "description": "Whether it is a recording/video"
                }
            },
            "required": ["session_id", "document_type", "has_recording"]
        }
    },
    {
        "name": "update_dispossession_track",
        "description": "Call after recency answer resolved",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "track": {
                    "type": "STRING",
                    "enum": ["section_6", "title_suit", "unclear"],
                    "description": "The dispossession track"
                }
            },
            "required": ["session_id", "track"]
        }
    },
    {
        "name": "request_clarification",
        "description": "Call when asking about a fuzziness flag",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "flag_id": {
                    "type": "STRING",
                    "description": "The ID of the fuzziness flag"
                },
                "question_asked": {
                    "type": "STRING",
                    "description": "The question asked to clarify"
                }
            },
            "required": ["session_id", "flag_id", "question_asked"]
        }
    },
    {
        "name": "trigger_analysis",
        "description": "Call when all schema fields covered and flags resolved",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "initiate_confirmation",
        "description": "Call to start the multi-step consent flow",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "confirm_step",
        "description": "Call for each consent step",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "step": {
                    "type": "STRING",
                    "enum": ["recipient", "contents", "attachments", "permission"],
                    "description": "The step being confirmed"
                },
                "confirmed": {
                    "type": "BOOLEAN",
                    "description": "Whether the client confirmed this step"
                }
            },
            "required": ["session_id", "step", "confirmed"]
        }
    },
    {
        "name": "abort_and_revise",
        "description": "Call if client says no at any consent step",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "session_id": {
                    "type": "STRING",
                    "description": "The current session ID"
                },
                "step": {
                    "type": "STRING",
                    "description": "The step where the client aborted"
                },
                "reason": {
                    "type": "STRING",
                    "description": "The reason for abortion/revision"
                }
            },
            "required": ["session_id", "step", "reason"]
        }
    }
]
