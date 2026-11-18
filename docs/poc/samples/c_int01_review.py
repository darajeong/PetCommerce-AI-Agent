"""C-INT-01 콘텐츠 검수: 생성 문장 1차 자동 표시 + 사람 검수 결과 점검 (W4, 주 담당 A, 2026-11-18 틀).

    # 1) C02-02 결과를 문장으로 나누고 1차 자동 표시 → 사람이 채울 검수표 CSV
    python docs/poc/samples/c_int01_review.py prepare --content <C02-02 결과.json|csv> \
        --facts <W1-04 상품 JSON> [<W1-04 상품 JSON> ...] --out W4-C-INT-01_REVIEW.csv [--summary 요약.md]
    # 2) 사람이 label·publish 등을 채운 검수표가 완료 기준을 지키는지 점검
    python docs/poc/samples/c_int01_review.py check --review W4-C-INT-01_REVIEW.csv [--summary 결과.md]
    python docs/poc/samples/c_int01_review.py --self-test

분류 4가지 (WBS C-INT-01): 사실 · 추정 · 금지 표현 · 확인 필요. 우선순위는 금지 표현 > 확인 필요 > 사실 > 추정.
- 자동 표시는 1차 후보일 뿐이다. 최종 분류(label)는 사람이 정하고, check 단계에서 완료 기준을 점검한다.
- 완료 기준: 미분류 0건, 확인 필요·금지 표현 문장의 공개 표시 0건 (+ 이 틀에서 추가: 사실·추정 문장의 근거 연결 100%).
- 합성(test) 데이터에만 근거한 문장은 사실이어도 실제 공개 불가 (W2-A02 합성 데이터 resale = prohibited).
- 금지 표현·확인 필요 규칙은 PoC용 팀 초안이며 법무 검토 전이다 (W4-C-INT-01_CONTENT_REVIEW.md §3).
- AI를 쓰지 않는다. 정해진 규칙과 W1-04 상품 JSON의 값만 비교한다.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = ("사실", "추정", "금지 표현", "확인 필요")
PUBLISH = ("공개 가능", "검토 후 공개", "공개 불가")
ACTIONS = ("유지", "수정", "삭제", "사람 확인")
COLUMNS = ["row_id", "product_id", "channel", "section", "sentence_no", "sentence",
           "auto_label", "auto_reasons", "rule_ids", "evidence_refs", "evidence_data_type",
           "label", "label_reason", "action", "publish", "reviewer", "reviewed_at"]

# ---------------------------------------------------------------- 규칙 (팀 초안, §3)
PROHIBITED = [  # (rule_id, 정규식, 이유)
    ("P01", r"최고|최상|최강|1위|넘버\s*원|유일|독보적|완벽|무조건|절대(?:로)?\s|최초", "근거 없는 최상급·단정 표현"),
    ("P02", r"100\s*%\s*(?:만족|효과|안전|보장|환불)|(?:만족|효과|안전)\S*\s*100\s*%", "100% 보장류 표현"),
    ("P03", r"치료|완치|치유|예방(?!\s*접종)|질병|질환|관절염|디스크|통증\s*(?:완화|감소|해소)|재활\s*치료|약효|면역력", "의약품이 아닌 제품의 질병 치료·예방 표방"),
    ("P04", r"최저가|파격\s*할인|폭탄\s*세일|오늘만|마감\s*임박|한정\s*수량|무료\s*배송\s*보장", "근거 없는 가격·긴급성 표현"),
    ("P05", r"타사|경쟁사|다른\s*(?:제품|브랜드)보다|짝퉁|가품", "비교·비방 표현"),
    ("P06", r"부작용\s*(?:이\s*)?없|절대\s*안전|인체\s*무해", "안전 단정 표현"),
]
CHECK = [
    ("C01", r"인증|KC|FDA|CE\s*마크|SGS|특허|시험\s*성적|검사\s*(?:완료|통과)", "인증·시험·특허 주장은 서류 확인 필요"),
    ("C02", r"수의사|전문가|임상|연구\s*결과|논문", "전문가·연구 근거 자료 필요"),
    ("C03", r"친환경|무독성|무해|BPA\s*프리|생분해|유기농", "환경·안전성 주장은 근거 자료 필요"),
    ("C04", r"국산|국내\s*(?:생산|제조)|한국\s*제조|Made\s*in\s*Korea", "원산지 주장은 원본 확인 필요"),
]
FIELD_WORDS = [  # 문장에 이 낱말이 있는데 해당 원본 값이 비어 있으면 확인 필요
    (r"(?<!포장)(?<!포장\s)(?<!패키지)(?<!패키지\s)(?:크기|사이즈|치수)|가로|세로|높이|길이", "product.dimensions"),
    (r"무게|중량", "product.weight"),
    (r"권장\s*체중|체중\s*\d|kg\s*이하\s*(?:강아지|반려견)", "product.recommended_pet_weight_max"),
    (r"배송비", "product.shipping.fee"),
    (r"판매량|\d+\s*개\s*판매", "product.sales_count"),
    (r"평점|별점", "product.rating"),
]
MATERIALS = {  # a03_normalize.MATERIALS 복사본 (main 브랜치에는 a03 가 없음). a03 를 고치면 같이 고친다
    "nylon": ["nylon", "polyamide", "나일론", "폴리아미드"],
    "polyester": ["polyester", "poly", "oxford", "oxford cloth", "폴리에스터", "폴리에스테르", "옥스포드"],
    "cotton": ["cotton", "면", "코튼"],
    "mesh": ["mesh", "air mesh", "메쉬", "메시", "에어메쉬"],
    "natural_rubber": ["natural rubber", "rubber", "천연고무", "고무"],
    "silicone": ["silicone", "food grade silicone", "실리콘", "식품 등급 실리콘", "식품등급 실리콘"],
    "eva": ["eva"],
    "tpr": ["tpr"],
    "plush": ["plush", "faux fur", "fleece", "플러시", "인조 모피", "플리스"],
    "memory_foam": ["memory foam", "foam", "메모리폼", "메모리 폼", "폼"],
}
try:
    sys.path.insert(0, str(HERE))
    from a03_normalize import MATERIALS as _M  # noqa: E402
    MATERIALS = _M
except Exception:
    pass
LEN = {"mm": 0.1, "cm": 1.0, "in": 2.54, "인치": 2.54}
WGT = {"g": 0.001, "kg": 1.0, "lb": 0.453592}
NUM_RE = re.compile(r"(₩|US\$|\$)?\s*(\d[\d,]*(?:\.\d+)?)\s*(mm|cm|kg|g|lb|in|인치|원|개|세트|점|%)?(?![A-Za-z])")
DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*X]\s*(\d+(?:\.\d+)?)(?:\s*[x×*X]\s*(\d+(?:\.\d+)?))?\s*(mm|cm|in|인치)")
QUESTION_RE = re.compile(r"(\?|까요?|나요|가요|ㄹ까|을까)\s*[?？]?\s*$")


# ---------------------------------------------------------------- 상품 원본 색인
def index_facts(doc: dict) -> dict:
    """W1-04 상품 JSON 에서 비교에 쓸 값(숫자·소재·누락 항목)을 모은다."""
    p = doc.get("product", {})
    meta = doc.get("field_meta", {})
    dt = lambda path: (meta.get(path) or {}).get("data_type") or "unknown"
    nums: list[dict] = []

    def add(v, unit, path, data_type=None):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            nums.append({"value": float(v), "unit": unit, "path": path, "data_type": data_type or dt(path)})

    price = p.get("original_price") or {}
    add(price.get("amount"), price.get("currency"), "product.original_price.amount")
    dims = p.get("dimensions") or {}
    for k in ("length", "width", "height"):
        add(dims.get(k), dims.get("unit"), f"product.dimensions.{k}", dt("product.dimensions"))
    w = p.get("weight") or {}
    add(w.get("value"), w.get("unit"), "product.weight", dt("product.weight"))
    pw = p.get("recommended_pet_weight_max")
    if isinstance(pw, dict):
        add(pw.get("value"), pw.get("unit"), "product.recommended_pet_weight_max")
    else:
        add(pw, "kg", "product.recommended_pet_weight_max")
    ship = p.get("shipping") or {}
    add(ship.get("fee"), ship.get("currency"), "product.shipping.fee")
    add(p.get("sales_count"), "개", "product.sales_count")
    add(p.get("rating"), None, "product.rating")
    for c in (doc.get("normalized_data") or {}).get("conversions") or []:
        add(c.get("normalized_value"), c.get("normalized_unit"), f"normalized:{c.get('field_path')}", c.get("data_type"))
    # A02 경고에 남은 가격 구간·MOQ 숫자 (예: "범위 3735~4427 KRW, 조건: 구간가 100개 4427 / …")
    for aid, out in (doc.get("agent_outputs") or {}).items():
        for i, wtxt in enumerate(out.get("warnings") or []):
            for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", wtxt):
                add(float(m.group().replace(",", "")), None, f"agent_outputs.{aid}.warnings[{i}]", out.get("data_type"))
    mats = {}
    for m in p.get("material") or []:
        key = _mat_key(str(m))
        mats[key] = dt("product.material")
    missing = {m["field_path"]: m["reason"] for m in doc.get("missing_fields") or []}
    for path, val in (("product.dimensions", p.get("dimensions")), ("product.weight", p.get("weight")),
                      ("product.recommended_pet_weight_max", pw), ("product.shipping.fee", ship.get("fee")),
                      ("product.sales_count", p.get("sales_count")), ("product.rating", p.get("rating"))):
        if val in (None, {}, []):
            missing.setdefault(path, "값 없음")
    return {"product_id": doc.get("product_id"), "nums": nums, "materials": mats, "missing": missing,
            "name": p.get("original_name") or ""}


def _mat_key(word: str) -> str:
    w = word.strip().lower()
    return next((k for k, syns in MATERIALS.items() if w == k or w in syns), w)


def _mat_words(sentence: str) -> list[str]:
    s = sentence.lower()
    found = []
    for key, syns in MATERIALS.items():
        for syn in sorted(syns, key=len, reverse=True):
            if len(syn) >= 2:
                hit = syn in s
            else:   # '면'처럼 한 글자는 '~하면'·'표면'과 헷갈리므로 소재 문맥일 때만 본다
                hit = re.search(rf"(?<![가-힣]){re.escape(syn)}(?=\s*(?:소재|원단|재질|혼방|\d))|순{re.escape(syn)}", s) is not None
            if hit:
                found.append(key)
                break
    return found


# ---------------------------------------------------------------- 문장 나누기·1차 표시
def split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*•·▶✔✅]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        parts = [x.strip() for x in re.split(r"(?<=[.!?。])\s+", line) if x.strip()]
        buf = ""
        for part in parts:   # "Q." 처럼 짧은 조각은 다음 조각에 붙인다
            buf = f"{buf} {part}".strip() if buf else part
            if len(buf) > 3:
                out.append(buf)
                buf = ""
        if buf:
            out.append(buf)
    return out


def _match_number(v: float, unit: str | None, facts: dict) -> dict | None:
    for n in facts["nums"]:
        fu = (n["unit"] or "").lower() if n["unit"] else None
        if unit in LEN and fu in LEN:
            if abs(v * LEN[unit] - n["value"] * LEN[fu]) < 0.05:
                return n
        elif unit in WGT and fu in WGT:
            if abs(v * WGT[unit] - n["value"] * WGT[fu]) < 0.0005:
                return n
        elif unit in ("원", "₩"):
            if fu in ("krw", None) and abs(v - n["value"]) < 0.5:
                return n
        elif unit in ("개", "세트", "점", None):
            if fu in ("개", None) and abs(v - n["value"]) < 1e-6:
                return n
    if unit in LEN or unit in WGT:   # A02 경고에 단위 없이 남은 값(포장 크기·총중량 등)과 같은 숫자
        return next((n for n in facts["nums"] if n["unit"] is None and n["path"].startswith("agent_outputs.")
                     and abs(v - n["value"]) < 1e-6), None)
    return None


def auto_review(sentence: str, facts: dict) -> dict:
    reasons, rules, evidence, ev_types = [], [], [], set()
    for rid, pat, why in PROHIBITED:
        if re.search(pat, sentence, re.I):
            reasons.append(why)
            rules.append(rid)
    prohibited = bool(rules)
    check = False
    for rid, pat, why in CHECK:
        if re.search(pat, sentence, re.I):
            reasons.append(why)
            rules.append(rid)
            check = True
    for pat, path in FIELD_WORDS:
        if re.search(pat, sentence) and path in facts["missing"]:
            reasons.append(f"원본에 없는 항목({path}: {facts['missing'][path]})")
            rules.append("C05")
            check = True
    found: list[tuple[str, str | None]] = []   # (숫자 글자, 단위)
    rest = sentence
    for m in DIM_RE.finditer(sentence):        # "20x25x15cm" → 세 숫자 모두 cm
        found += [(x, m.group(4)) for x in m.groups()[:3] if x]
        rest = rest.replace(m.group(0), " ")
    for m in NUM_RE.finditer(rest):
        pre, raw, unit = m.group(1), m.group(2), m.group(3)
        unit = "₩" if pre == "₩" else unit
        if unit is None and pre is None:
            continue   # 단위 없는 숫자(순서·개수 표현 등)는 사람이 본다
        found.append((raw, unit))
    for raw, unit in found:
        hit = _match_number(float(raw.replace(",", "")), unit, facts)
        if hit:
            evidence.append(hit["path"])
            ev_types.add(hit["data_type"])
        else:
            reasons.append(f"원본에 없는 수치({raw}{unit or ''})")
            rules.append("C06")
            check = True
    if re.search(r"무료\s*배송|배송비\s*(?:는\s*)?(?:무료|0\s*원)", sentence):
        fee = next((n for n in facts["nums"] if n["path"] == "product.shipping.fee"), None)
        if fee and fee["value"] == 0:
            evidence.append("product.shipping.fee")
            ev_types.add(fee["data_type"])
        else:
            reasons.append("무료 배송 표현인데 원본 배송비가 0이 아님·없음")
            rules.append("C06")
            check = True
    for key in _mat_words(sentence):
        if key in facts["materials"]:
            evidence.append("product.material")
            ev_types.add(facts["materials"][key])
        else:
            reasons.append(f"원본에 없는 소재({key})")
            rules.append("C07")
            check = True
    question = bool(QUESTION_RE.search(sentence))
    if prohibited:
        label = "금지 표현"
    elif check:
        label = "확인 필요"
    elif evidence:
        label = "사실"
    elif question:
        label = "사실"
        reasons.append("주장 없음(질문·제목)")
    else:
        label = "추정"
        reasons.append("원본과 직접 비교할 값이 없음 → 근거 필드를 사람이 연결")
    return {"auto_label": label, "auto_reasons": "; ".join(dict.fromkeys(reasons)), "rule_ids": ",".join(dict.fromkeys(rules)),
            "evidence_refs": ",".join(dict.fromkeys(evidence)), "evidence_data_type": ",".join(sorted(ev_types)) or ""}


def expected_publish(label: str, evidence_data_type: str, reasons: str) -> str:
    if label in ("금지 표현", "확인 필요"):
        return "공개 불가"
    if label == "추정":
        return "검토 후 공개"
    types = {t for t in evidence_data_type.split(",") if t}
    if types - {"actual"} and "주장 없음" not in reasons:
        return "공개 불가"   # 합성·Mock·출처 미상 근거는 실제 판매 콘텐츠에 쓰지 않는다
    return "공개 가능"


# ---------------------------------------------------------------- 입력 읽기
def read_content(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            items = list(csv.DictReader(f))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", data) if isinstance(data, dict) else data
    need = {"product_id", "channel", "section", "text"}
    for i, it in enumerate(items):
        if not need <= set(it):
            raise SystemExit(f"{path.name} {i + 1}번째 항목에 {sorted(need - set(it))} 없음 (입력 형식: 문서 §5)")
    return items


def prepare(content: Path, fact_paths: list[Path]) -> list[dict]:
    facts = {}
    for fp in fact_paths:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        facts[doc.get("product_id")] = index_facts(doc)
    rows = []
    for it in read_content(content):
        f = facts.get(it["product_id"])
        if f is None:
            raise SystemExit(f"상품 원본이 없음: {it['product_id']} (--facts 에 W1-04 JSON 추가)")
        for k, s in enumerate(split_sentences(it["text"]), 1):
            r = auto_review(s, f)
            rows.append({"row_id": f"{it['product_id']}-{it['channel']}-{len(rows) + 1:03d}", "product_id": it["product_id"],
                         "channel": it["channel"], "section": it["section"], "sentence_no": k, "sentence": s, **r,
                         "label": "", "label_reason": "", "action": "", "publish": "", "reviewer": "", "reviewed_at": ""})
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def prepare_summary(rows: list[dict]) -> str:
    L = ["# C-INT-01 1차 자동 표시 요약", "", "자동 표시는 후보다. 최종 분류는 검수표의 `label`에 사람이 적는다.", "",
         "| 상품 | 채널 | 문장 | 사실 | 추정 | 금지 표현 | 확인 필요 |", "|---|---|---:|---:|---:|---:|---:|"]
    for (pid, ch), grp in _group(rows).items():
        c = Counter(r["auto_label"] for r in grp)
        L.append(f"| {pid} | {ch} | {len(grp)} | " + " | ".join(str(c.get(x, 0)) for x in LABELS) + " |")
    flagged = [r for r in rows if r["auto_label"] in ("금지 표현", "확인 필요")]
    L += ["", f"## 금지 표현·확인 필요 후보 ({len(flagged)}건)", "", "| row_id | 1차 | 문장 | 이유 |", "|---|---|---|---|"]
    L += [f"| {r['row_id']} | {r['auto_label']} | {r['sentence']} | {r['auto_reasons']} |" for r in flagged]
    return "\n".join(L) + "\n"


def _group(rows):
    g: dict = {}
    for r in rows:
        g.setdefault((r["product_id"], r["channel"]), []).append(r)
    return g


# ---------------------------------------------------------------- 사람 검수 결과 점검
def check(path: Path) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    res = {"rows": len(rows), "products": sorted({r["product_id"] for r in rows}), "problems": [], "counts": Counter(),
           "agree": 0, "judged": 0}
    for r in rows:
        rid, label, pub = r["row_id"], r["label"].strip(), r["publish"].strip()
        if label not in LABELS:
            res["problems"].append((rid, "미분류" if not label else f"허용되지 않은 분류 '{label}'"))
            continue
        res["counts"][label] += 1
        res["judged"] += 1
        res["agree"] += label == r["auto_label"]
        exp = expected_publish(label, r.get("evidence_data_type", ""), r.get("auto_reasons", "") + r.get("label_reason", ""))
        if label in ("금지 표현", "확인 필요") and pub != "공개 불가":
            res["problems"].append((rid, f"{label} 문장이 '{pub or '빈칸'}'으로 표시됨 (공개 불가여야 함)"))
        elif pub not in PUBLISH:
            res["problems"].append((rid, "공개 여부 빈칸·허용되지 않은 값"))
        elif PUBLISH.index(pub) < PUBLISH.index(exp):
            res["problems"].append((rid, f"공개 여부 '{pub}'가 규칙상 '{exp}'보다 느슨함"))
        if label in ("사실", "추정") and not r["evidence_refs"].strip() and "주장 없음" not in (r["auto_reasons"] + r["label_reason"]):
            res["problems"].append((rid, f"{label} 문장인데 근거(evidence_refs) 없음"))
        if r["action"].strip() and r["action"].strip() not in ACTIONS:
            res["problems"].append((rid, f"허용되지 않은 조치 '{r['action']}'"))
        if not r["reviewer"].strip():
            res["problems"].append((rid, "검수자 빈칸"))
    unclassified = sum(1 for _, p in res["problems"] if p.startswith("미분류"))
    leaked = sum(1 for _, p in res["problems"] if "공개 불가여야 함" in p)
    no_ev = sum(1 for _, p in res["problems"] if "근거(evidence_refs) 없음" in p)
    res.update(unclassified=unclassified, leaked=leaked, no_evidence=no_ev,
               passed=unclassified == 0 and leaked == 0 and no_ev == 0 and len(res["products"]) >= 3 and not res["problems"])
    return res


def check_summary(res: dict) -> str:
    rate = f"{res['agree'] / res['judged'] * 100:.1f}%" if res["judged"] else "측정 불가"
    L = ["# C-INT-01 검수 결과 점검", "",
         f"- 판정: **{'충족' if res['passed'] else '미충족'}**",
         f"- 문장 {res['rows']}개 · 상품 {len(res['products'])}개 ({', '.join(res['products'])})",
         f"- 최종 분류: " + ", ".join(f"{k} {res['counts'].get(k, 0)}" for k in LABELS),
         f"- 미분류 {res['unclassified']}건 (기준 0) · 확인 필요·금지 표현 공개 표시 {res['leaked']}건 (기준 0) · 근거 없는 사실·추정 {res['no_evidence']}건 (기준 0)",
         f"- 자동 1차 표시와 사람 최종 분류 일치율: {rate} (참고 지표)"]
    if len(res["products"]) < 3:
        L.append("- 상품 3개 전수 검사 기준 미달")
    if res["problems"]:
        L += ["", "| row_id | 문제 |", "|---|---|"] + [f"| {a} | {b} |" for a, b in res["problems"]]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- self-test
SYN_PRODUCT = {  # 지어낸 상품 (실제 상품 값 아님)
    "product_id": "prod-test-01",
    "product": {"original_name": "TEST Large Dog Lift Harness", "original_price": {"amount": 4358.0, "currency": "KRW"},
                "options": [{"name": "색상", "value": "블랙"}], "dimensions": None, "weight": None,
                "material": ["폴리아미드", "폴리에스터"], "recommended_pet_weight_max": None, "sales_count": 8, "rating": 5.0,
                "shipping": {"method": "표준 배송", "fee": None, "currency": "KRW"}, "images": [], "reviews": []},
    "field_meta": {p: {"data_type": "actual"} for p in ("product.original_name", "product.original_price.amount",
                                                         "product.material", "product.sales_count", "product.rating")},
    "missing_fields": [{"field_path": "product.dimensions", "reason": "source_missing"},
                       {"field_path": "product.weight", "reason": "source_missing"},
                       {"field_path": "product.shipping.fee", "reason": "manual_review_required"}],
    "agent_outputs": {"A02": {"data_type": "actual", "warnings": ["가격은 최저가(3677)만 저장했다. 범위 3677~4358 KRW, 조건: 구간가 100 - 799 ₩4,358 (MOQ 100)"]}},
}
SYN_CONTENT = {"items": [
    {"product_id": "prod-test-01", "channel": "smartstore", "section": "핵심 장점",
     "text": "대형견 보행을 돕는 리프트 하네스입니다. 소재는 폴리아미드와 폴리에스터예요.\n- 관절염 치료에 효과적입니다.\n- 국내 최저가 보장!"},
    {"product_id": "prod-test-01", "channel": "smartstore", "section": "규격",
     "text": "무게는 0.5kg으로 가볍습니다. 100개부터 개당 4,358원입니다. 면 소재로 부드러워요."},
    {"product_id": "prod-test-01", "channel": "coupang", "section": "FAQ",
     "text": "Q. 세탁기에 넣어도 되나요? A. 손세탁을 권장합니다.\nKC 인증을 받은 제품입니다. 수의사가 추천하는 제품이에요. 구매자 90%가 만족했어요."},
]}


def self_test() -> int:
    results: list[tuple[str, bool]] = []

    def ok(name, cond):
        results.append((name, bool(cond)))

    ok("문장 나누기 (목록 기호·Q. 붙이기)", split_sentences("- 하나입니다. 둘이에요.\nQ. 셋인가요? A. 넷입니다.") ==
       ["하나입니다.", "둘이에요.", "Q. 셋인가요?", "A. 넷입니다."])
    with tempfile.TemporaryDirectory() as td:
        cp, fp = Path(td) / "c.json", Path(td) / "p.json"
        cp.write_text(json.dumps(SYN_CONTENT, ensure_ascii=False), encoding="utf-8")
        fp.write_text(json.dumps(SYN_PRODUCT, ensure_ascii=False), encoding="utf-8")
        rows = prepare(cp, [fp])
        by = {r["sentence"]: r for r in rows}
        a = lambda s: by[s]["auto_label"]
        ok("소재 일치 → 사실", a("소재는 폴리아미드와 폴리에스터예요.") == "사실" and "product.material" in by["소재는 폴리아미드와 폴리에스터예요."]["evidence_refs"])
        ok("질병 치료 → 금지 표현", a("관절염 치료에 효과적입니다.") == "금지 표현")
        ok("최저가 보장 → 금지 표현 (P04)", a("국내 최저가 보장!") == "금지 표현" and "P04" in by["국내 최저가 보장!"]["rule_ids"])
        ok("원본에 없는 무게 → 확인 필요", a("무게는 0.5kg으로 가볍습니다.") == "확인 필요")
        ok("MOQ·가격 숫자 일치 → 사실", a("100개부터 개당 4,358원입니다.") == "사실")
        ok("원본에 없는 소재(면) → 확인 필요", a("면 소재로 부드러워요.") == "확인 필요" and "C07" in by["면 소재로 부드러워요."]["rule_ids"])
        ok("질문 → 사실(주장 없음)", a("Q. 세탁기에 넣어도 되나요?") == "사실" and "주장 없음" in by["Q. 세탁기에 넣어도 되나요?"]["auto_reasons"])
        ok("인증 → 확인 필요", a("KC 인증을 받은 제품입니다.") == "확인 필요")
        ok("수의사 추천 → 확인 필요", a("수의사가 추천하는 제품이에요.") == "확인 필요")
        ok("원본에 없는 % → 확인 필요", a("구매자 90%가 만족했어요.") == "확인 필요")
        ok("근거 없는 일반 설명 → 추정", a("대형견 보행을 돕는 리프트 하네스입니다.") == "추정")
        ok("모든 문장에 1차 표시", all(r["auto_label"] in LABELS for r in rows) and len(rows) == 12)

        # 사람 검수 완료본 → check 통과
        for r in rows:
            r["label"] = r["auto_label"]
            r["reviewer"], r["reviewed_at"] = "A 형준", "2026-11-18"
            r["action"] = "유지" if r["label"] in ("사실", "추정") else "수정"
            if r["label"] == "추정":
                r["evidence_refs"] = "product.original_name"
            r["publish"] = expected_publish(r["label"], r["evidence_data_type"], r["auto_reasons"])
        rp = Path(td) / "review.csv"
        write_csv(rows, rp)
        res = check(rp)
        ok("완료본 점검: 문제 0건 (상품 1개라 판정은 미충족)", not res["problems"] and not res["passed"] and res["agree"] == 12)
        # 음성: 미분류 1건, 확인 필요를 공개 가능으로, 추정 근거 없음
        rows[0]["label"] = ""
        bad = next(r for r in rows if r["label"] == "확인 필요")
        bad["publish"] = "공개 가능"
        est = next(r for r in rows if r["label"] == "추정")
        est["evidence_refs"] = ""
        write_csv(rows, rp)
        res = check(rp)
        ok("음성: 미분류 검출", res["unclassified"] == 1)
        ok("음성: 확인 필요 공개 표시 검출", res["leaked"] == 1)
        ok("음성: 근거 없는 추정 검출", res["no_evidence"] >= 1)
        ok("합성 근거 사실은 공개 불가", expected_publish("사실", "test", "") == "공개 불가"
           and expected_publish("사실", "actual", "") == "공개 가능")
        ok("요약 표 생성", "| prod-test-01 | smartstore |" in prepare_summary(prepare(cp, [fp])))
        ok("점검 요약 생성", "판정: **미충족**" in check_summary(res))

    # 실제 A02 출력 모양 (2026-11-18 PR #12 prod-w2-01 JSON으로 확인한 경우를 지어낸 값으로 재현)
    f2 = index_facts({**SYN_PRODUCT, "product": {**SYN_PRODUCT["product"], "shipping": {"method": "표준", "fee": 0.0, "currency": "KRW"}},
                      "missing_fields": SYN_PRODUCT["missing_fields"][:2],
                      "agent_outputs": {"A02": {"data_type": "actual", "warnings": ["포장 정보: 크기 20x25x15 cm, 총중량 1.5 kg"]}}})
    ok("포장 크기 AxBxCcm → 사실 (A02 경고 근거, 상품 치수 누락과 구분)", auto_review("포장 크기는 20x25x15cm입니다.", f2)["auto_label"] == "사실")
    ok("무료 배송 + 배송비 0 → 사실", auto_review("배송비는 무료입니다.", f2)["auto_label"] == "사실")
    ok("무료 배송인데 배송비 없음 → 확인 필요", auto_review("무료 배송입니다.", index_facts(SYN_PRODUCT))["auto_label"] == "확인 필요")
    ok("평점 5.0점 → 사실", auto_review("평점 5.0점이에요.", f2)["auto_label"] == "사실")
    ok("'~하면'·'표면'은 소재 '면'으로 보지 않음", _mat_words("세탁하면 표면이 매끄러워요.") == [])

    for name, good in results:
        print(f"[{'PASS' if good else 'FAIL'}] {name}")
    failed = sum(1 for _, g in results if not g)
    print(f"\n{len(results) - failed}/{len(results)} PASS")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="C-INT-01 콘텐츠 검수 (1차 자동 표시·점검)")
    sub = ap.add_subparsers(dest="cmd")
    p1 = sub.add_parser("prepare")
    p1.add_argument("--content", type=Path, required=True)
    p1.add_argument("--facts", type=Path, nargs="+", required=True)
    p1.add_argument("--out", type=Path, default=HERE / "W4-C-INT-01_REVIEW.csv")
    p1.add_argument("--summary", type=Path)
    p2 = sub.add_parser("check")
    p2.add_argument("--review", type=Path, default=HERE / "W4-C-INT-01_REVIEW.csv")
    p2.add_argument("--summary", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test or not a.cmd:
        return self_test()
    if a.cmd == "prepare":
        rows = prepare(a.content, a.facts)
        write_csv(rows, a.out)
        text = prepare_summary(rows)
        if a.summary:
            a.summary.write_text(text, encoding="utf-8")
        print(text)
        print(f"검수표: {a.out} (label·action·publish·reviewer 를 사람이 채운 뒤 check)")
        return 0
    res = check(a.review)
    text = check_summary(res)
    if a.summary:
        a.summary.write_text(text, encoding="utf-8")
    print(text)
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
