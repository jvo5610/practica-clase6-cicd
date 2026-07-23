#!/usr/bin/env bash
set -euo pipefail

ARGOCD_VERSION="${ARGOCD_VERSION:-v3.4.5}"
KUBE_CONTEXT="${KUBE_CONTEXT:-docker-desktop}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta el comando requerido: $1" >&2
    exit 1
  fi
}

normalize_repo_url() {
  case "$1" in
    git@github.com:*)
      printf 'https://github.com/%s\n' "${1#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      printf 'https://github.com/%s\n' "${1#ssh://git@github.com/}"
      ;;
    https://github.com/*)
      printf '%s\n' "$1"
      ;;
    *)
      echo "El remote origin debe apuntar a GitHub: $1" >&2
      exit 1
      ;;
  esac
}

for command_name in docker git kubectl sed; do
  require_command "$command_name"
done

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop no está iniciado." >&2
  exit 1
fi

kubectl config use-context "$KUBE_CONTEXT"
kubectl wait node --all --for=condition=Ready --timeout=120s

origin_url="$(git remote get-url origin)"
repo_url="$(normalize_repo_url "$origin_url")"

if ! git show-ref --verify --quiet refs/heads/main; then
  echo "No existe la rama local main." >&2
  exit 1
fi

if ! git ls-remote "$repo_url" HEAD >/dev/null 2>&1; then
  echo "Argo CD necesita que el repositorio sea público: $repo_url" >&2
  exit 1
fi

if ! git ls-remote --exit-code --heads origin gitops >/dev/null 2>&1; then
  echo "Creando la rama remota gitops..."
  git push origin refs/heads/main:refs/heads/gitops
fi

echo "Instalando Argo CD $ARGOCD_VERSION..."
kubectl create namespace argocd \
  --dry-run=client \
  --output=yaml | kubectl apply --filename=-

kubectl apply \
  --namespace argocd \
  --server-side \
  --force-conflicts \
  --filename "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

kubectl wait \
  --namespace argocd \
  --for=condition=Available \
  deployment \
  --all \
  --timeout=300s

kubectl rollout status \
  --namespace argocd \
  statefulset/argocd-application-controller \
  --timeout=300s

echo "Registrando la aplicación GitOps..."
sed "s|__REPO_URL__|$repo_url|g" \
  gitops/argocd/application.yaml | kubectl apply --filename=-

echo
echo "Bootstrap terminado."
echo "Repositorio observado: $repo_url"
echo "Rama observada: gitops"
echo
echo "Estado:"
echo "  kubectl get applications --namespace argocd"
echo "  kubectl get pods --namespace argocd"
echo
echo "Interfaz local:"
echo "  kubectl port-forward --namespace argocd service/argocd-server 8080:443"
