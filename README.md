# Darwin AI · Content Studio

Sistema de generación de posts para LinkedIn e Instagram. Aprende el tono editorial de Darwin AI, acepta posts externos como inspiración, incorpora feedback humano y mejora con cada aprobación.

---

## Estructura del proyecto

```
darwin-ai-content-studio/
│
├── app.py                  # UI Streamlit — punto de entrada principal
├── content_generator.py    # Generador de posts via Claude API (Anthropic)
├── tone_learner.py         # Perfil de tono + construcción de system prompt
├── memory_store.py         # Capa de persistencia centralizada (todo I/O a disco)
│
├── data/                   # Generado automáticamente en el primer run
│   ├── tone_profile.json   # Perfil de voz y formato editorial de Darwin AI
│   ├── tone_examples.json  # Posts reales usados como ejemplos few-shot
│   ├── approved_posts.json # Historial de posts aprobados
│   └── feedback_log.json   # Rechazos con motivo y tags estructurados
│
├── requirements.txt
└── README.md
```

### Responsabilidad de cada módulo

| Archivo | Qué hace | Qué NO hace |
|---|---|---|
| `app.py` | UI, session state, flujo de aprobación | No escribe a disco directamente |
| `content_generator.py` | Llama a Claude API, construye prompts | No sabe nada de Streamlit |
| `tone_learner.py` | Perfil de tono, ejemplos few-shot, system prompt | No llama a ninguna API |
| `memory_store.py` | Lee y escribe todos los JSON | No genera contenido |

---

## Requisitos

- Python 3.9+
- Anthropic API key — obtener en [console.anthropic.com](https://console.anthropic.com)

---

## Setup

```bash
# 1. Clonar o descomprimir el proyecto
cd darwin-ai-content-studio

# 2. Crear entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
.venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key
export ANTHROPIC_API_KEY=tu_api_key_aquí   # macOS/Linux
set ANTHROPIC_API_KEY=tu_api_key_aquí      # Windows CMD
```

---

## Correr la app

```bash
streamlit run app.py
```

La primera vez que corra, `data/tone_profile.json` se genera automáticamente con el perfil base de Darwin AI. Podés editarlo a mano antes de generar el primer post.

---


## Flujo de uso en la app

```
Sidebar (opcional):
  → Pegá un post externo como referencia de ángulo o estructura

① Briefing:
  → Tema o noticia · Objetivo · Idioma · Red social
  → "Generar post →"

② Revisión:
  → Leés el post generado (editable antes de aprobar)
  → Métricas de palabras y rango recomendado por plataforma
  → Aprobar: se guarda y suma al pool de ejemplos de tono
  → Rechazar: escribís el motivo + tags → regenera inmediatamente
      con el feedback incorporado en el prompt
```

El sistema aprende acumulativamente: cada rechazo con motivo se inyecta en el system prompt de la siguiente generación. Cada aprobación se suma como ejemplo few-shot de alta calidad.

---

## Formato editorial de Darwin AI

Todos los posts siguen esta estructura fija (news curation):

```
[emoji] **Titular de la noticia**

💡 Señal clave: el dato más relevante en una oración

⚡ Dato concreto con cifra
⚡ Dato concreto con cifra
⚡ Dato concreto con cifra

🤯 Takeaway: impacto para empresas en LATAM

Fuente: [Nombre del medio]
```

---

## Idiomas soportados

| Idioma | Cuándo usarlo |
|---|---|
| Español | Default — audiencia LATAM general |
| Inglés | LinkedIn con audiencia C-level o tech internacional |
| Portugués | Posts con foco explícito en Brasil |

---

## Tags de feedback

Usados al rechazar un post para actualizar el perfil de tono automáticamente:

| Tag | Qué corrige |
|---|---|
| `falta_latam` | El post no conecta con mercados latinoamericanos |
| `muy_formal` | Tono demasiado corporativo |
| `falta_cta` | No hay llamada a la acción |
| `muy_largo` | Excede el límite recomendado para la plataforma |
| `muy_corto` | Por debajo del mínimo recomendado |
| `muy_generico` | Sin datos concretos ni casos reales |
| `tono_incorrecto` | No suena como Darwin AI |

---

## Editar el perfil de tono manualmente

`data/tone_profile.json` es el archivo central de configuración de tono. Podés editarlo directamente entre sesiones — el sistema lo recarga en cada generación.

```json
{
  "voice_traits": [...],         
  "structural_patterns": [...],  
  "vocabulary_signals": [...],   
  "avoid_patterns": [...],       
  "platform_notes": {
    "linkedin": "...",
    "instagram": "...",
    "idiomas": { "español": "...", "inglés": "...", "portugués": "..." }
  }
}
```

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `ANTHROPIC_API_KEY` | Sí | API key de Anthropic |

---

## Compatibilidad

- Python 3.9+ (usa `from __future__ import annotations` para compatibilidad de type hints)
- Modelo: `claude-sonnet-4-20250514`
- Streamlit: probado en 1.35+

---

## Smoke tests

```bash
# Verificar memory_store
python memory_store.py

# Verificar tone_learner + system prompt
python tone_learner.py

# Verificar generador (requiere ANTHROPIC_API_KEY real)
python content_generator.py
```
