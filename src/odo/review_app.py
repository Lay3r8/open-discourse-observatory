from __future__ import annotations

import os

import streamlit as st

from odo.config import Settings
from odo.review import (
    NON_RELEVANT_REASONS,
    ReviewItem,
    label_counts,
    load_review_queue,
    save_review,
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


def _clear_document_state(document_id: str) -> None:
    for prefix in ("evidence", "notes"):
        st.session_state.pop(f"{prefix}:{document_id}", None)
    st.session_state.pop("pending_non_relevant", None)
    st.session_state.pop("forced_document_id", None)


def _save(
    item: ReviewItem,
    label: str,
    *,
    reason_code: str | None = None,
) -> None:
    evidence = st.session_state.get(f"evidence:{item.candidate_document_id}", "")
    notes = st.session_state.get(f"notes:{item.candidate_document_id}", "")
    save_review(
        SETTINGS,
        RUN_ID,
        item.candidate_document_id,
        label=label,
        reviewer_id=REVIEWER,
        reason_code=reason_code,
        evidence_text=evidence,
        notes=notes,
    )
    st.session_state["last_feedback"] = (
        f"Enregistré : {label.replace('_', ' ')}"
    )
    skipped = st.session_state.setdefault("skipped_ids", set())
    skipped.discard(item.candidate_document_id)
    _clear_document_state(item.candidate_document_id)
    st.rerun()


def _latest_reviewed(items: tuple[ReviewItem, ...]) -> ReviewItem | None:
    reviewed = [item for item in items if item.reviewed_at is not None]
    if not reviewed:
        return None
    return max(reviewed, key=lambda item: item.reviewed_at)


def _current_item(items: tuple[ReviewItem, ...]) -> ReviewItem | None:
    forced = st.session_state.get("forced_document_id")
    if forced:
        for item in items:
            if item.candidate_document_id == forced:
                return item

    skipped = st.session_state.setdefault("skipped_ids", set())
    for item in items:
        if item.human_relevance is None and item.candidate_document_id not in skipped:
            return item
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

counts = label_counts(queue)
reviewed = queue.reviewed
progress = reviewed / queue.target if queue.target else 0

st.caption(f"Gold set · reviewer : {REVIEWER} · objectif : {queue.target}")
st.progress(progress, text=f"{reviewed} / {queue.target} annotés")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Revus", reviewed)
m2.metric("Pertinents", counts["relevant"])
m3.metric("Non pertinents", counts["not_relevant"])
m4.metric("Incertains", counts["uncertain"])

if feedback := st.session_state.pop("last_feedback", None):
    st.toast(feedback)

if reviewed >= queue.target:
    st.success(
        f"Objectif atteint : {reviewed} documents annotés. "
        "Le gold set initial est prêt pour le benchmark IA."
    )
    if st.button("Annuler la dernière décision", width="stretch"):
        restored = undo_last_review(
            SETTINGS,
            RUN_ID,
            reviewer_id=REVIEWER,
        )
        if restored:
            st.session_state["last_feedback"] = "Dernière décision annulée."
            st.rerun()
        st.info("Aucune décision à annuler.")
    st.stop()

item = _current_item(queue.items)

if item is None:
    skipped = st.session_state.get("skipped_ids", set())
    st.warning(
        "Tous les documents restants ont été passés dans cette session."
    )
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

if item.human_relevance:
    st.info(
        "Ce document est déjà annoté "
        f"« {item.human_relevance.replace('_', ' ')} ». "
        "Une nouvelle décision remplacera la valeur courante tout en conservant l’audit."
    )

with st.expander("Rappel du critère de pertinence"):
    st.markdown(
        """
**Pertinent** : la source décrit plausiblement une pression, sanction, exclusion,
obstruction, menace ou violence liée à une expression, position, affiliation,
participation ou opinion politique/idéologique.

**Non pertinent** : l’action est réelle mais n’est pas liée à ce type d’expression
politique/idéologique.

**Incertain** : le titre et/ou la source ne permettent pas de trancher raisonnablement.

L’orientation politique, le fait que ce document soit un candidat ou un contrôle,
et le mot ayant déclenché la découverte sont volontairement masqués.
        """
    )

with st.expander("Ajouter une justification ou une note (facultatif)"):
    st.text_area(
        "Élément probant / justification",
        value=item.evidence_text or "",
        key=f"evidence:{item.candidate_document_id}",
        placeholder="Ex. l’événement est annulé après une campagne visant les propos de l’intervenant…",
    )
    st.text_area(
        "Note personnelle",
        value=item.notes or "",
        key=f"notes:{item.candidate_document_id}",
        placeholder="Facultatif",
    )

pending_non_relevant = (
    st.session_state.get("pending_non_relevant") == item.candidate_document_id
)

if not pending_non_relevant:
    st.caption("Raccourcis : 1 = pertinent · 2 = non pertinent · 3 = incertain · O = source")
    c1, c2, c3 = st.columns(3)
    if c1.button(
        "Pertinent",
        type="primary",
        width="stretch",
        shortcut="1",
    ):
        _save(item, "relevant")

    if c2.button(
        "Non pertinent",
        width="stretch",
        shortcut="2",
    ):
        st.session_state["pending_non_relevant"] = item.candidate_document_id
        st.rerun()

    if c3.button(
        "Incertain",
        width="stretch",
        shortcut="3",
    ):
        _save(item, "uncertain", reason_code="insufficient_context")
else:
    st.warning("Choisis la raison principale du classement « non pertinent ».")
    for index in range(0, len(NON_RELEVANT_REASONS), 2):
        cols = st.columns(2)
        for offset, col in enumerate(cols):
            pos = index + offset
            if pos >= len(NON_RELEVANT_REASONS):
                continue
            reason_code, label = NON_RELEVANT_REASONS[pos]
            if col.button(
                label,
                key=f"reason:{reason_code}:{item.candidate_document_id}",
                width="stretch",
                shortcut=str(pos + 1),
            ):
                _save(item, "not_relevant", reason_code=reason_code)

    if st.button("← Revenir aux trois choix", width="stretch"):
        st.session_state.pop("pending_non_relevant", None)
        st.rerun()

st.divider()

nav1, nav2, nav3 = st.columns(3)

if nav1.button("Passer", width="stretch"):
    skipped = st.session_state.setdefault("skipped_ids", set())
    skipped.add(item.candidate_document_id)
    st.session_state.pop("pending_non_relevant", None)
    st.session_state.pop("forced_document_id", None)
    st.rerun()

previous = _latest_reviewed(queue.items)
if nav2.button(
    "Revoir le dernier",
    disabled=previous is None,
    width="stretch",
):
    if previous:
        st.session_state["forced_document_id"] = previous.candidate_document_id
        st.session_state.pop("pending_non_relevant", None)
        st.rerun()

if nav3.button("Annuler dernière", width="stretch"):
    restored = undo_last_review(
        SETTINGS,
        RUN_ID,
        reviewer_id=REVIEWER,
    )
    if restored:
        st.session_state["forced_document_id"] = restored
        st.session_state["last_feedback"] = "Dernière décision annulée."
        st.rerun()
    st.info("Aucune décision à annuler.")

skipped_count = len(st.session_state.get("skipped_ids", set()))
if skipped_count:
    st.caption(
        f"{skipped_count} document(s) passé(s) pour cette session. "
        "Ils reviendront après les autres ou au prochain lancement."
    )
