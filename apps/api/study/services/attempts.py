from study.domain.models import Attempt, Lesson


def best_attempt_for_lesson(lesson: Lesson) -> Attempt | None:
    return (
        Attempt.objects.filter(
            quiz__lesson=lesson,
            status=Attempt.Status.COMPLETED,
        )
        .order_by("-score", "completed_at", "id")
        .first()
    )


def result_payload(attempt: Attempt) -> dict:
    best = best_attempt_for_lesson(attempt.quiz.lesson)
    return {
        "id": attempt.id,
        "lesson": attempt.quiz.lesson_id,
        "status": attempt.status,
        "score": attempt.score,
        "total": attempt.total,
        "is_best": best is not None and best.id == attempt.id,
        "phase_scores": attempt.phase_scores,
        "study_plan": attempt.study_plan,
        "results": attempt.results,
        "created_at": attempt.created_at,
    }
