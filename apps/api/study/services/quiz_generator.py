import json
import re

from django.conf import settings
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from study.domain.models import Question

BANK_PER_KIND = 8

SHARED_CONTEXT = """Você gera itens de estudo em português do Brasil.
Misture o que o aluno anotou (prioridade) com o conteúdo da aula (contexto).
Cada item precisa de um "topic" curto (1–3 palavras) para o plano de revisão.
Responda APENAS com JSON válido, sem markdown."""

MCQ_PROMPT = """Gere exatamente {count} questões de múltipla escolha.
Formato:
{{
  "questions": [
    {{
      "prompt": "enunciado",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "topic": "HTTP",
      "explanation": "por que a correta está certa"
    }}
  ]
}}
correct_index é inteiro 0–3. Sempre 4 alternativas plausíveis."""

CLOZE_PROMPT = """Gere exatamente {count} frases com lacunas para completar.
Use exatamente 1 ou 2 ocorrências de ___ no prompt.
"options" tem 4 chips (respostas corretas + distratores).
"correct_values" é a lista das palavras que preenchem as lacunas, na ordem.
Formato:
{{
  "questions": [
    {{
      "prompt": "GET é um verbo ___ e ___.",
      "options": ["seguro", "idempotente", "mutável", "lento"],
      "correct_values": ["seguro", "idempotente"],
      "topic": "HTTP",
      "explanation": "por que essas palavras completam a frase"
    }}
  ]
}}
Toda entrada de correct_values deve aparecer em options."""

SCENARIO_PROMPT = """Gere exatamente {count} cenários curtos.
"prompt" é uma mensagem/situação para o aluno.
Ofereça 4 opções e uma correta.
Formato:
{{
  "questions": [
    {{
      "prompt": "Você precisa buscar um recurso sem alterar estado. O que usa?",
      "options": ["GET", "POST", "PATCH", "DELETE"],
      "correct_index": 0,
      "topic": "HTTP",
      "explanation": "GET não altera estado"
    }}
  ]
}}
correct_index é inteiro 0–3."""


class QuizGenerationError(Exception):
    """Raised when Hugging Face or the JSON payload cannot produce a bank."""


def _extract_json(raw: str) -> dict | list:
    text = (raw or "").strip()
    if not text:
        raise QuizGenerationError("A IA devolveu uma resposta vazia.")
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    array_start = text.find("[")
    array_end = text.rfind("]")
    if array_start != -1 and array_end != -1 and array_end > array_start:
        try:
            return json.loads(text[array_start : array_end + 1])
        except json.JSONDecodeError as exc:
            raise QuizGenerationError("Não foi possível ler o JSON da IA.") from exc
    raise QuizGenerationError("A resposta da IA não contém JSON válido.")


def _questions_list(payload: dict | list) -> list:
    if isinstance(payload, list):
        questions = payload
    else:
        questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise QuizGenerationError("O JSON da IA não trouxe questões.")
    return questions


def parse_mcq(raw: str) -> list[dict]:
    cleaned = []
    for index, item in enumerate(_questions_list(_extract_json(raw))):
        prompt = str(item.get("prompt") or "").strip()
        options = item.get("options")
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        if not prompt:
            raise QuizGenerationError(f"MCQ {index + 1} sem enunciado.")
        if not isinstance(options, list) or len(options) != 4:
            raise QuizGenerationError(f"MCQ {index + 1} precisa de 4 alternativas.")
        options = [str(option).strip() for option in options]
        try:
            correct_index = int(item.get("correct_index"))
        except (TypeError, ValueError) as exc:
            raise QuizGenerationError(f"MCQ {index + 1} com correct_index inválido.") from exc
        if not 0 <= correct_index <= 3:
            raise QuizGenerationError(f"MCQ {index + 1} com correct_index fora de 0–3.")
        cleaned.append(
            {
                "kind": Question.Kind.MCQ,
                "prompt": prompt,
                "options": options,
                "correct_index": correct_index,
                "correct_values": [],
                "topic": topic,
                "explanation": explanation,
                "order": index,
            }
        )
    return cleaned


def parse_cloze(raw: str) -> list[dict]:
    cleaned = []
    for index, item in enumerate(_questions_list(_extract_json(raw))):
        prompt = str(item.get("prompt") or "").strip()
        options = item.get("options")
        values = item.get("correct_values")
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        blanks = prompt.count("___")
        if blanks not in (1, 2):
            raise QuizGenerationError(f"Lacuna {index + 1} precisa de 1 ou 2 ocorrências de ___.")
        if not isinstance(options, list) or len(options) != 4:
            raise QuizGenerationError(f"Lacuna {index + 1} precisa de 4 opções.")
        if not isinstance(values, list) or len(values) != blanks:
            raise QuizGenerationError(
                f"Lacuna {index + 1}: correct_values deve ter {blanks} item(ns)."
            )
        options = [str(option).strip() for option in options]
        values = [str(value).strip() for value in values]
        option_lower = {option.lower() for option in options}
        if any(value.lower() not in option_lower for value in values):
            raise QuizGenerationError(f"Lacuna {index + 1}: resposta ausente nas opções.")
        cleaned.append(
            {
                "kind": Question.Kind.CLOZE,
                "prompt": prompt,
                "options": options,
                "correct_index": None,
                "correct_values": values,
                "topic": topic,
                "explanation": explanation,
                "order": index,
            }
        )
    return cleaned


def parse_scenario(raw: str) -> list[dict]:
    cleaned = []
    for index, item in enumerate(_questions_list(_extract_json(raw))):
        prompt = str(item.get("prompt") or "").strip()
        options = item.get("options")
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        if not prompt:
            raise QuizGenerationError(f"Cenário {index + 1} sem mensagem.")
        if not isinstance(options, list) or len(options) != 4:
            raise QuizGenerationError(f"Cenário {index + 1} precisa de 4 alternativas.")
        options = [str(option).strip() for option in options]
        try:
            correct_index = int(item.get("correct_index"))
        except (TypeError, ValueError) as exc:
            raise QuizGenerationError(f"Cenário {index + 1} com correct_index inválido.") from exc
        if not 0 <= correct_index <= 3:
            raise QuizGenerationError(f"Cenário {index + 1} com correct_index fora de 0–3.")
        cleaned.append(
            {
                "kind": Question.Kind.SCENARIO,
                "prompt": prompt,
                "options": options,
                "correct_index": correct_index,
                "correct_values": [],
                "topic": topic,
                "explanation": explanation,
                "order": index,
            }
        )
    return cleaned


def _complete(system: str, user: str) -> str:
    token = settings.HF_TOKEN
    if not token:
        raise QuizGenerationError(
            "HF_TOKEN não configurado. Coloque o token no arquivo apps/api/.env."
        )
    client = InferenceClient(api_key=token, timeout=180)
    try:
        response = client.chat_completion(
            model=settings.HF_MODEL,
            messages=[
                {"role": "system", "content": f"{SHARED_CONTEXT}\n{system}"},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
            temperature=0.4,
        )
    except HfHubHTTPError as exc:
        detail = str(exc)
        if "not supported" in detail.lower() or "model_not_supported" in detail:
            raise QuizGenerationError(
                f"O modelo {settings.HF_MODEL} não está disponível no plano gratuito. Troque HF_MODEL."
            ) from exc
        raise QuizGenerationError(
            "Falha ao chamar o Hugging Face. Confira o token, o modelo e a cota."
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise QuizGenerationError(f"Erro inesperado ao gerar o banco: {exc}") from exc
    try:
        message = response.choices[0].message
        return (message.content or message.reasoning or "") or ""
    except (AttributeError, IndexError, TypeError) as exc:
        raise QuizGenerationError("A IA devolveu uma resposta inesperada.") from exc


def generate_bank(class_content: str, learned_notes: str) -> tuple[str, list[dict]]:
    count = getattr(settings, "HF_BANK_PER_KIND", BANK_PER_KIND)
    material = (
        f"Conteúdo da aula:\n{class_content.strip()}\n\n"
        f"O que eu aprendi:\n{learned_notes.strip()}\n"
    )
    combined_raw: list[str] = []
    questions: list[dict] = []

    specs = [
        (MCQ_PROMPT.format(count=count), parse_mcq),
        (CLOZE_PROMPT.format(count=count), parse_cloze),
        (SCENARIO_PROMPT.format(count=count), parse_scenario),
    ]
    for system, parser in specs:
        raw = _complete(system, f"{material}\nGere {count} itens.")
        combined_raw.append(raw)
        questions.extend(parser(raw))
    return "\n\n---\n\n".join(combined_raw), questions
