"""Instala Argo CD y registra la aplicación GitOps de forma multiplataforma."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ARGOCD_VERSION = os.getenv("ARGOCD_VERSION", "v3.4.5")
KUBE_CONTEXT = os.getenv("KUBE_CONTEXT", "docker-desktop")
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def run(
    *command: str,
    capture_output: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        check=True,
        text=True,
        input=input_text,
        capture_output=capture_output,
    )


def output(*command: str) -> str:
    return run(*command, capture_output=True).stdout.strip()


def require_commands(*commands: str) -> None:
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise RuntimeError("Faltan comandos requeridos en PATH: " + ", ".join(missing))


def normalize_repo_url(remote: str) -> str:
    if remote.startswith("git@github.com:"):
        return f"https://github.com/{remote.removeprefix('git@github.com:')}"
    if remote.startswith("ssh://git@github.com/"):
        return f"https://github.com/{remote.removeprefix('ssh://git@github.com/')}"
    if remote.startswith("https://github.com/"):
        return remote
    raise RuntimeError(f"El remote origin debe apuntar a GitHub: {remote}")


def remote_branch_exists(branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    try:
        require_commands("docker", "git", "kubectl")
        run("docker", "info", capture_output=True)
        run("kubectl", "config", "use-context", KUBE_CONTEXT)
        run(
            "kubectl",
            "wait",
            "node",
            "--all",
            "--for=condition=Ready",
            "--timeout=120s",
        )

        origin_url = output("git", "remote", "get-url", "origin")
        repo_url = normalize_repo_url(origin_url)

        if (
            subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", "refs/heads/main"],
                cwd=REPOSITORY_ROOT,
                check=False,
            ).returncode
            != 0
        ):
            raise RuntimeError("No existe la rama local main.")

        public_check = subprocess.run(
            ["git", "ls-remote", repo_url, "HEAD"],
            cwd=REPOSITORY_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if public_check.returncode != 0:
            raise RuntimeError(
                f"Argo CD necesita que el repositorio sea público: {repo_url}"
            )

        if not remote_branch_exists("gitops"):
            print("Creando la rama remota gitops...")
            run("git", "push", "origin", "refs/heads/main:refs/heads/gitops")

        run("git", "fetch", "--quiet", "origin", "gitops")
        manifest = output(
            "git",
            "show",
            "FETCH_HEAD:gitops/production/kustomization.yaml",
        )
        if (
            "replace/after-first-workflow" in manifest
            or "newTag: bootstrap" in manifest
        ):
            raise RuntimeError(
                "La rama gitops todavía contiene la imagen provisional.\n"
                "Ejecuta CI/CD sobre main, espera el job de promoción y "
                "vuelve a intentar."
            )

        print(f"Instalando Argo CD {ARGOCD_VERSION}...")
        namespace_yaml = output(
            "kubectl",
            "create",
            "namespace",
            "argocd",
            "--dry-run=client",
            "--output=yaml",
        )
        run("kubectl", "apply", "--filename=-", input_text=namespace_yaml)

        install_url = (
            "https://raw.githubusercontent.com/argoproj/argo-cd/"
            f"{ARGOCD_VERSION}/manifests/install.yaml"
        )
        run(
            "kubectl",
            "apply",
            "--namespace",
            "argocd",
            "--server-side",
            "--force-conflicts",
            "--filename",
            install_url,
        )
        run(
            "kubectl",
            "wait",
            "--namespace",
            "argocd",
            "--for=condition=Available",
            "deployment",
            "--all",
            "--timeout=300s",
        )
        run(
            "kubectl",
            "rollout",
            "status",
            "--namespace",
            "argocd",
            "statefulset/argocd-application-controller",
            "--timeout=300s",
        )

        print("Registrando la aplicación GitOps...")
        template_path = REPOSITORY_ROOT / "gitops" / "argocd" / "application.yaml"
        application_yaml = template_path.read_text(encoding="utf-8").replace(
            "__REPO_URL__", repo_url
        )
        run("kubectl", "apply", "--filename=-", input_text=application_yaml)

        print("\nBootstrap terminado.")
        print(f"Repositorio observado: {repo_url}")
        print("Rama observada: gitops")
        print("\nEstado:")
        print("  kubectl get applications --namespace argocd")
        print("  kubectl get pods --namespace argocd")
        print("\nInterfaz local:")
        print(
            "  kubectl port-forward --namespace argocd service/argocd-server 8080:443"
        )
        return 0
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
