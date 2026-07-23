# Laboratorio paso a paso: CI/CD de una API Flask

En esta práctica vas a recorrer un pipeline completo:

```text
Pull request
  → análisis estático
  → unit tests
  → construcción de imagen
  → despliegue dev efímero
  → regresión HTTP
  → listo para merge
  → publicación en GHCR
  → aprobación
  → producción
```

La aplicación es una API Flask pequeña. El objetivo no es aprender Flask en
profundidad, sino observar cómo GitHub Actions controla el paso de un cambio
desde una rama hasta producción.

## Qué vas a comprobar

Al finalizar vas a poder demostrar que:

- un pull request no puede integrarse si falla un control;
- el análisis estático ocurre antes del despliegue;
- los unit tests revisan funciones y rutas sin levantar un servidor real;
- Docker Compose levanta un entorno dev efímero;
- los tests de regresión consumen la API desplegada mediante HTTP;
- un check verde indica que el cambio está listo para merge;
- `main` publica una imagen identificada por el SHA del commit;
- producción puede exigir aprobación antes de usar sus secretos;
- `/health` permite comprobar qué versión está desplegada.

# Parte 1 — Conocer el repositorio

## Paso 1. Revisar los archivos

Ubícate en la carpeta del repositorio:

```bash
cd practica-clase6-cicd
```

Identifica estos archivos:

```text
.
├── .github/workflows/cicd.yml       Pipeline de GitHub Actions
├── app/__init__.py                  API Flask
├── deploy/compose.prod.yaml         Despliegue de producción
├── tests/
│   ├── regression/test_api_contract.py
│   └── unit/test_app.py
├── compose.yaml                     Entorno local y dev
├── Dockerfile                       Imagen de la API
├── pyproject.toml                   Configuración de Ruff y Pytest
├── requirements-dev.txt             Herramientas de desarrollo
└── requirements.txt                 Dependencias de ejecución
```

## Paso 2. Leer los endpoints

Abre `app/__init__.py` y localiza:

| Endpoint | Función |
| --- | --- |
| `GET /` | Muestra el nombre de la API y sus rutas |
| `GET /health` | Informa estado, entorno y versión |
| `GET /api/stages` | Devuelve las etapas del pipeline |
| `GET /api/progress?completed=3` | Calcula el avance |

No modifiques nada todavía.

# Parte 2 — Ejecutar la API localmente

## Paso 3. Comprobar Docker

Ejecuta:

```bash
docker --version
docker compose version
```

Los dos comandos deben mostrar una versión. Si `docker compose` no existe,
instala Docker Desktop o el plugin Docker Compose.

## Paso 4. Levantar la API

Ejecuta:

```bash
docker compose up --build --wait
```

Qué debe ocurrir:

1. Docker descarga la imagen base de Python.
2. Instala Flask y Gunicorn.
3. Construye la imagen local.
4. Inicia el contenedor.
5. Espera hasta que `/health` responda correctamente.
6. Informa que el contenedor está `Healthy`.

Comprueba el estado:

```bash
docker compose ps
```

Resultado esperado: el servicio `api` aparece iniciado y saludable.

## Paso 5. Probar los endpoints

Ejecuta:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/api/stages
curl "http://localhost:8000/api/progress?completed=3"
```

La última consulta debe devolver:

```json
{
  "completed": 3,
  "percentage": 60,
  "total": 5
}
```

Comprueba también un error controlado:

```bash
curl -i "http://localhost:8000/api/progress?completed=invalido"
```

Resultado esperado:

```text
HTTP/1.1 400 BAD REQUEST
```

## Paso 6. Revisar logs y detener

Consulta los logs:

```bash
docker compose logs
```

Detén y elimina el entorno:

```bash
docker compose down
```

Comprueba:

```bash
docker compose ps
```

No debería quedar ningún contenedor del proyecto ejecutándose.

# Parte 3 — Ejecutar los controles localmente

## Paso 7. Crear un entorno virtual

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias:

```bash
pip install -r requirements-dev.txt
```

## Paso 8. Ejecutar el análisis estático

Primero, Ruff:

```bash
ruff check .
ruff format --check .
```

Ruff revisa errores de Python, imports, convenciones y formato.

Después, Bandit:

```bash
bandit --recursive app
```

Bandit busca patrones de código potencialmente inseguros.

Resultado esperado: ambos controles terminan sin errores.

## Paso 9. Ejecutar unit tests

```bash
pytest -v tests/unit
```

Resultado esperado:

```text
8 passed
```

Estos tests importan Flask y llaman a la aplicación dentro del proceso de
Pytest. Todavía no prueban un contenedor desplegado.

## Paso 10. Ejecutar regresión contra un despliegue

Vuelve a levantar la API:

```bash
docker compose up --build --wait
```

En otra terminal, activa el entorno virtual y ejecuta:

```bash
BASE_URL=http://localhost:8000 pytest -v -m regression tests/regression
```

En PowerShell:

```powershell
$env:BASE_URL="http://localhost:8000"
pytest -v -m regression tests/regression
```

Resultado esperado:

```text
4 passed
```

Estos tests llaman a la aplicación por HTTP. Para ellos, la API es un sistema
externo. Por eso pueden detectar problemas que un unit test no observa.

Detén el entorno:

```bash
docker compose down
```

# Parte 4 — Crear el repositorio en GitHub

## Paso 11. Crear un repositorio vacío

En GitHub:

1. Selecciona **New repository**.
2. Asigna un nombre, por ejemplo `formatec-flask-cicd`.
3. Selecciona **Public**.
4. No agregues README, `.gitignore` ni licencia.
5. Selecciona **Create repository**.

El repositorio público permite usar las funciones de protección necesarias con
una cuenta gratuita.

## Paso 12. Asociar el repositorio local

Reemplaza la URL por la de tu repositorio:

```bash
git remote add origin https://github.com/USUARIO/formatec-flask-cicd.git
git branch -M main
git push -u origin main
```

En GitHub, abre la pestaña **Actions**.

Debes ver el workflow **CI/CD**. En esta primera ejecución deberían correr:

1. `1 · Análisis estático y unit tests`;
2. `2 · Construir imagen`;
3. `4 · Publicar imagen`.

El job de producción se omite hasta que se configure
`PROD_DEPLOY_ENABLED=true`.

## Paso 13. Comprobar la imagen publicada

Cuando termine el workflow:

1. Vuelve a la página principal del repositorio.
2. Abre la sección **Packages**.
3. Selecciona la imagen del repositorio.
4. Busca una etiqueta con formato `sha-<commit>`.
5. Comprueba que también existe `latest`.

La etiqueta `latest` es cómoda para explorar. Producción utiliza la etiqueta
del SHA porque identifica un artefacto exacto e inmutable.

# Parte 5 — Provocar un fallo de regresión en un PR

Esta parte demuestra por qué no alcanza con análisis estático y unit tests.

## Paso 14. Crear una rama

```bash
git switch -c feature/romper-contrato
```

## Paso 15. Introducir un cambio incompatible

Abre `app/__init__.py`.

Dentro de la respuesta de `/api/progress`, cambia:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

por:

```python
"percent": calculate_progress(completed, len(STAGES)),
```

Guarda el archivo.

## Paso 16. Ejecutar los controles rápidos

```bash
ruff check .
ruff format --check .
bandit --recursive app
pytest tests/unit
```

Resultado esperado:

- Ruff pasa.
- Bandit pasa.
- Los unit tests pasan.

El código es válido y las pruebas internas no detectan el cambio de contrato.

## Paso 17. Registrar y subir el cambio

```bash
git add app/__init__.py
git commit -m "feat: renombrar campo percentage"
git push -u origin feature/romper-contrato
```

## Paso 18. Abrir el pull request

En GitHub:

1. Abre **Pull requests**.
2. Selecciona **New pull request**.
3. Usa `main` como base.
4. Usa `feature/romper-contrato` como compare.
5. Selecciona **Create pull request**.
6. Espera la ejecución de los checks.

## Paso 19. Observar el pipeline

En la pestaña **Checks**, observa:

1. El análisis estático queda verde.
2. Los unit tests quedan verdes.
3. La imagen se construye.
4. Docker Compose levanta el entorno `development`.
5. Los tests de regresión consultan la API.
6. La regresión falla porque espera `percentage` y recibe `percent`.
7. El entorno se elimina mediante el step de limpieza.
8. **Listo para merge** queda rojo.

Abre el log del test:

```text
test_progress_calculation_through_http
```

Busca la diferencia entre el JSON esperado y el recibido.

# Parte 6 — Corregir el cambio y habilitar el merge

## Paso 20. Restaurar el contrato

En `app/__init__.py`, vuelve a cambiar:

```python
"percent": calculate_progress(completed, len(STAGES)),
```

por:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

## Paso 21. Verificar localmente

```bash
docker compose up --build --wait
BASE_URL=http://localhost:8000 pytest -v -m regression tests/regression
docker compose down
```

Resultado esperado:

```text
4 passed
```

## Paso 22. Subir la corrección

```bash
git add app/__init__.py
git commit -m "fix: restaurar contrato de progress"
git push
```

No abras otro PR. El push actualiza el PR existente y vuelve a ejecutar el
workflow.

## Paso 23. Comprobar “Listo para merge”

Cuando termine:

1. Abre el PR.
2. Entra en **Checks**.
3. Selecciona **Listo para merge**.
4. Abre el resumen del job.

Debe mostrar:

| Control | Resultado |
| --- | --- |
| Análisis y unit tests | success |
| Imagen Docker | success |
| Dev y regresión | success |

Ahora el check queda verde.

# Parte 7 — Proteger la rama principal

Realiza esta configuración después de que GitHub haya registrado por primera
vez el check **Listo para merge**.

## Paso 24. Crear la regla de protección

En GitHub:

1. Abre **Settings**.
2. Entra en **Rules → Rulesets** o **Branches**.
3. Crea una regla para la rama `main`.
4. Activa **Require a pull request before merging**.
5. Activa **Require status checks to pass**.
6. Agrega el check **Listo para merge**.
7. Activa **Require branches to be up to date before merging**.
8. Opcionalmente exige una aprobación de código.
9. Bloquea pushes directos a `main`.
10. Guarda la regla.

Desde este momento, un PR con regresión fallida no puede integrarse.

# Parte 8 — Hacer merge y publicar el candidato

## Paso 25. Integrar el PR

Con todos los checks verdes:

1. Selecciona **Merge pull request**.
2. Confirma el merge.
3. Abre la pestaña **Actions**.
4. Entra en la ejecución disparada por el push a `main`.

Observa que GitHub repite análisis, tests y build. Esto es intencional: el
commit final de `main` puede diferir del commit original de la rama.

## Paso 26. Identificar el artefacto

Dentro del job **4 · Publicar imagen**, busca:

```text
ghcr.io/USUARIO/REPOSITORIO:sha-<SHA_COMPLETO>
```

Ese identificador representa el candidato exacto que puede promoverse a
producción.

Si no vas a realizar la parte de VM, puedes terminar aquí. Ya se completó:

```text
PR → dev → regresión → merge → imagen publicable
```

# Parte 9 — Preparar producción en una VM

Esta sección es para el docente o para quien quiera completar el despliegue
real.

## Paso 27. Preparar la VM

La VM Linux debe tener:

- acceso SSH;
- Docker Engine;
- plugin Docker Compose;
- salida a `ghcr.io`;
- un usuario autorizado para ejecutar Docker.

En la VM, verifica:

```bash
docker --version
docker compose version
```

Crea el directorio:

```bash
sudo mkdir -p /opt/formatec-api
sudo chown "$USER":"$USER" /opt/formatec-api
```

## Paso 28. Elegir cómo exponer la API

### Opción rápida para laboratorio

En la VM:

```bash
cat > /opt/formatec-api/.env <<'EOF'
BIND_ADDRESS=0.0.0.0
APP_PORT=8000
EOF
```

Abre el puerto `8000` en el firewall únicamente para las redes necesarias.

La URL será:

```text
http://IP_DE_LA_VM:8000
```

### Opción recomendada

No crees ese archivo. El Compose escuchará en `127.0.0.1:8000`.

Configura Nginx, Caddy o Traefik para publicar HTTPS y enviar las solicitudes a:

```text
http://127.0.0.1:8000
```

## Paso 29. Crear credenciales para GHCR

Crea un token de GitHub con permiso:

```text
read:packages
```

La VM usará ese token únicamente para descargar imágenes privadas.

No guardes el token en el repositorio ni dentro del archivo Compose.

## Paso 30. Obtener la identidad SSH del servidor

Desde una red confiable:

```bash
ssh-keyscan -H IP_O_HOSTNAME_DE_LA_VM
```

Copia la línea completa. Se usará como `PROD_KNOWN_HOSTS`.

# Parte 10 — Configurar el entorno production

## Paso 31. Crear el entorno

En GitHub:

1. Abre **Settings → Environments**.
2. Selecciona **New environment**.
3. Escribe `production`.
4. Guarda.

## Paso 32. Agregar la aprobación

Dentro del entorno `production`:

1. Activa **Required reviewers**.
2. Selecciona la persona que aprobará.
3. Si trabajan varias personas, activa **Prevent self-review**.
4. Restringe el entorno para aceptar únicamente la rama `main`.

El workflow podrá comenzar después del merge, pero el job no accederá a los
secretos hasta recibir aprobación.

## Paso 33. Crear las variables

Primero abre **Settings → Secrets and variables → Actions → Variables** y crea
esta variable de repositorio:

| Variable | Valor |
| --- | --- |
| `PROD_DEPLOY_ENABLED` | `true` |

El workflow evalúa esta variable antes de iniciar el job de producción. Por
eso debe ser una variable del repositorio y no del entorno.

Después, dentro de **Settings → Environments → production → Environment
variables**, crea:

| Variable | Ejemplo |
| --- | --- |
| `PROD_PATH` | `/opt/formatec-api` |
| `PROD_URL` | `http://192.0.2.10:8000` |

Si usas proxy HTTPS, `PROD_URL` debe contener la URL pública:

```text
https://api.ejemplo.com
```

## Paso 34. Crear los secrets

En **Environment secrets**, crea:

| Secret | Contenido |
| --- | --- |
| `PROD_HOST` | IP o hostname de la VM |
| `PROD_USER` | Usuario SSH |
| `PROD_SSH_KEY` | Clave privada SSH |
| `PROD_KNOWN_HOSTS` | Salida confiable de `ssh-keyscan` |
| `GHCR_USERNAME` | Usuario de GitHub |
| `GHCR_TOKEN` | Token con `read:packages` |

No escribas estos valores en el YAML.

# Parte 11 — Ejecutar el primer despliegue productivo

## Paso 35. Disparar nuevamente el workflow

Como `PROD_DEPLOY_ENABLED` se configuró después del merge anterior:

1. Abre **Actions**.
2. Selecciona **CI/CD**.
3. Selecciona **Run workflow**.
4. Usa la rama `main`.
5. Confirma.

## Paso 36. Aprobar producción

Cuando termine la publicación:

1. El job **5 · Desplegar producción** queda esperando.
2. Abre la ejecución.
3. Selecciona **Review deployments**.
4. Marca `production`.
5. Selecciona **Approve and deploy**.

Después de la aprobación, el workflow:

1. configura SSH;
2. copia `compose.prod.yaml` a la VM;
3. inicia sesión en GHCR;
4. descarga la imagen `sha-<commit>`;
5. actualiza el contenedor con Docker Compose;
6. espera el health check;
7. consulta `$PROD_URL/health`.

## Paso 37. Comprobar la versión

Desde tu equipo:

```bash
curl "$PROD_URL/health"
```

Resultado esperado:

```json
{
  "environment": "production",
  "status": "ok",
  "version": "<SHA DEL COMMIT>"
}
```

En la VM:

```bash
cd /opt/formatec-api
docker compose ps
docker compose logs --tail=50
```

# Parte 12 — Repetir el ciclo completo

## Paso 38. Crear un cambio válido

```bash
git switch main
git pull
git switch -c feature/nueva-etapa
```

Agrega una nueva etapa en `app/__init__.py`.

Actualiza:

- el conteo esperado;
- los unit tests;
- los tests de regresión;
- los porcentajes afectados.

## Paso 39. Validar y abrir el PR

```bash
ruff check .
ruff format --check .
bandit --recursive app
pytest tests/unit
docker compose up --build --wait
BASE_URL=http://localhost:8000 pytest -m regression tests/regression
docker compose down
git add .
git commit -m "feat: agregar nueva etapa"
git push -u origin feature/nueva-etapa
```

Abre el PR y espera **Listo para merge**.

## Paso 40. Promover a producción

1. Revisa el PR.
2. Confirma todos los checks verdes.
3. Haz merge.
4. Espera la nueva imagen `sha-<commit>`.
5. Revisa el despliegue pendiente.
6. Aprueba `production`.
7. Consulta `/health`.
8. Comprueba que el SHA coincide con el commit de `main`.

# Guía de observación

Durante la práctica, completa:

| Pregunta | Respuesta |
| --- | --- |
| ¿Qué evento inicia el pipeline del PR? | |
| ¿Qué job ejecuta Ruff y Bandit? | |
| ¿Por qué la regresión ocurre después del despliegue dev? | |
| ¿Qué hace `needs` entre los jobs? | |
| ¿Qué check se exige antes del merge? | |
| ¿Qué etiqueta identifica la imagen exacta? | |
| ¿Cuándo están disponibles los secrets de producción? | |
| ¿Qué endpoint confirma la versión desplegada? | |

# Criterios de finalización

La práctica está completa cuando puedes mostrar:

- [ ] API local saludable mediante Docker Compose.
- [ ] Ruff y Bandit en verde.
- [ ] Ocho unit tests aprobados.
- [ ] Cuatro tests de regresión aprobados.
- [ ] Un PR con una regresión fallida.
- [ ] La corrección del mismo PR.
- [ ] El check **Listo para merge** en verde.
- [ ] La protección de `main`.
- [ ] Una imagen GHCR identificada por SHA.
- [ ] El job de producción esperando aprobación.
- [ ] `/health` respondiendo con `environment: production`.
- [ ] El SHA de `/health` coincidiendo con el commit desplegado.

# Problemas frecuentes

## El puerto 8000 está ocupado

Usa otro puerto:

```bash
APP_PORT=8080 docker compose up --build --wait
BASE_URL=http://localhost:8080 pytest -m regression tests/regression
APP_PORT=8080 docker compose down
```

## El PR no despliega dev

Comprueba que:

- el PR apunta a `main`;
- no está en modo draft;
- el análisis estático terminó correctamente;
- los unit tests pasaron;
- la construcción de la imagen pasó.

## “Listo para merge” queda rojo

Abre el resumen del job. Mostrará cuál de estos controles falló:

- análisis y unit tests;
- construcción de la imagen;
- dev y regresión.

## Producción aparece omitida

Comprueba que la variable de repositorio existe en **Settings → Secrets and
variables → Actions**:

```text
PROD_DEPLOY_ENABLED=true
```

## Producción queda esperando

Es el comportamiento esperado cuando el entorno requiere aprobación. Usa
**Review deployments**.

## La VM no puede descargar la imagen

Comprueba:

- `GHCR_USERNAME`;
- que `GHCR_TOKEN` tenga `read:packages`;
- que el package permita acceso al repositorio;
- que la VM tenga salida a `ghcr.io`.

## El health check de producción falla

Desde la VM:

```bash
cd /opt/formatec-api
docker compose ps
docker compose logs
curl http://127.0.0.1:8000/health
```

Si localmente funciona pero `PROD_URL` no responde, revisa firewall, proxy
reverso, DNS y HTTPS.

# Referencias

- [Status checks](https://docs.github.com/en/pull-requests/reference/status-checks)
- [Entornos y aprobaciones](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [Publicación de imágenes en GHCR](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
