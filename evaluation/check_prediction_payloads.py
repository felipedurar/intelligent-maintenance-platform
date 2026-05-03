from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def post_json(api_base_url: str, payload: dict) -> tuple[int, dict]:
    request = Request(
        f"{api_base_url.rstrip('/')}/api/v1/predictions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


def validate_prediction(name: str, response: dict, expectation: dict) -> None:
    probability = response["failure_probability"]
    risk_class = response["risk_class"]

    expected_risk_class = expectation.get("expected_risk_class")
    if expected_risk_class and risk_class != expected_risk_class:
        raise AssertionError(f"{name}: expected risk class {expected_risk_class}, got {risk_class}")

    accepted_risk_classes = expectation.get("accepted_risk_classes")
    if accepted_risk_classes and risk_class not in accepted_risk_classes:
        raise AssertionError(f"{name}: expected one of {accepted_risk_classes}, got {risk_class}")

    min_probability = expectation.get("min_failure_probability")
    if min_probability is not None and probability < min_probability:
        raise AssertionError(f"{name}: expected probability >= {min_probability}, got {probability}")

    max_probability = expectation.get("max_failure_probability")
    if max_probability is not None and probability > max_probability:
        raise AssertionError(f"{name}: expected probability <= {max_probability}, got {probability}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live prediction smoke checks.")
    parser.add_argument("--api-base-url", default="http://localhost:8080")
    parser.add_argument("--payload-dir", default="evaluation/prediction_payloads")
    parser.add_argument("--expectations", default="evaluation/expected_prediction_bands.json")
    args = parser.parse_args()

    payload_dir = Path(args.payload_dir)
    expectations = json.loads(Path(args.expectations).read_text(encoding="utf-8"))

    for name, expectation in expectations.items():
        payload = json.loads((payload_dir / f"{name}.json").read_text(encoding="utf-8"))
        status_code, response = post_json(args.api_base_url, payload)
        if status_code != 200:
            raise AssertionError(f"{name}: expected HTTP 200, got {status_code}: {response}")
        validate_prediction(name, response, expectation)
        print(
            f"{name}: probability={response['failure_probability']:.4f} "
            f"risk_class={response['risk_class']} model_version={response['model_version']}"
        )

    invalid_payload = json.loads((payload_dir / "invalid_payload.json").read_text(encoding="utf-8"))
    invalid_status, _ = post_json(args.api_base_url, invalid_payload)
    if invalid_status < 400:
        raise AssertionError(f"invalid_payload: expected 4xx status, got {invalid_status}")
    print(f"invalid_payload: returned HTTP {invalid_status} as expected")


if __name__ == "__main__":
    main()
