"""
tone_learner.py
---------------
Aprende y representa el tono de Darwin AI a partir de posts de ejemplo.
Genera un system prompt dinámico que inyecta ese tono al generador.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Constantes ──────────────────────────────────────────────────────────────

TONE_PROFILE_PATH = Path("data/tone_profile.json")
EXAMPLES_PATH     = Path("data/tone_examples.json")

MAX_EXAMPLES_IN_PROMPT = 5   # más ejemplos = mejor tono, pero más tokens
MIN_WORDS_PER_POST     = 20  # filtra posts demasiado cortos para aprender


# ── Estructuras de datos ─────────────────────────────────────────────────────

@dataclass
class ToneProfile:
    """
    Perfil de tono extraído de los ejemplos.
    Se persiste en JSON y se actualiza con cada nueva aprobación.
    """
    voice_traits: list[str]        = field(default_factory=list)  # rasgos descriptivos del tono
    structural_patterns: list[str] = field(default_factory=list)  # patrones de estructura observados
    vocabulary_signals: list[str]  = field(default_factory=list)  # palabras/frases características
    avoid_patterns: list[str]      = field(default_factory=list)  # qué NO hace Darwin AI
    platform_notes: dict           = field(default_factory=dict)  # diferencias LinkedIn vs Instagram

    @classmethod
    def default_darwin(cls) -> "ToneProfile":
        """
        Perfil base para Darwin AI.
        Editá estos valores con lo que sabés del tono real de la empresa.
        Se irá refinando automáticamente con el feedback.
        """
        return cls(
            voice_traits=[
                "Experto pero accesible — habla de IA sin jerga innecesaria",
                "Optimista y concreto — promesas respaldadas por casos reales",
                "LATAM-first — menciona mercados latinoamericanos con especificidad",
                "Directo — va al punto en las primeras dos líneas",
                "Storyteller — usa anécdotas de clientes reales (anonimizadas)",
            ],
            structural_patterns=[
                "Abre con un dato sorprendente o pregunta retórica",
                "Desarrollo en 2-3 ideas conectadas, no listas largas",
                "Cierra con CTA claro: 'escribinos', 'agendá una demo', 'contanos'",
                "Usa saltos de línea generosamente — párrafos de 1-2 oraciones",
                "Emojis estratégicos: 1-3 por post, no decorativos sino funcionales",
            ],
            vocabulary_signals=[
                "agente conversacional", "automatización", "LATAM", "escala",
                "resultado", "cliente", "implementar", "conversación", "ROI",
            ],
            avoid_patterns=[
                "Frases genéricas de motivación sin sustancia ('el futuro es hoy')",
                "Listas de más de 5 ítems con bullets",
                "Lenguaje corporativo frío y distante",
                "Hashtags en exceso (máximo 3-5 en Instagram, 1-2 en LinkedIn)",
                "Pasivo: 'fue implementado', 'se realizó' → preferir voz activa",
            ],
            platform_notes={
                "linkedin": (
                    "Tono más formal pero no rígido. "
                    "Posts de 150-300 palabras. "
                    "Foco en ROI y casos de negocio. "
                    "Hashtags: 2-3 muy relevantes."
                ),
                "instagram": (
                    "Más visual y dinámico. "
                    "Texto más corto: 80-150 palabras en caption. "
                    "Emojis más presentes. "
                    "CTA hacia bio link o DMs. "
                    "Hashtags: 5-10, mezcla de nicho y amplio."
                ),
            }
        )


@dataclass
class ToneExample:
    """Un post real de Darwin AI usado como ejemplo de tono."""
    text: str
    platform: str          # "linkedin" | "instagram"
    performance: str       # "high" | "medium" | "low" — si lo sabés
    notes: Optional[str]   # observaciones manuales opcionales
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.text.split())


# ── Carga y persistencia ──────────────────────────────────────────────────────

def load_tone_profile() -> ToneProfile:
    if TONE_PROFILE_PATH.exists():
        data = json.loads(TONE_PROFILE_PATH.read_text(encoding="utf-8"))
        return ToneProfile(**data)
    # Primera vez: usar el perfil base y guardarlo
    profile = ToneProfile.default_darwin()
    save_tone_profile(profile)
    return profile


def save_tone_profile(profile: ToneProfile) -> None:
    TONE_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TONE_PROFILE_PATH.write_text(
        json.dumps(asdict(profile), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_examples() -> list[ToneExample]:
    if not EXAMPLES_PATH.exists():
        return []
    data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    return [ToneExample(**e) for e in data]


def save_examples(examples: list[ToneExample]) -> None:
    EXAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXAMPLES_PATH.write_text(
        json.dumps([asdict(e) for e in examples], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── Ingesta de nuevos ejemplos ────────────────────────────────────────────────

def add_example(
    text: str,
    platform: str,
    performance: str = "medium",
    notes: Optional[str] = None
) -> ToneExample:
    """
    Agrega un nuevo post de Darwin AI como ejemplo de tono.
    Limpia espacios extras y valida la longitud mínima.
    """
    text = _clean_text(text)

    if len(text.split()) < MIN_WORDS_PER_POST:
        raise ValueError(
            f"El post tiene menos de {MIN_WORDS_PER_POST} palabras — "
            "demasiado corto para aprender tono."
        )

    platform = platform.lower().strip()
    if platform not in ("linkedin", "instagram"):
        raise ValueError("platform debe ser 'linkedin' o 'instagram'")

    example = ToneExample(text=text, platform=platform,
                          performance=performance, notes=notes)

    examples = load_examples()
    examples.append(example)
    save_examples(examples)

    return example


def add_approved_post(text: str, platform: str) -> None:
    """
    Atajo: agrega un post que fue aprobado (y posiblemente publicado)
    como nuevo ejemplo de alta calidad.
    """
    add_example(text, platform, performance="high", notes="Aprobado por el equipo")


# ── Construcción del system prompt ───────────────────────────────────────────

def build_tone_system_prompt(
    platform: str,
    language: str = "español",
    examples: Optional[list[ToneExample]] = None,
    profile: Optional[ToneProfile] = None,
    feedback_summary: Optional[str] = None,
) -> str:
    """
    Construye el system prompt completo para el generador.
    Combina: perfil de tono + formato editorial + idioma + ejemplos few-shot + feedback.

    Args:
        platform:         "linkedin" o "instagram"
        language:         "español" | "inglés" | "portugués"
        examples:         lista de ejemplos (si None, carga desde disco)
        profile:          perfil de tono (si None, carga desde disco)
        feedback_summary: resumen de feedback reciente para inyectar

    Returns:
        System prompt listo para pasar a la Claude API.
    """
    if profile is None:
        profile = load_tone_profile()
    if examples is None:
        examples = load_examples()

    platform_note = profile.platform_notes.get(platform, "")

    # Instrucción de idioma
    language_note = {
        "español":   "Escribí el post completamente en español (es-LATAM). Tuteo, no voseo formal.",
        "inglés":    "Write the post entirely in English. Professional tone, no slang.",
        "portugués": "Escreva o post completamente em português (pt-BR). Tom profissional e direto.",
    }.get(language, f"Escribí el post en {language}.")

    # Seleccionar los mejores ejemplos para este platform
    platform_examples = _select_best_examples(examples, platform)

    prompt_parts = [
        "Sos el editor de contenido de Darwin AI, una startup de agentes conversacionales",
        "que opera en LATAM. Tu rol es curar noticias de IA y automatización y adaptarlas",
        "al formato editorial propio de Darwin AI para redes sociales.",
        "",
        "## Rasgos de voz de Darwin AI",
        *[f"- {trait}" for trait in profile.voice_traits],
        "",
        "## FORMATO EDITORIAL OBLIGATORIO",
        "Cada post debe seguir esta estructura exacta, sin excepciones:",
        "",
        "[emoji temático] **Titular de la noticia** (máx 12 palabras, mayúscula solo al inicio)",
        "",
        "💡 [Señal clave: el dato o hecho más relevante en una oración]",
        "",
        "⚡ [Dato o hecho concreto con cifra]",
        "⚡ [Dato o hecho concreto con cifra]",
        "⚡ [Dato o hecho concreto con cifra]",
        "(entre 3 y 5 bullets ⚡, nunca más)",
        "",
        "🤯 [Takeaway: impacto concreto para empresas en LATAM, una oración]",
        "",
        "Fuente: [Nombre del medio]",
        "",
        *[f"- {p}" for p in profile.structural_patterns
          if not p.startswith("FORMATO FIJO")],  # evitar duplicar la sección
        "",
        "## Vocabulario característico",
        "Usá naturalmente cuando sea relevante:",
        ", ".join(profile.vocabulary_signals),
        "",
        "## Qué NUNCA hacer",
        *[f"- {p}" for p in profile.avoid_patterns],
        "",
        f"## Idioma del post",
        language_note,
        "",
        f"## Instrucciones específicas para {platform.capitalize()}",
        platform_note,
    ]

    # Inyectar feedback si existe
    if feedback_summary:
        prompt_parts += [
            "",
            "## Feedback del equipo sobre posts anteriores",
            "Incorporá estas correcciones en el post que vas a generar:",
            feedback_summary,
        ]

    # Few-shot examples
    if platform_examples:
        prompt_parts += [
            "",
            f"## Ejemplos reales de posts de Darwin AI para {platform.capitalize()}",
            "Estos son posts que funcionaron bien. Aprendé el estilo, NO los copies:",
        ]
        for i, ex in enumerate(platform_examples, 1):
            label = f"[Ejemplo {i}" + (f" — {ex.performance} performance" if ex.performance != "medium" else "") + "]"
            prompt_parts += [label, ex.text, ""]

    prompt_parts += [
        "## Tu tarea",
        "Generá UN post para la red indicada. Respetá el tono de Darwin AI.",
        "Devolvé SOLO el texto del post, sin explicaciones ni metadatos.",
    ]

    return "\n".join(prompt_parts)


# ── Actualización del perfil con feedback ─────────────────────────────────────

def update_profile_from_feedback(
    feedback_tags: list[str],
    profile: Optional[ToneProfile] = None
) -> ToneProfile:
    """
    Actualiza el perfil de tono basado en tags de feedback recurrentes.
    Los tags son strings como: 'muy_formal', 'falta_cta', 'tono_correcto', etc.

    Solo modifica el perfil si un tag aparece con frecuencia suficiente
    (lógica extensible — hoy es un placeholder para la segunda iteración).
    """
    if profile is None:
        profile = load_tone_profile()

    # Mapeo de tags → ajustes al perfil
    # Expandir esto con el feedback real que recibas
    tag_actions = {
        "muy_formal":    lambda p: p.voice_traits.append("Evitá lenguaje demasiado formal — hablá como un colega experto"),
        "falta_cta":     lambda p: p.structural_patterns.append("Siempre terminá con un CTA explícito y específico"),
        "muy_largo":     lambda p: p.avoid_patterns.append("Posts de más de 300 palabras en LinkedIn pierden engagement"),
        "falta_latam":   lambda p: p.voice_traits.append("Mencioná LATAM o un mercado específico si es relevante"),
    }

    for tag in feedback_tags:
        action = tag_actions.get(tag)
        if action:
            action(profile)

    # Deduplicar listas
    profile.voice_traits        = list(dict.fromkeys(profile.voice_traits))
    profile.structural_patterns = list(dict.fromkeys(profile.structural_patterns))
    profile.avoid_patterns      = list(dict.fromkeys(profile.avoid_patterns))

    save_tone_profile(profile)
    return profile


# ── Helpers internos ──────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Normaliza espacios y saltos de línea."""
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)   # máximo dos saltos seguidos
    text = re.sub(r" {2,}", " ", text)        # elimina espacios dobles
    return text


def _select_best_examples(
    examples: list[ToneExample],
    platform: str,
    n: int = MAX_EXAMPLES_IN_PROMPT
) -> list[ToneExample]:
    """
    Selecciona los mejores N ejemplos para el platform dado.
    Prioridad: high > medium > low performance.
    """
    filtered = [e for e in examples if e.platform == platform]

    priority = {"high": 0, "medium": 1, "low": 2}
    filtered.sort(key=lambda e: priority.get(e.performance, 1))

    return filtered[:n]


# ── CLI de carga de ejemplos ──────────────────────────────────────────────────

def cli_load_examples():
    """
    Modo interactivo para cargar posts de Darwin AI desde la terminal.
    Usá esto para alimentar el sistema con ejemplos reales.
    """
    print("\n=== Cargador de ejemplos de tono — Darwin AI ===")
    print("Pegá posts reales de Darwin AI para que el sistema aprenda el estilo.")
    print("Escribí 'FIN' en una línea nueva para terminar el texto.\n")

    while True:
        platform = input("Platform (linkedin/instagram/q para salir): ").strip().lower()
        if platform == "q":
            break
        if platform not in ("linkedin", "instagram"):
            print("Opción inválida.")
            continue

        performance = input("Performance (high/medium/low) [medium]: ").strip() or "medium"
        notes       = input("Notas opcionales (Enter para omitir): ").strip() or None

        print("Pegá el texto del post (escribí FIN en línea nueva para terminar):")
        lines = []
        while True:
            line = input()
            if line.strip() == "FIN":
                break
            lines.append(line)

        text = "\n".join(lines)

        try:
            ex = add_example(text, platform, performance, notes)
            print(f"\n✓ Ejemplo guardado ({ex.word_count} palabras, platform: {platform})\n")
        except ValueError as e:
            print(f"\n✗ Error: {e}\n")


# ── Demo / smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--load" in sys.argv:
        cli_load_examples()
    else:
        # Smoke test: genera un system prompt de ejemplo
        profile = load_tone_profile()
        prompt  = build_tone_system_prompt("linkedin", profile=profile)

        print("=== System prompt generado ===\n")
        print(prompt)
        print(f"\n[{len(prompt.split())} palabras — {len(prompt)} caracteres]")
