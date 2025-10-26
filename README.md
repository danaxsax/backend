# Smart Wallet — Backend: CapitalOne service

Este repositorio contiene el backend mínimo usado durante el desarrollo del proyecto "Smart Wallet — Your Personal Finance Advisor" (paper: Hildegard Zerrweck, Cyrce Danae Salinas & Israel Booz Rodríguez, October 26, 2025). El sistema propone un enfoque "optimizer-first": calcula pagos óptimos sobre múltiples tarjetas de crédito usando un modelo explícito de interés compuesto y luego usa LLMs para generar retroalimentación personalizada y en lenguaje natural.

Este subdirectorio `CapitalOne/` incluye la API de desarrollo en Python + FastAPI, un pipeline para calcular el plan de pagos y ejemplos de integración con APIs externas (Gemini para explicaciones y la sandbox Nessie para datos sintéticos).

## Contenido relevante

- `server.py` — FastAPI principal que expone los endpoints usados por la UI (análisis, subida de archivos, auth básica simulada y endpoints de tarjetas).
- `pipeline.py` — Lógica del optimizador, construcción de prompts y llamada a Gemini para generar la retroalimentación en texto.
- `api/main.py` — Pequeña app FastAPI que demuestra el *auto-uploader* hacia la sandbox Nessie (nessieisreal) para generar datos sintéticos de cuentas/cliente/bills. Ejecuta el flujo en el evento `startup`.
- `requirements.txt` — Dependencias Python usadas en este módulo.
- `uploaded_files/` — Carpeta donde se guardan los archivos subidos por los usuarios (creada por `server.py`).

## Resumen del paper (breve)

Smart Wallet presenta un modelo que minimiza el interés compuesto y opcionalmente penaliza utilización por encima de un umbral. El flujo principal:

1. Ingesta de extractos (PDF) → extracción / normalización de campos relevantes (Bi, Li, Ai, di, mi, mmsi_i, PNIi, Mi).
2. Algoritmo greedy (óptimo para el LP planteado) que cubre mínimos y asigna presupuesto adicional a las tarjetas con mayor ganancia marginal (ϕi).
3. Generación de explicaciones en lenguaje natural mediante LLMs (Gemini / Anthropic) para dar recomendaciones accionables.

Más detalle en el paper incluido en la descripción del proyecto (resumen provisto por los autores).

## Requisitos

- Python 3.10+ recomendado
- (Opcional) Entorno virtual: venv / conda
- Dependencias listadas en `requirements.txt` (instalar con pip)
- Variables de entorno en un `.env` (ver sección abajo)

## Variables de entorno (importantes)

- `GEMINI_API_KEY` — clave para usar la API de Gemini (usada por `pipeline.py`).

Nota: `CapitalOne/api/main.py` usa la API sandbox de Nessie y en el ejemplo actual tiene una API key embebida; se recomienda modificar ese archivo para leer la key desde una variable de entorno (p.ej. `NESSIE_API_KEY`) si se pretende usar en otro entorno.

Para desarrollo local cree un archivo `.env` en `CapitalOne/` con al menos:

```
GEMINI_API_KEY=tu_gemini_api_key_aqui
# (opcional) NESSIE_API_KEY=tu_nessie_api_key
```

## Instalación y ejecución (desarrollo)

1. Posicionarse en la carpeta `CapitalOne/`:

```bash
cd /Users/os5165/projects/Hackathon/HackMTY/CapitalOne
```

2. Crear/activar un entorno virtual e instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate   # zsh / bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Definir el `.env` con `GEMINI_API_KEY` (y opcionalmente `NESSIE_API_KEY`).

4. Ejecutar el servidor principal (FastAPI) — ejemplo con `uvicorn`:

```bash
# desde la carpeta CapitalOne
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

5. (Opcional) Ejecutar la demo de auto-uploader (sandbox Nessie) — si desea ver cómo se crean clientes/cuentas/bills sintéticos:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8001
```

Nota: `api.main` ejecuta el flujo de upload en su `startup` (imprime el resultado y guarda `output2.txt`).

## Endpoints principales (API `server.py`)

- `POST /analysis` — cuerpo JSON: `{ "fullName": "Hildegard" }`
  - Busca el usuario en la base de datos sintética (map interno) y ejecuta `procesar_documentos_usuario` en `pipeline.py`. Retorna `perfil`, `retroalimentacion` y `detalle_tarjetas`.

- `POST /upload` — multipart/form-data con `file` (UploadFile)
  - Guarda el archivo en `uploaded_files/` y llama a `procesar_documentos_usuario` (según implementación, en el repo actual se pasa la ruta de archivo a la función).

- `POST /auth/register` y `POST /auth/login` — endpoints de ejemplo que imprimen los datos recibidos (simulados).

- `POST /user/profile`, `POST /cards`, `PUT /cards/{card_id}`, `DELETE /cards/{card_id}` — endpoints de ejemplo para flujo de frontend (reciben JSON y responden con eco).

Ejemplo con `curl` para `/analysis`:

```bash
curl -s -X POST http://localhost:8000/analysis \
  -H 'Content-Type: application/json' \
  -d '{"fullName":"Hildegard"}' | jq
```

Ejemplo para subir un archivo:

```bash
curl -s -X POST http://localhost:8000/upload \
  -F "file=@/ruta/a/extracto.pdf" | jq
```

## Diseño y detalles técnicos

- `pipeline.py` implementa:
  - Mapas públicos de tasas y nombres desde `database_banco`.
  - `plan_pagos_usuario`: algoritmo greedy que cubre mínimos y asigna presupuesto extra por mayor beneficio marginal (ϕ_i).
  - `generar_prompt_feedback`: crea el prompt en español que se envía a Gemini.
  - `procesar_documentos_usuario`: orquesta la ejecución completa y devuelve el `perfil`, la `retroalimentacion` (texto) y `detalle_tarjetas`.

- Las tasas se usan como coeficientes fijos por ciclo (ϕ_i). El problema es lineal en los pagos dada esa transformación.

## Consideraciones de privacidad y seguridad

- No suba claves secretas a repositorios públicos. Use `.env` y/o gestores de secretos.
- El pipeline actual usa datos sintéticos (Nessie) y tablas internas para desarrollo. Para producción debe reemplazarse la capa de persistencia y autenticación.

## Notas sobre LLMs y costos

- `pipeline.py` usa la librería `google.genai` para llamar a Gemini; asegúrese de tener la clave y límites configurados. Las llamadas a LLMs generan costos y latencia; durante pruebas puede simular las respuestas o usar prompts pequeños.
- `api/main.py` usa la sandbox Nessie para generar datos sintéticos — no requiere datos reales.

## Recomendaciones de desarrollo

- Añadir validación y pruebas unitarias para `plan_pagos_usuario` (casos: presupuesto insuficiente, pagos mínimos > presupuesto, múltiples tarjetas, MSI presente).
- Registrar y capturar excepciones en llamadas a la API de Gemini y reintentos si es necesario.

## Créditos y referencia del paper

Smart Wallet — Your Personal Finance Advisor

Hildegard Zerrweck, Cyrce Danae Salinas & Israel Booz Rodríguez — October 26, 2025

Resumen: Optimizer-first system que combina un modelo matemático de interés compuesto con LLMs para retroalimentación.

---

Si quieres, puedo:
- Añadir ejemplos de tests unitarios para `pipeline.py` (pytest).
- Modificar `api/main.py` para leer la API key de Nessie desde `.env`.
- Preparar un `docker-compose.yml` para levantar la API y la demo de Nessie localmente.

Contacta para que implemente cualquiera de estas tareas.
# backend



uvicorn main:app --reload --port 9000  