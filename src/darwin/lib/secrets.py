"""Optional GCP Secret Manager fallback for Darwin secrets.

If DARWIN_GCP_SECRET_PROJECT is set, attempts to resolve secrets via
`gcloud secrets versions access latest`. Otherwise returns None so
callers can raise a clear error about the missing env var.
"""

from __future__ import annotations

import logging
import os
import subprocess

log = logging.getLogger(__name__)


def resolve_gcp_secret(secret_name: str) -> str | None:
    project = os.environ.get("DARWIN_GCP_SECRET_PROJECT")
    if not project:
        return None
    try:
        result = subprocess.run(
            [
                "gcloud",
                "secrets",
                "versions",
                "access",
                "latest",
                f"--secret={secret_name}",
                f"--project={project}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        log.warning("could not resolve secret %s from gcloud: %s", secret_name, exc)
        return None
