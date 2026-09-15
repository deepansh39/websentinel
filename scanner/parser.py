import json
import os


def normalize_severity(riskcode):
    mapping = {
        "3": "Critical",
        "2": "High",
        "1": "Medium",
        "0": "Informational",
    }

    return mapping.get(
        str(riskcode),
        "Informational",
    )


def parse_zap_report(json_report_path):
    if not json_report_path:
        return []

    if not os.path.isfile(json_report_path):
        return []

    with open(
        json_report_path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    findings = []

    for site in data.get("site", []):

        site_name = site.get(
            "@name",
            "",
        )

        alerts = site.get(
            "alerts",
            [],
        )

        for alert in alerts:

            alert_name = alert.get(
                "alert",
                "Unnamed finding",
            )

            riskcode = alert.get(
                "riskcode",
                "0",
            )

            severity = normalize_severity(
                riskcode
            )

            confidence = alert.get(
                "confidence",
                "Unknown",
            )

            plugin_id = alert.get(
                "pluginid",
                "",
            )

            cwe_id = alert.get(
                "cweid",
                "",
            )

            instances = alert.get(
                "instances",
                [],
            )

            if not instances:
                instances = [{}]

            for instance in instances:

                findings.append(
                    {
                        "id": plugin_id,

                        "name": alert_name,

                        "severity": severity,

                        "confidence": confidence,

                        "url": instance.get(
                            "uri",
                            site_name,
                        ),

                        "parameter": instance.get(
                            "param",
                            "",
                        ),

                        "evidence": instance.get(
                            "evidence",
                            "",
                        ),

                        "cwe": cwe_id,

                        "owasp_category": "",
                    }
                )

    return findings