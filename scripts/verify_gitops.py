"""Verifica la entrega GitOps y la API sin depender de herramientas Unix."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

KUBE_CONTEXT = os.getenv("KUBE_CONTEXT", "docker-desktop")
APPLICATION = os.getenv("APPLICATION", "formatec-production")
ARGOCD_NAMESPACE = os.getenv("ARGOCD_NAMESPACE", "argocd")
APP_NAMESPACE = os.getenv("APP_NAMESPACE", "production")
LOCAL_PORT = int(os.getenv("LOCAL_PORT", "18082"))
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def run(
    *command: str,
    capture_output: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def output(*command: str) -> str:
    return run(*command, capture_output=True).stdout.strip()


def kubernetes_value(jsonpath: str) -> str:
    result = run(
        "kubectl",
        "get",
        "application",
        APPLICATION,
        "--namespace",
        ARGOCD_NAMESPACE,
        f"--output=jsonpath={jsonpath}",
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def require_commands(*commands: str) -> None:
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise RuntimeError("Faltan comandos requeridos en PATH: " + ", ".join(missing))


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    port_forward: subprocess.Popen[str] | None = None
    log_handle = None
    log_path = Path(tempfile.gettempdir()) / "formatec-gitops-port-forward.log"

    try:
        require_commands("git", "kubectl")
        run("kubectl", "config", "use-context", KUBE_CONTEXT)

        remote_line = output(
            "git", "ls-remote", "--exit-code", "origin", "refs/heads/gitops"
        )
        expected_revision = remote_line.split()[0]

        print("Esperando que Argo CD sincronice...")
        for attempt in range(1, 61):
            sync_status = kubernetes_value("{.status.sync.status}")
            health_status = kubernetes_value("{.status.health.status}")
            operation_phase = kubernetes_value("{.status.operationState.phase}")
            deployed_revision = kubernetes_value("{.status.sync.revision}")

            print(
                f"Intento {attempt}/60: "
                f"sync={sync_status or 'pendiente'} "
                f"health={health_status or 'pendiente'} "
                f"hook={operation_phase or 'pendiente'} "
                f"revision={deployed_revision or 'pendiente'}"
            )

            if (
                sync_status == "Synced"
                and health_status == "Healthy"
                and operation_phase == "Succeeded"
                and deployed_revision == expected_revision
            ):
                break
            if attempt == 60:
                run(
                    "kubectl",
                    "get",
                    "application",
                    APPLICATION,
                    "--namespace",
                    ARGOCD_NAMESPACE,
                    "--output=yaml",
                    check=False,
                )
                raise RuntimeError("Argo CD no alcanzó el estado esperado.")
            time.sleep(5)

        run(
            "kubectl",
            "rollout",
            "status",
            "deployment/formatec-api",
            "--namespace",
            APP_NAMESPACE,
            "--timeout=180s",
        )

        service_type = output(
            "kubectl",
            "get",
            "service",
            "formatec-api",
            "--namespace",
            APP_NAMESPACE,
            "--output=jsonpath={.spec.type}",
        )
        if service_type != "ClusterIP":
            raise RuntimeError(f"El Service expone un tipo inesperado: {service_type}")

        ingress_result = run(
            "kubectl",
            "get",
            "ingress",
            "--namespace",
            APP_NAMESPACE,
            "--no-headers",
            capture_output=True,
            check=False,
        )
        if ingress_result.returncode == 0 and ingress_result.stdout.strip():
            raise RuntimeError("No debería existir un Ingress en production.")

        log_handle = log_path.open("w", encoding="utf-8")
        port_forward = subprocess.Popen(
            [
                "kubectl",
                "port-forward",
                "--namespace",
                APP_NAMESPACE,
                "--address",
                "127.0.0.1",
                "service/formatec-api",
                f"{LOCAL_PORT}:80",
            ],
            cwd=REPOSITORY_ROOT,
            text=True,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )

        health_url = f"http://127.0.0.1:{LOCAL_PORT}/health"
        for attempt in range(1, 16):
            print(f"Health check local {attempt}/15")
            try:
                with urllib.request.urlopen(health_url, timeout=3) as response:
                    body = json.load(response)
                print(json.dumps(body, ensure_ascii=False, sort_keys=True))
                if (
                    body.get("status") == "ok"
                    and body.get("environment") == "production"
                    and str(body.get("version", "")).startswith("sha-")
                ):
                    print("Validación GitOps completada, incluido el hook PostSync.")
                    return 0
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                pass
            time.sleep(2)

        if log_handle is not None:
            log_handle.flush()
        if log_path.exists():
            print(log_path.read_text(encoding="utf-8"))
        raise RuntimeError("La API no respondió con el contrato esperado.")
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    finally:
        if port_forward is not None:
            stop_process(port_forward)
        if log_handle is not None:
            log_handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
