# Práctica: CI/CD con GitHub Actions

Repositorio autocontenido para transformar un cambio de código en una entrega
automática, visible y trazable. La práctica parte de la teoría de la Clase 6:
integrar, probar, construir, empaquetar y desplegar.

## Resultado final

Al terminar, cada estudiante habrá:

- trabajado con una rama y un pull request;
- observado un check fallido y lo habrá corregido;
- ejecutado lint, tests, build y construcción Docker en GitHub Actions;
- aprobado el cambio antes de incorporarlo a `main`;
- desplegado automáticamente la aplicación en GitHub Pages;
- identificado qué job, step, runner, evento, artefacto y entorno intervino.

La aplicación es una checklist interactiva de las cinco etapas del pipeline. No
usa librerías externas: el objetivo es estudiar la automatización, no resolver
dependencias de un framework.

## Alineación con la clase teórica

| Concepto de la clase | Evidencia en este repositorio |
| --- | --- |
| Integración continua | El job `ci` se ejecuta en cada PR y push a `main`. |
| Fallar rápido | Lint y tests se ejecutan antes del build y del despliegue. |
| Workflow, job, runner y step | Están identificados en `.github/workflows/cicd.yml`. |
| YAML | Eventos, permisos, dependencias y acciones están declarados como código. |
| Pull request y check rojo/verde | La actividad provoca un fallo controlado y luego lo corrige. |
| Artefacto versionable | El contenido de `dist/` se genera una sola vez y se entrega a Pages. |
| Paquete Docker | El pipeline construye la imagen y detiene el flujo si falla. |
| Entorno y permisos | El job `deploy` usa el entorno `github-pages` y permisos mínimos. |
| Entrega controlada | Solo `main`, después de CI verde, puede desplegar. |

## El pipeline que se va a observar

| Momento | Evento | Qué ocurre | ¿Despliega? |
| --- | --- | --- | --- |
| Trabajo en una rama | `push` a otra rama | No se ejecuta el workflow. | No |
| Apertura o actualización del PR | `pull_request` hacia `main` | Lint, tests, build y Docker. | No |
| Merge del PR | `push` a `main` | Repite CI, guarda el artefacto y ejecuta `deploy`. | Sí |
| Ejecución manual en `main` | `workflow_dispatch` | Ejecuta el pipeline completo. | Sí |

El job `deploy` declara `needs: ci`: si falla cualquier control, no hay entrega.
El despliegue usa exactamente el directorio `dist/` construido y validado por
el job anterior.

## Requisitos

- una cuenta gratuita de GitHub;
- Git instalado;
- Node.js 20 o posterior;
- Docker Desktop o Docker Engine (opcional para la prueba local del contenedor);
- un repositorio **público** para usar GitHub Pages con una cuenta gratuita.

Comprueba el entorno:

```bash
git --version
node --version
npm --version
docker --version
```

## Preparación del docente

1. Crear en GitHub un repositorio público vacío.
2. Copiar el contenido de esta carpeta al repositorio.
3. Subir el commit inicial a la rama `main`.
4. En **Settings → Pages → Build and deployment → Source**, seleccionar
   **GitHub Actions**.
5. En **Settings → Branches**, crear una regla para `main` que requiera pull
   request y el check **Integrar y validar**.
6. Confirmar que la ejecución inicial termina en verde y muestra la URL del
   entorno `github-pages`.

> La protección de rama puede depender del plan y del tipo de organización. Si
> no está disponible, se mantiene el flujo de PR como convención de la clase.

## Inicio rápido local

```bash
npm ci
npm run lint
npm test
npm run build
npm start
```

Abrir <http://localhost:8080>. Para detener el servidor, usar `Ctrl+C`.

Prueba opcional del mismo artefacto dentro de un contenedor:

```bash
docker build -t formatec-cicd:local .
docker run --rm -p 8080:80 formatec-cicd:local
```

## Guía de la práctica

Duración sugerida: 90 minutos. Trabajo individual o en parejas.

### 1. Reconocer el repositorio — 10 min

Localizar:

- el código de la aplicación en `src/`;
- los tests en `test/`;
- los comandos automatizados en `package.json`;
- la receta del contenedor en `Dockerfile`;
- el workflow en `.github/workflows/cicd.yml`.

Ejecutar localmente `npm ci`, `npm test` y `npm run build`. Comprobar que
aparece `dist/` y que Git no lo propone para commit: es un resultado generado.

### 2. Crear un cambio pequeño — 10 min

```bash
git switch -c feature/nueva-etapa
```

En `src/app.js`, cambiar el título de la etapa `Paquete` por `Empaquetado`.
Después:

```bash
npm test
```

El test debe fallar. Esto representa el **check rojo**: el cambio rompió un
contrato conocido antes de llegar al usuario.

### 3. Corregir el contrato — 10 min

En `test/app.test.js`, actualizar el valor esperado de `Paquete` a
`Empaquetado`. Ejecutar el mismo circuito que usará el runner:

```bash
npm run lint
npm test
npm run build
```

El resultado debe ser verde. Registrar el cambio:

```bash
git add src/app.js test/app.test.js
git commit -m "feat: renombrar etapa de empaquetado"
git push -u origin feature/nueva-etapa
```

### 4. Abrir el pull request — 15 min

1. Abrir un PR desde `feature/nueva-etapa` hacia `main`.
2. Entrar en la pestaña **Checks**.
3. Abrir el job **Integrar y validar**.
4. Identificar el evento, el runner y cada step.
5. Verificar que no existe un job de despliegue efectivo para el PR.

Responder:

1. ¿Qué paso fallaría si un test devuelve código de salida distinto de cero?
2. ¿Por qué el build se ejecuta después de los tests?
3. ¿Qué riesgo evita no desplegar desde un pull request?

### 5. Revisar, integrar y desplegar — 15 min

Con el check en verde, aprobar el PR y hacer merge. En **Actions**, abrir la
nueva ejecución disparada por el push a `main`.

Observar:

1. `ci` vuelve a validar el commit exacto incorporado a `main`;
2. `actions/upload-pages-artifact` guarda `dist/`;
3. `deploy` comienza solo cuando termina `ci`;
4. el entorno `github-pages` muestra la URL publicada.

Abrir la URL y confirmar que la interfaz muestra `Empaquetado`.

### 6. Leer el workflow como código — 15 min

Completar la tabla sin mirar la teoría:

| Pregunta | Respuesta en el YAML |
| --- | --- |
| ¿Cuándo se ejecuta? | `on` |
| ¿Dónde se ejecuta? | `runs-on` |
| ¿Qué unidades de trabajo existen? | `jobs` |
| ¿Qué tareas hace cada unidad? | `steps` |
| ¿Cómo se expresa la dependencia? | `needs` |
| ¿Cómo se limita el despliegue? | `if`, `environment` y `permissions` |
| ¿Qué resultado pasa de CI a CD? | artefacto de GitHub Pages |

### 7. Desafío — 15 min

Agregar una sexta etapa llamada `Observabilidad`.

Criterios de aceptación:

- la aplicación muestra seis etapas;
- el progreso continúa calculándose correctamente;
- existe al menos un test nuevo;
- el PR queda verde;
- el merge genera un nuevo despliegue.

## Anatomía del workflow

### Eventos

`pull_request` valida antes de integrar. `push` a `main` valida el resultado del
merge y habilita la entrega. `workflow_dispatch` permite repetir el pipeline
manualmente desde la pestaña Actions.

### Job `ci`

1. descarga el commit con `actions/checkout`;
2. prepara Node.js con `actions/setup-node`;
3. instala de forma reproducible con `npm ci`;
4. ejecuta lint y tests;
5. genera `dist/`;
6. comprueba que la imagen Docker se puede construir;
7. en `main`, empaqueta `dist/` como artefacto para Pages.

### Job `deploy`

- depende de `ci`;
- solo corre para `main` y nunca para un PR;
- recibe únicamente `pages: write` e `id-token: write`;
- publica en el entorno `github-pages`;
- expone la URL como salida del step `deployment`.

No hay contraseñas en el YAML. GitHub entrega credenciales temporales al job
con los permisos declarados.

## Evaluación

| Evidencia | Logrado |
| --- | --- |
| Explica la diferencia entre CI y CD usando este workflow. | ☐ |
| Presenta un PR con un cambio pequeño y trazable. | ☐ |
| Interpreta un check rojo a partir del log. | ☐ |
| Corrige el código o el test y obtiene un check verde. | ☐ |
| Identifica el artefacto que se despliega. | ☐ |
| Demuestra la aplicación publicada. | ☐ |
| Explica por qué el job `deploy` no corre en un PR. | ☐ |

## Problemas frecuentes

### Pages no despliega

Confirmar que el repositorio es público y que en **Settings → Pages** la fuente
seleccionada es **GitHub Actions**. Revisar también que la ejecución corresponde
a `main`, no a un PR.

### `deploy` aparece como omitido

Es el comportamiento correcto en un pull request. El `if` permite desplegar
solo desde `refs/heads/main`.

### `npm ci` falla

Usar Node.js 20 o posterior y no eliminar `package-lock.json`. Si se modifica
`package.json`, regenerar el lockfile con `npm install`.

### La URL todavía muestra la versión anterior

Comprobar que terminó el job `deploy` y hacer una recarga forzada del navegador.

### El build Docker falla localmente

Confirmar que Docker está iniciado. La publicación en Pages no ejecuta el
contenedor: Docker es una validación adicional de portabilidad.

## Extensión: publicar una imagen Docker

La clase teórica muestra login, build, tag y push. Como ampliación, se puede
agregar un job que publique en Docker Hub o GitHub Container Registry. Ese job
debe:

1. depender de `ci`;
2. ejecutarse solo desde `main` o desde tags;
3. obtener credenciales desde `secrets`, nunca desde el YAML;
4. producir tags trazables, por ejemplo el SHA y una versión;
5. publicar únicamente si todos los tests pasaron.

Esta extensión publica un paquete, pero no sustituye el despliegue de Pages:
**publicar una imagen** la deja disponible en un registry; **desplegar** pone la
aplicación en ejecución en un entorno.

## Estructura

```text
.
├── .github/workflows/cicd.yml
├── scripts/
│   ├── build.mjs
│   ├── lint.mjs
│   └── serve.mjs
├── src/
│   ├── app.js
│   ├── index.html
│   └── styles.css
├── test/app.test.js
├── Dockerfile
├── nginx.conf
├── package.json
└── README.md
```

## Referencias

- [Crear y probar código Node.js con GitHub Actions](https://docs.github.com/es/actions/tutorials/build-and-test-code/nodejs)
- [Usar workflows personalizados con GitHub Pages](https://docs.github.com/es/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Sintaxis de workflows](https://docs.github.com/es/actions/reference/workflows-and-actions/workflow-syntax)
- [Uso de secretos en GitHub Actions](https://docs.github.com/es/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)

