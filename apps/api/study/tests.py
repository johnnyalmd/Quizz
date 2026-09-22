from django.test import TestCase
from rest_framework.test import APIClient

from study.domain.models import Attempt, Lesson, Question, Quiz
from study.services.quiz_generator import parse_cloze, parse_mcq
from study.services.recommendations import build_study_plan
from study.services.sampling import sample_question_ids
from study.services.scoring import score_answer


def _seed_bank(lesson: Lesson, prefix: str = "q") -> Quiz:
    quiz = Quiz.objects.create(lesson=lesson, status=Quiz.Status.READY)
    order = 0
    for kind, extra in (
        (Question.Kind.MCQ, {"correct_index": 1, "correct_values": []}),
        (Question.Kind.CLOZE, {"correct_index": None, "correct_values": ["alpha"]}),
        (Question.Kind.SCENARIO, {"correct_index": 0, "correct_values": []}),
    ):
        for index in range(8):
            prompt = f"{prefix}-{kind}-{index} usa ___." if kind == Question.Kind.CLOZE else f"{prefix}-{kind}-{index}"
            Question.objects.create(
                quiz=quiz,
                kind=kind,
                topic="HTTP",
                prompt=prompt,
                options=["alpha", "beta", "gamma", "delta"],
                explanation="porque",
                order=order,
                **extra,
            )
            order += 1
    return quiz


class ParseTests(TestCase):
    def test_parse_mcq(self):
        raw = '{"questions":[{"prompt":"P","options":["a","b","c","d"],"correct_index":2,"topic":"HTTP","explanation":"e"}]}'
        items = parse_mcq(raw)
        self.assertEqual(items[0]["correct_index"], 2)

    def test_parse_cloze(self):
        raw = '{"questions":[{"prompt":"GET é ___ .","options":["seguro","idempotente","x","y"],"correct_values":["seguro"],"topic":"HTTP","explanation":"e"}]}'
        items = parse_cloze(raw)
        self.assertEqual(items[0]["correct_values"], ["seguro"])


class SessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.lesson = Lesson.objects.create(
            title="HTTP",
            class_content="REST",
            learned_notes="GET é seguro",
        )
        self.quiz = _seed_bank(self.lesson)

    def test_create_lesson(self):
        response = self.client.post(
            "/api/lessons/",
            {"title": "A", "class_content": "c", "learned_notes": "n"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_session_hides_answers_and_scores(self):
        start = self.client.post(f"/api/lessons/{self.lesson.id}/sessions/")
        self.assertEqual(start.status_code, 201)
        session_id = start.json()["id"]
        self.assertEqual(len(start.json()["phases"]), 3)
        self.assertEqual(len(start.json()["phases"][0]["questions"]), 5)
        question = start.json()["phases"][0]["questions"][0]
        self.assertNotIn("correct_index", question)

        answers = []
        for phase in start.json()["phases"]:
            for item in phase["questions"]:
                if phase["kind"] == "cloze":
                    answers.append(
                        {
                            "question_id": item["id"],
                            "selected_values": ["alpha"],
                            "timed_out": False,
                        }
                    )
                else:
                    answers.append(
                        {
                            "question_id": item["id"],
                            "selected_index": 1 if phase["kind"] == "mcq" else 0,
                            "timed_out": False,
                        }
                    )
        result = self.client.post(
            f"/api/sessions/{session_id}/answers/",
            {"answers": answers},
            format="json",
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["score"], 15)
        self.assertEqual(result.json()["lesson"], self.lesson.id)
        self.assertEqual(result.json()["study_plan"][0]["missed"], 0)

    def test_retry_varies_when_possible(self):
        first_ids = sample_question_ids(self.quiz, [])
        Attempt.objects.create(
            quiz=self.quiz,
            question_ids=first_ids,
            status=Attempt.Status.COMPLETED,
        )
        second = sample_question_ids(self.quiz, first_ids)
        self.assertEqual(len(second), 15)
        self.assertNotEqual(set(first_ids), set(second))


class ScoringTests(TestCase):
    def test_timeout_is_wrong(self):
        lesson = Lesson.objects.create(title="t", class_content="c", learned_notes="n")
        quiz = Quiz.objects.create(lesson=lesson, status=Quiz.Status.READY)
        question = Question.objects.create(
            quiz=quiz,
            kind=Question.Kind.MCQ,
            prompt="p",
            options=["a", "b", "c", "d"],
            correct_index=1,
        )
        result = score_answer(question, {"selected_index": 1, "timed_out": True})
        self.assertFalse(result["is_correct"])

    def test_study_plan_groups_topics(self):
        plan = build_study_plan(
            [
                {"is_correct": False, "topic": "HTTP", "prompt": "GET?"},
                {"is_correct": True, "topic": "HTTP", "prompt": "POST?"},
            ]
        )
        self.assertEqual(plan[0]["topic"], "HTTP")
        self.assertEqual(plan[0]["missed"], 1)
