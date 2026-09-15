import threading
import time
import uuid
from datetime import datetime, timezone

from database import (
    create_scan_record,
    update_scan_record,
)

from scanner.parser import parse_zap_report
from scanner.zap import run_zap_scan


scan_jobs = {}


def create_scan(target):
    scan_id = str(uuid.uuid4())

    scan_jobs[scan_id] = {
        "id": scan_id,
        "target": target,
        "status": "QUEUED",
        "stage": "Waiting to start",
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "findings": [],
        "error": None,
    }

    create_scan_record(
        scan_id=scan_id,
        target=target,
        status="QUEUED",
        stage="Waiting to start",
        progress=0,
    )

    thread = threading.Thread(
        target=_run_scan,
        args=(scan_id,),
        daemon=True,
    )

    thread.start()

    return scan_id


def get_scan(scan_id):
    return scan_jobs.get(scan_id)


def _update(scan_id, **values):
    if scan_id not in scan_jobs:
        return

    scan_jobs[scan_id].update(values)

    database_values = {}

    allowed_values = {
        "status",
        "stage",
        "progress",
        "started_at",
        "finished_at",
        "error",
    }

    for key, value in values.items():
        if key in allowed_values:
            database_values[key] = value

    if database_values:
        update_scan_record(
            scan_id,
            **database_values,
        )


def _run_scan(scan_id):
    job = scan_jobs[scan_id]

    try:
        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        _update(
            scan_id,
            status="STARTING",
            stage="Starting scan engine",
            progress=5,
            started_at=started_at,
        )

        time.sleep(1)

        _update(
            scan_id,
            status="RUNNING",
            stage="Launching OWASP ZAP",
            progress=10,
        )

        result = run_zap_scan(
            job["target"]
        )

        _update(
            scan_id,
            status="COLLECTING",
            stage="Collecting scan reports",
            progress=90,
        )

        time.sleep(1)

        findings = parse_zap_report(
            result.get("json_report")
        )

        scan_jobs[scan_id]["result"] = result
        scan_jobs[scan_id]["findings"] = findings

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        _update(
            scan_id,
            status="COMPLETE",
            stage="Scan completed",
            progress=100,
            finished_at=finished_at,
        )

        update_scan_record(
            scan_id,
            json_report=result.get(
                "json_report"
            ),
            html_report=result.get(
                "html_report"
            ),
        )

    except Exception as exc:

        finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        _update(
            scan_id,
            status="FAILED",
            stage="Scan failed",
            progress=100,
            error=str(exc),
            finished_at=finished_at,
        )