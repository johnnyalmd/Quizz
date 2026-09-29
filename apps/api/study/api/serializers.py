from rest_framework import serializers

from study.domain.models import Attempt, Lesson, Question, Quiz
from study.services.attempts import best_attempt_for_lesson


class LatestBankSerializer(serializers.ModelSerializer):
    counts = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "status", "error_message", "created_at", "counts"]

    def get_counts(self, obj: Quiz):
        questions = list(obj.questions.all()) if obj.pk else []
        return {
            "mcq": sum(1 for question in questions if question.kind == Question.Kind.MCQ),
            "cloze": sum(1 for question in questions if question.kind == Question.Kind.CLOZE),
            "scenario": sum(1 for question in questions if question.kind == Question.Kind.SCENARIO),
        }


class BestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attempt
        fields = ["id", "score", "total", "completed_at"]


class LessonSerializer(serializers.ModelSerializer):
    latest_bank = serializers.SerializerMethodField()
    best_attempt = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            "id",
            "title",
            "class_content",
            "learned_notes",
            "created_at",
            "updated_at",
            "latest_bank",
            "best_attempt",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "latest_bank", "best_attempt"]

    def get_latest_bank(self, obj: Lesson):
        quizzes = getattr(obj, "_prefetched_objects_cache", {}).get("quizzes")
        quiz = quizzes[0] if quizzes else obj.quizzes.first()
        if quiz is None:
            return None
        return LatestBankSerializer(quiz).data

    def get_best_attempt(self, obj: Lesson):
        attempt = best_attempt_for_lesson(obj)
        if attempt is None:
            return None
        return BestAttemptSerializer(attempt).data


class SessionQuestionSerializer(serializers.ModelSerializer):
    blank_count = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "kind", "prompt", "options", "blank_count"]

    def get_blank_count(self, obj: Question) -> int:
        return obj.prompt.count("___")


class SessionAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_index = serializers.IntegerField(required=False, allow_null=True)
    selected_values = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        required=False,
        default=list,
    )
    timed_out = serializers.BooleanField(default=False)


class SessionSubmitSerializer(serializers.Serializer):
    answers = SessionAnswerSerializer(many=True)

    def validate_answers(self, value):
        if not value:
            raise serializers.ValidationError("Envie as respostas da sessão.")
        return value
