from django.db import migrations


def backfill_completed_attempts(apps, schema_editor):
    from study.domain.models import Attempt, Question
    from study.services.recommendations import build_study_plan
    from study.services.scoring import phase_scores, score_answer

    for attempt in Attempt.objects.filter(status=Attempt.Status.COMPLETED):
        questions = {
            question.id: question
            for question in Question.objects.filter(id__in=attempt.question_ids)
        }
        submitted = {item.get("question_id"): item for item in (attempt.answers or [])}
        results = []
        for qid in attempt.question_ids:
            question = questions.get(qid)
            if question is None:
                continue
            results.append(score_answer(question, submitted.get(qid, {})))
        attempt.results = results
        attempt.total = len(results)
        if results:
            attempt.phase_scores = phase_scores(results)
            attempt.study_plan = build_study_plan(results)
        attempt.save(update_fields=["results", "total", "phase_scores", "study_plan"])


class Migration(migrations.Migration):

    dependencies = [
        ("study", "0002_attempt_total_results"),
    ]

    operations = [
        migrations.RunPython(backfill_completed_attempts, migrations.RunPython.noop),
    ]
