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
PARTIAL_SAMPLE_PATH = Path(__file__).resolve().parent / "W1-04_SAMPLE_PRODUCT_PARTIAL.json"
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


# 값이 비어 있어도 되는 키(정책 URL·확인일은 '아직 확인 전'을 뜻하므로 누락 사유 대상이 아님)
IGNORE_EMPTY_KEYS = {"usage_policy_url", "usage_checked_at"}
# 입력이 통째로 없을 때 Agent가 가질 수 있는 상태(성공으로 확정하지 않는다)
NOT_SUCCESS_STATUSES = {"partial_success", "needs_review", "on_hold", "failed"}


def collect_empty_paths(node: object, path: str) -> list:
    """null·빈 문자열·빈 배열·빈 객체인 JSON 경로를 모은다."""
    if isinstance(node, dict):
        if not node:
            return [path]
        found = []
        for key, value in node.items():
            if key in IGNORE_EMPTY_KEYS:
                continue
            found += collect_empty_paths(value, f"{path}.{key}")
        return found
    if isinstance(node, list):
        if not node:
            return [path]
        found = []
        for index, value in enumerate(node):
            found += collect_empty_paths(value, f"{path}[{index}]")
        return found
    return [path] if node is None or node == "" else []


def is_covered(path: str, missing_paths: set) -> bool:
    """빈 값의 경로가 missing_fields의 같은 경로 또는 상위 경로로 기록돼 있는지."""
    return any(path == m or path.startswith(m + ".") or path.startswith(m + "[")
               for m in missing_paths)


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
    # 계약: 키는 항상 있어야 하고(필수 키), 값은 null·[]일 수 있다.
    # 값이 비어 있으면 아래 '누락 사유 검사'에서 missing_fields 기록을 요구한다.
    require(isinstance(images, list), "B01: images는 배열이어야 합니다(비어 있으면 missing_fields에 기록)")
    require(description is None or isinstance(description, str),
            "B01: description은 문자열 또는 null이어야 합니다")
    require(isinstance(reviews, list), "B02: reviews는 배열이어야 합니다(비어 있으면 missing_fields에 기록)")
    for i, review in enumerate(reviews):
        require(isinstance(review["text"], (str, type(None))), f"B02: reviews[{i}].text 타입 오류")
        require("rating" in review, f"B02: reviews[{i}].rating 키 누락")
    for name in ("dimensions", "weight", "material", "reviews"):
        require(name in product, f"B04: product.{name} 키 누락")
    require(product["dimensions"] is None or isinstance(product["dimensions"], dict),
            "B04: dimensions는 object 또는 null이어야 합니다")
    require(product["weight"] is None or isinstance(product["weight"], dict),
            "B04: weight는 object 또는 null이어야 합니다")
    require(product["material"] is None or isinstance(product["material"], list),
            "B04: material은 배열 또는 null이어야 합니다")

    for kind, items in (("images", images), ("reviews", reviews)):
        for i, item in enumerate(items):
            label = f"{kind}[{i}]"
            require(item.get("data_type") in DATA_TYPES, f"{label}.data_type 오류")
            if kind == "images":
                require(item.get("image_role") in {"main", "detail", "other"},
                        f"{label}.image_role 오류")
            usage = item.get("usage")
            require(isinstance(usage, dict), f"{label}.usage: 객체 누락")
            require(set(usage) == {"store", "ai_input", "display", "resale"},
                    f"{label}.usage: 필수 용도 네 키 필요")
            allowed_values = {"allowed", "prohibited", "needs_review"}
            require(all(v in allowed_values for v in usage.values()),
                    f"{label}.usage: 허용되지 않은 상태값")
            rights = ("prohibited" if "prohibited" in usage.values() else
                      "usable" if all(v == "allowed" for v in usage.values()) else
                      "needs_review")
            require(item.get("rights_status") == rights,
                    f"{label}.rights_status: 용도별 사용 판정과 불일치")
            require("usage_policy_url" in item and "usage_checked_at" in item,
                    f"{label}: 정책 URL·확인일 필수 키 누락")
            policy_url = item["usage_policy_url"]
            checked_at = item["usage_checked_at"]
            require(policy_url is None or
                    (isinstance(policy_url, str) and policy_url.startswith(("https://", "http://"))),
                    f"{label}.usage_policy_url 오류")
            require(checked_at is None or isinstance(checked_at, str) and bool(checked_at.strip()),
                    f"{label}.usage_checked_at 오류")
            if any(v == "allowed" for v in usage.values()):
                require(bool(policy_url) and bool(checked_at),
                        f"{label}: allowed에 정책 근거 URL·확인일 필요")
            if rights == "usable":
                require(bool(policy_url) and bool(checked_at),
                        f"{label}: 권리 사용 가능 판정에 근거 필요")

    # 문서 3장의 B01·B02·B04 번역·정규화 입력 경로를 실제 데이터로 검증.
    nd = sample.get("normalized_data")
    require(isinstance(nd, dict), "normalized_data 객체 누락")
    if description is None or description == "":
        require(nd.get("translated_description") is None,
                "B01: 원본 description이 비어 있는데 번역문이 있습니다(null이어야 합니다)")
    else:
        require(isinstance(nd.get("translated_description"), str) and
                bool(nd["translated_description"].strip()),
                "B01: normalized_data.translated_description 누락")
    tr = nd.get("translated_reviews")
    require(isinstance(tr, list), "B02: normalized_data.translated_reviews 배열 누락")
    original_review_ids = {r["review_id"] for r in reviews}
    translated_review_ids = {r.get("review_id") for r in tr if isinstance(r, dict)}
    require(len(translated_review_ids) == len(tr) and translated_review_ids == original_review_ids,
            "B02: 번역 리뷰 ID와 원본 리뷰 ID 불일치")
    for i, r in enumerate(tr):
        require(isinstance(r.get("translated_text"), str) and bool(r["translated_text"].strip()),
                f"B02: translated_reviews[{i}].translated_text 오류")
    dims = nd.get("normalized_dimensions")
    weight = nd.get("normalized_weight")
    if product["dimensions"] is None:
        require(dims is None, "B04: 원본 dimensions가 null이면 normalized_dimensions도 null이어야 합니다")
    else:
        require(isinstance(dims, dict) and dims.get("unit") == "cm" and
                all(k in dims and (dims[k] is None or type(dims[k]) in (int, float))
                    for k in ("length", "width", "height")),
                "B04: normalized_data.normalized_dimensions 오류")
    if product["weight"] is None:
        require(weight is None, "B04: 원본 weight가 null이면 normalized_weight도 null이어야 합니다")
    else:
        require(isinstance(weight, dict) and weight.get("unit") == "kg" and
                "value" in weight and (weight["value"] is None or type(weight["value"]) in (int, float)),
                "B04: normalized_data.normalized_weight 오류")
    by_field = {entry.get("field_path"): entry for entry in nd.get("conversions", [])}
    pairs = []
    if dims is not None:
        pairs += [("product.dimensions.length", dims["length"], "cm"),
                  ("product.dimensions.width", dims["width"], "cm"),
                  ("product.dimensions.height", dims["height"], "cm")]
    if weight is not None:
        pairs.append(("product.weight.value", weight["value"], "kg"))
    for src, dst_value, dst_unit in pairs:
        src_value = read_path(sample, src)
        if src_value is None:
            require(dst_value is None, f"B04: {src}가 null인데 정규화 값이 있습니다(값을 만들어 내면 안 됩니다)")
            continue
        if dst_value is None:
            continue
        entry = by_field.get(src)
        require(isinstance(entry, dict) and entry.get("normalized_value") == dst_value
                and entry.get("normalized_unit") == dst_unit
                and entry.get("original_value") == src_value,
                f"B04: conversions[{src}] 원본·정규화 연결 누락 또는 값 불일치")



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

    # 누락 사유 검사: product 안의 빈 값(null·""·[]·{})은 모두 missing_fields에 기록돼 있어야 한다.
    missing_paths = {entry["field_path"] for entry in missing_fields}
    for empty_path in collect_empty_paths(product, "product"):
        require(is_covered(empty_path, missing_paths),
                f"누락 사유 없는 빈 값: {empty_path} (missing_fields에 기록해야 합니다)")

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
    blocked = {
        "B01": [p for p, empty in (("product.images", not images),
                                   ("product.description", not description)) if empty],
        "B02": [p for p, empty in (("product.reviews", not reviews),) if empty],
        "B04": [p for p, empty in (("product.dimensions", product["dimensions"] is None),
                                   ("product.weight", product["weight"] is None)) if empty],
    }
    for agent_id, missing_inputs in blocked.items():
        output = outputs[agent_id]
        if missing_inputs:
            # 입력이 없으면 추측으로 채우지 않고 성공이 아닌 상태와 사유를 남긴다.
            require(output["status"] in NOT_SUCCESS_STATUSES,
                    f"{agent_id}: 입력 누락({', '.join(missing_inputs)})인데 status가 "
                    f"{output['status']}입니다 (성공으로 확정할 수 없음)")
            reason = output["result"].get("reason")
            require(isinstance(reason, str) and bool(reason.strip()),
                    f"{agent_id}: 입력 누락 시 result.reason(사유)이 필요합니다")
    if not blocked["B01"]:
        require(bool(outputs["B01"]["result"].get("features")), "B01: features 누락")
    if not blocked["B02"]:
        require(bool(outputs["B02"]["result"].get("positive_points")), "B02: positive_points 누락")
    if not blocked["B04"]:
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
        "정규화 무게 경로 누락": lambda s: s["normalized_data"].pop("normalized_weight"),
        "권한 요약값 불일치": lambda s: s["product"]["images"][0].__setitem__("rights_status", "usable"),
        "정의 밖 용도별 권한값": lambda s: s["product"]["reviews"][0]["usage"].__setitem__("ai_input", "maybe"),
        "사용 권한 필수 키 누락": lambda s: s["product"]["images"][0]["usage"].pop("resale"),
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


def run_partial_tests(partial: dict, base: dict) -> int:
    """부분 수집 계약 검사: 누락 사유가 기록된 빈 값은 허용하고, 사유 없는 빈 값·성공 확정은 거부한다.

    음성 테스트는 '거부되었는가'뿐 아니라 '의도한 이유로 거부되었는가'(메시지 포함 여부)도 확인한다.
    """
    def drop_missing(path):
        def mutate(s):
            s["missing_fields"][:] = [m for m in s["missing_fields"] if m["field_path"] != path]
        return mutate

    def set_status(agent, status):
        return lambda s: s["agent_outputs"][agent].__setitem__("status", status)

    # (설명, 기준 샘플, 변형, 거부 메시지에 포함돼야 하는 문구)
    negatives = [
        ("누락 사유 없는 빈 이미지", partial, drop_missing("product.images"), "누락 사유 없는 빈 값: product.images"),
        ("누락 사유 없는 빈 리뷰", partial, drop_missing("product.reviews"), "누락 사유 없는 빈 값: product.reviews"),
        ("누락 사유 없는 null 크기", partial, drop_missing("product.dimensions"), "누락 사유 없는 빈 값: product.dimensions"),
        ("누락 사유 없는 null 무게", partial, drop_missing("product.weight"), "누락 사유 없는 빈 값: product.weight"),
        ("누락 사유 없는 null 평점(스칼라)", base,
         lambda s: s["product"].__setitem__("rating", None), "누락 사유 없는 빈 값: product.rating"),
        ("이미지 없는데 B01 성공", partial, set_status("B01", "success"), "B01: 입력 누락"),
        ("리뷰 없는데 B02 성공", partial, set_status("B02", "success"), "B02: 입력 누락"),
        ("크기·무게 없는데 B04 성공", partial, set_status("B04", "success"), "B04: 입력 누락"),
        ("입력 누락 Agent의 사유 비어 있음", partial,
         lambda s: s["agent_outputs"]["B02"]["result"].__setitem__("reason", ""), "result.reason"),
        ("원본 null인데 정규화 크기를 만들어 냄", partial,
         lambda s: s["normalized_data"].__setitem__(
             "normalized_dimensions", {"length": 1, "width": 1, "height": 1, "unit": "cm"}), "null이어야"),
        ("값이 있는데 누락으로 기록", partial,
         lambda s: s["missing_fields"].append(
             {"field_path": "product.description", "reason": "source_missing", "next_action": "확인"}),
         "값이 있는데 누락"),
        ("누락 사유 코드 오류", partial,
         lambda s: s["missing_fields"][-1].__setitem__("reason", "unknown"), "누락 사유 코드"),
    ]
    count = 0
    for label, origin, mutation, expected in negatives:
        broken = copy.deepcopy(origin)
        mutation(broken)
        try:
            validate(broken)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            if expected not in str(exc):
                raise ValueError(f"FAIL(다른 이유로 거부): {label} → {exc}") from exc
            print(f"PASS(부분 수집 오류 검출): {label} → {exc}")
            count += 1
        else:
            raise ValueError(f"FAIL(오류 미검출): {label}")

    # 허용되어야 하는 경우: 누락 사유가 기록된 빈 값
    allowed = copy.deepcopy(base)
    allowed["product"]["rating"] = None
    allowed["missing_fields"].append(
        {"field_path": "product.rating", "reason": "source_missing", "next_action": "평점 수동 확인"})
    validate(allowed)
    print("PASS(허용 확인): 누락 사유가 기록된 null 평점은 통과")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="W1-04 합성 Mock 계약 검사")
    parser.add_argument("--self-test", action="store_true", help="고의 오류 주입 검증까지 실행")
    parser.add_argument("--sample", type=Path, default=SAMPLE_PATH, help="검증할 JSON 경로")
    args = parser.parse_args()
    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    validate(sample)
    print("PASS: W1-04 샘플 구조 / A03 번역·정규화 경로 / 이미지·리뷰 사용 권한 / 근거·상태·버전 검증")
    partial = None
    if args.sample == SAMPLE_PATH:
        partial = json.loads(PARTIAL_SAMPLE_PATH.read_text(encoding="utf-8"))
        validate(partial)
        print("PASS: 부분 수집 샘플(누락 사유 기록, 이미지·리뷰·규격 누락) 구조·상태 검증")
    if args.self_test:
        count = run_self_tests(sample)
        print(f"PASS: 의도적 오류 {count}종 모두 검출")
        if partial is not None:
            partial_count = run_partial_tests(partial, sample)
            print(f"PASS: 부분 수집 계약 오류 {partial_count}종 모두 검출 (총 {count + partial_count}종)")
    print("주의: 합성 Mock 데이터의 계약 검증이며 실제 Agent·API 실행이나 분석 내용의 진실성 검증은 아닙니다.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, IndexError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
