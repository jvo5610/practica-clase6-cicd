"""Muestra la contraseña inicial de Argo CD de forma multiplataforma."""

from __future__ import annotations

import base64
import json
import subprocess
import sys


def main() -> int:
    try:
        result = subprocess.run(
            [
                "kubectl",
                "get",
                "secret",
                "argocd-initial-admin-secret",
                "--namespace",
                "argocd",
                "--output=json",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        secret = json.loads(result.stdout)
        encoded_password = secret["data"]["password"]
        password = base64.b64decode(encoded_password).decode("utf-8")
        print(password)
        return 0
    except (
        KeyError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"No se pudo obtener la contraseña: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
