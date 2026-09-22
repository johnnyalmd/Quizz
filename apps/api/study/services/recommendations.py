def build_study_plan(results: list[dict]) -> list[dict]:
    missed: dict[str, list[dict]] = {}
    for item in results:
        if item.get("is_correct"):
            continue
        topic = (item.get("topic") or "").strip() or "Geral"
        missed.setdefault(topic, []).append(item)

    plan = []
    for topic, items in missed.items():
        examples = "; ".join(entry["prompt"][:80] for entry in items[:2])
        plan.append(
            {
                "topic": topic,
                "missed": len(items),
                "advice": (
                    f"Errou {len(items)} questão(ões) em {topic}. "
                    f"Revise este tópico nas suas anotações e no conteúdo da aula. "
                    f"Exemplos: {examples}."
                ),
            }
        )
    if not plan:
        plan.append(
            {
                "topic": "Tudo certo",
                "missed": 0,
                "advice": "Você acertou tudo nesta sessão. Retente para variar as perguntas e fixar ainda mais.",
            }
        )
    return plan
