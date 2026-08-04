"""Adaptive question recommender (Person 3).

The app only needs these three names:

    from recommender import assemble_features, recommend_next

    vector = assemble_features(st.session_state.history, question)
    rec = recommend_next(vector, exclude=served_question_ids)
    # rec.next_question_id, rec.decision, rec.confidence

rules_baseline is the non-ML comparison, also reachable by setting
RECOMMENDER_MODE=baseline.
"""

from recommender.engine import recommend_next, rules_baseline
from recommender.features import assemble_features

__all__ = ["recommend_next", "rules_baseline", "assemble_features"]
