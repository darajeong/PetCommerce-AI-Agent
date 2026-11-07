"""A02-02 입력표(사실 값)와 합성 콘텐츠를 합쳐 W1-04 상품 JSON을 만든다.

    python docs/poc/samples/a02_build_product.py [--facts W2-A02-02_FACTS_INPUT.csv] [--out-dir docs/poc/samples]

W1-07 1.1절(2026-11-06 확정) 데이터 구성:
- 사실 값(상품명·가격·판매량·평점·옵션·규격·배송·공급처): 사람이 상품 페이지를 직접 열어 입력표에
  적은 값만 쓴다. `data_type: actual`, `collection_method: manual`.
- 이미지·리뷰·상세 설명: 원문 사용 권한이 `needs_review`라 쓰지 않고, 아래 합성 콘텐츠로 대체한다
  (`data_type: test`). 합성 자료라 저장·AI 입력·표시는 허용, 판매 콘텐츠 재사용은 금지.
- 입력표 빈칸은 "사람 확인 전"(`manual_review_required`), `없음`은 원본에 없음(`source_missing`)으로
  누락 처리하고 값을 추정하지 않는다.
AI가 상품 페이지를 열거나 읽지 않는다. 이 스크립트는 사람이 적은 표만 읽는다.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
USAGE_POLICY = "docs/poc/samples/W2-A02_TEST_PRODUCTS_README.md"
SYNTHETIC_USAGE = {"store": "allowed", "ai_input": "allowed", "display": "allowed", "resale": "prohibited"}

# 합성 콘텐츠: 실제 상품 페이지의 설명·리뷰를 옮긴 것이 아니라 상품 유형에 맞춰 팀이 새로 쓴 문장이다.
SYNTHETIC = {
    "prod-w2-01": {
        "description": ("TEST DATA (synthetic). Rear support lift sling for large dogs with weak hind legs. "
                        "Padded belly panel, long carry handle, adjustable straps."),
        "description_ko": ("테스트 데이터(합성). 뒷다리가 약한 대형견용 후방 보조 리프트 슬링. "
                           "패딩 복부 패널, 긴 손잡이, 조절 가능한 끈."),
        "reviews": [
            ("Helps my old lab climb the stairs.", "노견 래브라도가 계단 오를 때 도움이 돼요.", 5),
            ("Handle is too short for a tall person.", "키 큰 사람에게는 손잡이가 너무 짧아요.", 3),
            ("Padding is soft on the belly.", "배 부분 패딩이 부드러워요.", 5),
            ("Strap slipped off during a walk.", "산책 중에 끈이 빠졌어요.", 2),
            ("Good after my dog's knee surgery.", "강아지 무릎 수술 후에 좋아요.", 5),
            ("Too narrow for a 45 kg dog.", "45kg 강아지에게는 폭이 좁아요.", 2),
            ("Easy to put on while the dog stands.", "강아지가 서 있을 때 착용시키기 쉬워요.", 4),
            ("Velcro wore out in a month.", "한 달 만에 벨크로가 약해졌어요.", 2),
            ("Saves my back when lifting.", "들어 올릴 때 허리가 덜 아파요.", 5),
            ("Strap slips when the dog turns.", "강아지가 방향을 틀 때 끈이 미끄러져요.", 2),
            ("Washes fine by hand.", "손세탁해도 괜찮아요.", 4),
            ("Smaller than the size chart.", "사이즈표보다 작아요.", 3),
            ("Stitching on the handle is strong.", "손잡이 박음질이 튼튼해요.", 4),
            ("My dog walks longer with it.", "이걸로 강아지가 더 오래 걸어요.", 5),
            ("Not for daily walking, only support.", "일상 산책용이 아니라 보조용이에요.", 3),
            ("Velcro catches dog hair.", "벨크로에 털이 붙어요.", 3),
            ("Good price for rehab use.", "재활용으로 가격이 괜찮아요.", 4),
            ("Arrived quickly.", "빨리 도착했어요.", 4),
            ("Velcro stopped holding after washing.", "세탁 후 벨크로가 잘 안 붙어요.", 2),
            ("Would buy a bigger size next time.", "다음엔 더 큰 사이즈로 살 거예요.", 4),
        ],
    },
    "prod-w2-07": {
        "description": ("TEST DATA (synthetic). Rectangle bed for large dogs. Removable washable cover, "
                        "non-slip bottom, fiber filling."),
        "description_ko": ("테스트 데이터(합성). 대형견용 직사각형 침대. 분리 세탁 가능한 커버, "
                           "미끄럼 방지 바닥, 섬유 충전재."),
        "reviews": [
            ("Big enough for my 38 kg dog.", "38kg 강아지에게 충분히 커요.", 5),
            ("Filling went flat in three weeks.", "3주 만에 충전재가 납작해졌어요.", 2),
            ("Cover is easy to wash.", "커버 세탁이 쉬워요.", 5),
            ("Zipper broke on the first wash.", "첫 세탁 때 지퍼가 고장 났어요.", 2),
            ("My dog sleeps here all night.", "강아지가 밤새 여기서 자요.", 5),
            ("Thinner than expected.", "생각보다 얇아요.", 3),
            ("No smell when unpacked.", "포장을 풀 때 냄새가 없어요.", 4),
            ("Middle sank after a month.", "한 달 지나니 가운데가 꺼졌어요.", 2),
            ("Bottom does not slide on wood floor.", "마루에서 바닥이 미끄러지지 않아요.", 4),
            ("Flat in the middle quickly.", "가운데가 금방 납작해져요.", 2),
            ("Soft fabric, dog likes it.", "천이 부드러워서 강아지가 좋아해요.", 5),
            ("Color a bit different from photo.", "사진과 색이 조금 달라요.", 3),
            ("Took two weeks to arrive.", "도착까지 2주 걸렸어요.", 3),
            ("Good for an older dog.", "노견에게 좋아요.", 4),
            ("Seams look strong.", "이음새가 튼튼해 보여요.", 4),
            ("Dog hair sticks to the cover.", "커버에 털이 붙어요.", 3),
            ("Zipper got stuck after drying.", "건조 후 지퍼가 걸려요.", 2),
            ("Fits in a crate.", "켄넬 안에 들어가요.", 4),
            ("Fair price for the size.", "크기 대비 가격이 적당해요.", 4),
            ("Would recommend for big dogs.", "대형견에게 추천해요.", 5),
        ],
    },
    "prod-w2-09": {
        "description": ("TEST DATA (synthetic). Silicone treat ball for large dogs. Fill with food and freeze. "
                        "Textured surface for licking."),
        "description_ko": ("테스트 데이터(합성). 대형견용 실리콘 간식 공. 음식을 채워 얼려서 사용. "
                           "핥기용 요철 표면."),
        "reviews": [
            ("Keeps my husky busy for 30 minutes.", "허스키가 30분 동안 집중해요.", 5),
            ("Torn after one day of chewing.", "하루 씹고 찢어졌어요.", 1),
            ("Easy to fill and freeze.", "채워서 얼리기 쉬워요.", 5),
            ("Not for strong chewers.", "세게 씹는 강아지용은 아니에요.", 2),
            ("Good size for a large mouth.", "입이 큰 강아지에게 맞는 크기예요.", 4),
            ("Dishwasher safe, very handy.", "식기세척기 사용 가능해서 편해요.", 4),
            ("Hard to clean the inside.", "안쪽 세척이 어려워요.", 3),
            ("Small pieces came off when chewed.", "씹으니 작은 조각이 떨어졌어요.", 2),
            ("Slows down my dog's eating.", "강아지가 천천히 먹게 돼요.", 5),
            ("Silicone smell at first.", "처음에 실리콘 냄새가 나요.", 3),
            ("Color faded after washing.", "세척 후 색이 바랬어요.", 3),
            ("Great on hot days with frozen yogurt.", "더운 날 얼린 요거트로 좋아요.", 5),
            ("Torn in two days by my shepherd.", "셰퍼드가 이틀 만에 찢었어요.", 1),
            ("Cheap and works well.", "싸고 잘 작동해요.", 4),
            ("Bigger than I expected.", "생각보다 커요.", 4),
            ("Safe so far for my retriever.", "리트리버에게 아직은 안전해요.", 4),
            ("Pieces broke off, threw it away.", "조각이 떨어져서 버렸어요.", 1),
            ("Good for anxious dogs.", "불안해하는 강아지에게 좋아요.", 4),
            ("Shipping was fast.", "배송이 빨랐어요.", 4),
            ("Average quality.", "품질은 보통이에요.", 3),
        ],
    },
}

FACT_FIELDS = [  # (입력표 key, W1-04 경로)
    ("original_name", "product.original_name"), ("price_min", "product.original_price.amount"),
    ("currency", "product.original_price.currency"), ("sales_count", "product.sales_count"),
    ("rating", "product.rating"), ("material", "product.material"),
    ("supplier_name", "product.supplier.name"),
]


def read_facts(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    ids = [h.split(" ")[0] for h in rows[0][2:]]
    facts = {pid: {} for pid in ids}
    for row in rows[1:]:
        for pid, val in zip(ids, row[2:]):
            facts[pid][row[0]] = val.strip()
    return facts


def build(pid: str, f: dict[str, str]) -> dict:
    url = f["source_url"]
    at = (f.get("collected_at") or "2026-11-05").replace(" ", "T")
    at = at if "T" in at else at + "T00:00"
    at = at if "+" in at else at + ":00+09:00"
    missing: list[dict] = []
    field_meta: dict[str, dict] = {}

    def val(key, path, cast=str):
        raw = f.get(key, "")
        if raw == "" or raw == "없음":
            missing.append({"field_path": path,
                            "reason": "source_missing" if raw == "없음" else "manual_review_required",
                            "next_action": "원본에 표시 없음" if raw == "없음" else "사람이 상품 페이지에서 확인 후 입력표에 기록"})
            return None
        return cast(raw)

    def num(key, path):
        return val(key, path, lambda s: float(s.replace(",", "")))

    name = val("original_name", "product.original_name")
    price = num("price_min", "product.original_price.amount")
    currency = val("currency", "product.original_price.currency")
    sales = val("sales_count", "product.sales_count", lambda s: int(s.replace(",", "")))
    rating = num("rating", "product.rating")
    material = None
    if f.get("material") in ("", "없음"):
        val("material", "product.material")
    else:
        material = [m.strip() for m in f["material"].split(";") if m.strip()]

    dims = None
    if all(f.get(k, "") in ("", "없음") for k in ("length", "width", "height")):
        val("length", "product.dimensions")
    else:
        dims = {k: (None if f.get(k, "") in ("", "없음") else float(f[k])) for k in ("length", "width", "height")}
        dims["unit"] = f.get("dim_unit") or None
        for k in ("length", "width", "height"):
            if dims[k] is None:
                val(k, f"product.dimensions.{k}")
    weight = None
    if f.get("weight", "") in ("", "없음"):
        val("weight", "product.weight")
    else:
        weight = {"value": float(f["weight"]), "unit": f.get("weight_unit") or None}
    pet = None
    if f.get("pet_weight_max", "") in ("", "없음"):
        val("pet_weight_max", "product.recommended_pet_weight_max")
    else:  # W1-04 v0.2 제안 형식 {value, unit}
        pet = {"value": float(f["pet_weight_max"]), "unit": f.get("pet_weight_unit") or None}
    ship = {"method": f.get("shipping_method") or None,
            "fee": None if f.get("shipping_fee", "") in ("", "없음") else float(f["shipping_fee"]),
            "currency": f.get("shipping_currency") or None}
    if ship["method"] is None:
        val("shipping_method", "product.shipping.method")
    if ship["fee"] is None:
        val("shipping_fee", "product.shipping.fee")
    supplier_name = val("supplier_name", "product.supplier.name")
    options = []
    for i, pair in enumerate(p for p in f.get("options", "").split(";") if "=" in p):
        n, v = pair.split("=", 1)
        options.append({"option_id": f"opt-{pid[-2:]}-{i+1:02d}", "name": n.strip(), "value": v.strip(),
                        "data_type": "actual", "source_url": url})
    if not options:
        val("options", "product.options")

    syn = SYNTHETIC[pid]
    syn_url = f"https://example.com/synthetic/{pid}"
    images = [{"image_id": f"img-{pid[-2:]}-{i+1:02d}", "image_no": i + 1,
               "image_role": "main" if i == 0 else "detail",
               "url": f"https://example.com/synthetic-images/{pid}-{i+1}.jpg", "source_url": syn_url,
               "rights_status": "prohibited", "data_type": "test", "usage": dict(SYNTHETIC_USAGE),
               "usage_policy_url": USAGE_POLICY, "usage_checked_at": at} for i in range(5)]
    reviews = [{"review_id": f"review-{pid[-2:]}-{i+1:02d}", "text": t, "rating": r, "source_url": syn_url,
                "data_type": "test", "rights_status": "prohibited", "usage": dict(SYNTHETIC_USAGE),
                "usage_policy_url": USAGE_POLICY, "usage_checked_at": at}
               for i, (t, _, r) in enumerate(syn["reviews"])]

    product = {
        "source_url": url, "platform": f.get("platform") or "alibaba", "collection_method": "manual",
        "collected_at": at, "original_name": name, "description": syn["description"],
        "description_id": f"desc-{pid}", "original_price": {"amount": price, "currency": currency},
        "options": options, "dimensions": dims, "weight": weight, "material": material,
        "recommended_pet_weight_max": pet, "sales_count": sales, "rating": rating, "shipping": ship,
        "supplier": {"supplier_id": f"sup-{pid}", "name": supplier_name, "source_url": url, "data_type": "actual"},
        "images": images, "reviews": reviews,
    }
    for _, path in FACT_FIELDS:
        field_meta[path] = {"data_type": "actual", "source_url": url, "source_id": path, "collected_at": at}
    for k in ("description", "description_id"):
        field_meta[f"product.{k}"] = {"data_type": "test", "source_url": syn_url,
                                      "source_id": f"desc-{pid}", "collected_at": at}

    warnings = ["사실 값은 사람이 직접 확인한 실제 값, 이미지·리뷰·설명은 합성 테스트 데이터다 (W1-07 1.1절, 2026-11-06 팀 확정)."]
    if f.get("price_max"):
        warnings.append(f"가격은 최저가({f['price_min']})만 저장했다. 범위 {f['price_min']}~{f['price_max']} {currency}, 조건: {f.get('price_note') or '없음'}")
    if f.get("review_count"):
        warnings.append(f"실제 상품 리뷰 수는 {f['review_count']}개이며 리뷰 원문은 저장하지 않았다.")
    if f.get("product_use"):
        warnings.append(f"용도: {f['product_use']}")
    if f.get("large_dog_label"):
        warnings.append(f"상세 페이지 대형견 표기: {f['large_dog_label']}")
    pending = sum(1 for m in missing if m["reason"] == "manual_review_required")
    status = "partial_success" if pending else "success"
    run_id = f"run-{pid}-a02"

    return {
        "schema_version": "0.1", "product_id": pid, "category_id": f.get("category_id"),
        "run": {"run_id": run_id, "job_id": None, "status": status, "started_at": at, "ended_at": at},
        "input_version": 1, "source_version": 1, "product": product, "field_meta": field_meta,
        "missing_fields": missing,
        "normalized_data": {"translated_name": None, "translated_description": syn["description_ko"],
                            "translated_reviews": [{"review_id": f"review-{pid[-2:]}-{i+1:02d}", "translated_text": ko}
                                                   for i, (_, ko, _) in enumerate(syn["reviews"])]},
        "evidence": [],
        "agent_outputs": {"A02": {
            "run_id": run_id, "product_id": pid, "agent_id": "A02", "input_version": 1, "result_version": 1,
            "status": status, "result": {"source_version": 1, "record_created": True, "pending_manual_fields": pending},
            "evidence_ids": [], "warnings": warnings, "errors": [], "retry_count": 0,
            "started_at": at, "ended_at": at, "data_type": "actual"}},
        "errors": [],
        "approval": {"status": "not_requested", "target_version": None, "approver": None,
                     "approved_at": None, "reason": None},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="A02-02 입력표 → W1-04 상품 JSON")
    ap.add_argument("--facts", type=Path, default=HERE / "W2-A02-02_FACTS_INPUT.csv")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    a = ap.parse_args()
    for pid, f in read_facts(a.facts).items():
        doc = build(pid, f)
        out = a.out_dir / f"W2-A02-02_PRODUCT_{pid}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        m = doc["missing_fields"]
        print(f"{out.name}: A02 {doc['agent_outputs']['A02']['status']}, "
              f"사람 확인 전 {sum(x['reason'] == 'manual_review_required' for x in m)}개, "
              f"원본 없음 {sum(x['reason'] == 'source_missing' for x in m)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
