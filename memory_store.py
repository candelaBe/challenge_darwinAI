"""
memory_store.py
---------------
Capa de persistencia centralizada. Todo lo que toca disco pasa por acá.
El resto del sistema (generador, UI) importa desde aquí — nunca escribe JSON directamente.

Schema de archivos:
  data/tone_profile.json      → perfil de tono de Darwin AI
  data/tone_examples.json     → posts reales usados como few-shot
  data/approved_posts.json    → posts aprobados por el equipo
  data/feedback_log.json      → rechazos con motivo y tags
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

DATA_DIR           = Path("data")
TONE_PROFILE_PATH  = DATA_DIR / "tone_profile.json"
TONE_EXAMPLES_PATH = DATA_DIR / "tone_examples.json"
APPROVED_PATH      = DATA_DIR / "approved_posts.json"
FEEDBACK_PATH      = DATA_DIR / "feedback_log.json"


# ── Schema de referencia ──────────────────────────────────────────────────────
#
# tone_profile.json
# {
#   "voice_traits":        [str],   rasgos de voz de Darwin AI
#   "structural_patterns": [str],   patrones de estructura observados
#   "vocabulary_signals":  [str],   palabras/frases características
#   "avoid_patterns":      [str],   qué NUNCA hacer
#   "platform_notes":      {        diferencias por red social
#     "linkedin":  str,
#     "instagram": str
#   }
# }
#
# tone_examples.json
# [
#   {
#     "text":        str,           texto del post
#     "platform":    str,           "linkedin" | "instagram"
#     "performance": str,           "high" | "medium" | "low"
#     "notes":       str | null,    observaciones manuales
#     "word_count":  int
#   }
# ]
#
# approved_posts.json
# [
#   {
#     "text":      str,
#     "platform":  str,
#     "topic":     str,
#     "approved_at": str            ISO timestamp
#   }
# ]
#
# feedback_log.json
# [
#   {
#     "text":       str,            texto del post rechazado
#     "platform":   str,
#     "topic":      str,
#     "reason":     str,            motivo libre del operador
#     "tags":       [str],          tags estructurados (falta_latam, muy_formal, etc.)
#     "rejected_at": str            ISO timestamp
#   }
# ]


# ── Primitivas de I/O ─────────────────────────────────────────────────────────

def _read(path: Path, default: Any) -> Any:
    """Lee JSON desde disco. Devuelve `default` si el archivo no existe."""
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
    """Escribe JSON a disco, creando el directorio si hace falta."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append(path: Path, entry: dict) -> None:
    """Agrega una entrada a una lista JSON persistida."""
    entries = _read(path, [])
    entries.append(entry)
    _write(path, entries)


# ── Tone profile ──────────────────────────────────────────────────────────────

def read_tone_profile() -> dict:
    return _read(TONE_PROFILE_PATH, {})


def write_tone_profile(profile: dict) -> None:
    _write(TONE_PROFILE_PATH, profile)


# ── Tone examples ─────────────────────────────────────────────────────────────

def read_tone_examples() -> list[dict]:
    return _read(TONE_EXAMPLES_PATH, [])


def write_tone_examples(examples: list[dict]) -> None:
    _write(TONE_EXAMPLES_PATH, examples)


def append_tone_example(example: dict) -> None:
    """Agrega un ejemplo sin reescribir toda la lista manualmente."""
    _append(TONE_EXAMPLES_PATH, example)


# ── Approved posts ────────────────────────────────────────────────────────────

def read_approved() -> list[dict]:
    return _read(APPROVED_PATH, [])


def append_approved(entry: dict) -> None:
    from datetime import datetime, timezone
    entry.setdefault("approved_at", datetime.now(timezone.utc).isoformat())
    _append(APPROVED_PATH, entry)


# ── Feedback log ──────────────────────────────────────────────────────────────

def read_feedback() -> list[dict]:
    return _read(FEEDBACK_PATH, [])


def append_feedback(entry: dict) -> None:
    from datetime import datetime, timezone
    entry.setdefault("rejected_at", datetime.now(timezone.utc).isoformat())
    _append(FEEDBACK_PATH, entry)


def read_recent_feedback(n: int = 5) -> list[dict]:
    """Últimos N feedbacks con motivo explícito — para inyectar al prompt."""
    all_fb = read_feedback()
    with_reason = [e for e in all_fb if e.get("reason", "").strip()]
    return with_reason[-n:]


# ── Stats (para sidebar de Streamlit) ────────────────────────────────────────

def get_memory_stats() -> dict:
    """
    Resumen del estado de la memoria — se muestra en la UI.
    Llamada barata: solo cuenta entradas, no carga textos.
    """
    return {
        "tone_examples":   len(read_tone_examples()),
        "approved_posts":  len(read_approved()),
        "rejected_posts":  len(read_feedback()),
        "has_tone_profile": TONE_PROFILE_PATH.exists(),
    }


# ── Reset (útil para tests y demos) ──────────────────────────────────────────

def reset_feedback() -> None:
    """Borra solo el log de feedback. El tono y los ejemplos se mantienen."""
    if FEEDBACK_PATH.exists():
        FEEDBACK_PATH.unlink()


def reset_all() -> None:
    """Borra toda la memoria. Usar solo en desarrollo."""
    for path in [TONE_PROFILE_PATH, TONE_EXAMPLES_PATH, APPROVED_PATH, FEEDBACK_PATH]:
        if path.exists():
            path.unlink()


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Smoke test: memory_store ===\n")

    # Write / read tone profile
    sample_profile = {"voice_traits": ["Directo", "LATAM-first"], "platform_notes": {}}
    write_tone_profile(sample_profile)
    loaded = read_tone_profile()
    assert loaded["voice_traits"] == sample_profile["voice_traits"]
    print("✓ tone_profile read/write")

    # Append tone example
    append_tone_example({"text": "Post de prueba", "platform": "linkedin",
                         "performance": "high", "notes": None, "word_count": 4})
    examples = read_tone_examples()
    assert len(examples) >= 1
    print(f"✓ tone_examples append → {len(examples)} ejemplo(s)")

    # Append approved
    append_approved({"text": "Post aprobado", "platform": "instagram", "topic": "IA"})
    approved = read_approved()
    assert approved[-1]["approved_at"]
    print(f"✓ approved_posts append con timestamp")

    # Append feedback
    append_feedback({"text": "Post rechazado", "platform": "linkedin",
                     "topic": "test", "reason": "Muy genérico", "tags": ["muy_generico"]})
    recent = read_recent_feedback(n=3)
    assert recent[-1]["reason"] == "Muy genérico"
    print(f"✓ feedback_log append + read_recent_feedback")

    # Stats
    stats = get_memory_stats()
    print(f"\n✓ Stats: {stats}")

    # Reset feedback solo
    reset_feedback()
    assert read_feedback() == []
    print("✓ reset_feedback — feedback limpio, el resto intacto")

    print("\nTodos los tests pasaron.")
