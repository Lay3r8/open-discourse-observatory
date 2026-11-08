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


## Navigation vs undo

`Revoir le dernier` opens the most recently reviewed document. Once a reviewed document is open, the same control becomes `Annoté précédent` and walks backward through earlier reviewed documents.

This is navigation only. `Annuler dernière action` restores the database state before the last annotation action. It is backed by the audit table and can be pressed repeatedly to roll back multiple accidental actions, including two consecutive clicks on the same label.


## Two-axis review v2

The browser now asks two separate questions:

1. whether the described action is coercive;
2. only when coercion is present, whether it targets political/ideological expression, opinion, affiliation or activity.

The final `relevant/not_relevant/uncertain` value is derived automatically. This avoids forcing the reviewer to compress cases such as workplace sanctions, terrorism without an expressive target, state-policy boycotts and non-coercive political criticism into one ambiguous button.

Existing v1 decisions are preserved but do not count toward v2 progress until recoded.


## No-coercion reason taxonomy

The no-coercion reasons intentionally avoid asking the reviewer to infer why the lexical discovery engine matched a document.

- `Sujet sans rapport / contenu general`: the article is simply outside the research topic (for example a CRE market outlook).
- `Analyse / contexte sans incident distinct`: the article discusses censorship/coercion/political controversy in general or as background, but does not provide a distinct incident to code.

The former `Aucune action coercitive identifiable` category was removed because, with discovery tokens blinded, it overlapped operationally with `Contexte / information seulement` and was not reliably codable.
