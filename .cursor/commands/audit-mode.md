## Socle commun — Audit Houston

Mode audit only.

Do not edit source code.
Do not modify app behavior.
You may produce audit findings in the chat response or a short-lived working note — do not add audit report files to the repository (Git is history).

Never edit source files during audit mode.

Context:
Houston is in dev phase only. No staging/prod compatibility requirement.

Audit objective:
Technical/product codebase audit focused on scalability, structure, maintainability, duplicated patterns, fragile architecture, backend/frontend drift, and missing tests.

Read first:
- AGENTS.md
- nearest AGENTS.md for the audited area
- relevant .cursor/rules
- [`docs/product/current_state.md`](../../docs/product/current_state.md)
- related code and tests

Output: max 10 findings with evidence, severity, recommended fix, and test suggestions.

End with: top 3 fixes, quick wins, structural issues to plan later.
