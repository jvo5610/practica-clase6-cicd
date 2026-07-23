#!/usr/bin/env bash
set -euo pipefail

KUBE_CONTEXT="${KUBE_CONTEXT:-docker-desktop}"
APPLICATION="${APPLICATION:-formatec-production}"
ARGOCD_NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
APP_NAMESPACE="${APP_NAMESPACE:-production}"
LOCAL_PORT="${LOCAL_PORT:-18082}"

# shellcheck disable=SC2329
cleanup() {
  if [ -n "${PORT_FORWARD_PID:-}" ]; then
    kill "$PORT_FORWARD_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT

kubectl config use-context "$KUBE_CONTEXT" >/dev/null

echo "Esperando que Argo CD sincronice..."
for attempt in $(seq 1 60); do
  sync_status="$(
    kubectl get application "$APPLICATION" \
      --namespace "$ARGOCD_NAMESPACE" \
      --output=jsonpath='{.status.sync.status}' 2>/dev/null || true
  )"
  health_status="$(
    kubectl get application "$APPLICATION" \
      --namespace "$ARGOCD_NAMESPACE" \
      --output=jsonpath='{.status.health.status}' 2>/dev/null || true
  )"

  echo "Intento $attempt/60: sync=${sync_status:-pendiente} health=${health_status:-pendiente}"

  if [ "$sync_status" = "Synced" ] && [ "$health_status" = "Healthy" ]; then
    break
  fi

  if [ "$attempt" -eq 60 ]; then
    echo "Argo CD no alcanzó Synced/Healthy." >&2
    kubectl get application "$APPLICATION" \
      --namespace "$ARGOCD_NAMESPACE" \
      --output=yaml
    exit 1
  fi

  sleep 5
done

kubectl rollout status deployment/formatec-api \
  --namespace "$APP_NAMESPACE" \
  --timeout=180s

service_type="$(
  kubectl get service formatec-api \
    --namespace "$APP_NAMESPACE" \
    --output=jsonpath='{.spec.type}'
)"

if [ "$service_type" != "ClusterIP" ]; then
  echo "El Service expone un tipo inesperado: $service_type" >&2
  exit 1
fi

if kubectl get ingress --namespace "$APP_NAMESPACE" --no-headers 2>/dev/null |
  grep -q .; then
  echo "No debería existir un Ingress en production." >&2
  exit 1
fi

kubectl port-forward \
  --namespace "$APP_NAMESPACE" \
  --address 127.0.0.1 \
  service/formatec-api "$LOCAL_PORT":80 \
  > /tmp/formatec-gitops-port-forward.log 2>&1 &
PORT_FORWARD_PID=$!

for attempt in $(seq 1 15); do
  echo "Health check local $attempt/15"
  if response="$(curl --fail --silent "http://127.0.0.1:$LOCAL_PORT/health")"; then
    echo "$response"
    case "$response" in
      *'"status":"ok"'*'"environment":"production"'* | \
        *'"environment":"production"'*'"status":"ok"'*)
        echo "Validación GitOps completada."
        exit 0
        ;;
    esac
  fi
  sleep 2
done

cat /tmp/formatec-gitops-port-forward.log
echo "La API no respondió con el contrato esperado." >&2
exit 1
