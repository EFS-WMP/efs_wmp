# ITAD Core Workspace

## Codex Checklist
Use CODEX_CHECKLIST.md for every Codex change set / PR.

Note: tasks.md is the canonical Phase 0 Lock Review tracker.

## SoR Guardrails
Run the guard script to ensure canonical Phase 0 docs still contain the locked SoR wording and exclude forbidden phrases:

```
powershell -ExecutionPolicy Bypass -File scripts/phase0_sor_guard.ps1
```
