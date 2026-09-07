# civictech_db — Static Indian Law JSON Database

## Source
**Repository**: https://github.com/civictech-India/Indian-Law-Penal-Code-Json  
**Organization**: civictech-India (community-maintained open legal data project)  
**License**: Public domain / open use for legal research  
**Downloaded**: 2026-09-07  

## Files

| File | Act | Sections | Coverage |
|---|---|---|---|
| `ipc.json` | Indian Penal Code, 1860 | 575 | Full (all chapters) |
| `iea.json` | Indian Evidence Act, 1872 | 184 | Full (all chapters) |
| `crpc.json` | Code of Criminal Procedure, 1973 | 525 | Full (all chapters) |
| `cpc.json` | Code of Civil Procedure, 1908 | Full | Full (all chapters) |

## Schema (per entry)
```json
{
  "chapter": "Chapter XVII",
  "chapter_title": "Of Criminal Trespass",
  "Section": "441",
  "section_title": "Criminal trespass",
  "section_desc": "Whoever enters into or upon property..."
}
```

## Important Notes
- **These are OLD code texts**: IPC → superseded by BNS 2023 for events on/after 1 July 2024.
  CrPC → superseded by BNSS 2023. IEA → superseded by BSA 2023.
- **BNS/BNSS/BSA 2023 texts are NOT in this repo** — those are sourced separately from the
  statute_library.py (verified against NCRB Sankalan portal) and injected via section_mapping.py.
- The `statute_analysis_node` uses these old-code JSONs for events before 1 July 2024, and
  applies the transition mapping from section_mapping.py for events on/after 1 July 2024.
- **Verification status**: Community-maintained; cross-check critical provisions against
  India Code official PDFs before citing in any court document.

## Update Policy
Re-download if any Amendment Act is notified by Parliament.
Run: `cd backend/app/legal_data/civictech_db && bash update.sh`
