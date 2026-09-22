from django.contrib import admin

from study.domain.models import Attempt, Lesson, Question, Quiz


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title",)


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("id", "lesson", "status", "created_at")
    list_filter = ("status",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "kind", "topic", "order")
    list_filter = ("kind",)


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "quiz", "status", "score", "created_at")
    list_filter = ("status",)
