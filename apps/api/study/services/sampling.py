import random

from django.conf import settings

from study.domain.models import Attempt, Question, Quiz

PHASE_KINDS = (
    Question.Kind.MCQ,
    Question.Kind.CLOZE,
    Question.Kind.SCENARIO,
)


def _per_phase() -> int:
    return int(getattr(settings, "SESSION_QUESTIONS_PER_PHASE", 5))


def _draw(quiz: Quiz, exclude: set[int]) -> list[int]:
    per_phase = _per_phase()
    picked: list[int] = []
    for kind in PHASE_KINDS:
        pool = list(quiz.questions.filter(kind=kind).values_list("id", flat=True))
        if len(pool) < per_phase:
            raise ValueError(f"O banco não tem {per_phase} questões do tipo {kind}.")
        unused = [qid for qid in pool if qid not in exclude]
        used = [qid for qid in pool if qid in exclude]
        random.shuffle(unused)
        random.shuffle(used)
        picked.extend((unused + used)[:per_phase])
    return picked


def sample_question_ids(quiz: Quiz, exclude_ids: list[int] | None = None) -> list[int]:
    exclude = set(exclude_ids or [])
    picked = _draw(quiz, exclude)
    if not exclude:
        return picked
    for _ in range(7):
        if set(picked) != exclude:
            return picked
        picked = _draw(quiz, exclude)
    return picked


def last_attempt_question_ids(quiz: Quiz) -> list[int]:
    last = (
        Attempt.objects.filter(quiz=quiz, status=Attempt.Status.COMPLETED)
        .order_by("-created_at")
        .first()
    )
    if last is None:
        return []
    return list(last.question_ids or [])
