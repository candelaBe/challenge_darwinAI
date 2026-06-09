"""
content_generator.py
--------------------
Genera posts de LinkedIn/Instagram para Darwin AI.
Combina: tono aprendido + feedback histórico + post externo de inspiración.
Es un módulo puro — sin Streamlit, testeable desde terminal.
"""
from __future__ import annotations

import os
import json
import anthropic
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from tone_learner import (
    build_tone_system_prompt,
    load_examples,
    load_tone_profile,
)

# ── Config ───────────────────────────────────────────────────────────────────

MODEL      = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024
FEEDBACK_LOG     = Path("data/feedback_log.json")
APPROVED_LOG     = Path("data/approved_posts.json")

# ── Estructuras ───────────────────────────────────────────────────────────────

@dataclass
class GenerationRequest:
    platform: str               # "linkedin" | "instagram"
    topic: str                  # tema / noticia a curar
    objective: str              # "awareness" | "lead_gen" | "engagement" | "educación"
    language: str = "español"   # "español" | "inglés" | "portugués"
    inspiration_post: Optional[str] = None   # post externo pegado en la UI
    extra_context: Optional[str] = None      # notas adicionales del operador


@dataclass
class GeneratedPost:
    text: str
    platform: str
    topic: str
    model: str
    prompt_tokens: int
    completion_tokens: int


# ── Feedback histórico ────────────────────────────────────────────────────────

def load_recent_feedback(n: int = 5) -> list[dict]:
    """
    Carga los últimos N feedbacks de rechazos para inyectarlos al prompt.
    Solo feedbacks con razón explícita — los vacíos no aportan.
    """
    if not FEEDBACK_LOG.exists():
        return []
    entries = json.loads(FEEDBACK_LOG.read_text(encoding="utf-8"))
    with_reason = [e for e in entries if e.get("reason", "").strip()]
    return with_reason[-n:]


def format_feedback_for_prompt(feedback_entries: list[dict]) -> Optional[str]:
    """Formatea el feedback histórico como sección del prompt."""
    if not feedback_entries:
        return None
    lines = []
    for entry in feedback_entries:
        platform = entry.get("platform", "")
        reason   = entry.get("reason", "")
        tags     = ", ".join(entry.get("tags", []))
        line = f"- [{platform}] {reason}"
        if tags:
            line += f" (tags: {tags})"
        lines.append(line)
    return "\n".join(lines)


# ── Construcción del user prompt ──────────────────────────────────────────────

def build_user_prompt(req: GenerationRequest) -> str:
    """
    El user prompt es breve y específico.
    Todo el contexto de tono ya está en el system prompt.
    """
    parts = [
        f"Generá un post de {req.platform.capitalize()} para Darwin AI.",
        f"Tema: {req.topic}",
        f"Objetivo: {req.objective}",
    ]

    if req.inspiration_post:
        parts += [
            "",
            "## Post externo de inspiración",
            "Tomá la ESTRUCTURA o el ÁNGULO de este post, pero adaptalo completamente",
            "al tono de Darwin AI. No copies frases ni datos:",
            req.inspiration_post.strip(),
        ]

    if req.extra_context:
        parts += [
            "",
            "## Contexto adicional",
            req.extra_context.strip(),
        ]

    parts += [
        "",
        "Recordá: devolvé SOLO el texto del post, listo para publicar.",
    ]

    return "\n".join(parts)


# ── Generador principal ───────────────────────────────────────────────────────

def generate_post(
    req: GenerationRequest,
    api_key: Optional[str] = None,
) -> GeneratedPost:
    """
    Genera un post completo integrando tono, feedback e inspiración.

    Args:
        req:     parámetros de la solicitud
        api_key: si None, usa ANTHROPIC_API_KEY del entorno

    Returns:
        GeneratedPost con el texto y métricas de uso
    """
    # Cargar contexto
    profile  = load_tone_profile()
    examples = load_examples()
    recent_fb = load_recent_feedback()
    feedback_summary = format_feedback_for_prompt(recent_fb)

    # Construir prompts
    system_prompt = build_tone_system_prompt(
        platform=req.platform,
        language=req.language,
        examples=examples,
        profile=profile,
        feedback_summary=feedback_summary,
    )
    user_prompt = build_user_prompt(req)

    # Llamada a la API de Anthropic
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()

    return GeneratedPost(
        text=text,
        platform=req.platform,
        topic=req.topic,
        model=MODEL,
        prompt_tokens=response.usage.input_tokens,
        completion_tokens=response.usage.output_tokens,
    )


# ── Persistencia de resultados ────────────────────────────────────────────────

def save_approved(post: GeneratedPost) -> None:
    """Guarda un post aprobado — se usa como ejemplo de tono futuro."""
    APPROVED_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if APPROVED_LOG.exists():
        entries = json.loads(APPROVED_LOG.read_text(encoding="utf-8"))

    entries.append({
        "text": post.text,
        "platform": post.platform,
        "topic": post.topic,
        "model": post.model,
    })
    APPROVED_LOG.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # También registrar en tone_learner para que influya en el próximo prompt
    from tone_learner import add_approved_post
    add_approved_post(post.text, post.platform)


def save_rejected(
    post: GeneratedPost,
    reason: str,
    tags: Optional[list[str]] = None,
) -> None:
    """Guarda un post rechazado con motivo — alimenta el feedback loop."""
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if FEEDBACK_LOG.exists():
        entries = json.loads(FEEDBACK_LOG.read_text(encoding="utf-8"))

    entries.append({
        "text": post.text,
        "platform": post.platform,
        "topic": post.topic,
        "reason": reason,
        "tags": tags or [],
    })
    FEEDBACK_LOG.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── CLI / smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: export ANTHROPIC_API_KEY=... antes de correr este módulo")
        sys.exit(1)

    print("=== Smoke test: content_generator ===\n")

    req = GenerationRequest(
        platform="linkedin",
        topic="Cómo los agentes conversacionales reducen el churn en ecommerce LATAM",
        objective="lead_gen",
        inspiration_post=(
            "Most companies spend thousands acquiring customers "
            "and almost nothing keeping them. "
            "One conversation at the right moment changes everything."
        ),
    )

    print(f"Generando post para {req.platform} — tema: {req.topic}\n")
    post = generate_post(req)

    print("── POST GENERADO ──────────────────────────────────")
    print(post.text)
    print("───────────────────────────────────────────────────")
    print(f"\nTokens usados: {post.prompt_tokens} prompt / {post.completion_tokens} completion")
    print(f"Modelo: {post.model}")

    # Simular rechazo con feedback
    save_rejected(
        post,
        reason="Demasiado genérico, no menciona LATAM ni un caso concreto",
        tags=["falta_latam", "muy_generico"],
    )
    print("\n✓ Feedback de rechazo guardado")

    # Segunda generación — ya incorpora el feedback anterior
    print("\n── REGENERANDO con feedback ──────────────────────")
    post2 = generate_post(req)
    print(post2.text)
    print("───────────────────────────────────────────────────")
    print(f"\nTokens: {post2.prompt_tokens} prompt / {post2.completion_tokens} completion")
