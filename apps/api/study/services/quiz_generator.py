import json
import re

from django.conf import settings
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from study.domain.models import Question

BANK_PER_KIND = 8

SHARED_CONTEXT = """Você gera itens de estudo em português do Brasil.
Use SOMENTE fatos que aparecem no conteúdo da aula ou nas anotações do aluno.
Não invente termos, APIs, datas ou conceitos que não estejam nesse material.
Cada item precisa de um "topic" curto (1–3 palavras) tirado do material.
Responda APENAS com JSON válido, sem markdown."""

MCQ_PROMPT = """Gere exatamente {count} questões de múltipla escolha sobre o material.
Regras:
- O enunciado e as 4 opções devem ser texto visível e completo (nunca só A/B/C/D).
- Tem que existir UMA opção realmente correta, que responde ao enunciado.
- Se a pergunta pede a diferença entre dois conceitos, a correta deve dizer essa diferença.
  Não inverta definições. Não use uma característica comum (ex.: os dois usam cobre/fibra) como se fosse a diferença.
- A resposta correta OBRIGATORIAMENTE aparece em options, no índice correct_index.
- As 3 erradas são do mesmo assunto, mas estão erradas.
- correct_index é inteiro 0–3 e options[correct_index] é a resposta certa.
Formato:
{{
  "questions": [
    {{
      "prompt": "enunciado baseado no material",
      "options": ["resposta A", "resposta B", "resposta C", "resposta D"],
      "correct_index": 0,
      "correct_answer": "resposta A",
      "topic": "HTTP",
      "explanation": "por que a correta está certa, usando o material"
    }}
  ]
}}"""

CLOZE_PROMPT = """Gere exatamente {count} frases com lacunas para completar, só com o material.
Regras:
- Use exatamente 1 ou 2 ocorrências de ___ no prompt.
- "options" tem 4 chips visíveis: as respostas corretas e distratores do mesmo assunto.
- "correct_values" preenche as lacunas na ordem e CADA valor deve ser igual a um item de options.
- Não use opções vazias nem letras soltas (A/B/C/D).
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
}}"""

SCENARIO_PROMPT = """Gere exatamente {count} cenários curtos baseados só no material.
Regras:
- "prompt" é uma mensagem/situação clara.
- As 4 opções são respostas visíveis e completas.
- A correta está em options[correct_index] e também em correct_answer, com o mesmo texto.
Formato:
{{
  "questions": [
    {{
      "prompt": "Você precisa buscar um recurso sem alterar estado. O que usa?",
      "options": ["GET", "POST", "PATCH", "DELETE"],
      "correct_index": 0,
      "correct_answer": "GET",
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


def _clean_options(options, index: int, label: str) -> list[str]:
    if not isinstance(options, list) or len(options) != 4:
        raise QuizGenerationError(f"{label} {index + 1} precisa de 4 alternativas visíveis.")
    cleaned = [str(option).strip() for option in options]
    if any(not option for option in cleaned):
        raise QuizGenerationError(f"{label} {index + 1} tem opção vazia.")
    if len(set(item.lower() for item in cleaned)) < 4:
        raise QuizGenerationError(f"{label} {index + 1} tem opções repetidas.")
    letters_only = all(option.upper() in {"A", "B", "C", "D"} and len(option) == 1 for option in cleaned)
    if letters_only:
        raise QuizGenerationError(
            f"{label} {index + 1} precisa de respostas em texto, não só letras A–D."
        )
    return cleaned


def _match_option(value: str, options: list[str]) -> str | None:
    needle = str(value).strip().lower()
    for option in options:
        if option.lower() == needle:
            return option
    return None


def _resolve_correct_index(item: dict, options: list[str], index: int, label: str) -> int:
    answer = item.get("correct_answer")
    if answer:
        matched = _match_option(str(answer), options)
        if matched is None:
            raise QuizGenerationError(
                f"{label} {index + 1}: a resposta correta não está nas opções visíveis."
            )
        return next(i for i, option in enumerate(options) if option.lower() == matched.lower())

    raw_index = item.get("correct_index")
    try:
        correct_index = int(raw_index)
    except (TypeError, ValueError) as exc:
        raise QuizGenerationError(f"{label} {index + 1} com correct_index inválido.") from exc
    if not 0 <= correct_index <= 3:
        raise QuizGenerationError(f"{label} {index + 1} com correct_index fora de 0–3.")
    return correct_index


def _assert_mcq_has_real_answer(prompt: str, options: list[str], correct_index: int, index: int) -> None:
    text = prompt.lower()
    correct = options[correct_index].lower()
    inverted = (
        "lan cobre área ampla",
        "lan cobre uma área ampla",
        "wan cobre área local",
        "wan cobre uma área local",
        "lan cobre area ampla",
        "wan cobre area local",
    )
    if any(phrase in correct for phrase in inverted):
        raise QuizGenerationError(
            f"MCQ {index + 1}: a opção marcada como certa inverte o conceito e está errada."
        )

    asks_difference = "diferença" in text or "diferenca" in text
    if not asks_difference:
        return

    media_hints = ("cobre", "fibra", "sem fio", "wireless", "transmissões", "transmissoes")
    contrast_hints = ("local", "ampla", "geográfica", "geografica", "curta", "longa", "maior", "menor")
    media_hits = sum(1 for hint in media_hints if hint in correct)
    contrast_hits = sum(1 for hint in contrast_hints if hint in correct)
    if media_hits >= 2 and contrast_hits == 0:
        raise QuizGenerationError(
            f"MCQ {index + 1}: a opção marcada como certa não descreve a diferença pedida no enunciado."
        )


def parse_mcq(raw: str) -> list[dict]:
    cleaned = []
    for index, item in enumerate(_questions_list(_extract_json(raw))):
        prompt = str(item.get("prompt") or "").strip()
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        if not prompt:
            raise QuizGenerationError(f"MCQ {index + 1} sem enunciado.")
        options = _clean_options(item.get("options"), index, "MCQ")
        correct_index = _resolve_correct_index(item, options, index, "MCQ")
        _assert_mcq_has_real_answer(prompt, options, correct_index, index)
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
        values = item.get("correct_values")
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        blanks = prompt.count("___")
        if blanks not in (1, 2):
            raise QuizGenerationError(f"Lacuna {index + 1} precisa de 1 ou 2 ocorrências de ___.")
        options = _clean_options(item.get("options"), index, "Lacuna")
        if not isinstance(values, list) or len(values) != blanks:
            raise QuizGenerationError(
                f"Lacuna {index + 1}: correct_values deve ter {blanks} item(ns)."
            )
        aligned = []
        for value in values:
            matched = _match_option(str(value), options)
            if matched is None:
                raise QuizGenerationError(
                    f"Lacuna {index + 1}: a resposta '{value}' não está nas opções visíveis."
                )
            aligned.append(matched)
        values = aligned
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
        explanation = str(item.get("explanation") or "").strip()
        topic = str(item.get("topic") or "").strip()[:80]
        if not prompt:
            raise QuizGenerationError(f"Cenário {index + 1} sem mensagem.")
        options = _clean_options(item.get("options"), index, "Cenário")
        correct_index = _resolve_correct_index(item, options, index, "Cenário")
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
        raw = _complete(
            system,
            (
                f"{material}\nGere {count} itens usando só esse material. "
                "Toda resposta correta precisa aparecer nas opções."
            ),
        )
        combined_raw.append(raw)
        questions.extend(parser(raw))
    return "\n\n---\n\n".join(combined_raw), questions
