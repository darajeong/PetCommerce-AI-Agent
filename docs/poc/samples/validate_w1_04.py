"""W1-04 합성 Mock JSON의 구조와 내부 참조를 검증합니다.

프로젝트 루트에서 실행:
    python docs/poc/samples/validate_w1_04.py

의도적 오류 주입 검사:
    python docs/poc/samples/validate_w1_04.py --self-test

외부 라이브러리가 필요하지 않습니다. 실제 API/Agent 실행이나 내용의 진실성은 검증하지 않습니다.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

SAMPLE_PATH = Path(__file__).resolve().parent / "W1-04_SAMPLE_PRODUCT.json"
RUN_STATUSES = {
    "pending", "running", "success", "partial_success", "failed",
    "needs_review", "approval_pending", "approved", "rejected", "on_hold",
}
APPROVAL_STATUSES = {"not_requested", "approval_pending", "approved", "rejected"}
DATA_TYPES = {"actual", "test", "mock"}
MISSING_REASONS = {
    "source_missing", "login_required", "access_restricted",
    "collection_failed", "manual_review_required",
}
REQUIRED_ENVELOPE = {
    "run_id", "product_id", "agent_id", "input_version", "result_version",
    "status", "result", "evidence_ids", "warnings", "errors", "retry_count",
    "started_at", "ended_at", "data_type",
}
# 점(.)으로 구분한 키와 선택적 배열 인덱스([0])를 찾는 경로 문법.
SEGMENT_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?$")


def require(condition: bool, message: str) -> None:
    """python -O 환경에서도 검사가 건너뛰어지지 않도록 assert 대신 사용합니다."""
    if not condition:
        raise ValueError(message)


def positive_version(value: object, label: str) -> None:
    require(type(value) is int and value >= 1, f"{label}: 1 이상의 정수여야 합니다")


def read_path(root: object, path: str) -> object:
    """예: product.reviews[0].rating → 실제 JSON 데이터의 값."""
    require(isinstance(path, str) and bool(path), "경로가 비어 있습니다")
    current = root
    for segment in path.split("."):
        match = SEGMENT_PATTERN.fullmatch(segment)
        require(match is not None, f"잘못된 경로 문법: {path}")
        key, index = match.groups()
        require(isinstance(current, dict) and key in current, f"존재하지 않는 경로: {path}")
        current = current[key]
        if index is not None:
            require(isinstance(current, list), f"배열이 아닌 경로: {path}")
            number = int(index)
            require(number < len(current), f"배열 범위를 벗어난 경로: {path}")
            current = current[number]
    return current


def check_claim_evidence(
    result: object, path: str, valid_ids: set[str], target_paths: dict[str, str],
    envelope_ids: set[str],
) -> None:
    """중요 주장(claim) 또는 근거가 명시된 객체에 유효한 근거가 있는지 검사."""
    if isinstance(result, list):
        for i, item in enumerate(result):
            check_claim_evidence(item, f"{path}[{i}]", valid_ids, target_paths, envelope_ids)
        return
    if not isinstance(result, dict):
        return

    # 자유 텍스트를 전부 의미 분석할 수는 없으므로 명시적으로 'claim'으로 표현된 주장과
    # B04의 size_info처럼 구조화된 핵심 판단을 검사한다.
    needs_evidence = "claim" in result or path.endswith(".size_info")
    if needs_evidence:
        require(bool(result.get("claim", "value")), f"{path}: 주장이 비어 있습니다")
        ids = result.get("evidence_ids")
        require(isinstance(ids, list) and len(ids) > 0, f"{path}: 중요 주장에 근거가 없습니다")
        for evidence_id in ids:
            require(isinstance(evidence_id, str) and evidence_id in valid_ids,
                    f"{path}: 잘못된 근거 ID {evidence_id}")
            require(evidence_id in envelope_ids, f"{path}: Agent envelope에 근거 ID 누락: {evidence_id}")
            require(target_paths[evidence_id] == path,
                    f"{path}: 근거 {evidence_id}의 target_path 불일치")
    elif "evidence_ids" in result:
        ids = result["evidence_ids"]
        require(isinstance(ids, list), f"{path}.evidence_ids: 배열이어야 합니다")
        for evidence_id in ids:
            require(evidence_id in valid_ids and evidence_id in envelope_ids,
                    f"{path}: 근거 ID가 존재하지 않거나 envelope에 없습니다: {evidence_id}")

    for key, value in result.items():
        if key != "evidence_ids":
            check_claim_evidence(value, f"{path}.{key}", valid_ids, target_paths, envelope_ids)


def validate(sample: dict) -> None:
    require(isinstance(sample, dict), "샘플 최상위는 object여야 합니다")
    require(sample.get("schema_version") == "0.1", "schema_version은 0.1이어야 합니다")
    require(bool(sample.get("product_id")), "product_id 누락")
    require(bool(sample.get("category_id")), "category_id 누락")
    run = sample["run"]
    require(bool(run.get("run_id")), "run_id 누락")
    require(run.get("status") in RUN_STATUSES, "run.status: 정의되지 않은 실행 상태")
    positive_version(sample.get("input_version"), "input_version")
    positive_version(sample.get("source_version"), "source_version")

    product = sample["product"]
    require(product["collection_method"] in {"auto", "manual", "mock"}, "collection_method 오류")
    require(bool(product["source_url"]) and bool(product["platform"]), "상품 출처 누락")
    for name in ("original_name", "description", "sales_count", "rating", "shipping", "supplier"):
        require(name in product, f"product.{name}: 필수 키 누락")

    # A02 결과에서 B01·B02·B04가 별도의 필드명 변경 없이 직접 읽을 수 있어야 함.
    images, description = product["images"], product["description"]  # B01
    reviews = product["reviews"]  # B02 + B04
    require(isinstance(images, list) and bool(images), "B01: images가 비어 있거나 배열 아님")
    require(isinstance(description, str) and bool(description.strip()), "B01: description 누락")
    require(isinstance(reviews, list) and bool(reviews), "B02: reviews가 비어 있거나 배열 아님")
    for i, review in enumerate(reviews):
        require(isinstance(review["text"], str) and bool(review["text"].strip()),
                f"B02: reviews[{i}].text 오류")
        require("rating" in review, f"B02: reviews[{i}].rating 누락")
    for name in ("dimensions", "weight", "material", "reviews"):
        require(name in product, f"B04: product.{name} 키 누락")
    require(isinstance(product["dimensions"], dict), "B04: dimensions는 object여야 합니다")
    require(isinstance(product["weight"], dict), "B04: weight는 object여야 합니다")
    require(isinstance(product["material"], list), "B04: material은 배열이어야 합니다")

    for i, image in enumerate(images):
        require(image["data_type"] in DATA_TYPES, f"images[{i}].data_type 오류")
        require(image["rights_status"] in {"usable", "needs_review", "prohibited"},
                f"images[{i}].rights_status 오류")
    for i, review in enumerate(reviews):
        require(review["data_type"] in DATA_TYPES, f"reviews[{i}].data_type 오류")

    # field_meta 및 missing_fields의 경로가 실제 데이터에 존재하는지 확인.
    field_meta = sample["field_meta"]
    require(isinstance(field_meta, dict), "field_meta는 object여야 합니다")
    for field_path, metadata in field_meta.items():
        read_path(sample, field_path)
        require(metadata["data_type"] in DATA_TYPES, f"field_meta.{field_path}: data_type 오류")
    missing_fields = sample["missing_fields"]
    require(isinstance(missing_fields, list), "missing_fields는 배열이어야 합니다")
    for entry in missing_fields:
        field_path = entry["field_path"]
        value = read_path(sample, field_path)
        require(value is None or value == [] or value == "",
                f"missing_fields.{field_path}: 값이 있는데 누락 처리되어 있습니다")
        require(entry["reason"] in MISSING_REASONS,
                f"missing_fields.{field_path}: 누락 사유 코드가 잘못되었습니다")
        require(isinstance(entry["next_action"], str) and bool(entry["next_action"].strip()),
                f"missing_fields.{field_path}: 다음 조치 누락")

    # 근거 ID, 근거 원본 ID, 근거 대상 경로 검사.
    evidence = sample["evidence"]
    require(isinstance(evidence, list), "evidence는 배열이어야 합니다")
    ids = [e["evidence_id"] for e in evidence]
    require(len(ids) == len(set(ids)), "evidence_id가 중복되었습니다")
    valid_ids = set(ids)
    target_paths = {e["evidence_id"]: e["target_path"] for e in evidence}
    image_ids = {image["image_id"] for image in images}
    review_ids = {review["review_id"] for review in reviews}
    for e in evidence:
        read_path(sample, e["target_path"])
        source_type, source_id = e["source_type"], e["source_id"]
        if source_type == "image":
            require(source_id in image_ids, f"근거 {e['evidence_id']}: 이미지 ID 없음")
        elif source_type == "review":
            require(source_id in review_ids, f"근거 {e['evidence_id']}: 리뷰 ID 없음")
        elif source_type == "description":
            require(source_id == product["description_id"], "설명문 근거 ID 불일치")
        elif source_type == "product_field":
            require(source_id.startswith("product."), "상품 필드 근거의 경로 오류")
            read_path(sample, source_id)
        else:
            raise ValueError(f"알 수 없는 근거 유형: {source_type}")

    outputs = sample["agent_outputs"]
    require(isinstance(outputs, dict) and bool(outputs), "agent_outputs가 비어 있습니다")
    for agent_id, output in outputs.items():
        require(isinstance(output, dict), f"{agent_id}: 결과 envelope가 object가 아닙니다")
        require(REQUIRED_ENVELOPE <= set(output), f"{agent_id}: 공통 출력 필드 누락")
        require(output["agent_id"] == agent_id, f"{agent_id}: agent_id 불일치")
        require(output["run_id"] == run["run_id"], f"{agent_id}: run_id 불일치")
        require(output["product_id"] == sample["product_id"], f"{agent_id}: product_id 불일치")
        positive_version(output["input_version"], f"{agent_id}.input_version")
        require(output["input_version"] == sample["input_version"], f"{agent_id}: input_version 불일치")
        positive_version(output["result_version"], f"{agent_id}.result_version")
        require(output["status"] in RUN_STATUSES, f"{agent_id}.status: 정의되지 않은 상태")
        require(isinstance(output["result"], dict), f"{agent_id}.result: object여야 합니다")
        if output["status"] != "failed":
            require(bool(output["result"]), f"{agent_id}.result: 실패가 아닌데 비어 있습니다")
        require(output["data_type"] in DATA_TYPES, f"{agent_id}.data_type 오류")
        require(type(output["retry_count"]) is int and 0 <= output["retry_count"] <= 2,
                f"{agent_id}.retry_count: 0~2여야 합니다")
        for name in ("warnings", "errors", "evidence_ids"):
            require(isinstance(output[name], list), f"{agent_id}.{name}: 배열이어야 합니다")
        require(all(id_ in valid_ids for id_ in output["evidence_ids"]),
                f"{agent_id}: 근거 ID 참조 오류")
        for error in output["errors"]:
            required = {"agent_id", "stage", "error_type", "cause", "auto_retryable",
                        "retry_count", "manual_fallback_possible", "mock_fallback_possible", "next_action"}
            require(isinstance(error, dict) and required <= set(error),
                    f"{agent_id}.errors: 필수 오류 필드 누락")
        check_claim_evidence(output["result"], f"agent_outputs.{agent_id}.result",
                             valid_ids, target_paths, set(output["evidence_ids"]))

    # 필수 결과의 핵심 필드 검사: 빈 결과 혹은 근거 없는 B04 판정을 방지.
    for agent_id in ("A02", "B01", "B02", "B04"):
        require(agent_id in outputs, f"필수 샘플 Agent 누락: {agent_id}")
    require(bool(outputs["B01"]["result"].get("features")), "B01: features 누락")
    require(bool(outputs["B02"]["result"].get("positive_points")), "B02: positive_points 누락")
    b04 = outputs["B04"]["result"]
    require(isinstance(b04.get("size_info"), dict), "B04: size_info 누락")
    require(bool(b04.get("suitability")), "B04: suitability 누락")
    require(bool(b04.get("reason")), "B04: reason 누락")
    if b04["suitability"] == "needs_review":
        require(any(entry["field_path"] == "product.recommended_pet_weight_max"
                    for entry in missing_fields), "B04: 정보 부족 판정의 누락 근거가 없습니다")

    approval = sample["approval"]
    require(approval["status"] in APPROVAL_STATUSES, "approval.status: 정의되지 않은 승인 상태")
    if approval["status"] == "approved":
        require(bool(approval.get("approver")) and bool(approval.get("approved_at")),
                "승인 완료에 approver/approved_at이 필요합니다")
        target = approval.get("target_version")
        require(isinstance(target, str) and ":" in target, "승인 대상 버전 형식 오류")
        approved_agent, approved_version = target.split(":", 1)
        require(approved_agent in outputs and approved_version == str(outputs[approved_agent]["result_version"]),
                "현재 결과 버전과 승인 대상 버전이 일치하지 않습니다")


def run_self_tests(sample: dict) -> int:
    """정상 통과에 더해 의도적인 잘못된 입력이 실제로 거부되는지 확인한다."""
    cases = {
        "B04 빈 결과": lambda s: s["agent_outputs"]["B04"].__setitem__("result", {}),
        "result_version = 0": lambda s: s["agent_outputs"]["B01"].__setitem__("result_version", 0),
        "정의 밖 Agent 상태": lambda s: s["agent_outputs"]["B01"].__setitem__("status", "unknown"),
        "정의 밖 실행 상태": lambda s: s["run"].__setitem__("status", "unknown"),
        "없는 누락 필드 경로": lambda s: s["missing_fields"].append(
            {"field_path": "product.fake_field", "reason": "source_missing", "next_action": "확인"}),
        "근거 없는 B01 주장": lambda s: s["agent_outputs"]["B01"]["result"]["features"][0].__setitem__("evidence_ids", []),
        "근거 없는 B04 중요 정보": lambda s: s["agent_outputs"]["B04"]["result"]["size_info"].pop("evidence_ids"),
        "근거 타깃 불일치": lambda s: s["evidence"][0].__setitem__("target_path", "agent_outputs.B02.result.review_count"),
        "정의 밖 승인 상태": lambda s: s["approval"].__setitem__("status", "running"),
        "B01 입력 description 삭제": lambda s: s["product"].pop("description"),
        "Agent run_id 불일치": lambda s: s["agent_outputs"]["B01"].__setitem__("run_id", "wrong-run"),
        "정의 밖 누락 사유": lambda s: s["missing_fields"][0].__setitem__("reason", "other"),
        "없는 evidence_id 참조": lambda s: s["agent_outputs"]["B01"].__setitem__("evidence_ids", ["ev-not-found"]),
        "없는 이미지 원본 ID": lambda s: s["evidence"][0].update(source_type="image", source_id="img-missing"),
    }
    count = 0
    for label, mutation in cases.items():
        broken = copy.deepcopy(sample)
        mutation(broken)
        try:
            validate(broken)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            print(f"PASS(오류 검출): {label} → {exc}")
            count += 1
        else:
            raise ValueError(f"FAIL(오류 미검출): {label}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="W1-04 합성 Mock 계약 검사")
    parser.add_argument("--self-test", action="store_true", help="고의 오류 주입 검증까지 실행")
    parser.add_argument("--sample", type=Path, default=SAMPLE_PATH, help="검증할 JSON 경로")
    args = parser.parse_args()
    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    validate(sample)
    print("PASS: W1-04 샘플 JSON 구조 / A02→B01·B02·B04 필드 직접 읽기 / 근거·상태·버전 검증")
    if args.self_test:
        count = run_self_tests(sample)
        print(f"PASS: 의도적 오류 {count}종 모두 검출")
    print("주의: 합성 Mock 데이터의 계약 검증이며 실제 Agent·API 실행이나 분석 내용의 진실성 검증은 아닙니다.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, IndexError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
