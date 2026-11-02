
import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


sample_product = {
    "product_id": "mock-product-001",
    "product_name": "sample_pet_product",
    "data_type": "mock",
}


def validate_sample(product):
    required_fields = [
        "product_id",
        "product_name",
        "data_type",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not product.get(field)
    ]

    passed = not missing_fields

    return {
        "poc_id": "W1-08",
        "test_type": "environment_smoke_test",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "result": "pass" if passed else "fail",
        "judgement": "성공" if passed else "실패",
        "product_id": product.get("product_id"),
        "data_type": product.get("data_type"),
        "missing_fields": missing_fields,
    }


def main():
    parser = argparse.ArgumentParser(
        description="W1-08 공통 실행 환경 스모크 테스트"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="결과 JSON을 저장할 경로",
    )
    args = parser.parse_args()

    result = validate_sample(sample_product)

    result_text = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    )

    print(result_text)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            result_text + "\n",
            encoding="utf-8",
            newline="\n",
        )

    if result["result"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
