from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from study.api.serializers import LessonSerializer, SessionQuestionSerializer, SessionSubmitSerializer
from study.domain.models import Attempt, Lesson, Question, Quiz
from study.services.quiz_generator import QuizGenerationError, generate_bank
from study.services.recommendations import build_study_plan
from study.services.sampling import last_attempt_question_ids, sample_question_ids
from study.services.scoring import KIND_PHASE, phase_scores, score_answer

TIME_LIMITS = {
    Question.Kind.MCQ: None,
    Question.Kind.CLOZE: 30,
    Question.Kind.SCENARIO: 30,
}


def _session_payload(attempt: Attempt) -> dict:
    questions = {
        question.id: question
        for question in Question.objects.filter(id__in=attempt.question_ids)
    }
    ordered = [questions[qid] for qid in attempt.question_ids if qid in questions]
    phases = []
    for kind in (Question.Kind.MCQ, Question.Kind.CLOZE, Question.Kind.SCENARIO):
        group = [question for question in ordered if question.kind == kind]
        phases.append(
            {
                "phase": KIND_PHASE[kind],
                "kind": kind,
                "time_limit_seconds": TIME_LIMITS[kind],
                "questions": SessionQuestionSerializer(group, many=True).data,
            }
        )
    return {
        "id": attempt.id,
        "lesson": attempt.quiz.lesson_id,
        "lesson_title": attempt.quiz.lesson.title,
        "status": attempt.status,
        "phases": phases,
    }


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer

    def get_queryset(self):
        return Lesson.objects.prefetch_related(
            Prefetch("quizzes", queryset=Quiz.objects.order_by("-created_at").prefetch_related("questions"))
        )

    @action(detail=True, methods=["post"], url_path="generate-bank")
    def generate_bank_action(self, request, pk=None):
        lesson = self.get_object()
        quiz = Quiz.objects.create(lesson=lesson, status=Quiz.Status.PENDING)
        try:
            raw, questions = generate_bank(lesson.class_content, lesson.learned_notes)
        except QuizGenerationError as exc:
            quiz.status = Quiz.Status.FAILED
            quiz.error_message = str(exc)
            quiz.save(update_fields=["status", "error_message"])
            return Response(LatestBankPayload(quiz), status=status.HTTP_502_BAD_GATEWAY)

        with transaction.atomic():
            quiz.raw_model_response = raw
            quiz.status = Quiz.Status.READY
            quiz.error_message = ""
            quiz.save(update_fields=["raw_model_response", "status", "error_message"])
            Question.objects.bulk_create([Question(quiz=quiz, **item) for item in questions])

        quiz = Quiz.objects.prefetch_related("questions").get(pk=quiz.pk)
        return Response(LatestBankPayload(quiz), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="sessions")
    def start_session(self, request, pk=None):
        lesson = self.get_object()
        quiz = lesson.quizzes.filter(status=Quiz.Status.READY).order_by("-created_at").first()
        if quiz is None:
            return Response(
                {"detail": "Gere o banco de questões antes de iniciar a sessão."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            question_ids = sample_question_ids(quiz, last_attempt_question_ids(quiz))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        attempt = Attempt.objects.create(quiz=quiz, question_ids=question_ids)
        attempt = Attempt.objects.select_related("quiz__lesson").get(pk=attempt.pk)
        return Response(_session_payload(attempt), status=status.HTTP_201_CREATED)


def LatestBankPayload(quiz: Quiz) -> dict:
    from study.api.serializers import LatestBankSerializer

    return LatestBankSerializer(quiz).data


class SessionViewSet(viewsets.GenericViewSet):
    queryset = Attempt.objects.select_related("quiz__lesson")

    def retrieve(self, request, pk=None):
        attempt = self.get_object()
        if attempt.status != Attempt.Status.IN_PROGRESS:
            return Response(
                {"detail": "Esta sessão já foi concluída."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(_session_payload(attempt))

    @action(detail=True, methods=["post"])
    def answers(self, request, pk=None):
        attempt = self.get_object()
        if attempt.status != Attempt.Status.IN_PROGRESS:
            return Response(
                {"detail": "Esta sessão já foi concluída."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SessionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted = {item["question_id"]: item for item in serializer.validated_data["answers"]}
        questions = {
            question.id: question
            for question in Question.objects.filter(id__in=attempt.question_ids)
        }
        results = []
        for qid in attempt.question_ids:
            question = questions.get(qid)
            if question is None:
                continue
            results.append(score_answer(question, submitted.get(qid, {})))

        scores = phase_scores(results)
        total = len(results)
        score = sum(1 for item in results if item["is_correct"])
        plan = build_study_plan(results)
        attempt.answers = serializer.validated_data["answers"]
        attempt.score = score
        attempt.phase_scores = scores
        attempt.study_plan = plan
        attempt.status = Attempt.Status.COMPLETED
        attempt.completed_at = timezone.now()
        attempt.save()
        return Response(
            {
                "id": attempt.id,
                "lesson": attempt.quiz.lesson_id,
                "status": attempt.status,
                "score": score,
                "total": total,
                "phase_scores": scores,
                "study_plan": plan,
                "results": results,
                "created_at": attempt.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
