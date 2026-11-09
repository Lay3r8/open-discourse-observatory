from __future__ import annotations

import os

import streamlit as st

from odo.config import Settings
from odo.review import (
    ReviewItem,
    coercion_counts,
    label_counts,
    load_review_queue,
    previous_reviewed_item,
    save_structured_review,
    undo_last_review,
)

st.set_page_config(
    page_title="ODO · Revue sémantique",
    page_icon="🧭",
    layout="centered",
)

st.markdown(
    """
    <style>
    div.stButton > button {
        min-height: 3.1rem;
        font-weight: 650;
        border-radius: 0.65rem;
    }
    div[data-testid="stLinkButton"] a {
        min-height: 2.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        st.error(f"Configuration manquante : {name}")
        st.stop()
    return value


RUN_ID = _required_env("ODO_REVIEW_RUN_ID")
REVIEWER = _required_env("ODO_REVIEWER_ID")
TARGET = int(os.getenv("ODO_REVIEW_TARGET", "150"))
SETTINGS = Settings.from_env()


def _clear_draft() -> None:
    st.session_state.pop("draft_document_id", None)
    st.session_state.pop("draft_coercion", None)


def _clear_document_state(document_id: str) -> None:
    for prefix in ("evidence", "notes"):
        st.session_state.pop(f"{prefix}:{document_id}", None)
    st.session_state.pop("forced_document_id", None)
    _clear_draft()


def _set_coercion_draft(item: ReviewItem) -> None:
    st.session_state["draft_document_id"] = item.candidate_document_id
    st.session_state["draft_coercion"] = "yes"


def _has_coercion_draft(item: ReviewItem) -> bool:
    return (
        st.session_state.get("draft_document_id") == item.candidate_document_id
        and st.session_state.get("draft_coercion") == "yes"
    )


def _save(
    item: ReviewItem,
    *,
    coercion: str,
    scope: str,
) -> None:
    evidence = st.session_state.get(f"evidence:{item.candidate_document_id}", "")
    notes = st.session_state.get(f"notes:{item.candidate_document_id}", "")
    relevance = save_structured_review(
        SETTINGS,
        RUN_ID,
        item.candidate_document_id,
        coercion=coercion,
        scope=scope,
        reviewer_id=REVIEWER,
        evidence_text=evidence,
        notes=notes,
    )
    display = {
        "relevant": "pertinent",
        "not_relevant": "hors périmètre",
        "uncertain": "incertain",
    }[relevance]
    st.session_state["last_feedback"] = f"Enregistré : {display}"
    skipped = st.session_state.setdefault("skipped_ids", set())
    skipped.discard(item.candidate_document_id)
    _clear_document_state(item.candidate_document_id)
    st.rerun()


def _current_item(items: tuple[ReviewItem, ...]) -> ReviewItem | None:
    forced = st.session_state.get("forced_document_id")
    if forced:
        for current in items:
            if current.candidate_document_id == forced:
                return current

    skipped = st.session_state.setdefault("skipped_ids", set())
    for current in items:
        if not current.is_current_review and current.candidate_document_id not in skipped:
            return current
    return None


try:
    queue = load_review_queue(
        SETTINGS,
        RUN_ID,
        target=TARGET,
    )
except Exception as exc:
    st.error(f"Impossible de charger la file de revue : {exc}")
    st.stop()

labels = label_counts(queue)
coercion = coercion_counts(queue)
reviewed = queue.reviewed
legacy = sum(
    item.human_relevance is not None and not item.is_current_review
    for item in queue.items
)
progress = reviewed / queue.target if queue.target else 0

st.caption(f"Gold set v2 · reviewer : {REVIEWER} · objectif : {queue.target}")
st.progress(progress, text=f"{reviewed} / {queue.target} recodés en v2")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Revus", reviewed)
m2.metric("Coercition", coercion["yes"])
m3.metric("Pertinents", labels["relevant"])
m4.metric("Hors champ", labels["not_relevant"])
m5.metric("Incertains", labels["uncertain"])

if legacy:
    st.caption(
        f"{legacy} annotation(s) de l’ancien schéma sont conservées mais doivent être "
        "recodées sur les deux axes. Leur ancien label est masqué pendant la revue."
    )

if feedback := st.session_state.pop("last_feedback", None):
    st.toast(feedback)

if reviewed >= queue.target:
    st.success(
        f"Objectif atteint : {reviewed} documents recodés sur les deux axes. "
        "Le gold set v2 est prêt pour le benchmark IA."
    )
    if st.button("Annuler la dernière action", width="stretch"):
        restored = undo_last_review(
            SETTINGS,
            RUN_ID,
            reviewer_id=REVIEWER,
        )
        if restored:
            st.session_state["forced_document_id"] = restored
            st.session_state["last_feedback"] = "Dernière action annulée."
            st.rerun()
        st.info("Aucune action à annuler.")
    st.stop()

item = _current_item(queue.items)

if item is None:
    skipped = st.session_state.get("skipped_ids", set())
    st.warning("Tous les documents restants ont été passés dans cette session.")
    if skipped and st.button(
        f"Remettre les {len(skipped)} documents passés dans la file",
        width="stretch",
    ):
        st.session_state["skipped_ids"] = set()
        st.rerun()
    st.stop()

st.divider()

language = item.source_language or "langue non fournie"
st.caption(
    f"{item.source_common_name or 'source inconnue'} · "
    f"{item.discovery_date.isoformat()} · {language}"
)
st.subheader(item.title or "(titre absent)")

if item.canonical_url:
    st.link_button(
        "Ouvrir l’article source ↗",
        item.canonical_url,
        width="stretch",
        shortcut="O",
    )
else:
    st.caption("Aucune URL source exploitable pour ce document.")

if item.is_current_review:
    scope_display = {
        "yes": "oui",
        "no": "non",
        "uncertain": "incertain",
        "not_applicable": "n/a",
    }.get(item.expressive_scope_assessment, "—")
    st.info(
        "Annotation v2 actuelle : "
        f"coercition = **{item.coercion_assessment}** · "
        f"périmètre expression politique = **{scope_display}** · "
        f"résultat = **{item.human_relevance}**. "
        "Une nouvelle décision remplacera ces valeurs tout en conservant l’audit."
    )
elif item.human_relevance is not None:
    st.info(
        "Une annotation de l’ancien schéma existe pour ce document. "
        "Son contenu est volontairement masqué afin de ne pas biaiser le recodage v2."
    )

with st.expander("Rappel des deux questions"):
    st.markdown(
        """
**1 · Coercition ?**  
Y a-t-il une action qui impose ou cherche à imposer un coût, une restriction,
une sanction, une exclusion, une obstruction, une suppression, une menace ou
une violence ? Une critique ou une tentative de persuasion seule n’est pas coercitive.

**2 · Périmètre de l’étude ?**  
Si la réponse 1 est oui : cette coercition vise-t-elle la cible en raison de son
**expression, opinion, affiliation ou activité politique/idéologique** ?

Exemples :
- critique politique sans menace → **non** à la coercition ;
- licenciement pour harcèlement → **oui** à la coercition, **non** au périmètre ;
- boycott d’une équipe pour faire pression sur une politique d’État → **oui**, puis **non** ;
- conférence annulée à cause des opinions politiques de l’intervenant → **oui**, puis **oui**.

**Règle documentaire :** juge l’article comme source. S’il documente clairement au moins
un incident qualifiant, code cet incident même si le titre porte surtout sur une arrestation,
un procès ou les suites de l’affaire.

Le statut candidat/contrôle, le token de découverte et toute attribution idéologique
restent masqués.
        """
    )

with st.expander("Ajouter une justification ou une note (facultatif)"):
    st.text_area(
        "Élément probant / justification",
        value=item.evidence_text or "",
        key=f"evidence:{item.candidate_document_id}",
        placeholder="Facultatif — utile surtout pour les cas difficiles.",
    )
    st.text_area(
        "Note personnelle",
        value=item.notes or "",
        key=f"notes:{item.candidate_document_id}",
        placeholder="Facultatif",
    )

if not _has_coercion_draft(item):
    st.markdown("### 1 · Y a-t-il une action coercitive ?")
    st.caption("Raccourcis : 1 = oui · 2 = non · 3 = incertain · O = source")
    c1, c2, c3 = st.columns(3)

    if c1.button("Oui", type="primary", width="stretch", shortcut="1"):
        _set_coercion_draft(item)
        st.rerun()

    if c2.button("Non", width="stretch", shortcut="2"):
        _save(
            item,
            coercion="no",
            scope="not_applicable",
        )

    if c3.button("Incertain", width="stretch", shortcut="3"):
        _save(
            item,
            coercion="uncertain",
            scope="not_applicable",
        )

else:
    st.markdown(
        "### 2 · Cette coercition vise-t-elle une expression, opinion, affiliation "
        "ou activité politique/idéologique de la cible ?"
    )
    st.caption("Raccourcis : 1 = oui · 2 = non · 3 = incertain")
    c1, c2, c3 = st.columns(3)

    if c1.button(
        "Oui · dans le périmètre",
        type="primary",
        width="stretch",
        shortcut="1",
    ):
        _save(item, coercion="yes", scope="yes")

    if c2.button("Non · hors périmètre", width="stretch", shortcut="2"):
        _save(item, coercion="yes", scope="no")

    if c3.button("Incertain", width="stretch", shortcut="3"):
        _save(item, coercion="yes", scope="uncertain")

    if st.button("← Revenir à la question 1", width="stretch"):
        _clear_draft()
        st.rerun()

st.divider()

nav1, nav2, nav3 = st.columns(3)

if nav1.button("Passer", width="stretch"):
    skipped = st.session_state.setdefault("skipped_ids", set())
    skipped.add(item.candidate_document_id)
    st.session_state.pop("forced_document_id", None)
    _clear_draft()
    st.rerun()

previous = previous_reviewed_item(
    queue.items,
    item.candidate_document_id if item.is_current_review else None,
)
previous_label = "← Annoté précédent" if item.is_current_review else "Revoir le dernier"
if nav2.button(
    previous_label,
    disabled=previous is None,
    width="stretch",
    help="Navigue vers le document v2 annoté précédent sans modifier les labels.",
):
    if previous:
        st.session_state["forced_document_id"] = previous.candidate_document_id
        _clear_draft()
        st.rerun()

if nav3.button(
    "Annuler dernière action",
    width="stretch",
    help="Restaure l’état avant le dernier clic d’annotation. Peut être utilisé plusieurs fois.",
):
    restored = undo_last_review(
        SETTINGS,
        RUN_ID,
        reviewer_id=REVIEWER,
    )
    if restored:
        st.session_state["forced_document_id"] = restored
        _clear_draft()
        st.session_state["last_feedback"] = "Dernière action annulée."
        st.rerun()
    st.info("Aucune action à annuler.")

st.caption(
    "Les deux axes constituent le gold set. Justification et notes sont facultatives."
)

skipped_count = len(st.session_state.get("skipped_ids", set()))
if skipped_count:
    st.caption(
        f"{skipped_count} document(s) passé(s) pour cette session. "
        "Ils reviendront après les autres ou au prochain lancement."
    )
