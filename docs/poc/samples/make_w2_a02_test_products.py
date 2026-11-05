"""W2 A02/A03 대체 경로용 합성 테스트 상품 3건을 W1-04 v0.1 구조로 만든다.

실제 상품·판매자·리뷰가 아니며 모든 값은 data_type "test" 이다.
"""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
AT = "2026-11-05T15:00:00+09:00"
RATE_USD_KRW = 1400.0  # 테스트용 고정 환율 (실제 환율 아님)
NEEDS_REVIEW_USAGE = {"store": "needs_review", "ai_input": "needs_review",
                      "display": "needs_review", "resale": "needs_review"}

PRODUCTS = [
    {
        "no": "001", "category_id": "pet_harness",
        "name": "TEST Padded No-Pull Harness for Large Dogs",
        "name_ko": "대형견용 패딩 노풀 하네스 (테스트)",
        "desc": "TEST DATA. Padded vest harness for large dogs. Chest girth 70-90 cm. "
                "Nylon outer, mesh lining. Two leash rings. Weight 0.45 kg.",
        "desc_ko": "테스트 데이터. 대형견용 패딩 조끼형 하네스. 가슴둘레 70-90cm. "
                   "겉감 나일론, 안감 메시. 리드줄 고리 2개. 무게 0.45kg.",
        "price": 5.20, "dims": None, "dims_unit": None,
        "weight": (450, "g"), "material": ["nylon", "mesh"], "pet_max": 40,
        "options": [("size", "L"), ("size", "XL"), ("color", "black")],
        "sales": 1200, "rating": 4.6, "ship": ("express", None),
        "reviews": [
            ("Fits my 35 kg retriever well.", "35kg 리트리버에게 잘 맞아요.", 5),
            ("The buckle broke after two weeks.", "2주 만에 버클이 부러졌어요.", 2),
            ("Padding is soft, no rubbing.", "패딩이 부드러워서 쓸리지 않아요.", 5),
            ("Size runs small, order one size up.", "사이즈가 작게 나와요. 한 치수 크게 주문하세요.", 3),
            ("Good pulling control on walks.", "산책할 때 당김 조절이 잘 돼요.", 5),
            ("Buckle feels cheap and plastic.", "버클이 싸구려 플라스틱 느낌이에요.", 2),
            ("Reflective strip is useful at night.", "반사띠가 밤에 유용해요.", 4),
            ("Too small for a 45 kg dog.", "45kg 강아지에게는 너무 작아요.", 2),
            ("Easy to put on and take off.", "입히고 벗기기 쉬워요.", 5),
            ("Stitching came loose at the strap.", "끈 부분 박음질이 풀렸어요.", 2),
            ("My dog seems comfortable.", "강아지가 편해 보여요.", 4),
            ("Color is the same as the photo.", "색상이 사진과 같아요.", 4),
            ("Size chart was accurate for us.", "저희는 사이즈표가 정확했어요.", 4),
            ("Ring is strong enough for a big dog.", "고리가 대형견에게 충분히 튼튼해요.", 5),
            ("Smells of chemicals at first.", "처음에 화학 냄새가 나요.", 3),
            ("Mesh dries quickly after washing.", "세탁 후 메시가 빨리 말라요.", 4),
            ("Straps slip loose during walks.", "산책 중에 끈이 헐거워져요.", 2),
            ("Good value for the price.", "가격 대비 괜찮아요.", 4),
            ("Buckle cracked when my dog pulled hard.", "강아지가 세게 당기자 버클에 금이 갔어요.", 1),
            ("Would buy again in XL.", "XL로 다시 살 거예요.", 4),
        ],
    },
    {
        "no": "002", "category_id": "pet_bedding",
        "name": "TEST Washable Rectangle Dog Bed Mattress Large",
        "name_ko": "세탁 가능한 대형견 직사각형 매트리스 (테스트)",
        "desc": "TEST DATA. Rectangle dog bed for large dogs. Size 1100 x 800 x 120 mm. "
                "Removable washable cover. Polyester filling. Weight 3.2 kg.",
        "desc_ko": "테스트 데이터. 대형견용 직사각형 침대. 크기 1100 x 800 x 120mm. "
                   "분리 세탁 가능한 커버. 폴리에스터 충전재. 무게 3.2kg.",
        "price": 18.50, "dims": (1100, 800, 120), "dims_unit": "mm",
        "weight": (3.2, "kg"), "material": ["polyester", "cotton"], "pet_max": None,
        "options": [("size", "XL"), ("color", "gray")],
        "sales": 340, "rating": 4.3, "ship": ("standard", None),
        "reviews": [
            ("Big enough for my 40 kg shepherd.", "40kg 셰퍼드에게 충분히 커요.", 5),
            ("Filling went flat after a month.", "한 달 만에 충전재가 납작해졌어요.", 2),
            ("Cover washes well in the machine.", "커버가 세탁기로 잘 빨려요.", 5),
            ("Zipper broke when removing the cover.", "커버를 벗기다 지퍼가 고장 났어요.", 2),
            ("My dog sleeps on it every night.", "강아지가 매일 밤 여기서 자요.", 5),
            ("Thinner than I expected.", "생각보다 얇아요.", 3),
            ("No smell after unpacking.", "포장을 풀었을 때 냄새가 없어요.", 4),
            ("Edges lost shape quickly.", "가장자리가 금방 모양이 망가졌어요.", 2),
            ("Non-slip bottom works on tile.", "미끄럼 방지 바닥이 타일에서 잘 돼요.", 4),
            ("Got flat in the middle after weeks.", "몇 주 지나니 가운데가 꺼졌어요.", 2),
            ("Soft surface, dog loves it.", "표면이 부드러워서 강아지가 좋아해요.", 5),
            ("Color slightly darker than photo.", "사진보다 색이 조금 어두워요.", 3),
            ("Shipping took three weeks.", "배송에 3주 걸렸어요.", 3),
            ("Good for old dogs with joint pain.", "관절이 안 좋은 노견에게 좋아요.", 4),
            ("Seams are well sewn.", "이음새 바느질이 잘 돼 있어요.", 4),
            ("Hair sticks to the fabric.", "털이 천에 잘 붙어요.", 3),
            ("Zipper got stuck after washing.", "세탁 후 지퍼가 걸려요.", 2),
            ("Fits in my car trunk too.", "차 트렁크에도 들어가요.", 4),
            ("Reasonable price for the size.", "크기에 비해 가격이 적당해요.", 4),
            ("Would recommend for large breeds.", "대형견에게 추천해요.", 5),
        ],
    },
    {
        "no": "003", "category_id": "pet_toy",
        "name": "TEST Tough Rubber Chew Bone for Large Breeds",
        "name_ko": "대형견용 튼튼한 고무 씹는 뼈 (테스트)",
        "desc": "TEST DATA. Chew bone toy for large dogs. Length 7.5 in. "
                "Natural rubber. Weight 280 g.",
        "desc_ko": "테스트 데이터. 대형견용 씹는 뼈 장난감. 길이 7.5인치. "
                   "천연 고무. 무게 280g.",
        "price": 2.30, "dims": (7.5, None, None), "dims_unit": "in",
        "weight": (280, "g"), "material": ["natural rubber"], "pet_max": None,
        "options": [("color", "orange")],
        "sales": None, "rating": 4.1, "ship": ("standard", 1.50),
        "reviews": [
            ("Lasted three weeks with my lab.", "래브라도와 3주 버텼어요.", 4),
            ("Pieces broke off within a day.", "하루 만에 조각이 떨어져 나갔어요.", 1),
            ("My dog loves the texture.", "강아지가 질감을 좋아해요.", 5),
            ("Not indestructible as the title says.", "제목처럼 부서지지 않는 건 아니에요.", 2),
            ("Good size for a big mouth.", "입이 큰 강아지에게 적당한 크기예요.", 4),
            ("Strong rubber smell.", "고무 냄새가 강해요.", 3),
            ("Easy to clean with water.", "물로 씻기 쉬워요.", 4),
            ("Small pieces came off, be careful.", "작은 조각이 떨어지니 조심하세요.", 2),
            ("Keeps my dog busy for hours.", "강아지가 몇 시간씩 가지고 놀아요.", 5),
            ("Too hard for an older dog.", "노견에게는 너무 딱딱해요.", 3),
            ("Color faded quickly.", "색이 금방 바랬어요.", 3),
            ("Floats in water, fun at the lake.", "물에 떠서 호수에서 재밌어요.", 4),
            ("Chewed through in two days.", "이틀 만에 다 씹어 버렸어요.", 1),
            ("Cheap and works okay.", "싸고 그럭저럭 괜찮아요.", 3),
            ("Bigger than I thought.", "생각보다 커요.", 4),
            ("Safe so far for my husky.", "허스키에게 아직까지는 안전해요.", 4),
            ("Bits broke off and I threw it away.", "조각이 떨어져서 버렸어요.", 1),
            ("Good for teething.", "이갈이할 때 좋아요.", 4),
            ("Shipping was fast.", "배송이 빨랐어요.", 4),
            ("Average quality.", "품질은 보통이에요.", 3),
        ],
    },
]

LENGTH_TO_CM = {"mm": 0.1, "cm": 1.0, "in": 2.54}
WEIGHT_TO_KG = {"g": 0.001, "kg": 1.0, "lb": 0.45359237}


def meta(path_id, url):
    return {"data_type": "test", "source_url": url, "source_id": path_id, "collected_at": AT}


def build(p):
    pid = f"prod-test-{p['no']}"
    url = f"https://example.com/test-products/{p['no']}"
    run_id = f"run-test-{p['no']}"
    product = {
        "source_url": url, "platform": "test_catalog", "collection_method": "mock",
        "collected_at": AT, "original_name": p["name"], "description": p["desc"],
        "description_id": f"desc-test-{p['no']}",
        "original_price": {"amount": p["price"], "currency": "USD"},
        "options": [{"option_id": f"opt-{p['no']}-{i+1:02d}", "name": n, "value": v,
                     "data_type": "test", "source_url": url}
                    for i, (n, v) in enumerate(p["options"])],
        "dimensions": None, "weight": {"value": p["weight"][0], "unit": p["weight"][1]},
        "material": p["material"], "recommended_pet_weight_max": p["pet_max"],
        "sales_count": p["sales"], "rating": p["rating"],
        "shipping": {"method": p["ship"][0], "fee": p["ship"][1], "currency": "USD"},
        "supplier": {"supplier_id": f"sup-test-{p['no']}", "name": f"TEST Supplier {p['no']}",
                     "source_url": url, "data_type": "test"},
        "images": [], "reviews": [],
    }
    if p["dims"]:
        l, w, h = p["dims"]
        product["dimensions"] = {"length": l, "width": w, "height": h, "unit": p["dims_unit"]}
    for i in range(5):
        product["images"].append({
            "image_id": f"img-{p['no']}-{i+1:02d}", "image_no": i + 1,
            "image_role": "main" if i == 0 else "detail",
            "url": f"https://example.com/test-images/{p['no']}-{i+1}.jpg",
            "source_url": url, "rights_status": "needs_review", "data_type": "test",
            "usage": dict(NEEDS_REVIEW_USAGE), "usage_policy_url": None, "usage_checked_at": None,
        })
    for i, (text, _, rating) in enumerate(p["reviews"]):
        product["reviews"].append({
            "review_id": f"review-{p['no']}-{i+1:02d}", "text": text, "rating": rating,
            "source_url": url, "data_type": "test", "rights_status": "needs_review",
            "usage": dict(NEEDS_REVIEW_USAGE), "usage_policy_url": None, "usage_checked_at": None,
        })

    field_meta = {}
    scalar_paths = ["original_name", "description", "description_id", "original_price.amount",
                    "original_price.currency", "weight.value", "weight.unit", "material",
                    "recommended_pet_weight_max", "sales_count", "rating", "shipping.method",
                    "shipping.fee", "supplier.name"]
    if product["dimensions"]:
        scalar_paths += ["dimensions.length", "dimensions.width", "dimensions.height", "dimensions.unit"]
    else:
        scalar_paths += ["dimensions"]
    for sp in scalar_paths:
        path = f"product.{sp}"
        field_meta[path] = meta(product["description_id"] if sp.startswith("description") else path, url)
    for i in range(len(product["options"])):
        path = f"product.options[{i}].value"
        field_meta[path] = meta(path, url)

    missing = []
    def miss(path, reason, action):
        missing.append({"field_path": path, "reason": reason, "next_action": action})
    if product["dimensions"] is None:
        miss("product.dimensions", "source_missing", "착용형 상품이라 크기 대신 가슴둘레 범위만 표기됨. 설명문 수치로 확인")
    else:
        for k in ("width", "height"):
            if product["dimensions"][k] is None:
                miss(f"product.dimensions.{k}", "source_missing", "길이만 표기됨. 공급처 문의 필요")
    if product["recommended_pet_weight_max"] is None:
        miss("product.recommended_pet_weight_max", "source_missing", "공급처에 최대 권장 체중 확인")
    if product["sales_count"] is None:
        miss("product.sales_count", "source_missing", "원본에 판매량 표시 없음")
    if product["shipping"]["fee"] is None:
        miss("product.shipping.fee", "manual_review_required", "배송비는 수량·지역별로 달라 수동 확인")

    # A03 번역·정규화
    conversions = []
    def conv(path, ov, ou, nv, nu, rate, src):
        conversions.append({"field_path": path, "original_value": ov, "original_unit": ou,
                            "normalized_value": nv, "normalized_unit": nu, "conversion_rate": rate,
                            "rate_source": src, "converted_at": AT, "data_type": "test"})
    conv("product.original_price.amount", p["price"], "USD", round(p["price"] * RATE_USD_KRW, 0), "KRW",
         RATE_USD_KRW, "테스트용 고정 환율(실제 환율 아님)")
    norm_dims = None
    if product["dimensions"]:
        unit = product["dimensions"]["unit"]
        f = LENGTH_TO_CM[unit]
        norm_dims = {"unit": "cm"}
        for k in ("length", "width", "height"):
            v = product["dimensions"][k]
            nv = None if v is None else round(v * f, 2)
            norm_dims[k] = nv
            if v is not None:
                conv(f"product.dimensions.{k}", v, unit, nv, "cm", f,
                     "길이 단위 변환" if f != 1 else "동일 단위 보존")
    wv, wu = p["weight"]
    wf = WEIGHT_TO_KG[wu]
    nw = round(wv * wf, 3)
    conv("product.weight.value", wv, wu, nw, "kg", wf, "무게 단위 변환" if wf != 1 else "동일 단위 보존")

    normalized = {
        "translated_name": p["name_ko"],
        "translated_description": p["desc_ko"],
        "translated_reviews": [{"review_id": f"review-{p['no']}-{i+1:02d}", "translated_text": ko}
                               for i, (_, ko, _) in enumerate(p["reviews"])],
        "conversions": conversions,
        "normalized_dimensions": norm_dims if norm_dims else
            {"length": None, "width": None, "height": None, "unit": "cm"},
        "normalized_weight": {"value": nw, "unit": "kg"},
    }

    def envelope(agent, result, warnings):
        return {"run_id": run_id, "product_id": pid, "agent_id": agent, "input_version": 1,
                "result_version": 1, "status": "success", "result": result, "evidence_ids": [],
                "warnings": warnings, "errors": [], "retry_count": 0,
                "started_at": AT, "ended_at": AT, "data_type": "test"}

    warn = "본 결과는 합성 테스트 데이터 기반입니다(실제 상품 아님)."
    a03_warn = [warn, "환율은 테스트용 고정값으로 실제 가격 결정에 사용하지 않는다."]
    if norm_dims is None or None in (norm_dims.get("width"), norm_dims.get("height")):
        a03_warn.append("크기 일부가 원본에 없어 정규화 크기에 null이 포함된다.")

    return pid, {
        "schema_version": "0.1", "product_id": pid, "category_id": p["category_id"],
        "run": {"run_id": run_id, "job_id": None, "status": "success", "started_at": AT, "ended_at": AT},
        "input_version": 1, "source_version": 1, "product": product,
        "field_meta": field_meta, "missing_fields": missing, "normalized_data": normalized,
        "evidence": [],
        "agent_outputs": {
            "A02": envelope("A02", {"source_version": 1, "record_created": True}, [warn]),
            "A03": envelope("A03", {"normalized_data_ref": {"source_version": 1, "result_version": 1},
                                    "translated_review_count": len(p["reviews"]),
                                    "conversion_count": len(conversions)}, a03_warn),
        },
        "errors": [],
        "approval": {"status": "not_requested", "target_version": None, "approver": None,
                     "approved_at": None, "reason": None},
    }


def read_path(root, path):
    import re
    cur = root
    for seg in path.split("."):
        m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", seg)
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            cur = cur[int(m.group(2))]
    return cur


def check(doc):
    """W1-04 규칙 중 A02·A03 범위만 자체 점검한다 (B01·B02·B04 결과는 범위 밖)."""
    errs = []
    for path in doc["field_meta"]:
        try:
            read_path(doc, path)
        except (KeyError, IndexError, TypeError):
            errs.append(f"field_meta 경로 없음: {path}")
    for m in doc["missing_fields"]:
        v = read_path(doc, m["field_path"])
        if v not in (None, [], ""):
            errs.append(f"값이 있는데 누락 처리: {m['field_path']}")
    for item in doc["product"]["images"] + doc["product"]["reviews"]:
        u = item["usage"]
        expect = ("usable" if all(x == "allowed" for x in u.values()) else
                  "prohibited" if "prohibited" in u.values() else "needs_review")
        if item["rights_status"] != expect:
            errs.append(f"rights_status 불일치: {item.get('image_id') or item.get('review_id')}")
    src_ids = {r["review_id"] for r in doc["product"]["reviews"]}
    tr_ids = {r["review_id"] for r in doc["normalized_data"]["translated_reviews"]}
    if src_ids != tr_ids:
        errs.append("번역 리뷰 ID가 원본과 다름")
    for c in doc["normalized_data"]["conversions"]:
        if read_path(doc, c["field_path"]) != c["original_value"]:
            errs.append(f"변환 원본값 불일치: {c['field_path']}")
        if c["conversion_rate"] and round(c["original_value"] * c["conversion_rate"], 3) != round(c["normalized_value"], 3):
            if c["normalized_unit"] != "KRW":
                errs.append(f"변환 계산 불일치: {c['field_path']}")
    nd = doc["normalized_data"]["normalized_dimensions"]
    for c in doc["normalized_data"]["conversions"]:
        if c["field_path"].startswith("product.dimensions."):
            k = c["field_path"].rsplit(".", 1)[1]
            if nd[k] != c["normalized_value"]:
                errs.append(f"normalized_dimensions.{k} 불일치")
    return errs


OUT.mkdir(parents=True, exist_ok=True)
ok = True
for p in PRODUCTS:
    pid, doc = build(p)
    errs = check(doc)
    path = OUT / f"W2-A02_TEST_PRODUCT_{p['no']}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{path.name}: 리뷰 {len(doc['product']['reviews'])}, 이미지 {len(doc['product']['images'])}, "
          f"누락 {len(doc['missing_fields'])}, 변환 {len(doc['normalized_data']['conversions'])}, "
          f"점검 {'PASS' if not errs else 'FAIL ' + '; '.join(errs)}")
    ok = ok and not errs
sys.exit(0 if ok else 1)
