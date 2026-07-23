# Laboratorio: GitHub Actions y Kubernetes local sin exposición pública

Esta práctica implementa un flujo CI/CD completo para una API Flask:

```text
Pull request
  → análisis estático
  → unit tests
  → imagen en GHCR
  → namespace dev efímero en Docker Desktop Kubernetes
  → regresión HTTP
  → listo para merge
  → aprobación
  → namespace production local
  → regresión post-deploy
```

El cluster Kubernetes no recibe conexiones desde Internet:

- no se crea Ingress;
- no se crea Service `LoadBalancer`;
- no se crea Service `NodePort`;
- la API usa únicamente Service `ClusterIP`;
- los tests abren temporalmente un `port-forward` en `127.0.0.1`;
- el túnel se cierra al terminar el job;
- el router doméstico no necesita publicar puertos.

> “Sin exposición a Internet” significa que no existen conexiones entrantes
> hacia el cluster. El equipo sí necesita conexiones salientes HTTPS hacia
> GitHub y GHCR para recibir jobs y descargar imágenes.

# Arquitectura del laboratorio

Se utilizan dos tipos de runner.

| Trabajo | Runner | Motivo |
| --- | --- | --- |
| Ruff, Bandit y unit tests | GitHub-hosted | Entorno limpio y descartable |
| Construcción y publicación | GitHub-hosted | Puede publicar directamente en GHCR |
| Kubernetes dev | Self-hosted local | Tiene acceso al contexto `docker-desktop` |
| Kubernetes production | Self-hosted local | Tiene acceso al cluster local |

El runner self-hosted inicia una conexión saliente hacia GitHub. GitHub no
inicia una conexión hacia tu notebook.

# Flujo del pull request

Cuando se abre o actualiza un PR hacia `main`:

1. GitHub ejecuta Ruff.
2. GitHub ejecuta Bandit.
3. GitHub ejecuta los unit tests.
4. GitHub construye la imagen.
5. GitHub publica `sha-<commit>` y `pr-<número>` en GHCR.
6. El runner local recibe el job.
7. Crea el namespace `dev-pr-<número>`.
8. Crea un pull secret temporal para GHCR.
9. Despliega dos réplicas de la API.
10. Espera el rollout.
11. Abre un túnel solamente en `127.0.0.1:18080`.
12. Ejecuta la regresión HTTP.
13. Cierra el túnel.
14. Elimina el namespace completo.
15. El check **Listo para merge** informa el resultado.

# Flujo de producción

Después del merge a `main`:

1. Se repiten análisis, unit tests y build.
2. Se publica la imagen exacta `sha-<commit>`.
3. El job referencia el entorno protegido `production`.
4. GitHub solicita aprobación.
5. El runner local despliega en el namespace `production`.
6. Kubernetes realiza un RollingUpdate.
7. Se ejecuta la regresión post-deploy.
8. Si falla, el workflow ejecuta `kubectl rollout undo`.
9. Si pasa, el deployment queda ejecutándose localmente.

# Parte 1 — Revisar el repositorio

## Paso 1. Identificar los archivos

```text
.
├── .github/
│   ├── actionlint.yaml
│   └── workflows/cicd.yml
├── app/__init__.py
├── k8s/app.yaml
├── tests/
│   ├── regression/test_api_contract.py
│   └── unit/test_app.py
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

Responsabilidad de cada archivo:

| Archivo | Responsabilidad |
| --- | --- |
| `app/__init__.py` | API Flask |
| `Dockerfile` | Imagen ejecutable |
| `compose.yaml` | Desarrollo local sin Kubernetes |
| `k8s/app.yaml` | Deployment y Service internos |
| `tests/unit` | Pruebas dentro del proceso Python |
| `tests/regression` | Pruebas contra una API desplegada |
| `cicd.yml` | Orquestación completa |

## Paso 2. Revisar la API

| Endpoint | Resultado |
| --- | --- |
| `GET /` | Nombre y rutas disponibles |
| `GET /health` | Estado, entorno y versión |
| `GET /api/stages` | Etapas del pipeline |
| `GET /api/progress?completed=3` | Porcentaje de avance |

# Parte 2 — Comprobar la aplicación localmente

## Paso 3. Levantar con Docker Compose

```bash
docker compose up --build --wait
```

Comprueba:

```bash
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/api/stages
curl "http://localhost:8000/api/progress?completed=3"
```

Resultado esperado para `/health`:

```json
{
  "environment": "local",
  "status": "ok",
  "version": "development"
}
```

Detén el entorno:

```bash
docker compose down
```

## Paso 4. Ejecutar los controles locales

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Ejecuta:

```bash
ruff check .
ruff format --check .
bandit --recursive app
pytest -v tests/unit
```

Resultados esperados:

```text
Ruff: sin errores
Bandit: sin hallazgos
Pytest: 8 passed
```

# Parte 3 — Crear el cluster de Docker Desktop

## Paso 5. Crear el cluster

En Docker Desktop 4.51 o posterior:

1. Abre **Kubernetes**.
2. Selecciona **Create cluster**.
3. Selecciona el provisioner `kind`.
4. Usa un nodo para esta práctica.
5. Selecciona **Create**.
6. Espera hasta que el estado sea verde.

## Paso 6. Seleccionar el contexto

```bash
kubectl config get-contexts
kubectl config use-context docker-desktop
kubectl cluster-info
kubectl get nodes
```

Resultado esperado:

- contexto actual: `docker-desktop`;
- al menos un nodo;
- nodo con estado `Ready`.

## Paso 7. Validar permisos

```bash
kubectl auth can-i create namespaces
kubectl auth can-i create deployments --namespace default
kubectl auth can-i create services --namespace default
```

Los tres comandos deben responder:

```text
yes
```

## Paso 8. Comprobar que no hay exposición

```bash
kubectl get services --all-namespaces
```

Los servicios internos del sistema pueden aparecer, pero esta práctica no
necesita ningún Ingress, NodePort o LoadBalancer.

# Parte 4 — Crear el repositorio de GitHub

## Paso 9. Crear un repositorio vacío

En GitHub:

1. Selecciona **New repository**.
2. Asigna un nombre, por ejemplo `formatec-flask-k8s`.
3. Preferentemente usa un repositorio privado.
4. No agregues README, licencia ni `.gitignore`.
5. Selecciona **Create repository**.

Un runner self-hosted no debe ejecutar código de colaboradores desconocidos.
Para una clase, limita el repositorio a participantes confiables.

## Paso 10. Asociar el repositorio

```bash
git remote add origin https://github.com/USUARIO/formatec-flask-k8s.git
git branch -M main
git push -u origin main
```

La primera ejecución utilizará runners hospedados por GitHub. Producción se
omite porque todavía no existe `PROD_DEPLOY_ENABLED=true`.

# Parte 5 — Instalar el runner self-hosted

## Paso 11. Abrir la configuración

En el repositorio:

1. Abre **Settings**.
2. Selecciona **Actions → Runners**.
3. Selecciona **New self-hosted runner**.
4. Selecciona macOS, Windows o Linux según tu equipo.
5. Selecciona la arquitectura correcta.

GitHub mostrará comandos específicos y un token de registro temporal.

## Paso 12. Descargar el runner

Crea una carpeta fuera del repositorio:

```bash
mkdir -p "$HOME/actions-runner-formatec"
cd "$HOME/actions-runner-formatec"
```

Ejecuta los comandos de descarga que GitHub muestra en pantalla.

No copies comandos de otro repositorio: el token es temporal y está asociado
al repositorio actual.

## Paso 13. Registrar la etiqueta `local-k8s`

GitHub mostrará un comando similar a:

```bash
./config.sh --url https://github.com/USUARIO/REPOSITORIO --token TOKEN
```

Agrega la etiqueta:

```bash
./config.sh \
  --url https://github.com/USUARIO/REPOSITORIO \
  --token TOKEN \
  --labels local-k8s
```

Cuando pregunte por el nombre, puedes usar:

```text
docker-desktop-k8s
```

Cuando pregunte por el work folder, acepta `_work`.

## Paso 14. Iniciar el runner

```bash
./run.sh
```

La terminal debe mostrar:

```text
Listening for Jobs
```

En GitHub, dentro de **Settings → Actions → Runners**, el runner debe aparecer:

```text
Idle
```

Para la primera práctica, déjalo ejecutándose en esa terminal.

## Paso 15. Validar herramientas desde el mismo usuario

Abre otra terminal con el mismo usuario que ejecuta `run.sh`:

```bash
kubectl config current-context
kubectl get nodes
python3 --version
curl --version
```

El contexto debe ser:

```text
docker-desktop
```

El runner usa el kubeconfig de ese usuario. Si ejecutas el runner con otro
usuario o como servicio, ese usuario también debe tener acceso al contexto.

# Parte 6 — Configurar GitHub

## Paso 16. Crear el entorno development

En **Settings → Environments**:

1. Crea `development`.
2. No agregues aprobación manual.
3. No agregues secrets.

El entorno dev se crea y destruye automáticamente por PR.

## Paso 17. Crear el entorno production

En **Settings → Environments**:

1. Crea `production`.
2. Agrega un **Required reviewer**.
3. Si trabajan varias personas, activa **Prevent self-review**.
4. Restringe el despliegue a la rama `main`.

No necesitas secrets SSH, IPs, dominios ni credenciales manuales de GHCR. El
workflow utiliza el `GITHUB_TOKEN` temporal del propio job.

## Paso 18. Habilitar producción

Abre:

```text
Settings → Secrets and variables → Actions → Variables
```

Crea:

| Nombre | Valor |
| --- | --- |
| `PROD_DEPLOY_ENABLED` | `true` |

# Parte 7 — Ejecutar un PR completo

## Paso 19. Crear una rama

```bash
git switch -c feature/romper-contrato
```

## Paso 20. Introducir una regresión

En `app/__init__.py`, cambia:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

por:

```python
"percent": calculate_progress(completed, len(STAGES)),
```

## Paso 21. Confirmar que los tests rápidos no la detectan

```bash
ruff check .
ruff format --check .
bandit --recursive app
pytest tests/unit
```

Resultado esperado:

- análisis estático verde;
- seguridad verde;
- unit tests verdes.

## Paso 22. Subir la rama

```bash
git add app/__init__.py
git commit -m "feat: renombrar campo percentage"
git push -u origin feature/romper-contrato
```

## Paso 23. Abrir el PR

En GitHub:

1. Abre **Pull requests**.
2. Crea un PR desde `feature/romper-contrato` hacia `main`.
3. No lo marques como draft.
4. Abre la pestaña **Checks**.

## Paso 24. Observar la publicación

Los primeros jobs deben mostrar:

```text
1 · Análisis estático y unit tests   success
2 · Construir imagen                 success
3 · Publicar imagen                  success
```

En **Packages**, aparecerán:

```text
sha-<commit>
pr-<número>
```

## Paso 25. Observar el namespace dev

Mientras el job `4 · Kubernetes dev y regresión` está ejecutándose, abre una
terminal local:

```bash
kubectl get namespaces --watch
```

Debe aparecer:

```text
dev-pr-<número>
```

En otra terminal:

```bash
kubectl get all --namespace dev-pr-<número>
```

Debes ver:

- un Deployment;
- dos Pods;
- un Service `ClusterIP`;
- ningún Ingress;
- ningún puerto público.

## Paso 26. Observar la regresión fallida

El runner abre temporalmente:

```text
127.0.0.1:18080 → Service formatec-api:80
```

La regresión espera `percentage`, pero la API responde `percent`.

Resultado:

```text
4 · Kubernetes dev y regresión   failure
Listo para merge                 failure
```

Después del fallo:

```bash
kubectl get namespace dev-pr-<número>
```

El namespace debe estar eliminado o en estado `Terminating`.

# Parte 8 — Corregir y habilitar el merge

## Paso 27. Restaurar el contrato

Vuelve a usar:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

## Paso 28. Subir la corrección

```bash
git add app/__init__.py
git commit -m "fix: restaurar contrato de progress"
git push
```

El mismo PR vuelve a ejecutar el workflow.

## Paso 29. Comprobar el resultado

El resumen **Listo para merge** debe mostrar:

| Control | Resultado |
| --- | --- |
| Análisis y unit tests | success |
| Imagen Docker | success |
| Publicación GHCR | success |
| Kubernetes dev y regresión | success |

El namespace dev se elimina aunque la prueba termine correctamente.

# Parte 9 — Proteger main

## Paso 30. Crear una regla

En **Settings → Rules → Rulesets** o **Branches**:

1. Aplica la regla a `main`.
2. Exige pull request.
3. Exige el check **Listo para merge**.
4. Exige que la rama esté actualizada.
5. Opcionalmente exige aprobación de código.
6. Bloquea pushes directos.

# Parte 10 — Desplegar production

## Paso 31. Hacer merge

Con el PR verde:

1. Selecciona **Merge pull request**.
2. Confirma.
3. Abre **Actions**.
4. Selecciona la ejecución de `main`.

## Paso 32. Observar la espera

Los jobs hospedados por GitHub ejecutan:

```text
análisis → build → publicación
```

El job:

```text
5 · Kubernetes production
```

queda esperando aprobación del entorno.

Mientras espera:

- el runner local todavía no recibió el job;
- el cluster no cambió;
- el job no accedió al cluster.

## Paso 33. Aprobar

En GitHub:

1. Abre la ejecución.
2. Selecciona **Review deployments**.
3. Marca `production`.
4. Selecciona **Approve and deploy**.

## Paso 34. Observar el runner

La terminal del runner debe mostrar que recibió:

```text
5 · Kubernetes production
```

El job:

1. selecciona `docker-desktop`;
2. crea el namespace `production`;
3. configura el pull secret temporal;
4. aplica el Deployment y el Service;
5. espera el RollingUpdate;
6. abre `127.0.0.1:18081`;
7. ejecuta la regresión;
8. cierra el túnel.

## Paso 35. Comprobar Kubernetes

```bash
kubectl get all --namespace production
kubectl get deployment formatec-api --namespace production
kubectl get pods --namespace production
kubectl get service formatec-api --namespace production
```

Resultado esperado:

```text
Deployment disponible
2 Pods Ready
Service tipo ClusterIP
```

Comprueba que la imagen coincide con `main`:

```bash
kubectl get deployment formatec-api \
  --namespace production \
  --output=jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

## Paso 36. Consultar producción localmente

Abre manualmente un túnel local:

```bash
kubectl port-forward \
  --namespace production \
  --address 127.0.0.1 \
  service/formatec-api 8080:80
```

En otra terminal:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/stages
```

`/health` debe mostrar:

```json
{
  "environment": "production",
  "status": "ok",
  "version": "<SHA de main>"
}
```

Detén el túnel con `Ctrl+C`.

# Parte 11 — Validar que no existe exposición

## Paso 37. Revisar el Service

```bash
kubectl get service formatec-api \
  --namespace production \
  --output=yaml
```

Busca:

```yaml
type: ClusterIP
```

No deben existir:

```yaml
type: NodePort
type: LoadBalancer
```

## Paso 38. Buscar recursos expuestos

```bash
kubectl get ingress --all-namespaces
kubectl get services --all-namespaces
```

La aplicación no debe aparecer como Ingress, NodePort o LoadBalancer.

## Paso 39. Comprobar conexiones

Cuando no hay un `kubectl port-forward` activo:

```bash
curl http://127.0.0.1:8080/health
```

La conexión debe fallar. Kubernetes continúa ejecutando la API, pero no existe
un camino desde el host hasta el Service.

# Parte 12 — Actualización y rollback

## Paso 40. Revisar el historial

```bash
kubectl rollout history deployment/formatec-api \
  --namespace production
```

## Paso 41. Observar una nueva promoción

En un nuevo PR:

1. modifica la API;
2. actualiza los tests;
3. espera dev y regresión;
4. haz merge;
5. aprueba production.

Kubernetes crea una revisión nueva y reemplaza los pods gradualmente.

## Paso 42. Rollback manual

```bash
kubectl rollout undo deployment/formatec-api \
  --namespace production

kubectl rollout status deployment/formatec-api \
  --namespace production
```

El workflow hace este rollback automáticamente si la regresión post-deploy
falla.

# Seguridad del runner self-hosted

El workflow contiene dos controles importantes:

1. El job dev solo acepta PRs cuya rama pertenece al mismo repositorio.
2. Producción solo acepta `main` y requiere el entorno protegido.

Los PR desde forks externos no pueden publicar ni ejecutar el runner local.

Aun así:

- usa únicamente colaboradores confiables;
- revisa cambios en `.github/workflows/` y `k8s/`;
- no guardes credenciales personales en la máquina del runner;
- usa un cluster dedicado al laboratorio;
- detén el runner cuando no se utiliza;
- no uses este runner para repositorios públicos con contribuciones abiertas.

# Problemas frecuentes

## El job queda en “Queued”

Comprueba:

1. que `./run.sh` esté ejecutándose;
2. que GitHub muestre el runner como `Idle`;
3. que tenga la etiqueta `local-k8s`;
4. que el equipo tenga salida HTTPS.

## `docker-desktop` no existe

```bash
kubectl config get-contexts
```

Si no aparece:

1. abre Docker Desktop;
2. crea o inicia el cluster Kubernetes;
3. espera el estado verde.

## El runner no accede a Kubernetes

Ejecuta con el mismo usuario del runner:

```bash
kubectl config current-context
kubectl get nodes
```

Si el runner se instaló como servicio, comprueba qué usuario ejecuta el
servicio y dónde busca su kubeconfig.

## `ImagePullBackOff`

```bash
kubectl describe pod \
  --namespace production \
  --selector app=formatec-api
```

Comprueba:

- que el job `3 · Publicar imagen` pasó;
- que la imagen `sha-<commit>` existe;
- que el package está vinculado al repositorio;
- que `GITHUB_TOKEN` tiene permiso `packages: read`;
- que Docker Desktop tiene salida a `ghcr.io`.

## El namespace dev permanece

```bash
kubectl delete namespace dev-pr-NUMERO
```

Después revisa el step **Destruir el namespace efímero**.

## El puerto local está ocupado

Busca un `kubectl port-forward` anterior y detenlo. El workflow utiliza:

```text
18080 para dev
18081 para production
```

## Producción aparece omitida

Comprueba la variable de repositorio:

```text
PROD_DEPLOY_ENABLED=true
```

## Producción queda esperando

Es el comportamiento esperado. Selecciona **Review deployments** y aprueba el
entorno `production`.

# Criterios de finalización

- [ ] Docker Desktop Kubernetes está activo.
- [ ] El contexto es `docker-desktop`.
- [ ] El runner `local-k8s` aparece online.
- [ ] Ruff, Bandit y unit tests pasan.
- [ ] El PR publica una imagen `pr-<número>`.
- [ ] Aparece un namespace dev efímero.
- [ ] La regresión bloquea un contrato incompatible.
- [ ] El namespace dev se elimina.
- [ ] **Listo para merge** queda verde después de corregir.
- [ ] Production espera aprobación.
- [ ] Production despliega dos pods.
- [ ] La imagen desplegada coincide con el SHA de `main`.
- [ ] El Service es `ClusterIP`.
- [ ] No existe Ingress, NodePort ni LoadBalancer.
- [ ] `/health` solo responde mientras existe un port-forward local.

# Referencias

- [Kubernetes en Docker Desktop](https://docs.docker.com/desktop/use-desktop/kubernetes/)
- [Runners self-hosted](https://docs.github.com/en/actions/reference/runners/self-hosted-runners)
- [Seguridad de GitHub Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [Secrets para registries privados](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_create_secret_docker-registry/)
