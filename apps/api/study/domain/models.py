from django.db import models


class Lesson(models.Model):
    title = models.CharField("título", max_length=255)
    class_content = models.TextField("conteúdo da aula")
    learned_notes = models.TextField("o que eu aprendi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Quiz(models.Model):
    """Question bank generated for a lesson."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        READY = "ready", "Pronto"
        FAILED = "failed", "Falhou"

    lesson = models.ForeignKey(Lesson, related_name="quizzes", on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    raw_model_response = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Banco #{self.pk} ({self.lesson.title})"


class Question(models.Model):
    class Kind(models.TextChoices):
        MCQ = "mcq", "Múltipla escolha"
        CLOZE = "cloze", "Lacuna"
        SCENARIO = "scenario", "Cenário"

    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.MCQ)
    topic = models.CharField(max_length=80, blank=True)
    prompt = models.TextField()
    options = models.JSONField(default=list)
    correct_index = models.PositiveSmallIntegerField(null=True, blank=True)
    correct_values = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["kind", "order", "id"]

    def __str__(self) -> str:
        return self.prompt[:80]


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Em andamento"
        COMPLETED = "completed", "Concluída"

    quiz = models.ForeignKey(Quiz, related_name="attempts", on_delete=models.CASCADE)
    question_ids = models.JSONField(default=list)
    answers = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    phase_scores = models.JSONField(default=list, blank=True)
    study_plan = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Sessão #{self.pk}"
