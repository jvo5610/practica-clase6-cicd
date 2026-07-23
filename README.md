# Laboratorio desde cero: CI/CD con GitHub Actions y Argo CD

Esta práctica parte de:

- una cuenta de GitHub;
- Docker Desktop con un cluster Kubernetes local;
- Git y una terminal Bash.

Al finalizar tendrás:

```text
Pull request
  → Ruff
  → Bandit
  → unit tests
  → Docker Compose
  → regresión HTTP
  → Listo para merge

Merge a main
  → nueva validación
  → imagen inmutable en GHCR
  → actualización de la rama gitops
  → Argo CD detecta el cambio
  → despliegue en Docker Desktop Kubernetes
  → smoke test PostSync
```

No se utiliza:

- runner self-hosted;
- SSH;
- VPN;
- webhook;
- Ingress;
- LoadBalancer;
- NodePort;
- IP pública;
- Argo CD expuesto a Internet.

Argo CD consulta GitHub desde el cluster mediante conexiones salientes. GitHub
Actions nunca se conecta al cluster local.

Por eso el laboratorio funciona detrás de NAT y no requiere abrir puertos en el
router.

# 1. Qué contiene el repositorio

```text
.
├── .github/workflows/cicd.yml
├── app/__init__.py
├── gitops/
│   ├── argocd/application.yaml
│   └── production/kustomization.yaml
├── k8s/base/
│   ├── deployment.yaml
│   ├── kustomization.yaml
│   ├── service.yaml
│   └── smoke-test.yaml
├── scripts/
│   ├── bootstrap-argocd.sh
│   └── verify-gitops.sh
├── tests/
│   ├── regression/test_api_contract.py
│   └── unit/test_app.py
├── compose.yaml
├── Dockerfile
├── pyproject.toml
├── requirements-dev.txt
└── requirements.txt
```

## Responsabilidades

| Componente | Responsabilidad |
| --- | --- |
| GitHub Actions | Integración continua y promoción |
| Docker Compose | Entorno de regresión previo al merge |
| GHCR | Registro de imágenes |
| Rama `gitops` | Estado deseado de producción |
| Argo CD | Entrega continua |
| Kubernetes | Entorno productivo local |
| Hook `PostSync` | Validación posterior al despliegue |

# 2. Requisitos

## Paso 1. Comprobar Docker Desktop

```bash
docker version
docker compose version
```

Los dos comandos deben responder correctamente.

## Paso 2. Comprobar Git

```bash
git --version
```

## Paso 3. Comprobar Bash

En macOS o Linux:

```bash
bash --version
```

En Windows, ejecuta la práctica desde Git Bash o WSL.

## Paso 4. Comprobar Kubernetes

```bash
kubectl version --client
kubectl config get-contexts
```

Si `docker-desktop` todavía no existe, créalo en la siguiente sección.

# 3. Crear el cluster local

## Paso 5. Habilitar Kubernetes

En Docker Desktop 4.51 o posterior:

1. Abre Docker Desktop.
2. Selecciona **Kubernetes**.
3. Selecciona **Create cluster**.
4. Elige `kind`.
5. Usa un nodo.
6. Selecciona **Create**.
7. Espera el indicador verde.

## Paso 6. Seleccionar el contexto

```bash
kubectl config use-context docker-desktop
kubectl cluster-info
kubectl get nodes
```

Resultado esperado:

```text
desktop-control-plane   Ready
```

## Paso 7. Comprobar permisos

```bash
kubectl auth can-i create namespaces
kubectl auth can-i create deployments --namespace default
kubectl auth can-i create customresourcedefinitions
```

Los tres comandos deben responder:

```text
yes
```

# 4. Crear el fork

Cada estudiante trabaja en su propio fork. Eso permite que cada persona tenga:

- su propio GitHub Actions;
- su propio package en GHCR;
- su propia rama `gitops`;
- su propio cluster Argo CD.

## Paso 8. Crear el fork

En GitHub:

1. Abre el repositorio entregado por el docente.
2. Selecciona **Fork**.
3. Usa tu cuenta como propietario.
4. Conserva el nombre del repositorio.
5. Selecciona **Create fork**.

El fork debe ser público para que Argo CD pueda leerlo sin credenciales.

## Paso 9. Habilitar Actions

Dentro del fork:

1. Abre **Actions**.
2. Selecciona **I understand my workflows, go ahead and enable them**.

## Paso 10. Clonar el fork

Reemplaza `TU_USUARIO`:

```bash
git clone https://github.com/TU_USUARIO/practica-clase6-cicd.git
cd practica-clase6-cicd
```

Comprueba:

```bash
git remote -v
git branch --show-current
```

El remote `origin` debe apuntar a tu fork y la rama debe ser `main`.

# 5. Configurar permisos de GitHub Actions

El workflow necesita escribir únicamente en:

- GHCR, para publicar la imagen;
- la rama `gitops`, para registrar la promoción.

## Paso 11. Permitir escritura

En el fork:

1. Abre **Settings**.
2. Selecciona **Actions → General**.
3. Baja hasta **Workflow permissions**.
4. Selecciona **Read and write permissions**.
5. Guarda.

No debes crear tokens personales ni secrets para este laboratorio.

## Paso 12. Crear el entorno production

En el fork:

1. Abre **Settings → Environments**.
2. Selecciona **New environment**.
3. Escribe `production`.
4. Guarda.

Para una promoción automática no agregues reviewers.

Para practicar aprobación manual:

1. Agrega tu usuario como **Required reviewer**.
2. No actives **Prevent self-review** si trabajas solo.

# 6. Ejecutar CI por primera vez

## Paso 13. Iniciar manualmente el workflow

En GitHub:

1. Abre **Actions**.
2. Selecciona **CI/CD**.
3. Selecciona **Run workflow**.
4. Elige `main`.
5. Confirma.

## Paso 14. Observar análisis y unit tests

Abre el job:

```text
1 · Análisis estático y unit tests
```

Debe ejecutar:

```text
Ruff
Bandit
8 unit tests
```

## Paso 15. Observar Docker Compose

Abre:

```text
2 · Docker Compose y regresión
```

El job:

1. construye la imagen;
2. inicia Gunicorn con Docker Compose;
3. espera `/health`;
4. ejecuta cuatro tests HTTP;
5. elimina el entorno.

Resultado esperado:

```text
4 passed
```

## Paso 16. Observar la publicación

Abre:

```text
3 · Publicar imagen
```

Se publican dos tags:

```text
ghcr.io/TU_USUARIO/practica-clase6-cicd:sha-<commit>
ghcr.io/TU_USUARIO/practica-clase6-cicd:latest
```

# 7. Hacer pública la imagen

GHCR crea el primer package como privado. Argo CD no tiene credenciales
personales, por lo que la imagen debe ser pública.

Este paso se realiza una sola vez por fork.

## Paso 17. Cambiar la visibilidad

Después de terminar el job de publicación:

1. Abre tu perfil de GitHub.
2. Selecciona **Packages**.
3. Abre `practica-clase6-cicd`.
4. Selecciona **Package settings**.
5. Baja hasta **Danger Zone**.
6. Selecciona **Change visibility**.
7. Selecciona **Public**.
8. Confirma escribiendo el nombre solicitado.

> GitHub advierte que un package público no puede volver a ser privado. Usa
> este repositorio exclusivamente para la práctica.

Comprueba sin autenticación:

```bash
docker pull ghcr.io/TU_USUARIO/practica-clase6-cicd:latest
```

# 8. Confirmar la promoción

## Paso 18. Aprobar si configuraste reviewer

Si el job:

```text
4 · Promover estado GitOps
```

está esperando:

1. abre la ejecución;
2. selecciona **Review deployments**;
3. marca `production`;
4. selecciona **Approve and deploy**.

Si no configuraste reviewer, el job continúa automáticamente.

## Paso 19. Revisar el commit GitOps

El job copia desde el commit aprobado los manifests de `k8s/` y
`gitops/production/`. Después fija en la rama `gitops` la imagen inmutable:

```yaml
images:
  - name: formatec-api
    newName: ghcr.io/TU_USUARIO/practica-clase6-cicd
    newTag: sha-<commit>
```

Comprueba:

```bash
git fetch origin gitops
git show origin/gitops:gitops/production/kustomization.yaml
```

No cambies tu rama local a `gitops`.

# 9. Instalar Argo CD automáticamente

Primero se publica la imagen y se actualiza `gitops`; recién entonces se
registra la aplicación. Así Argo CD nunca intenta desplegar el valor provisional
del repositorio.

El script:

1. verifica Docker, Git y Kubernetes;
2. selecciona `docker-desktop`;
3. comprueba que `gitops` ya contiene una imagen promovida;
4. instala Argo CD `v3.4.5`;
5. espera todos los componentes;
6. registra el fork como repositorio observado;
7. crea la Application `formatec-production`.

## Paso 20. Ejecutar el bootstrap

Desde la raíz del repositorio:

```bash
./scripts/bootstrap-argocd.sh
```

La primera instalación puede tardar varios minutos. Si la promoción aún no
terminó, el script se detiene antes de crear la Application y explica qué falta.

## Paso 21. Comprobar Argo CD

```bash
kubectl get pods --namespace argocd
kubectl get applications --namespace argocd
```

Los pods de Argo CD deben quedar `Running`.

## Paso 22. Confirmar la rama GitOps

```bash
git ls-remote --heads origin gitops
```

Debe mostrar una referencia:

```text
refs/heads/gitops
```

# 10. Esperar la entrega continua

Argo CD consulta GitHub periódicamente. Sin webhook, la detección puede tardar
hasta aproximadamente tres minutos.

## Paso 23. Observar la Application

```bash
kubectl get application formatec-production \
  --namespace argocd \
  --watch
```

El estado esperado es:

```text
SYNC STATUS   HEALTH STATUS
Synced        Healthy
```

Usa `Ctrl+C` para salir.

## Paso 24. Ejecutar la verificación automatizada

```bash
./scripts/verify-gitops.sh
```

El script verifica:

- Application `Synced`;
- Application `Healthy`;
- Deployment disponible;
- Service `ClusterIP`;
- ausencia de Ingress;
- `/health`;
- `environment: production`.

Resultado final esperado:

```text
Validación GitOps completada.
```

## Paso 25. Revisar Kubernetes

```bash
kubectl get all --namespace production
```

Debes encontrar:

- un Deployment;
- dos Pods;
- un Service `ClusterIP`;
- ningún Ingress;
- ningún puerto público.

Comprueba la imagen:

```bash
kubectl get deployment formatec-api \
  --namespace production \
  --output=jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```

Debe coincidir con el tag SHA publicado por GitHub Actions.

# 11. Ver la API sin exponerla

## Paso 26. Abrir un túnel local

```bash
kubectl port-forward \
  --namespace production \
  --address 127.0.0.1 \
  service/formatec-api 8080:80
```

## Paso 27. Probar la API

En otra terminal:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/stages
curl "http://127.0.0.1:8080/api/progress?completed=3"
```

`/health` debe devolver:

```json
{
  "environment": "production",
  "status": "ok",
  "version": "sha-<commit>"
}
```

Detén el túnel con `Ctrl+C`.

Sin el túnel:

```bash
curl http://127.0.0.1:8080/health
```

La conexión debe fallar. La API continúa funcionando dentro del cluster, pero
no está expuesta.

# 12. Comprobar el PostSync

Argo CD ejecuta un Job después de que Deployment y Service están saludables.

El Job consulta dentro del cluster:

```text
http://formatec-api/health
http://formatec-api/api/stages
```

## Paso 28. Revisar el historial de sincronización

```bash
kubectl describe application formatec-production --namespace argocd
```

Busca una operación `Succeeded`.

El Job exitoso se elimina automáticamente. Si falla, permanece temporalmente
para diagnóstico y la sincronización queda fallida.

# 13. Práctica con pull request

Ahora se prueba el control previo al merge.

## Paso 29. Crear una rama

```bash
git switch main
git pull
git switch -c feature/romper-contrato
```

## Paso 30. Introducir una regresión

En `app/__init__.py`, cambia:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

por:

```python
"percent": calculate_progress(completed, len(STAGES)),
```

## Paso 31. Comprobar los controles rápidos

```bash
source .venv/bin/activate 2>/dev/null || true
ruff check .
ruff format --check .
bandit --recursive app
pytest tests/unit
```

Los controles deben pasar. La regresión todavía no fue ejecutada.

## Paso 32. Subir la rama

```bash
git add app/__init__.py
git commit -m "feat: renombrar campo percentage"
git push -u origin feature/romper-contrato
```

## Paso 33. Abrir un PR dentro del fork

En GitHub:

1. abre **Pull requests** dentro de tu fork;
2. crea un PR de `feature/romper-contrato` hacia `main`;
3. abre **Checks**.

No abras este PR hacia el repositorio del docente: la promoción productiva de
cada estudiante ocurre en su propio fork.

## Paso 34. Interpretar el check rojo

Resultado esperado:

```text
1 · Análisis estático y unit tests   success
2 · Docker Compose y regresión       failure
Listo para merge                     failure
```

La regresión observa:

```text
esperado: percentage
recibido: percent
```

Producción no cambia.

# 14. Corregir y volver a promover

## Paso 35. Restaurar el contrato

Vuelve a:

```python
"percentage": calculate_progress(completed, len(STAGES)),
```

## Paso 36. Subir la corrección

```bash
git add app/__init__.py
git commit -m "fix: restaurar contrato de progress"
git push
```

El mismo PR se actualiza.

## Paso 37. Esperar el check verde

Resultado esperado:

```text
1 · Análisis estático y unit tests   success
2 · Docker Compose y regresión       success
Listo para merge                     success
```

## Paso 38. Hacer merge

1. Selecciona **Merge pull request**.
2. Confirma.
3. Observa la ejecución de `main`.
4. Aprueba `production` si corresponde.
5. Espera Argo CD.
6. Ejecuta:

```bash
./scripts/verify-gitops.sh
```

El SHA de `/health` debe cambiar al nuevo commit.

# 15. Proteger main

Después de que GitHub haya registrado **Listo para merge**:

1. abre **Settings → Rules → Rulesets** o **Branches**;
2. crea una regla para `main`;
3. exige pull request;
4. exige el check **Listo para merge**;
5. exige que la rama esté actualizada;
6. bloquea pushes directos.

No protejas la rama `gitops` en esta práctica: GitHub Actions necesita
actualizarla.

# 16. Acceder a la interfaz de Argo CD

No es necesario instalar el CLI.

## Paso 39. Obtener la contraseña inicial

```bash
kubectl get secret argocd-initial-admin-secret \
  --namespace argocd \
  --output=jsonpath='{.data.password}' |
base64 --decode
echo
```

Usuario:

```text
admin
```

## Paso 40. Abrir la interfaz local

```bash
kubectl port-forward \
  --namespace argocd \
  --address 127.0.0.1 \
  service/argocd-server 8080:443
```

Abre:

```text
https://127.0.0.1:8080
```

El certificado local genera una advertencia del navegador. Argo CD continúa
sin exposición pública.

# 17. Reiniciar el laboratorio

## Eliminar únicamente la aplicación

```bash
kubectl delete application formatec-production --namespace argocd
kubectl delete namespace production --ignore-not-found
```

Volver a registrar:

```bash
./scripts/bootstrap-argocd.sh
```

## Eliminar Argo CD completamente

```bash
kubectl delete namespace argocd
kubectl delete namespace production --ignore-not-found
```

La rama `gitops`, el fork y las imágenes de GHCR no se eliminan.

# 18. Problemas frecuentes

## `bootstrap-argocd.sh` dice que el repositorio debe ser público

Comprueba que:

- `origin` apunta a tu fork;
- el fork es público;
- puedes abrirlo sin iniciar sesión.

```bash
git remote -v
git ls-remote origin HEAD
```

## La rama `gitops` no existe

```bash
git push origin main:gitops
```

Después vuelve a ejecutar el bootstrap.

## El job de promoción no puede hacer push

Configura:

```text
Settings
→ Actions
→ General
→ Workflow permissions
→ Read and write permissions
```

No protejas `gitops`.

## Argo CD muestra `ImagePullBackOff`

Comprueba:

1. que el workflow publicó la imagen;
2. que el package es público;
3. que el tag SHA existe;
4. que Docker Desktop tiene salida a `ghcr.io`.

```bash
kubectl describe pods --namespace production
```

## Argo CD todavía no detecta el commit

Sin webhook puede tardar unos minutos.

Comprueba:

```bash
git fetch origin gitops
git log --oneline origin/gitops -3
kubectl get application formatec-production --namespace argocd
```

## El hook PostSync falla

```bash
kubectl get jobs,pods --namespace production
kubectl logs job/formatec-api-smoke --namespace production
```

## El puerto 8000 está ocupado durante Compose

```bash
APP_PORT=8081 docker compose up --build --wait
BASE_URL=http://127.0.0.1:8081 pytest -m regression tests/regression
APP_PORT=8081 docker compose down
```

# 19. Criterios de finalización

- [ ] Fork público creado.
- [ ] Actions habilitado.
- [ ] Workflow con permisos de escritura.
- [ ] Cluster `docker-desktop` Ready.
- [ ] Argo CD instalado mediante el script.
- [ ] Rama remota `gitops` creada.
- [ ] Análisis estático aprobado.
- [ ] Ocho unit tests aprobados.
- [ ] Cuatro tests de regresión aprobados.
- [ ] Imagen SHA publicada en GHCR.
- [ ] Package público.
- [ ] Commit de promoción en `gitops`.
- [ ] Application `Synced`.
- [ ] Application `Healthy`.
- [ ] Dos pods de producción Ready.
- [ ] Service `ClusterIP`.
- [ ] Smoke test PostSync aprobado.
- [ ] API accesible únicamente mediante port-forward local.
- [ ] PR rojo observado.
- [ ] PR corregido y verde.
- [ ] Nueva versión promovida después del merge.

# 20. Referencias

- [Argo CD](https://argo-cd.readthedocs.io/en/stable/)
- [Sincronización automática](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)
- [Automatización desde CI](https://argo-cd.readthedocs.io/en/stable/user-guide/ci_automation/)
- [Sync hooks](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/)
- [Kubernetes en Docker Desktop](https://docs.docker.com/desktop/use-desktop/kubernetes/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
