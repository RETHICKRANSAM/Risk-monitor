import csv
import json
import random
from datetime import datetime, timedelta


def convert_csv_to_json():
    input_file = "data/Test_data.csv"
    output_file = "data/test_data.json"

    findings = []
    now = datetime.now()

    with open(input_file) as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            try:
                wrong_fragment = float(row.get("wrong_fragment", 0))
                num_failed_logins = float(row.get("num_failed_logins", 0))
                num_compromised = float(row.get("num_compromised", 0))

                serror_rate = float(row.get("serror_rate", 0))
                dst_host_srv_serror_rate = float(row.get("dst_host_srv_serror_rate", 0))
                dst_host_rerror_rate = float(row.get("dst_host_rerror_rate", 0))

            except ValueError:
                wrong_fragment = 0
                num_failed_logins = 0
                num_compromised = 0
                serror_rate = 0
                dst_host_srv_serror_rate = 0
                dst_host_rerror_rate = 0

            if wrong_fragment > 0 or num_failed_logins > 0 or num_compromised > 0:
                severity = "Critical"
            elif serror_rate > 0.5 or dst_host_srv_serror_rate > 0.5:
                severity = "High"
            elif dst_host_rerror_rate > 0.5:
                severity = "Medium"
            elif row.get("flag") != "SF":
                severity = "Low"
            else:
                severity = "Info"

            protocol = row.get("protocol_type", "unknown")
            service = row.get("service", "unknown")
            flag = row.get("flag", "none")

            days_ago = random.randint(0, 30)
            reported_date = (now - timedelta(days=days_ago)).strftime("%b %d, %Y")

            finding = {
                "id": i + 1,
                "name": f"{protocol.upper()} / {service} / {flag}",
                "vendor": "Network Sensor",
                "vendor_initial": "N",
                "vendor_colors": ["#3b82f6", "#2563eb"],
                "reported": reported_date,
                "severity": severity,
            }

            findings.append(finding)

    with open(output_file, "w") as f:
        json.dump(findings, f, indent=2)

    print(f"Converted {len(findings)} rows to {output_file}")


def create_endpoints_json():
    input_file = "data/Test_data.csv"
    output_file = "data/endpoints.json"

    endpoints = []

    with open(input_file) as f:
        reader = csv.DictReader(f)

        for i, row in enumerate(reader):
            risk = int(
                float(row.get("serror_rate", 0)) * 50
                + float(row.get("dst_host_srv_serror_rate", 0)) * 50,
            )

            if risk >= 80:
                status = "Critical"
            elif risk >= 50:
                status = "Warning"
            else:
                status = "Healthy"

            endpoint = {
                "id": i + 1,
                "hostname": f"HOST-{i + 1:05d}",
                "ip": f"10.10.{(i % 250) + 1}.{(i * 3 % 250) + 1}",
                "os": random.choice(
                    [
                        "Windows 11",
                        "Windows 10",
                        "Ubuntu 24.04",
                        "Windows Server 2022",
                    ]
                ),
                "status": status,
                "risk_score": risk,
                "last_seen": (datetime.now() - timedelta(minutes=i)).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            }

            endpoints.append(endpoint)

    with open(output_file, "w") as f:
        json.dump(endpoints, f, indent=2)

    print(f"Created {len(endpoints)} endpoints in {output_file}")


if __name__ == "__main__":
    convert_csv_to_json()
    create_endpoints_json()
