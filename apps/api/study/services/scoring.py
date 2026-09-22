from study.domain.models import Question

KIND_PHASE = {
    Question.Kind.MCQ: 1,
    Question.Kind.CLOZE: 2,
    Question.Kind.SCENARIO: 3,
}


def _norm(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def score_answer(question: Question, payload: dict) -> dict:
    timed_out = bool(payload.get("timed_out"))
    selected_index = payload.get("selected_index")
    selected_values = payload.get("selected_values") or []
    if selected_index is not None:
        try:
            selected_index = int(selected_index)
        except (TypeError, ValueError):
            selected_index = None
    selected_values = [str(value) for value in selected_values]

    is_correct = False
    if not timed_out:
        if question.kind in (Question.Kind.MCQ, Question.Kind.SCENARIO):
            is_correct = selected_index == question.correct_index
        elif question.kind == Question.Kind.CLOZE:
            expected = [_norm(value) for value in (question.correct_values or [])]
            got = [_norm(value) for value in selected_values]
            is_correct = got == expected and len(got) == len(expected)

    return {
        "question_id": question.id,
        "kind": question.kind,
        "phase": KIND_PHASE.get(question.kind, 1),
        "topic": question.topic,
        "prompt": question.prompt,
        "options": question.options,
        "selected_index": selected_index,
        "selected_values": selected_values,
        "correct_index": question.correct_index,
        "correct_values": question.correct_values or [],
        "timed_out": timed_out,
        "is_correct": is_correct,
        "explanation": question.explanation,
    }


def phase_scores(results: list[dict]) -> list[dict]:
    scores = []
    for phase, kind in ((1, Question.Kind.MCQ), (2, Question.Kind.CLOZE), (3, Question.Kind.SCENARIO)):
        items = [item for item in results if item["phase"] == phase]
        total = len(items)
        score = sum(1 for item in items if item["is_correct"])
        scores.append({"phase": phase, "kind": kind, "score": score, "total": total})
    return scores
