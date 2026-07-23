# Práctica: CI/CD de una API Flask

Clase práctica alineada con la Clase 6 de CI/CD. El repositorio contiene una
API Flask, sus tests, análisis estático, Docker Compose para desarrollo y un
workflow completo desde pull request hasta producción.

## ¿El flujo propuesto es correcto?

Sí, con esta separación:

1. Un pull request dispara análisis estático y unit tests.
2. Si pasan, se construye la imagen Docker.
3. La API se despliega en un entorno `development` efímero dentro del runner.
4. Los tests de regresión atacan la API por HTTP, como un consumidor externo.
5. El check **Listo para merge** queda verde solo si todos los controles pasan.
6. La protección de `main` exige ese check antes del merge.
7. El merge vuelve a validar el commit de `main` y publica su imagen en GHCR.
8. El job de `production` espera una aprobación manual.
9. Después de la aprobación, actualiza una VM Linux mediante Docker Compose y
   verifica `/health`.

No se despliega directamente a producción desde el PR. Tampoco se considera
que publicar una imagen sea lo mismo que desplegarla.

## API

| Endpoint | Resultado |
| --- | --- |
| `GET /` | Nombre de la API y enlaces disponibles |
| `GET /health` | Estado, entorno y versión desplegada |
| `GET /api/stages` | Contrato de las etapas del pipeline |
| `GET /api/progress?completed=3` | Progreso calculado |

Ejemplo:

```json
{
  "completed": 3,
  "percentage": 60,
  "total": 5
}
```

## Estructura

```text
.
├── .github/workflows/cicd.yml
├── app/__init__.py
├── deploy/compose.prod.yaml
├── tests/
│   ├── regression/test_api_contract.py
│   └── unit/test_app.py
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

## Ejecución local con Docker Compose

Requisito: Docker con el plugin Compose.

```bash
docker compose up --build --wait
```

Probar:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/stages
curl "http://localhost:8000/api/progress?completed=3"
```

Ver logs y detener:

```bash
docker compose logs -f
docker compose down
```

## Ejecución local sin Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
flask --app app:create_app run --port 8000
```

En otra terminal:

```bash
ruff check .
ruff format --check .
bandit --recursive app
pytest tests/unit
BASE_URL=http://localhost:8000 pytest -m regression tests/regression
```

## Qué hace el workflow

### 1. Análisis estático y unit tests

- Ruff revisa errores, imports, estilo y formato.
- Bandit busca patrones inseguros en el código Python.
- Pytest ejecuta tests aislados usando el cliente de Flask.

### 2. Construcción

Docker construye una imagen asociada al SHA del commit. Si el Dockerfile o las
dependencias fallan, el pipeline se detiene antes de desplegar.

### 3. Desarrollo efímero

En cada apertura o actualización de un PR no borrador:

```bash
docker compose up --detach --build --wait
pytest -m regression tests/regression
docker compose down
```

Este entorno existe solo durante el job. No ofrece una URL pública. Es un
despliegue real del contenedor dentro del runner y resulta suficiente para
validar integración, health check y contratos HTTP.

### 4. Listo para merge

El job **Listo para merge** resume los resultados y falla si alguno de los jobs
anteriores no terminó correctamente. Debe configurarse como check obligatorio
de `main`.

### 5. Publicación y producción

Después del merge:

- se repiten análisis, tests y build sobre el commit real de `main`;
- la imagen se publica como `ghcr.io/owner/repo:sha-<commit>`;
- el entorno `production` solicita aprobación;
- la VM descarga esa imagen exacta;
- Docker Compose reemplaza el contenedor;
- el workflow comprueba `PROD_URL/health`.

## Configuración de GitHub

### Protección de `main`

En **Settings → Branches** o **Settings → Rules → Rulesets**:

1. exigir pull request antes de integrar;
2. exigir el check **Listo para merge**;
3. exigir que la rama esté actualizada antes del merge;
4. opcionalmente exigir una aprobación de código;
5. impedir pushes directos a `main`.

### Entorno `production`

En **Settings → Environments**, crear `production`:

- permitir despliegues únicamente desde `main`;
- agregar un required reviewer;
- impedir self-review si hay más de una persona;
- crear la variable `PROD_URL`, por ejemplo `https://api.ejemplo.com`;
- crear la variable `PROD_PATH`, por ejemplo `/opt/formatec-api`.

El workflow comienza automáticamente tras el merge, pero el job de producción
queda en espera hasta recibir la aprobación.

### Secrets necesarios

| Nombre | Contenido |
| --- | --- |
| `PROD_HOST` | Hostname o IP de la VM |
| `PROD_USER` | Usuario SSH con acceso a Docker |
| `PROD_SSH_KEY` | Clave privada SSH |
| `PROD_KNOWN_HOSTS` | Clave pública del host en formato `known_hosts` |
| `GHCR_USERNAME` | Usuario que la VM usa para leer GHCR |
| `GHCR_TOKEN` | Token con permiso `read:packages` |

Generar `PROD_KNOWN_HOSTS` desde una red confiable:

```bash
ssh-keyscan -H api.ejemplo.com
```

La VM necesita Docker Engine y el plugin Docker Compose. El puerto de la API
queda publicado solo en `127.0.0.1:8000`; un proxy reverso existente debe
exponer HTTPS y enviar tráfico a ese puerto.

## Actividad práctica

Duración sugerida: 100 minutos.

### Parte 1: local

1. Levantar la API con Docker Compose.
2. Consultar los cuatro endpoints.
3. Ejecutar unit tests y regresión.
4. Diferenciar tests internos de tests HTTP externos.

### Parte 2: provocar un check rojo

Crear una rama:

```bash
git switch -c feature/renombrar-regresion
```

En `app/__init__.py`, cambiar la etapa `Regresión` por `Pruebas de regresión`
sin actualizar los tests. Abrir el PR y observar:

- Ruff y Bandit pasan;
- los unit tests fallan;
- los jobs dependientes no despliegan;
- **Listo para merge** queda rojo.

### Parte 3: corregir y desplegar dev

Actualizar el contrato esperado en `tests/unit/test_app.py` y
`tests/regression/test_api_contract.py`. Subir el commit.

Observar que ahora:

1. pasa el análisis estático;
2. se construye la imagen;
3. Compose levanta el entorno development;
4. los tests atacan la API por HTTP;
5. el entorno se destruye incluso si un test falla;
6. **Listo para merge** queda verde.

### Parte 4: producción

Hacer merge. Abrir la ejecución de `main` y localizar:

1. la imagen versionada con el SHA;
2. el job esperando aprobación;
3. el entorno y sus secretos protegidos;
4. el despliegue en la VM;
5. la verificación final de `/health`.

## Criterios de evaluación

| Evidencia | Logrado |
| --- | --- |
| Explica por qué el PR no despliega producción. | ☐ |
| Diferencia análisis estático, unit test y regresión. | ☐ |
| Interpreta un check rojo desde los logs. | ☐ |
| Demuestra el despliegue efímero con Compose. | ☐ |
| Identifica la imagen exacta que llega a producción. | ☐ |
| Explica el valor del entorno protegido y la aprobación. | ☐ |
| Comprueba la versión mediante `/health`. | ☐ |

## Observaciones de diseño

- Un PR actualizado cancela el despliegue dev anterior del mismo PR.
- Los PR borrador no consumen tiempo desplegando.
- `main` se valida otra vez porque el commit integrado puede diferir del
  commit observado inicialmente en la rama.
- Producción usa la etiqueta inmutable del SHA, no `latest`.
- El check requerido es la notificación de que el candidato está listo.
- Para tener una URL preview pública por PR se necesita una plataforma externa
  o infraestructura adicional; el runner efímero no puede ofrecerla después de
  finalizar el job.

## Referencias

- [Status checks y protección del merge](https://docs.github.com/en/pull-requests/reference/status-checks)
- [Entornos y reglas de protección](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Publicar imágenes Docker en GHCR](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)

