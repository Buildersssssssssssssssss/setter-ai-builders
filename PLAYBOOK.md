# Playbook — Setter AI Builders
**Para el equipo de Marketing**
Versión 1.0 — Mayo 2026

---

## ¿Qué es el Setter?

El Setter es un agente de inteligencia artificial que opera desde la cuenta de Instagram `@ai__builders`. Su función es **responder automáticamente** a comentarios y mensajes directos, calificar leads y agendar llamadas, simulando una conversación humana natural.

El setter **no reemplaza al equipo de ventas** — lo prepara. Cuando el setter termina su trabajo, el lead llega a la llamada ya calificado y con contexto.

---

## Qué eventos escucha

El setter reacciona a tres tipos de interacciones en Instagram:

| Evento | Descripción |
|---|---|
| **DM (Mensaje Directo)** | Alguien escribe directamente al inbox de `@ai__builders` |
| **Comentario en publicación** | Alguien comenta en un post o reel de la cuenta |
| **Story Reply** | Alguien responde a una historia de la cuenta |

> El setter **ignora** reacciones, likes, menciones y cualquier interacción que no sea texto.

---

## Cómo registrar una publicación en el Google Sheets

El Sheets es la forma en que el equipo de marketing le dice al setter **qué publicaciones monitorear** y **qué keywords activan el flujo de bienvenida**.

**Link:** [Data Setter IG](https://docs.google.com/spreadsheets/d/1S1ozS_dFctYYmbe5DW7zbPD9AIZBb6FbEzdd-e0xbYY/edit)

### Paso a paso

1. Copia la URL de la publicación de Instagram (post, reel o historia)
2. Pégala en la columna **URL Publicación**
3. Marca el checkbox en la columna **Buscar ID** de esa fila — esto ejecuta un script que consulta la API de Instagram y rellena automáticamente la columna **ID** con el identificador numérico de la publicación
4. Completa las demás columnas según la tabla de abajo

### Columnas del Sheets

| Columna | Qué va aquí |
|---|---|
| **Descripción** | Nombre interno para identificar la publicación (ej: "FEED Miami Inmersivo") |
| **URL Publicación** | URL copiada de Instagram |
| **Buscar ID** | Checkbox — márcalo para ejecutar el script que busca el ID |
| **ID** | Se llena automáticamente. Es el identificador numérico de la publicación |
| **Tipo** | `POST`, `REEL` o `HISTORIA` |
| **Context** | Descripción breve de qué trata la publicación (el setter usa esto como contexto) |
| **Keywords** | Palabras que, si aparecen en un comentario, activan el flujo de bienvenida. Separadas por coma |
| **URL_info_to_send** | Link que se enviará al usuario por DM cuando se detecte la keyword (ej: Typeform) |

### Sobre las Keywords

- Son **case-insensitive**: `Miami`, `miami` y `MIAMI` son equivalentes
- Soportan **múltiples valores** separados por coma: `Miami, inmersivo, quiero info`
- Para cubrir errores de escritura, agrégalos como variantes: `Miami, miamy, miami beach`
- Si el comentario de un usuario contiene alguna de las keywords → el setter activa el flujo especial de bienvenida

> **Importante:** si una fila no tiene ID, el setter no puede hacer matching de keywords para esa publicación. Siempre usar el checkbox "Buscar ID" después de agregar una URL.

---

## Qué hace el setter cuando ocurre cada evento

### Flujo 1 — Comentario con keyword detectada

1. Un usuario comenta en una publicación registrada en el Sheets con una keyword
2. El setter envía un **DM de bienvenida** al usuario con la URL de información
3. El setter hace un **reply público** al comentario indicando que ya envió la info por DM

Ejemplo de DM:
```
Hola [Nombre]

Te damos la bienvenida a AI Builders, una comunidad que convierte talento
en impacto real por medio de AI.

Te envío la información de tu interés: [URL del Sheets]

Si tienes alguna duda, cuéntame por acá.
```

Ejemplo de reply al comentario:
```
Te envié la info por DM, cualquier duda me avisas
```

### Flujo 2 — DM directo o Story Reply

1. El usuario escribe al DM o responde una historia
2. El setter inicia una conversación de calificación en 3 fases:
   - **Abrir**: saludo natural + pregunta abierta para generar comodidad
   - **Calificar**: entre 3 y 5 preguntas para entender perfil, motivación y capacidad de inversión
   - **Pitch**: propuesta de llamada cuando el lead está calificado
3. El setter guarda el lead con sus scores en la base de datos

### Flujo 3 — Escalación a humano

Si el setter detecta una queja, problema técnico o algo que requiere atención humana:

1. Deja de responder al usuario automáticamente
2. Envía una alerta al grupo de WhatsApp **"Alertas Setter AI Builders"** con el username y el motivo
3. Incluye un **link de reactivación** — cuando el equipo termina de atender al usuario, hace clic en ese link y el setter vuelve a estar activo para esa persona
4. Si nadie reactiva manualmente, el setter se reactiva solo a las **48 horas**

---

## Sistema anti-ban

Para proteger la cuenta de Instagram, el setter tiene las siguientes protecciones activas:

### Delay humanizado
Antes de cada respuesta, el setter espera entre **15 y 45 segundos** con variación aleatoria para no parecer un bot.

### Horario de negocio
El setter solo responde entre las **7am y 11pm (hora Colombia)**. Los mensajes que llegan fuera de ese horario se ignoran silenciosamente.

### Rate limiting por usuario
- Máximo **3 respuestas por hora** al mismo usuario
- Máximo **10 respuestas por día** al mismo usuario
- Si se supera el límite, el mensaje se ignora

### Bloqueo post-error 403
Si Instagram rechaza un envío por "fuera de ventana de 24h", el setter bloquea automáticamente a ese usuario por **24 horas** para no reintentar y acumular señales negativas.

### Deduplicación de eventos
Meta a veces envía el mismo evento de webhook 2 o 3 veces. El setter detecta duplicados y los ignora, evitando responder múltiples veces al mismo mensaje o comentario.

### Pausa de emergencia
En cualquier momento, el equipo técnico puede activar `SETTER_PAUSED=true` en las variables de entorno de Railway para detener **todas** las respuestas sin redesplegar.

### Filtro de cuenta propia
El setter ignora cualquier evento generado por la propia cuenta `@ai__builders` para evitar loops de auto-respuesta.

---

## Alertas al equipo (WhatsApp)

El setter envía alertas al grupo **"Alertas Setter AI Builders"** en estos casos:

| Situación | Qué llega al grupo |
|---|---|
| DM fallido (error 403 o 400) | Username del usuario + descripción del error + nota de atención manual |
| Escalación a humano | Username + último mensaje del usuario + link para reactivar el setter |

---

## Calificación automática de leads

Cada conversación genera un **score automático** que se guarda en la base de datos (tabla `leads_setter` en Supabase).

Se calculan dos scores en paralelo:

| Score | Evalúa | Rango |
|---|---|---|
| **Score Virtual** | Ganas de aprender, crecimiento profesional, claridad de motivación | 0–100 |
| **Score Inmersivo** | Hambre de crecimiento, intención de ejecución, interés en comunidad y mentoría | 0–100 |

El setter también detecta y registra:

- **Programa recomendado**: `virtual` / `inmersivo` / `dual` / `nurture` / `descalificado`
- **Prioridad comercial**: `alta` / `media` / `baja`
- **Fit financiero**: capacidad estimada de asumir la inversión (USD 1,500 virtual / USD 5,000 inmersivo)
- **Driver**: resumen del dolor o deseo detectado en la conversación
- **Notas de calificación**: observaciones comerciales

### Niveles por score

| Rango | Nivel |
|---|---|
| 70–100 | Alto |
| 40–69 | Medio (nurture) |
| 1–39 | Bajo |
| 0 | Descalificado |

---

## Preguntas frecuentes

**¿Qué pasa si una publicación no tiene ID en el Sheets?**
El setter no puede hacer matching de keywords para esa publicación. Siempre marcar "Buscar ID" después de agregar una URL.

**¿Puedo cambiar las keywords de una publicación?**
Sí, edita directamente la celda en el Sheets. Los cambios aplican en máximo 5 minutos (el setter cachea los datos por ese tiempo).

**¿El setter responde de noche?**
No. Está configurado para responder solo entre 7am y 11pm hora Colombia.

**¿Cómo sé si el setter está funcionando?**
Las alertas de WhatsApp son la señal principal. También puedes revisar los logs en el panel de Railway.

**¿Puedo pausar el setter temporalmente?**
Sí. Pídele al equipo técnico que active `SETTER_PAUSED=true` en las variables de entorno de Railway.

**¿Qué pasa si el setter le responde a alguien que no debería?**
El setter tiene una whitelist de pruebas (`BOOL_TEST=true`). En producción responde a todos. Si hay un caso específico, el equipo técnico puede escalar manualmente o pausar el setter.
