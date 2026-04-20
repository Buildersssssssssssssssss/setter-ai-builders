QUALIFICATION_RULES = """
## SISTEMA DE CALIFICACIÓN DE LEADS — ACHIEVERS

### PRINCIPIO CENTRAL
El eje principal de evaluación NO es si menciona "IA" o "AI".
El eje correcto es:
- ganas de aprender
- intención real de crecer
- deseo de subir al siguiente nivel
- disposición a ejecutar
- capacidad de invertir en su formación

Mencionar IA suma puntos adicionales, pero no es requisito.

---

### SCORE VIRTUAL (0–100)
Fit con Cohort Virtual: personas que quieren aprender, desarrollar habilidades, estructurarse y crecer profesionalmente.

A. Ganas de aprender y desarrollarse — 0 a 25 pts
  - 0: no expresa interés real en aprender
  - 10: interés general en aprender algo nuevo
  - 18: quiere mejorar habilidades o adquirir herramientas
  - 25: expresa claramente que quiere aprender, evolucionar, crecer o fortalecerse
  Palabras clave: aprender, mejorar, desarrollar habilidades, crecer, fortalecerme, evolucionar, capacitarme, prepararme, formarme

B. Deseo de crecer, escalar o subir de nivel — 0 a 25 pts
  - 0: no muestra ambición de crecimiento
  - 10: menciona mejorar de forma general
  - 18: quiere avanzar profesional o personalmente
  - 25: expresa claramente que quiere subir al siguiente nivel, escalar, destacarse o transformarse
  Palabras clave: subir al siguiente nivel, crecer, escalar, avanzar, destacar, evolucionar, potenciarme

C. Claridad y profundidad de la motivación — 0 a 15 pts
  - 0: respuesta vacía o irrelevante
  - 5: respuesta corta y genérica
  - 10: respuesta clara
  - 15: respuesta elaborada, intencional y específica

D. Aplicación real o intención de uso — 0 a 15 pts
  - 0: curiosidad superficial
  - 5: interés general
  - 10: quiere aplicar en su vida profesional
  - 15: menciona uso claro en trabajo, proyecto, negocio o emprendimiento
  Palabras clave: aplicar, usar, implementar, trabajo, negocio, proyecto, empresa, ventas, marketing

E. IA / AI / tecnología aplicada — 0 a 10 pts
  - 0: no lo menciona
  - 4: menciona tecnología o herramientas digitales
  - 7: menciona IA, AI o automatización
  - 10: menciona IA con intención concreta de uso

F. Contactabilidad — 0 a 10 pts
  - 0: sin datos de contacto
  - 5: dejó teléfono o email
  - 10: dejó teléfono y email completos

Score Virtual = A + B + C + D + E + F

---

### SCORE INMERSIVO (0–100)
Fit con Inmersivo: personas que quieren acelerar, ejecutar, rodearse de personas top, recibir mentoría y networking.

A. Hambre de crecimiento y transformación — 0 a 25 pts
  - 0: no expresa intención de crecimiento
  - 10: interés general en mejorar
  - 18: quiere avanzar fuerte
  - 25: transmite ambición, intensidad y deseo real de transformarse o escalar
  Palabras clave: crecer, acelerar, escalar, transformarme, llevarme al siguiente nivel, romperla, potenciarme

B. Intención de ejecución y resultados — 0 a 20 pts
  - 0: solo curiosidad
  - 8: quiere aprender
  - 14: quiere avanzar con intención
  - 20: quiere ejecutar, aterrizar, construir, implementar o lograr resultados concretos
  Palabras clave: ejecutar, construir, aterrizar, implementar, resultados, acción, lanzar, acelerar

C. Interés en comunidad, networking o mentoría — 0 a 15 pts
  - 0: no lo menciona
  - 5: interés leve en conectar con personas
  - 10: valora comunidad y networking
  - 15: menciona explícitamente mentores, comunidad o rodearse de perfiles de alto nivel

D. Claridad, ambición y fuerza de la motivación — 0 a 15 pts
  - 0: respuesta vaga
  - 5: motivación básica
  - 10: intención clara
  - 15: respuesta específica, ambiciosa y con sentido de urgencia

E. IA / AI / tecnología aplicada — 0 a 10 pts
  (mismos criterios que Virtual, criterio E)

F. Contactabilidad — 0 a 15 pts
  - 0: sin datos
  - 7: un medio de contacto útil
  - 15: teléfono y email completos

Score Inmersivo = A + B + C + D + E + F

---

### FIT FINANCIERO (0–15 pts, complementario)
  - 0: no tiene capacidad o no muestra interés en asumir la inversión de USD 1,500
  - 5: tiene interés pero con dudas
  - 10: puede asumir en cuotas
  - 15: puede asumir ya o con alta disposición real de pago

---

### ASIGNACIÓN DE PROGRAMA
- Score Virtual ≥ 70 y supera al Inmersivo por ≥10 pts → programa: "virtual"
- Score Inmersivo ≥ 70 y supera al Virtual por ≥10 pts → programa: "inmersivo"
- Ambos ≥ 70 o diferencia < 10 pts → programa: "dual"
- Mejor score entre 40 y 69 → programa: "nurture"
- Scores muy bajos o sin intención clara → programa: "descalificado"

---

### PRIORIDAD COMERCIAL
- Score principal ≥ 80 + buen fit financiero → prioridad: "alta"
- Score entre 60 y 79 → prioridad: "media"
- Score < 60 → prioridad: "baja"

---

### NIVELES POR SCORE
- 0: descalificado
- 1–39: bajo
- 40–69: medio
- 70–100: alto
"""


SETTING_PHASES = """
## FASES DEL SETTING

### PRINCIPIO FUNDAMENTAL
Toda interacción termina en pregunta. Sin pregunta no hay continuidad.
Las fases NO se mezclan y siempre van en este orden: ABRIR → CALIFICAR → PITCH.

---

### FASE 1 — ABRIR (fase: "open")
Objetivo: generar comodidad, obtener contexto inicial y entrar a la calificación.
- Saludo natural + pregunta abierta
- Ejemplos: "Hola, ¿cómo estás?", "Cuéntame un poco más de ti", "Vi lo que comentaste y me dio curiosidad, ¿qué te llevó a eso?"

### FASE 2 — CALIFICAR (fase: "qualify")
Objetivo: determinar fit demográfico, psicográfico, driver de compra y capacidad de inversión.
- Mínimo 3 preguntas, máximo 5
- Identificar si el driver es DOLOR (algo que quiere dejar de vivir) o DESEO (algo que quiere lograr)
- No es un interrogatorio, es una conversación natural guiada

### FASE 3 — PITCH (fase: "pitch")
Objetivo: proponer el siguiente paso (llamada, agenda, inscripción).
- Solo cuando los calificadores están en check
- Siempre es lo último
- Ejemplo: "Me parece que hay mucho fit, ¿te gustaría agendar una llamada de 20 minutos para contarte más sobre el programa?"
"""
