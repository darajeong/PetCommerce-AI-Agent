"""확장 프로그램 추출본(JSON) → A02-02 입력표 형식 CSV + 검사 보고서 (2026-11-17).

    python docs/poc/samples/a02_capture_to_facts.py 추출본1.json [추출본2.json ...]
        [--template docs/poc/samples/W2-A02-02_FACTS_INPUT.csv]
        [--out docs/poc/samples/W2-A02-02_FACTS_CAPTURE.csv] [--report docs/poc/samples/W2-A02-02_CAPTURE_CHECK.md]
        [--rate USD:KRW=1400 --rate-source "출처·기준일"]
    python docs/poc/samples/a02_capture_to_facts.py --self-test

흐름: 확장 프로그램(a02_capture_ext) 저장본 → 이 스크립트 → a02_build_product.py --facts <출력 CSV> → a03_normalize.py
- 출력 CSV는 사람이 쓰는 입력표(W2-A02-02_FACTS_INPUT.csv)와 같은 형식이라 뒤 단계를 그대로 쓴다.
- 확장이 못 찾은 값은 빈칸(사람 확인 전 = manual_review_required)으로 둔다. '없음'(원본에 없음)은 사람만 판단한다.
- 가격은 a02_price_parse.py로 통화·범위를 검사한다. error면 가격 칸을 비우고, needs_review면 값은 넣되 보고서에 표시한다.
- 상품 유형(category_id)은 페이지 값이 아니라 팀이 정한 값이라 입력표에서 가져온다.
- 보고서에는 사람이 입력한 값(입력표)과 확장 추출 값을 칸별로 비교한 결과가 들어간다 (A02 자동화 정확도 근거).
- 이미지 주소는 추출본에만 남기고 입력표에는 넣지 않는다 (W1-07 1.1절, usage = needs_review).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a02_price_parse import check_plausibility, parse_price_text, parse_tiers  # noqa: E402

try:
    from a03_normalize import MATERIALS  # noqa: E402
except Exception:  # a03 가 없어도 동작 (소재 비교만 글자 비교로)
    MATERIALS = {}

ATTR_RULES = {  # 입력표 항목 ← 속성 이름 (영문·한국어 페이지)
    "material": r"^(?!.*pack).*(material|소재|재질)",
    "size": r"^(size|product size|dimensions?|item size|크기|사이즈|치수|제품 크기)$",
    "weight": r"^(weight|product weight|net weight|item weight|무게|중량|순중량)$",
    "pet_weight": r"(pet|dog).*weight|권장 체중|적용 체중",
    "package_size": r"package size|패키지\s*크기|포장\s*크기",
    "package_weight": r"gross weight|총\s*중량|포장\s*(무게|중량)",
    "breed_size": r"breed size|pet size|dog size|품종\s*크기|견종\s*크기|적용\s*크기",
}
# 앞뒤 빈칸이 있는 " - "만 본다 ("Long-Lasting" 같은 낱말 속 하이픈에서 자르지 않도록)
TITLE_SUFFIX = re.compile(r"\s+[-|]\s+(?:Buy\b.*?|[^-|]*?)\s*on Alibaba\.com$|\s+[-|]\s+Buy\b.*$", re.I)
STORE_SRC = re.compile(r"store|seller|company|supplier|shop", re.I)
DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?\s*(mm|cm|m|inches|inch|in)\b", re.I)
WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|lbs|lb|oz)\b", re.I)
NUMERIC_KEYS = {"price_min", "price_max", "sales_count", "rating", "review_count", "length", "width", "height", "weight"}
COMPARE_KEYS = ["original_name", "price_min", "price_max", "currency", "options", "length", "width", "height", "weight",
                "material", "sales_count", "rating", "review_count", "supplier_name", "package_size", "package_weight"]


def money(x: float, cur: str | None) -> str:
    """배송비 메모용 금액 표기 (KRW는 ₩와 천 단위 쉼표)."""
    return f"₩{x:,.0f}" if cur == "KRW" else f"{num_str(x)} {cur or ''}".strip()


def num_str(x: float | None) -> str:
    if x is None:
        return ""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def find_attrs(attrs: list[dict], key: str) -> list[dict]:
    rule = re.compile(ATTR_RULES[key], re.I)
    return [a for a in attrs if rule.search(a["name"].strip())]


def find_attr(attrs: list[dict], key: str) -> str | None:
    hit = find_attrs(attrs, key)
    return hit[0]["value"] if hit else None


MONEY = r"(₩\s?[\d,]+(?:\.\d+)?|US\$\s?[\d,.]+|\$\s?[\d,.]+|[\d,]+(?:\.\d+)?\s?원)"


def parse_shipping(text: str, cands: list[dict] | None = None) -> dict:
    """배송 상자 글자 → 배송 등급·물류·배송비(할인가·정가, 몇 개 기준)·무료 배송 한도·도착 예정.
    배송지·수량·프로모션에 따라 바뀌는 값이라 원문도 같이 남긴다.
    예) 영어: "Shipping Change Standard Shipping fee: ₩444,021 ₩471,347 for 100 pieces Guaranteed delivery: Nov 26 - Dec 28"
        한국어: "배송 스탠더드 Alibaba.com Logistics 배송비:100개당 ₩442,283 ₩469,519 보장된 배송: 11월 25일 ~ 12월 27일" """
    t = re.sub(r"\s+", " ", text or "").strip()
    out = {"raw": t, "method": None, "tier": None, "carrier": None, "carrier_from": None, "fee": None, "fee_original": None,
           "fee_text": None, "per_qty": None, "free_upto": None, "delivery": None, "currency": None}
    tier = re.search(r"\b(Standard|Economy|Express|Premium)\b|(스탠더드|스탠다드|이코노미|익스프레스|프리미엄)", t, re.I)
    if tier:
        out["tier"] = tier.group(0)
    carrier = re.search(r"Alibaba\.com\s*Logistics|\b[A-Z][A-Za-z.&]+ Logistics\b", t)
    if carrier:
        out["carrier"], out["carrier_from"] = carrier.group(0), "text"
    elif any(c.get("value") == "aliLogistics" for c in cands or []):
        out["carrier"], out["carrier_from"] = "Alibaba.com Logistics", "page_data:logisticsFtType"
    out["method"] = " ".join(x for x in (out["tier"], out["carrier"]) if x) or None
    fee = re.search(r"(?:Shipping fee|Shipping cost|배송비)\s*[:：]?\s*(?:(\d[\d,]*)\s*(?:개당|pieces?|pcs|units?)\s*(?:당)?\s*)?"
                    + MONEY + r"(?:\s+" + MONEY + r")?(?:\s*(?:for|/)\s*(\d[\d,]*)\s*(?:pieces?|pcs|units?))?", t, re.I)
    if fee:
        out["fee_text"] = fee.group(0)
        p = parse_price_text(fee.group(2))
        out["fee"], out["currency"] = p["min"], p["currency"]
        if fee.group(3):   # 두 번째 금액 = 할인 전 정가(취소선)
            out["fee_original"] = parse_price_text(fee.group(3))["min"]
        q = fee.group(1) or fee.group(4)
        out["per_qty"] = int(q.replace(",", "")) if q else None
    free = re.search(r"(?:Free shipping|무료\s*배송)[^₩$\d]{0,20}" + MONEY, t, re.I)
    if free:
        out["free_upto"] = free.group(1).replace(" ", "")
        if out["currency"] is None:
            out["currency"] = parse_price_text(free.group(1))["currency"]
    dl = re.search(r"(?:Guaranteed delivery|Estimated delivery|보장된 배송|예상 배송|도착 예정)\s*[:：]?\s*([A-Za-z0-9가-힣 ~\-–./]{3,30})", t, re.I)
    if dl:
        out["delivery"] = dl.group(1).strip()
    return out


OPT_DIM_RE = re.compile(r"(?:^|(?P<label>[^:：/]{1,12})[:：]\s*)?(?P<l>\d+(?:\.\d+)?)\s*[x×*X]\s*(?P<w>\d+(?:\.\d+)?)\s*[x×*X]\s*(?P<h>\d+(?:\.\d+)?)"
                        r"(?:\s*/\s*(?P<h2>\d+(?:\.\d+)?))?\s*(?P<u>mm|cm|inches|inch|in)\b", re.I)


def option_dims(options: list[dict]) -> list[dict]:
    """옵션 값 안의 치수 (예: 'M: 54*43*18/13cm') → [{label, length, width, height, height2, unit}]"""
    out = []
    for o in options or []:
        for val in o.get("values") or []:
            m = OPT_DIM_RE.search(val)
            if m:
                out.append({"label": (m.group("label") or val.split(":")[0]).strip(), "length": float(m.group("l")),
                            "width": float(m.group("w")), "height": float(m.group("h")),
                            "height2": float(m.group("h2")) if m.group("h2") else None,
                            "unit": {"inch": "in", "inches": "in"}.get(m.group("u").lower(), m.group("u").lower()), "raw": val})
    return out


def read_template(path: Path) -> tuple[list[list[str]], dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    ids = [h.split(" ")[0] for h in rows[0][2:]]
    human = {pid: {} for pid in ids}
    for row in rows[1:]:
        for pid, val in zip(ids, row[2:]):
            human[pid][row[0]] = val.strip()
    return rows, human


def build_column(cap: dict, human: dict[str, str], rates: dict[str, float]) -> tuple[dict[str, str], dict]:
    f = cap.get("fields", {})
    g = lambda k: ((f.get(k) or {}).get("value") or "").strip()
    v: dict[str, str] = {"category_id": human.get("category_id", ""), "source_url": cap.get("source_url", ""),
                         "platform": cap.get("platform") or ""}
    rep: dict = {"product_id": cap.get("product_id"), "notes": []}
    v["original_name"] = TITLE_SUFFIX.sub("", g("original_name"))
    if re.search(r"[가-힣]", v["original_name"]):
        rep["notes"].append("상품명이 한국어 번역 제목으로 보임. 원문(영어) 제목이 필요하면 사이트 언어를 English로 바꿔 다시 추출")

    # ---- 가격 (통화·범위 검사)
    ctx = g("currency_setting") or None
    site = cap.get("host")
    moq_m = re.search(r"\d[\d,]*", g("moq_text"))
    moq = int(moq_m.group().replace(",", "")) if moq_m else None
    tiers = cap.get("price_tiers") or []
    pr, kind = None, None
    if tiers:
        pr, kind = parse_tiers(tiers, ctx, site, moq), "tiers"
    elif g("price_text"):
        pr, kind = parse_price_text(g("price_text"), ctx, site), "text"
    cross = None
    if kind == "tiers" and g("price_text"):
        cross = parse_price_text(g("price_text"), ctx, site)
        if cross["status"] != "error" and pr["min"] is not None and cross["currency"] == pr["currency"] \
                and (cross["min"], cross["max"]) != (pr["min"], pr["max"]) and cross["kind"] == "range":
            pr["reviews"].append(f"가격 글자 범위({cross['min']:g}~{cross['max']:g})와 구간가 범위({pr['min']:g}~{pr['max']:g})가 다름")
            pr["status"] = "error" if pr["errors"] else "needs_review"
        elif cross["currency"] and pr["currency"] and cross["currency"] != pr["currency"]:
            pr["warnings"].append(f"가격 글자 '{cross['raw']}'({f.get('price_text', {}).get('source')})는 화면 구간가({pr['currency']})와 "
                                  f"통화가 달라 입력표에 쓰지 않음 (사이트 기준 통화 값으로 보임)")
    if kind == "text" and ctx and pr["currency"] and pr["currency"] != ctx.upper():
        pr["reviews"].append(f"화면 표시 통화({ctx}) 가격을 못 뽑고 다른 통화({pr['currency']}) 가격만 있음 "
                             f"(출처 {f.get('price_text', {}).get('source')}) → 화면 가격을 사람이 확인")
        pr["status"] = "error" if pr["errors"] else "needs_review"
    if pr and pr["status"] != "error" and pr.get("min") is not None:
        v["price_min"], v["price_max"] = num_str(pr["min"]), num_str(pr["max"])
        v["currency"] = pr["currency"] or ""
        if kind == "tiers":
            v["price_note"] = "구간가 " + " / ".join(f"{t['quantity']['raw']} {t['price']['raw']}" for t in pr["tiers"])
        else:
            v["price_note"] = f"가격 글자 {pr['raw']}"
            src = (f.get("price_text") or {}).get("source") or ""
            if re.search(r"promotion|discount", src, re.I):   # 할인가면 같은 묶음의 할인 전 범위도 적는다
                parent = src.split(":", 1)[-1].rsplit(".", 1)[0]
                orig = next((c["value"] for c in (cap.get("price_candidates") or {}).get("page_data") or []
                             if c["path"].rsplit(".", 1)[0] == parent and c["path"].endswith("priceRangeText")), None)
                v["price_note"] = f"할인가 {pr['raw']}" + (f" (할인 전 {orig})" if orig else "")
        if moq:
            v["price_note"] += f" (MOQ {moq})"
    plaus = check_plausibility(pr["min"] if pr else None, pr["max"] if pr else None, pr["currency"] if pr else None, rates)
    rep.update(price=pr, price_kind=kind, plausibility=plaus, moq=moq)

    # ---- 옵션·속성
    v["options"] = "; ".join(f"{o['name']}={'/'.join(o['values'])}" for o in cap.get("options") or [])
    attrs = cap.get("attributes") or []
    mats: list[str] = []   # '소재'·'재질'처럼 소재 속성이 여러 칸이면 모두 합친다
    for a in find_attrs(attrs, "material"):
        for m in (x.strip() for x in re.split(r"[;,/]|\band\b", a["value"])):
            if m and m not in mats:
                mats.append(m)
    if mats:
        v["material"] = ";".join(mats)
    for a in find_attrs(attrs, "breed_size"):
        if re.search(r"대형|large|big", a["value"], re.I):
            rep["notes"].append(f"속성 '{a['name']}: {a['value']}'에 대형 표기 있음 → large_dog_label 판단 참고 (입력표에는 사람이 기록)")
    size = find_attr(attrs, "size")
    if size:
        m = DIM_RE.search(size)
        if m:
            v["length"], v["width"] = m.group(1), m.group(2)
            v["height"] = m.group(3) or ""
            v["dim_unit"] = {"inch": "in", "inches": "in"}.get(m.group(4).lower(), m.group(4).lower())
        else:
            rep["notes"].append(f"크기 속성 '{size}'을 치수로 읽지 못해 빈칸 (옵션 사이즈일 수 있음)")
    wt = find_attr(attrs, "weight")
    if wt:
        m = WEIGHT_RE.search(wt)
        if m:
            v["weight"], v["weight_unit"] = m.group(1), {"lbs": "lb"}.get(m.group(2).lower(), m.group(2).lower())
        else:
            rep["notes"].append(f"무게 속성 '{wt}'을 읽지 못해 빈칸")
    pw = find_attr(attrs, "pet_weight")
    if pw and (m := WEIGHT_RE.search(pw)):
        v["pet_weight_max"], v["pet_weight_unit"] = m.group(1), {"lbs": "lb"}.get(m.group(2).lower(), m.group(2).lower())
    v["package_size"] = find_attr(attrs, "package_size") or ""
    v["package_weight"] = find_attr(attrs, "package_weight") or ""

    # 옵션 이름 안의 치수: 속성에 상품 치수가 없을 때 가장 큰 옵션을 대표 치수로 (대형견 PoC 기준, 사람이 바꿀 수 있음)
    dims = option_dims(cap.get("options") or [])
    rep["option_dims"] = dims
    if dims:
        listing = ", ".join(f"{d['label']} {num_str(d['length'])}×{num_str(d['width'])}×{num_str(d['height'])}"
                            + (f"/{num_str(d['height2'])}" if d["height2"] else "") + d["unit"] for d in dims)
        if not v.get("length"):
            big = max(dims, key=lambda d: d["length"] * d["width"])
            v["length"], v["width"], v["height"] = num_str(big["length"]), num_str(big["width"]), num_str(big["height"])
            v["dim_unit"] = big["unit"]
            v["size_note"] = (f"옵션별 치수: {listing}. 대표 치수는 가장 큰 옵션({big['label']})을 자동 선택 (대형견 PoC 기준, 사람 확인)"
                              + (f". 높이 {num_str(big['height'])}/{num_str(big['height2'])}는 앞 숫자를 씀" if big["height2"] else ""))
        else:
            v["size_note"] = f"옵션별 치수: {listing}"

    # 대형견 표기: 제목·속성(적용 대상·품종 크기)에 large/대형이 있으면 "예" + 근거. 없으면 비워 사람이 판단 ("아니오"는 자동으로 쓰지 않음)
    evidence = []
    if re.search(r"\blarge\b|\bbig\b|대형", v["original_name"], re.I):
        evidence.append("제목")
    for a in attrs:
        if re.search(ATTR_RULES["breed_size"] + r"|applicable pet|suitable for|적용 대상", a["name"], re.I) \
                and re.search(r"\blarge\b|\bbig\b|대형", a["value"], re.I):
            evidence.append(f"속성 '{a['name']}: {a['value']}'")
    if evidence:
        v["large_dog_label"] = "예"
        rep["notes"].append(f"대형견 표기 '예' 자동 기록 (근거: {', '.join(evidence)})")

    # 배송 상자 글자 → 배송 방법·배송비 (v0.4.0 이상 추출본)
    ship_txt = g("shipping_text")
    rep["shipping"] = None
    if ship_txt:
        sh = parse_shipping(ship_txt, cap.get("shipping_candidates"))
        rep["shipping"] = sh
        method = sh["method"] or ""
        extra = []
        if sh["per_qty"]:
            extra.append(f"배송비는 {sh['per_qty']}개 기준")
        if sh["fee_original"] is not None:
            extra.append(f"할인 전 {money(sh['fee_original'], sh['currency'])}")
        if sh["free_upto"]:
            extra.append(f"무료 배송 최대 {sh['free_upto']}")
        if sh["delivery"]:
            extra.append(f"도착 보장 {sh['delivery']}")
        if sh["carrier_from"] and sh["carrier_from"] != "text":
            rep["notes"].append(f"물류 '{sh['carrier']}'는 배송 상자 글자가 아니라 {sh['carrier_from']}에서 읽음")
        if sh["fee"] is not None and sh["fee_original"] and sh["fee"] < sh["fee_original"] * 0.5:
            rep["notes"].append(f"배송비 할인 폭이 큼 ({money(sh['fee_original'], sh['currency'])} → {money(sh['fee'], sh['currency'])}). 첫 주문 할인 같은 조건인지 사람 확인")
        v["shipping_method"] = (method + (f" ({', '.join(extra)})" if extra else "")).strip()
        if sh["fee"] is not None:
            v["shipping_fee"], v["shipping_currency"] = num_str(sh["fee"]), sh["currency"] or ""
        elif sh["free_upto"]:
            v["shipping_fee"], v["shipping_currency"] = "0", sh["currency"] or ""
            rep["notes"].append(f"배송비 숫자가 없고 무료 배송({sh['free_upto']} 한도)만 있어 배송비 0으로 기록")
        if not method:
            rep["notes"].append(f"배송 상자에서 배송 방법을 못 읽음: '{sh['raw'][:80]}'")
        if ctx and sh["currency"] and sh["currency"] != ctx.upper():
            rep["notes"].append(f"배송비 통화({sh['currency']})가 화면 통화({ctx})와 다름")

    # ---- 그 밖의 사실 값
    for k in ("sales_count", "rating", "review_count"):
        v[k] = g(k).replace(",", "")
    # 평점이 스토어(공급업체) 평가에서 나왔으면 상품 값이 아니므로 비운다 (v0.2.0 이하 추출본 대응)
    rsrc = (f.get("rating") or {}).get("source") or ""
    if v["rating"] and STORE_SRC.search(rsrc):
        rep["notes"].append(f"평점 {v['rating']}은 스토어 평가({rsrc})라 비움")
        v["rating"] = ""
        if v["review_count"] and (f.get("review_count") or {}).get("source") == "text":
            rep["notes"].append(f"리뷰 수 {v['review_count']}도 스토어 리뷰 수일 수 있어 비움 (사람 확인)")
            v["review_count"] = ""
    if v["review_count"] and not v["rating"] and (f.get("review_count") or {}).get("source") == "text":
        rep["notes"].append(f"리뷰 수 {v['review_count']}는 상품 평점 없이 화면 글자에서만 찾은 값이라 비움 (스토어 리뷰 수일 수 있음, 사람 확인)")
        v["review_count"] = ""
    v["supplier_name"] = g("supplier_name")
    v["collected_at"] = (cap.get("captured_at") or "")[:16].replace("T", " ")
    tool = cap.get("tool", {})
    v["collector"] = (f"{cap.get('collector') or '확인자 미기재'} (확장 프로그램 {tool.get('name', '?')} "
                      f"{tool.get('version', '?')} 추출, 저장 전 사람 확인)")
    rep["images"] = len(cap.get("image_urls") or [])
    rep["edited_fields"] = cap.get("edited_fields") or []
    rep["capture_mode"] = cap.get("capture_mode")
    return v, rep


def _mat_keys(s: str) -> set[str]:
    out = set()
    for m in (x.strip().lower() for x in s.split(";") if x.strip()):
        out.add(next((k for k, syns in MATERIALS.items() if m == k or m in syns), m))
    return out


def _kg(s: str) -> float | None:
    m = WEIGHT_RE.search(s or "")
    if not m:
        return None
    return float(m.group(1)) * {"kg": 1, "g": 0.001, "lb": 0.453592, "lbs": 0.453592, "oz": 0.0283495}[m.group(2).lower()]


def compare(key: str, human: str, cap: str) -> str:
    if human == "":
        return "비교 안 함 (사람 값 없음)"
    if human == "없음":
        return "일치 (둘 다 없음)" if cap == "" else "불일치 (사람은 '없음')"
    if cap == "":
        return "확장 못 찾음"
    if key in NUMERIC_KEYS:
        try:
            same = abs(float(human.replace(",", "")) - float(cap)) < 1e-6
        except ValueError:
            same = False
    elif key == "material" and MATERIALS:
        same = _mat_keys(human) == _mat_keys(cap)
    elif key == "package_size":
        norm = lambda s: re.sub(r"\s+", "", s.lower().replace("×", "x").replace("*", "x"))
        same = norm(human) == norm(cap)
    elif key == "package_weight":
        a, b = _kg(human), _kg(cap)
        same = a is not None and b is not None and abs(a - b) < 1e-6
    else:
        same = re.sub(r"\s+", " ", human).strip().casefold() == re.sub(r"\s+", " ", cap).strip().casefold()
    return "일치" if same else "불일치"


def render_report(results: list[tuple[dict, dict, dict]], files: list[str], rate_note: str) -> str:
    L = ["# A02-02 확장 프로그램 추출 검사 보고서", "",
         f"- 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
         f"- 추출본: {', '.join(files)}",
         f"- 환율: {rate_note}",
         "- 빈칸은 확장이 못 찾은 값이다. a02_build_product.py에서 `manual_review_required`(사람 확인 전)로 처리된다.",
         "- 이미지는 주소만 추출본에 남기고 입력표에는 넣지 않았다 (W1-07 1.1절, usage = needs_review).", ""]
    for v, rep, human in results:
        pr, pl = rep["price"], rep["plausibility"]
        L += [f"## {rep['product_id']}", "",
              f"- 출처: {v['source_url']}", f"- 추출 시각: {v['collected_at']} · 방식: {rep['capture_mode']}",
              f"- 사람이 고친 칸: {', '.join(rep['edited_fields']) or '없음'} · 이미지 주소 {rep['images']}개", "",
              "### 가격 검사", ""]
        if pr is None:
            L += ["- 가격을 찾지 못함 → 사람 확인 필요", ""]
        else:
            L += [f"- 판정: **{pr['status']}** ({'수량별 구간가' if rep['price_kind'] == 'tiers' else '가격 글자'})",
                  f"- 통화: {pr['currency'] or '판별 못 함'}"
                  + (f" (근거: {pr.get('currency_basis') or pr['tiers'][0]['price']['currency_basis']})" if pr['currency'] else ""),
                  f"- 최저~최고: {num_str(pr['min'])} ~ {num_str(pr['max'])}" + (f" · MOQ {rep['moq']}" if rep['moq'] else "")]
            if rep["price_kind"] == "tiers":
                L += ["", "| 수량 | 가격 | 읽은 값 | 판정 |", "|---|---|---|---|"]
                for t in pr["tiers"]:
                    q, p = t["quantity"], t["price"]
                    qs = (f"{q['min']} 이상" if q["open_ended"] else f"{q['min']}~{q['max']}" if q["max"] is not None
                          else f"{q['min']}~(끝 미표시)")
                    L.append(f"| {q['raw']} | {p['raw']} | {qs} · {num_str(p['min'])} {p['currency'] or '?'} | {p['status']} |")
                L.append("")
            for title, key in (("오류", "errors"), ("사람 확인 필요", "reviews"), ("참고", "warnings")):
                if pr[key]:
                    L += [f"- {title}:"] + [f"  - {x}" for x in pr[key]]
        L.append(f"- 원화 상식선: " + (f"{pl['krw_min']:,}원 ~ {pl['krw_max']:,}원 (환율 {pl['rate']:g})" if pl["checked"] else "검사 생략")
                 + ("".join(f" / {x}" for x in pl["reviews"] + pl["warnings"])))
        blanks = [k for k in ("original_name", "price_min", "currency", "options", "material", "length", "weight",
                              "sales_count", "rating", "review_count", "supplier_name", "shipping_method", "shipping_fee",
                              "large_dog_label", "product_use", "package_size", "package_weight") if not v.get(k)]
        L += ["", "### 빈칸 (사람 확인 필요)", "", "- " + (", ".join(blanks) or "없음")]
        L += [f"- {n}" for n in rep["notes"]]
        rows = [(k, human.get(k, ""), v.get(k, ""), compare(k, human.get(k, ""), v.get(k, ""))) for k in COMPARE_KEYS]
        judged = [r for r in rows if not r[3].startswith("비교 안 함")]
        same = sum(1 for r in judged if r[3].startswith("일치"))
        L += ["", f"### 사람 입력값과 비교 (일치 {same}/{len(judged)})", "", "| 항목 | 사람 입력 | 확장 추출 | 결과 |", "|---|---|---|---|"]
        L += [f"| {k} | {h or '·'} | {c or '·'} | {r} |" for k, h, c, r in rows]
        L.append("")
    return "\n".join(L) + "\n"


def run(capture_paths: list[Path], template: Path, out_csv: Path, report: Path, rates: dict, rate_note: str) -> list:
    rows, human = read_template(template)
    caps = [json.loads(p.read_text(encoding="utf-8")) for p in capture_paths]
    seen = set()
    results = []
    for cap in caps:
        pid = cap.get("product_id")
        if not pid:
            raise SystemExit(f"product_id 없음: 확장 팝업에서 상품 ID를 고르고 저장했는지 확인 ({cap.get('source_url')})")
        if pid in seen:
            raise SystemExit(f"같은 상품 ID 추출본이 두 개: {pid} (최신 것 하나만 넣기)")
        seen.add(pid)
        v, rep = build_column(cap, human.get(pid, {}), rates)
        results.append((v, rep, human.get(pid, {})))
    header = ["key", rows[0][1]] + [f"{rep['product_id']} (확장 추출 {v['collected_at']})" for v, rep, _ in results]
    out = [header] + [[r[0], r[1]] + [v.get(r[0], "") for v, _, _ in results] for r in rows[1:]]
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(out)
    report.write_text(render_report(results, [p.name for p in capture_paths], rate_note), encoding="utf-8")
    return results


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    results: list[tuple[str, bool]] = []

    def check(name: str, cond) -> None:
        results.append((name, bool(cond)))

    tdir = HERE / "a02_capture_ext" / "test"
    caps = [tdir / "sample_capture_prod-w2-01.json", tdir / "sample_capture_prod-w2-09.json"]
    template = HERE / "W2-A02-02_FACTS_INPUT.csv"
    with tempfile.TemporaryDirectory() as td:
        out_csv, report = Path(td) / "facts.csv", Path(td) / "report.md"
        res = run(caps, template, out_csv, report, {"USD:KRW": 1400.0}, "테스트용 고정 환율(실제 환율 아님)")
        v1, r1, _ = res[0]
        v9, r9, _ = res[1]
        check("01 구간가 → 최저·최고·통화", (v1["price_min"], v1["price_max"], v1["currency"]) == ("3735", "4427", "KRW"))
        check("01 가격 판정 ok", r1["price"]["status"] == "ok")
        check("01 price_note 에 구간·MOQ", v1["price_note"].startswith("구간가 100 - 799 pieces ₩4,427") and "(MOQ 100)" in v1["price_note"])
        check("01 소재 ; 로 구분", v1["material"] == "Nylon;Polyester")
        check("01 크기 60x40x10 cm", (v1["length"], v1["width"], v1["height"], v1["dim_unit"]) == ("60", "40", "10", "cm"))
        check("01 무게 0.45 kg", (v1["weight"], v1["weight_unit"]) == ("0.45", "kg"))
        check("01 포장 크기·총중량", v1["package_size"] == "20X25X15 cm" and v1["package_weight"] == "1.500 kg")
        check("01 배송 글자 없으면 배송 빈칸", not v1.get("shipping_method") and not v1.get("shipping_fee"))
        check("01 제목에 Large Dogs → 대형견 표기 '예' + 근거", v1["large_dog_label"] == "예" and any("근거: 제목" in n for n in r1["notes"]))
        check("01 category_id 는 입력표에서", v1["category_id"] == "pet_harness")
        check("01 확인 일시 형식", v1["collected_at"] == "2026-11-17 10:00")
        check("09 USD 구간가", (v9["price_min"], v9["price_max"], v9["currency"]) == ("2.5", "3.8", "USD"))
        check("09 가격 글자와 구간가 범위 일치", r9["price"]["status"] == "ok")
        check("09 옵션 형식", v9["options"] == "Color=Blue/Orange")
        check("09 무게 180 g", (v9["weight"], v9["weight_unit"]) == ("180", "g"))
        check("09 원화 상식선 검사 (환율 있음)", r9["plausibility"]["checked"] and not r9["plausibility"]["reviews"])

        # 뒤 단계(a02_build_product)가 이 CSV를 그대로 읽는지
        import a02_build_product as b
        facts = b.read_facts(out_csv)
        check("입력표 형식으로 다시 읽힘", set(facts) == {"prod-w2-01", "prod-w2-09"})
        doc = b.build("prod-w2-01", facts["prod-w2-01"])
        check("W1-04 상품 JSON 생성", doc["product"]["original_price"] == {"amount": 3735.0, "currency": "KRW"})
        check("못 찾은 배송 방법 → manual_review_required",
              any(m["field_path"] == "product.shipping.method" and m["reason"] == "manual_review_required" for m in doc["missing_fields"]))

        text = report.read_text(encoding="utf-8")
        check("보고서: 사람 값 비교 표", "### 사람 입력값과 비교" in text)
        check("보고서: 소재 동의어 비교 (폴리아미드=Nylon)", MATERIALS == {} or "| material | 폴리아미드;폴리에스터 | Nylon;Polyester | 일치 |" in text)
        check("보고서: 가격 일치 (사람 3735 = 확장 3735)", "| price_min | 3735 | 3735 | 일치 |" in text)

        # 음성: 구간이 겹치면 가격 칸을 비우고 오류를 보고
        bad = json.loads(caps[0].read_text(encoding="utf-8"))
        bad["price_tiers"][1]["quantity_text"] = "700 - 4999 pieces"
        bp = Path(td) / "bad.json"
        bp.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        res = run([bp], template, out_csv, report, {}, "없음")
        vb, rb, _ = res[0]
        check("음성: 구간 겹침 → 가격 빈칸", vb.get("price_min", "") == "" and rb["price"]["status"] == "error")
        # 음성: 통화 기호가 모호하고 설정도 없으면 통화 빈칸
        amb = json.loads(caps[0].read_text(encoding="utf-8"))
        amb["price_tiers"] = []
        amb["fields"]["price_text"]["value"] = "¥108"
        amb["fields"]["currency_setting"] = {"value": None, "source": None}
        bp.write_text(json.dumps(amb, ensure_ascii=False), encoding="utf-8")
        va, ra, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("음성: ¥ 모호 → 숫자만 넣고 통화 빈칸·확인 필요", va["price_min"] == "108" and va["currency"] == "" and ra["price"]["status"] == "needs_review")
        # 음성: 가격 글자 범위와 구간가 범위가 다르면 확인 필요
        diff = json.loads(caps[1].read_text(encoding="utf-8"))
        diff["fields"]["price_text"]["value"] = "USD 2.00 - 3.80"
        bp.write_text(json.dumps(diff, ensure_ascii=False), encoding="utf-8")
        _, rd, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("음성: 가격 글자·구간가 범위 다름 → needs_review", rd["price"]["status"] == "needs_review")

        # 한국어 페이지 형태 (2026-11-17 실제 추출에서 확인된 모양을 지어낸 값으로 재현)
        ko = json.loads(caps[0].read_text(encoding="utf-8"))
        ko["fields"]["original_name"]["value"] = "대형 개 리프트 하네스 - Buy  Product on Alibaba.com"
        ko["fields"]["price_text"] = {"value": "USD 2.7", "source": "jsonld"}
        ko["attributes"] = [{"name": "소재", "value": "폴리아미드"}, {"name": "재질", "value": "폴리에스터"},
                            {"name": "단일 패키지 크기", "value": "20X25X15 cm"}, {"name": "단일 총 중량", "value": "1.500 kg"},
                            {"name": "품종 크기", "value": "대형, 중간, 작은"}]
        bp.write_text(json.dumps(ko, ensure_ascii=False), encoding="utf-8")
        vk, rk, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("한국어: 소재·재질 두 칸 합침", vk["material"] == "폴리아미드;폴리에스터")
        check("한국어: 단일 패키지 크기·단일 총 중량", vk["package_size"] == "20X25X15 cm" and vk["package_weight"] == "1.500 kg")
        check("제목 끝 ' - Buy … on Alibaba.com' 제거", vk["original_name"] == "대형 개 리프트 하네스")
        check("한국어 제목·대형 표기 메모", any("한국어" in n for n in rk["notes"]) and any("대형 표기" in n for n in rk["notes"]))
        check("JSON-LD USD 가격은 구간가(KRW)와 통화 달라 참고만",
              rk["price"]["status"] == "ok" and vk["currency"] == "KRW" and any("통화가 달라" in w for w in rk["price"]["warnings"]))

        # 2026-11-18 세 상품 추출에서 확인된 문제 (지어낸 값으로 재현)
        rg = json.loads(caps[0].read_text(encoding="utf-8"))
        rg["fields"]["original_name"]["value"] = "Long-Lasting Washable Bed - Buy Long-lasting Bed Product on Alibaba.com"
        rg["price_tiers"] = []
        rg["fields"]["price_text"] = {"value": "USD 8.23", "source": "jsonld"}
        rg["fields"]["rating"] = {"value": "4.8", "source": "page_data:detailData.globalData.review.storeReview.averageStar"}
        rg["fields"]["review_count"] = {"value": "1710", "source": "text"}
        bp.write_text(json.dumps(rg, ensure_ascii=False), encoding="utf-8")
        vg, rgr, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("제목 속 하이픈(Long-Lasting)에서 자르지 않음", vg["original_name"] == "Long-Lasting Washable Bed")
        check("스토어 평점·리뷰 수는 비움", vg["rating"] == "" and vg["review_count"] == "" and any("스토어" in n for n in rgr["notes"]))
        check("화면 통화(KRW) 없이 USD만 → 확인 필요",
              rgr["price"]["status"] == "needs_review" and any("화면 표시 통화" in x for x in rgr["price"]["reviews"]))

        # v0.4.0: 배송 상자 글자·옵션 치수 (지어낸 값)
        sp = json.loads(caps[1].read_text(encoding="utf-8"))
        sp["fields"]["shipping_text"] = {"value": "배송 스탠더드 Alibaba.com Logistics 배송비: 100개당 ₩442,283 무료 배송 최대한도 ₩27,236",
                                         "source": "dom:shipping-box"}
        sp["options"] = [{"name": "Size", "values": ["M: 54*43*18/13cm", "L: 67*50*18/13cm"]}]
        sp["attributes"] = [a for a in sp["attributes"] if a["name"] != "Size"]
        bp.write_text(json.dumps(sp, ensure_ascii=False), encoding="utf-8")
        vs, rs, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("배송: 방법·배송비(100개 기준)·무료 배송 한도", vs["shipping_method"] == "스탠더드 Alibaba.com Logistics (배송비는 100개 기준, 무료 배송 최대 ₩27,236)"
              and (vs["shipping_fee"], vs["shipping_currency"]) == ("442283", "KRW"))
        check("옵션 치수 → 가장 큰 옵션(L)을 대표 치수로", (vs["length"], vs["width"], vs["height"], vs["dim_unit"]) == ("67", "50", "18", "cm")
              and "가장 큰 옵션(L)" in vs["size_note"] and "M 54×43×18/13cm" in vs["size_note"])
        fr = json.loads(caps[0].read_text(encoding="utf-8"))
        fr["fields"]["shipping_text"] = {"value": "Shipping Free shipping up to ₩27,236 Standard Alibaba.com Logistics", "source": "dom:shipping-box"}
        fr["fields"]["original_name"]["value"] = "TEST Small Pet Collar"
        bp.write_text(json.dumps(fr, ensure_ascii=False), encoding="utf-8")
        vf, rf, _ = run([bp], template, out_csv, report, {}, "없음")[0]
        check("배송비 숫자 없이 무료 배송만 → 0 + 메모", vf["shipping_fee"] == "0" and any("무료 배송" in n for n in rf["notes"]))
        check("대형 표기 없으면 '아니오'로 단정하지 않고 빈칸", vf.get("large_dog_label", "") == "")

    real = HERE / "a02_captures" / "prod-w2-01_capture_20261117-0921.json"
    if real.exists():   # 첫 실사용 추출본(v0.1.0) 회귀 확인
        with tempfile.TemporaryDirectory() as td:
            vr, rr, _ = run([real], template, Path(td) / "f.csv", Path(td) / "r.md", {}, "없음")[0]
        check("실제 추출본: KRW 구간가 3677~4358", (vr["price_min"], vr["price_max"], vr["currency"], rr["price"]["status"]) == ("3677", "4358", "KRW", "ok"))
        check("실제 추출본: 소재 2개·공급처·리뷰 수", vr["material"] == "폴리아미드;폴리에스터" and vr["review_count"] == "13"
              and vr["supplier_name"].startswith("Chaozhou"))
    r07 = HERE / "a02_captures" / "prod-w2-07_capture_20261118-0947.json"
    r09 = HERE / "a02_captures" / "prod-w2-09_capture_20261118-0947.json"
    if r07.exists() and r09.exists():   # v0.3.0 범위가 상품 회귀 확인
        with tempfile.TemporaryDirectory() as td:
            (v7, p7, _), (v9, p9, _) = run([r07, r09], template, Path(td) / "f.csv", Path(td) / "r.md", {}, "없음")
        check("실제 07: 할인 범위가 KRW·할인 전 범위 메모", (v7["price_min"], v7["price_max"], v7["currency"]) == ("10125", "11628", "KRW")
              and "할인 전 ₩11,245-12,926" in v7["price_note"] and p7["price"]["status"] == "ok")
        check("실제 07: 상품 평점 없음 → 글자에서 찾은 리뷰 수(스토어) 비움", v7["rating"] == "" and v7["review_count"] == "")
        check("실제 07: 옵션 치수 L 67×50×18cm (11/09 사람 입력과 같음)", (v7["length"], v7["width"], v7["height"], v7["dim_unit"]) == ("67", "50", "18", "cm"))
        check("실제 07·09: 대형견 표기 '예' (제목 For Large Dogs)", v7["large_dog_label"] == "예" and v9["large_dog_label"] == "예")
    s01, s07, s09 = (HERE / "a02_captures" / f"prod-w2-0{n}_capture_20261118-1007.json" for n in (1, 7, 9))
    if s01.exists() and s07.exists() and s09.exists():   # v0.4.0 배송 상자 회귀 확인
        with tempfile.TemporaryDirectory() as td:
            (a1, _, _), (a7, b7, _), (a9, _, _) = run([s01, s07, s09], template, Path(td) / "f.csv", Path(td) / "r.md", {}, "없음")
        check("실제 v0.4 01: 배송 Standard·₩444,021(100개 기준)·할인 전·도착 보장",
              a1["shipping_method"].startswith("Standard Alibaba.com Logistics (배송비는 100개 기준, 할인 전 ₩471,347")
              and (a1["shipping_fee"], a1["shipping_currency"]) == ("444021", "KRW") and "Nov 26 - Dec 28" in a1["shipping_method"])
        check("실제 v0.4 07: Economy ₩766(10개 기준) + 할인 폭 확인 메모", a7["shipping_fee"] == "766" and a7["shipping_method"].startswith("Economy")
              and any("할인 폭" in n for n in b7["notes"]))
        check("실제 v0.4 09: ₩217,816(200개 기준)", a9["shipping_fee"] == "217816" and "200개 기준" in a9["shipping_method"])
        check("실제 09: 범위가 KRW·상품명 온전", (v9["price_min"], v9["price_max"], v9["currency"]) == ("2528", "5056", "KRW")
              and v9["original_name"].startswith("Long-lasting Interactive Dog Toy"))

    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} PASS")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="확장 프로그램 추출본 → A02-02 입력표 형식 CSV + 검사 보고서")
    ap.add_argument("captures", nargs="*", type=Path)
    ap.add_argument("--template", type=Path, default=HERE / "W2-A02-02_FACTS_INPUT.csv")
    ap.add_argument("--out", type=Path, default=HERE / "W2-A02-02_FACTS_CAPTURE.csv")
    ap.add_argument("--report", type=Path, default=HERE / "W2-A02-02_CAPTURE_CHECK.md")
    ap.add_argument("--rate", action="append", default=[], help="예: USD:KRW=1400")
    ap.add_argument("--rate-source", help="환율 출처와 기준일")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test or not a.captures:
        return self_test()
    rates = {}
    for r in a.rate:
        k, val = r.split("=", 1)
        rates[k.strip().upper()] = float(val)
    note = (", ".join(a.rate) + f" ({a.rate_source or '출처 미기재'})") if rates else "입력 없음 (KRW 외 상식선 검사 생략)"
    res = run(a.captures, a.template, a.out, a.report, rates, note)
    for v, rep, _ in res:
        pr = rep["price"]
        print(f"{rep['product_id']}: 가격 {pr['status'] if pr else '못 찾음'}, 빈칸 "
              f"{sum(1 for k in COMPARE_KEYS if not v.get(k))}개 → {a.out.name}")
    print(f"보고서: {a.report}")
    print(f"다음: python {HERE / 'a02_build_product.py'} --facts {a.out} --out-dir <출력 폴더>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
