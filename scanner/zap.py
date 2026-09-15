import os
import shutil
import subprocess
from urllib.parse import urlparse


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

REPORTS_DIR = os.path.join(
    BASE_DIR,
    "reports",
)

ZAP_IMAGE = "ghcr.io/zaproxy/zaproxy:stable"


def validate_target(target):
    target = target.strip()

    parsed = urlparse(target)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            "Target must start with http:// or https://"
        )

    if not parsed.netloc:
        raise ValueError(
            "Invalid target URL"
        )

    return target


def get_docker_path():
    docker_path = shutil.which("docker")

    if docker_path:
        return docker_path

    fallback = os.path.expanduser(
        "~/.docker/bin/docker"
    )

    if os.path.exists(fallback):
        return fallback

    raise RuntimeError(
        "Docker CLI was not found."
    )


def run_zap_scan(target):
    target = validate_target(target)

    docker_path = get_docker_path()

    os.makedirs(
        REPORTS_DIR,
        exist_ok=True,
    )

    target_name = (
        urlparse(target)
        .netloc
        .replace(":", "_")
        .replace("/", "_")
    )

    json_report = (
        f"{target_name}_findings.json"
    )

    html_report = (
        f"{target_name}_report.html"
    )

    json_host_path = os.path.join(
        REPORTS_DIR,
        json_report,
    )

    html_host_path = os.path.join(
        REPORTS_DIR,
        html_report,
    )

    json_container_path = (
        f"/zap/wrk/{json_report}"
    )

    html_container_path = (
        f"/zap/wrk/{html_report}"
    )

    command = [
        docker_path,
        "run",
        "--rm",
        "-v",
        f"{REPORTS_DIR}:/zap/wrk/:rw",
        "-t",
        ZAP_IMAGE,
        "zap-full-scan.py",
        "-t",
        target,
        "-J",
        json_container_path,
        "-r",
        html_container_path,
        "-I",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    json_exists = os.path.isfile(
        json_host_path
    )

    html_exists = os.path.isfile(
        html_host_path
    )

    return {
        "return_code": result.returncode,

        "stdout": result.stdout,

        "stderr": result.stderr,

        "json_report": json_host_path,

        "html_report": html_host_path,

        "json_exists": json_exists,

        "html_exists": html_exists,

        "target": target,

        "command": command,
    }