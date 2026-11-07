"""A03-02 정규화 PoC: W1-04 상품 JSON의 원본 값을 공통 단위로 변환한다.

    python docs/poc/samples/a03_normalize.py <입력.json> [--output <출력.json>]
        [--rate USD:KRW=1400 --rate-source "..."] [--at 2026-11-07T12:00:00+09:00]
    python docs/poc/samples/a03_normalize.py --self-test

- 원본 `product`는 바꾸지 않고 `normalized_data`와 `agent_outputs.A03`만 새로 쓴다.
- 번역(`translated_*`)은 A03-01 범위라 입력에 있으면 그대로 둔다.
- 변환 기준: 길이 cm, 무게 kg, 가격 KRW(환율을 인자로 받은 경우만).
- 변환할 수 없는 값은 추정하지 않고 `normalized_data.unconverted[]`와 A03 경고에 남긴다.
- `normalized_pet_weight_max`·`normalized_material`·`duplicates`·`unconverted`는
  W1-04 v0.2 제안(PR #1 코멘트) 필드이며 v0.2 확정 시 이름을 맞춘다.
- 외부 라이브러리·외부 API를 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

LENGTH_TO_CM = {"mm": 0.1, "cm": 1.0, "m": 100.0, "in": 2.54, "inch": 2.54}
WEIGHT_TO_KG = {"g": 0.001, "kg": 1.0, "lb": 0.45359237, "lbs": 0.45359237, "oz": 0.028349523125}
MATERIALS = {  # 팀 공통 소재 목록(제안) ← 원문 표기
    "nylon": ["nylon"],
    "polyester": ["polyester", "poly", "oxford", "oxford cloth"],
    "cotton": ["cotton"],
    "mesh": ["mesh", "air mesh"],
    "natural_rubber": ["natural rubber", "rubber"],
    "silicone": ["silicone", "food grade silicone"],
    "eva": ["eva"],
    "tpr": ["tpr"],
    "plush": ["plush", "faux fur", "fleece"],
    "memory_foam": ["memory foam", "foam"],
}


def _round(v: float) -> float:
    return round(v, 4)


def normalize(doc: dict, rates: dict[str, float], rate_source: str | None, at: str) -> dict:
    out = copy.deepcopy(doc)
    p = out["product"]
    nd = out.setdefault("normalized_data", {})
    conversions, unconverted, warnings = [], [], []

    def conv(path, ov, ou, nv, nu, rate, src, data_type):
        conversions.append({"field_path": path, "original_value": ov, "original_unit": ou,
                            "normalized_value": nv, "normalized_unit": nu, "conversion_rate": rate,
                            "rate_source": src, "converted_at": at, "data_type": data_type})

    def skip(path, value, reason):
        unconverted.append({"field_path": path, "original_value": value, "reason": reason})

    dt = doc.get("field_meta", {}).get("product.original_price.amount", {}).get("data_type", "test")

    # 가격
    price = p.get("original_price") or {}
    amount, cur = price.get("amount"), (price.get("currency") or "").upper()
    if amount is not None:
        if cur == "KRW":
            conv("product.original_price.amount", amount, "KRW", amount, "KRW", 1, "동일 통화 보존", dt)
        elif f"{cur}:KRW" in rates:
            r = rates[f"{cur}:KRW"]
            conv("product.original_price.amount", amount, cur, round(amount * r), "KRW", r,
                 rate_source or "환율 출처 미기재", dt)
        else:
            skip("product.original_price.amount", amount,
                 f"{cur or '통화 미표기'}→KRW 환율이 입력되지 않음 (추정하지 않음)")

    # 크기
    dims = p.get("dimensions")
    norm_dims = {"length": None, "width": None, "height": None, "unit": "cm"}
    if isinstance(dims, dict):
        unit = (dims.get("unit") or "").lower()
        for k in ("length", "width", "height"):
            v = dims.get(k)
            if v is None:
                continue
            if unit in LENGTH_TO_CM:
                f = LENGTH_TO_CM[unit]
                norm_dims[k] = _round(v * f)
                conv(f"product.dimensions.{k}", v, unit, norm_dims[k], "cm", f,
                     "동일 단위 보존" if f == 1 else "길이 단위 변환", dt)
            else:
                skip(f"product.dimensions.{k}", v, f"알 수 없는 길이 단위: {unit or '미표기'}")
    nd["normalized_dimensions"] = norm_dims

    # 무게
    w = p.get("weight")
    norm_w = {"value": None, "unit": "kg"}
    if isinstance(w, dict) and w.get("value") is not None:
        unit = (w.get("unit") or "").lower()
        if unit in WEIGHT_TO_KG:
            f = WEIGHT_TO_KG[unit]
            norm_w["value"] = _round(w["value"] * f)
            conv("product.weight.value", w["value"], unit, norm_w["value"], "kg", f,
                 "동일 단위 보존" if f == 1 else "무게 단위 변환", dt)
        else:
            skip("product.weight.value", w["value"], f"알 수 없는 무게 단위: {unit or '미표기'}")
    nd["normalized_weight"] = norm_w

    # 권장 체중 (v0.1: number, v0.2 제안: {value, unit})
    pw = p.get("recommended_pet_weight_max")
    norm_pw = {"value": None, "unit": "kg"}
    if isinstance(pw, dict) and pw.get("value") is not None:
        unit = (pw.get("unit") or "").lower()
        if unit in WEIGHT_TO_KG:
            f = WEIGHT_TO_KG[unit]
            norm_pw["value"] = _round(pw["value"] * f)
            conv("product.recommended_pet_weight_max.value", pw["value"], unit, norm_pw["value"], "kg", f,
                 "동일 단위 보존" if f == 1 else "무게 단위 변환", dt)
        else:
            skip("product.recommended_pet_weight_max.value", pw["value"], f"알 수 없는 무게 단위: {unit or '미표기'}")
    elif isinstance(pw, (int, float)):
        skip("product.recommended_pet_weight_max", pw, "v0.1 숫자 필드라 단위를 알 수 없음 (kg로 추정하지 않음)")
    nd["normalized_pet_weight_max"] = norm_pw

    # 소재
    norm_mat = []
    for m in p.get("material") or []:
        key = m.strip().lower()
        hit = next((k for k, syns in MATERIALS.items() if key == k.replace("_", " ") or key in syns), None)
        if hit and key == hit.replace("_", " "):
            norm_mat.append({"original": m, "normalized": hit, "confidence": "high"})
        elif hit:
            norm_mat.append({"original": m, "normalized": hit, "confidence": "medium"})
        else:
            norm_mat.append({"original": m, "normalized": "other", "confidence": "low"})
    nd["normalized_material"] = norm_mat

    # 중복 (원본은 지우지 않고 표시만)
    dups = []
    seen: dict[str, list[str]] = {}
    for img in p.get("images") or []:
        seen.setdefault(img.get("url"), []).append(img["image_id"])
    dups += [{"type": "image_url", "ids": ids, "rule": "같은 이미지 URL"} for ids in seen.values() if len(ids) > 1]
    seen = {}
    for r in p.get("reviews") or []:
        seen.setdefault(" ".join((r.get("text") or "").split()).lower(), []).append(r["review_id"])
    dups += [{"type": "review_text", "ids": ids, "rule": "공백·대소문자 제외 동일 원문"} for t, ids in seen.items() if t and len(ids) > 1]
    nd["duplicates"] = dups

    nd["conversions"] = conversions
    nd["unconverted"] = unconverted
    if unconverted:
        warnings.append(f"변환하지 못한 값 {len(unconverted)}건: normalized_data.unconverted 참고")
    if any(c["normalized_unit"] == "KRW" and c["original_unit"] != "KRW" for c in conversions):
        warnings.append("가격 환산은 입력된 환율 기준이며 실제 가격 결정에는 별도 확인이 필요하다.")
    if dt != "actual":
        warnings.append(f"입력 데이터 구분: {dt}")

    run = out.get("run", {})
    out.setdefault("agent_outputs", {})["A03"] = {
        "run_id": run.get("run_id"), "product_id": out.get("product_id"), "agent_id": "A03",
        "input_version": out.get("input_version", 1),
        "result_version": out.get("agent_outputs", {}).get("A03", {}).get("result_version", 0) + 1,
        "status": "partial_success" if unconverted else "success",
        "result": {"normalized_data_ref": {"source_version": out.get("source_version", 1)},
                   "conversion_count": len(conversions), "unconverted_count": len(unconverted),
                   "duplicate_groups": len(dups)},
        "evidence_ids": [], "warnings": warnings, "errors": [], "retry_count": 0,
        "started_at": at, "ended_at": at, "data_type": dt,
    }
    return out


def self_test() -> int:
    """PR #10 테스트 상품 3건으로 기대값과 음성 사례를 확인한다."""
    here = Path(__file__).resolve().parent
    at = "2026-11-07T12:00:00+09:00"
    rates = {"USD:KRW": 1400.0}
    fails = 0

    def check(label, cond):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + label)
        fails += 0 if cond else 1

    for n in ("001", "002", "003"):
        src = here / f"W2-A02_TEST_PRODUCT_{n}.json"
        if not src.exists():
            print(f"SKIP {src.name} 없음 (PR #10 병합 전)")
            continue
        doc = json.loads(src.read_text(encoding="utf-8"))
        expect = doc["normalized_data"]
        res = normalize(doc, rates, "테스트용 고정 환율(실제 환율 아님)", at)
        nd = res["normalized_data"]
        check(f"{n} 원본 product 불변", res["product"] == doc["product"])
        check(f"{n} 번역 보존", nd["translated_reviews"] == expect["translated_reviews"])
        want = {k: (v if v is None or k == "unit" else _round(v)) for k, v in expect["normalized_dimensions"].items()}
        check(f"{n} 크기 일치", nd["normalized_dimensions"] == want)
        check(f"{n} 무게 일치", nd["normalized_weight"]["value"] == _round(expect["normalized_weight"]["value"]))
        price = next(c for c in nd["conversions"] if c["field_path"] == "product.original_price.amount")
        check(f"{n} 가격 KRW", price["normalized_value"] == round(doc["product"]["original_price"]["amount"] * 1400))
        has_pw = doc["product"]["recommended_pet_weight_max"] is not None
        check(f"{n} 권장 체중 단위 미상은 변환 안 함", (not has_pw) or any(u["field_path"] == "product.recommended_pet_weight_max" for u in nd["unconverted"]))
        check(f"{n} A03 상태", res["agent_outputs"]["A03"]["status"] == ("partial_success" if nd["unconverted"] else "success"))

    base = {"product_id": "p", "run": {"run_id": "r"}, "product": {
        "original_price": {"amount": 10, "currency": "CNY"},
        "dimensions": {"length": 3, "width": None, "height": None, "unit": "ft"},
        "weight": {"value": 2, "unit": "lb"}, "recommended_pet_weight_max": {"value": 88, "unit": "lb"},
        "material": ["Oxford", "Bamboo"],
        "images": [{"image_id": "i1", "url": "u"}, {"image_id": "i2", "url": "u"}],
        "reviews": [{"review_id": "r1", "text": "Good  bed"}, {"review_id": "r2", "text": "good bed"}]}}
    res = normalize(base, rates, None, at)
    nd = res["normalized_data"]
    check("음성: 환율 없는 CNY는 변환 안 함", any(u["field_path"] == "product.original_price.amount" for u in nd["unconverted"]))
    check("음성: 모르는 길이 단위 ft는 변환 안 함", nd["normalized_dimensions"]["length"] is None)
    check("lb→kg 무게", nd["normalized_weight"]["value"] == _round(2 * 0.45359237))
    check("권장 체중 객체 lb→kg", nd["normalized_pet_weight_max"]["value"] == _round(88 * 0.45359237))
    check("소재 동의어·기타", [m["normalized"] for m in nd["normalized_material"]] == ["polyester", "other"])
    check("중복 이미지·리뷰 표시", {d["type"] for d in nd["duplicates"]} == {"image_url", "review_text"})
    check("부분 성공 상태", res["agent_outputs"]["A03"]["status"] == "partial_success")
    print("결과:", "PASS" if not fails else f"FAIL {fails}건")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="A03-02 정규화 PoC")
    ap.add_argument("input", nargs="?", type=Path)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--rate", action="append", default=[], help="예: USD:KRW=1400")
    ap.add_argument("--rate-source", help="환율 출처와 기준일")
    ap.add_argument("--at", default="2026-11-07T12:00:00+09:00", help="변환 시각 (ISO 8601)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.input:
        ap.error("입력 파일이 필요합니다")
    rates = {}
    for r in a.rate:
        pair, val = r.split("=")
        rates[pair.upper()] = float(val)
    doc = json.loads(a.input.read_text(encoding="utf-8"))
    res = normalize(doc, rates, a.rate_source, a.at)
    text = json.dumps(res, ensure_ascii=False, indent=2) + "\n"
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    s = res["agent_outputs"]["A03"]
    print(f"A03 {s['status']}: 변환 {s['result']['conversion_count']}건, 미변환 {s['result']['unconverted_count']}건, "
          f"중복 {s['result']['duplicate_groups']}그룹", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
