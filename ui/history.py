import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

SESSIONS_DIR = Path("data/sessions")


def initialize_history():

    if "history" not in st.session_state:
        st.session_state.history = []

    if "session_id" not in st.session_state:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        st.session_state.session_id = f"{stamp}-{uuid.uuid4().hex[:6]}"

        st.session_state.session_started = datetime.now().isoformat(timespec="seconds")


def add_attempt(question_id, result, tests_passed, tests_total, evaluation=None):
    """Record one submission.

    evaluation: the LLMEvaluation for this attempt, when one was produced.
    Only passing submissions get graded, so failures carry no scores — the
    recommender expects exactly that and falls back to its cold-start values.
    These two fields are what feed the model's efficiency/style features, so
    dropping them here silently degrades every recommendation.
    """

    attempt = {
        "question_id": question_id,
        "result": result,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "efficiency_score": evaluation.efficiency_score if evaluation else None,
        "style_score": evaluation.style_score if evaluation else None,
    }

    st.session_state.history.append(attempt)

    save_session()


def save_session():
    """Write the session transcript to data/sessions/<session_id>.json.

    Rewrites the whole file on every attempt — a session is a few dozen small
    dicts, so this is cheaper than tracking appends and survives a browser tab
    closing mid-session.

    This is the transcript source docs/evaluation_plan_recommender.md depends
    on. Never let a write failure end someone's assessment, same reasoning as
    recommender.engine._log.

    Note it stores no byom_config: an API key must not reach disk.
    """
    try:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        payload = {
            "session_id": st.session_state.session_id,
            "started_at": st.session_state.get("session_started"),
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            # Provenance for Week 13: which model produced these scores. Never
            # the api_key — see the docstring.
            "provider": st.session_state.get("byom_config", {}).get("provider"),
            "model": st.session_state.get("byom_config", {}).get("model"),
            "base_url": st.session_state.get("byom_config", {}).get("base_url"),
            "served": list(st.session_state.get("served", [])),
            "history": st.session_state.history,
        }

        path = SESSIONS_DIR / f"{st.session_state.session_id}.json"

        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    except OSError:
        pass


def get_history():

    return st.session_state.history
