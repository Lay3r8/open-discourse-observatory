# Local review UI

The semantic gold set is reviewed through a local Streamlit application backed directly by PostgreSQL.

## Launch

```bash
uv run odo review \
  --run-id semantic-v1-2025-01-01-2025-01-08-bfe1d5267a05 \
  --reviewer simon \
  --target 150
```

The server binds to `127.0.0.1` only and uses port 8501 by default. Under WSL, ODO attempts to open the Windows browser automatically. Use `--no-browser` if desired.

## UX principles

- one document at a time;
- resume at the next unreviewed item;
- target is explicit (150 by default), rather than presenting the full 500-row sample as a task;
- candidate vs negative-control status is hidden;
- discovery token is hidden;
- no ideological label is shown or requested;
- relevant/uncertain are one-click decisions;
- non-relevant requires one additional quick reason;
- optional evidence/notes are available without blocking fast triage;
- skip is session-local;
- the last reviewed document can be reopened;
- every label change is audit-logged and the last action can be undone.

## Decision criterion

The UI asks only whether the document plausibly describes pressure, sanction, exclusion, obstruction, threat or violence tied to political/ideological expression, affiliation, participation or viewpoint.

It does **not** ask who is left/right. Ideological attribution remains a later, separate stage.

## Review target

For the initial AI benchmark, 100–150 independently human-reviewed documents are sufficient to start measuring model behavior. The rest of the 500-row sample remains available for later expansion and disagreement review.


## Resume behavior

Completed labels are stored immediately in PostgreSQL. Relaunching the UI with the same run ID and target rebuilds the same deterministic review queue and resumes at the first unreviewed document. Therefore, if the browser/app is closed while viewing an unreviewed article, that article is normally shown again on restart. Session-only `Passer` choices are intentionally not persisted, so skipped documents may reappear after a restart.
