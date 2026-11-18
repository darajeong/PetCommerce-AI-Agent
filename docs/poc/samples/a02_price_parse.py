"""A02 가격·통화 파서와 범위 검사 (확장 프로그램 추출본용, 2026-11-17).

    python docs/poc/samples/a02_price_parse.py --self-test
    python docs/poc/samples/a02_price_parse.py "US$2.50 - 3.80" --site alibaba.com [--context-currency KRW]

하는 일
- 가격 문자열에서 통화를 판별한다. 통화 코드(USD·KRW 등) → 고유 기호(US$·₩·€ 등) → 페이지 통화 설정 →
  사이트 기본값 순으로 쓰고, 무엇으로 판별했는지 `currency_basis`에 남긴다. `$`·`¥`처럼 여러 통화에
  쓰이는 기호는 근거가 없으면 정하지 않는다(`needs_review`).
- 단일가, 범위(2.50 - 3.80), 수량별 구간(100 - 799 pieces / ₩4,427)을 숫자로 바꾼다.
- 검사: 0보다 큰지, 최소 ≤ 최대, 소수점 없는 통화(KRW·JPY)의 소수, 구간 수량 순서·겹침·빈 구간,
  수량이 늘 때 단가 상승, 통화 혼합, 첫 구간 수량과 MOQ 차이, 원화 환산 상식선(환율을 인자로 받은 경우만).
- 결과 `status`: ok / needs_review / error. 값을 추정해서 채우지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

KNOWN_CODES = {"USD", "KRW", "CNY", "EUR", "JPY", "GBP", "HKD", "CAD", "AUD", "TWD", "SGD", "THB", "VND", "INR"}
CODE_ALIASES = {"RMB": "CNY"}
# 한 통화로만 읽히는 기호. 긴 것부터 찾는다 (US$ 를 $ 보다 먼저).
UNIQUE_SYMBOLS = [("US$", "USD"), ("HK$", "HKD"), ("CA$", "CAD"), ("AU$", "AUD"), ("NT$", "TWD"),
                  ("CN¥", "CNY"), ("JP¥", "JPY"), ("C$", "CAD"), ("A$", "AUD"), ("S$", "SGD"),
                  ("₩", "KRW"), ("원", "KRW"), ("€", "EUR"), ("£", "GBP"), ("元", "CNY"), ("円", "JPY")]
# 여러 통화에 쓰이는 기호 (NFKC 정규화 뒤 ￥→¥, ＄→$).
AMBIGUOUS_SYMBOLS = {"$": {"USD", "CAD", "AUD", "HKD", "TWD", "SGD"}, "¥": {"CNY", "JPY"}}
# 사이트 기본 통화: 모호한 기호를 페이지 통화 설정 없이 읽을 때만 쓴다.
SITE_DEFAULTS = {"alibaba.com": {"$": "USD"}, "taobao.com": {"¥": "CNY"}, "tmall.com": {"¥": "CNY"},
                 "1688.com": {"¥": "CNY"}}
ZERO_DECIMAL = {"KRW", "JPY", "VND"}
RANGE_SEP = r"(?:-|–|—|~|〜|to)"
# 숫자: 공백 천 단위(1 234,56) 또는 일반(1,234.56 / 3,80 / 4427)
NUM_RE = re.compile(r"\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d[\d.,]*\d|\d")
PLAUSIBLE_KRW = (100, 10_000_000)   # 원화 환산 상식선 (개당 단가)
MAX_RANGE_RATIO = 20                # 최대/최소가 이보다 크면 사람 확인


def _site_key(site: str | None) -> str | None:
    if not site:
        return None
    site = site.lower()
    return next((k for k in SITE_DEFAULTS if site == k or site.endswith("." + k)), site)


def to_number(s: str, currency: str | None = None) -> tuple[float | None, list[str]]:
    """숫자 글자를 float 로 바꾼다. 읽은 방식이 애매하면 경고를 같이 돌려준다."""
    notes: list[str] = []
    s = re.sub(r"[   ']", "", s)
    has_c, has_d = "," in s, "." in s
    if has_c and has_d:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        body = s.replace(thou, "")
        if body.count(dec) != 1:
            return None, [f"숫자 형식을 읽지 못함: {s}"]
        return float(body.replace(dec, ".")), notes
    if has_c:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):
            return float(s.replace(",", "")), notes
        if re.fullmatch(r"\d+,\d{1,2}", s):
            return float(s.replace(",", ".")), ["쉼표를 소수점으로 읽음"]
        return None, [f"숫자 형식을 읽지 못함: {s}"]
    if has_d:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s) and (currency in ZERO_DECIMAL or s.count(".") > 1):
            return float(s.replace(".", "")), ["점을 천 단위 구분으로 읽음"]
        if re.fullmatch(r"\d+\.\d+", s):
            if len(s.split(".")[1]) > 2 and currency not in ZERO_DECIMAL:
                notes.append("소수 셋째 자리 이상 (천 단위 점인지 확인)")
            return float(s), notes
        return None, [f"숫자 형식을 읽지 못함: {s}"]
    return float(s), notes


def detect_currency(text: str, context_currency: str | None = None, site: str | None = None) -> dict:
    """통화를 판별한다. 반환: currency, basis, errors, reviews, warnings, stripped(통화 표시를 지운 글자)."""
    out = {"currency": None, "basis": None, "errors": [], "reviews": [], "warnings": [], "stripped": text}
    found: dict[str, str] = {}   # currency -> basis
    rest = text
    for code in re.findall(r"(?<![A-Za-z])([A-Z]{3})(?![A-Za-z])", rest):
        cur = CODE_ALIASES.get(code, code)
        if cur in KNOWN_CODES:
            found.setdefault(cur, "code")
    rest = re.sub(r"(?<![A-Za-z])(?:" + "|".join(sorted(KNOWN_CODES | set(CODE_ALIASES))) + r")(?![A-Za-z])", " ", rest)
    for sym, cur in UNIQUE_SYMBOLS:
        if sym in rest:
            found.setdefault(cur, "symbol")
            rest = rest.replace(sym, " ")
    ambiguous = [s for s in AMBIGUOUS_SYMBOLS if s in rest]
    for s in ambiguous:
        rest = rest.replace(s, " ")
    out["stripped"] = rest
    ctx = (context_currency or "").upper() or None

    if len(found) > 1:
        out["errors"].append(f"통화가 두 개 이상 표시됨: {', '.join(sorted(found))}")
        return out
    if found:
        cur, basis = next(iter(found.items()))
        out.update(currency=cur, basis=basis)
        for s in ambiguous:
            if cur not in AMBIGUOUS_SYMBOLS[s]:
                out["errors"].append(f"기호 {s} 와 통화 {cur} 가 맞지 않음")
        if ctx and ctx != cur:
            out["warnings"].append(f"페이지 통화 설정({ctx})과 가격 표시 통화({cur})가 다름")
        return out
    if ambiguous:
        s = ambiguous[0]
        if len(ambiguous) > 1:
            out["errors"].append(f"모호한 기호가 두 종류: {' '.join(ambiguous)}")
            return out
        if ctx and ctx in AMBIGUOUS_SYMBOLS[s]:
            out.update(currency=ctx, basis="page_setting")
            return out
        default = SITE_DEFAULTS.get(_site_key(site) or "", {}).get(s)
        if default:
            out.update(currency=default, basis="site_default")
            out["warnings"].append(f"기호 {s} 를 사이트 기본값 {default} 로 읽음 (페이지 통화 설정 확인 권장)")
            return out
        out["reviews"].append(f"기호 {s} 는 여러 통화에 쓰여 판별 불가 (페이지 통화 설정 필요)")
        return out
    if ctx:
        out.update(currency=ctx, basis="page_setting")
        out["warnings"].append("가격 글자에 통화 표시가 없어 페이지 통화 설정으로 읽음")
        return out
    out["reviews"].append("통화 표시 없음")
    return out


def _status(r: dict) -> str:
    return "error" if r["errors"] else "needs_review" if r["reviews"] else "ok"


def parse_price_text(text: str, context_currency: str | None = None, site: str | None = None) -> dict:
    """가격 문자열 하나(단일가 또는 범위)를 읽는다."""
    raw = text
    text = unicodedata.normalize("NFKC", text or "").strip()
    res = {"raw": raw, "currency": None, "currency_basis": None, "min": None, "max": None, "kind": None,
           "status": "ok", "errors": [], "reviews": [], "warnings": []}
    if not text:
        res["errors"].append("빈 가격 글자")
        res["status"] = _status(res)
        return res
    cur = detect_currency(text, context_currency, site)
    res.update(currency=cur["currency"], currency_basis=cur["basis"])
    for k in ("errors", "reviews", "warnings"):
        res[k] += cur[k]
    body = re.sub(r"/\s*[A-Za-z가-힣]+\.?", " ", cur["stripped"])   # "/ piece", "/개" 제거
    nums = [(m.group(), m.start(), m.end()) for m in NUM_RE.finditer(body)]
    if not nums:
        res["errors"].append("숫자 없음")
    elif len(nums) > 2:
        res["errors"].append(f"숫자가 {len(nums)}개라 가격 글자로 볼 수 없음")
    else:
        values = []
        for s, _, _ in nums:
            v, notes = to_number(s, res["currency"])
            if v is None:
                res["errors"] += notes
            else:
                values.append(v)
                res["warnings"] += notes
        if len(values) == len(nums):
            if len(values) == 2:
                between = body[nums[0][2]:nums[1][1]]
                if not re.search(RANGE_SEP, between):
                    res["reviews"].append(f"두 숫자 사이에 범위 기호가 없음: '{between.strip()}'")
                res.update(kind="range", min=values[0], max=values[1])
            else:
                res.update(kind="single", min=values[0], max=values[0])
            if res["min"] <= 0:
                res["errors"].append("가격이 0 이하")
            if res["min"] > res["max"]:
                res["errors"].append("최소가가 최대가보다 큼 (범위가 뒤집힘)")
            if res["currency"] in ZERO_DECIMAL and any(v != int(v) for v in values):
                res["reviews"].append(f"{res['currency']}는 소수점이 없는 통화인데 소수가 있음")
    res["status"] = _status(res)
    return res


def parse_quantity(text: str) -> dict:
    """수량 구간 글자: '100 - 799 pieces', '>= 10000 pieces', '10000개 이상', '10000+ pcs', '100개'."""
    t = unicodedata.normalize("NFKC", text or "").strip()
    out = {"raw": text, "min": None, "max": None, "open_ended": False, "unit": None, "errors": []}
    tail = re.sub(r"\s*(?:or more|and above|이상)\s*$", "", t, flags=re.I).strip()
    unit = re.search(r"\d\s*\+?\s*([A-Za-z가-힣]+)\s*\+?$", tail)
    if unit:
        out["unit"] = unit.group(1)
    n = lambda s: int(s.replace(",", ""))
    m = re.search(r"([\d,]+)\s*" + RANGE_SEP + r"\s*([\d,]+)", t)
    if m:
        out.update(min=n(m.group(1)), max=n(m.group(2)))
    elif re.search(r"(?:≥|>=|>|over|above)\s*[\d,]+|[\d,]+\s*(?:[A-Za-z가-힣]+?\s*)?(?:\+|이상|or more|and above)",
                   t, re.I):
        out.update(min=n(re.search(r"[\d,]+", t).group()), open_ended=True)
    elif len(re.findall(r"[\d,]+", t)) == 1:
        out["min"] = n(re.search(r"[\d,]+", t).group())
    else:
        out["errors"].append(f"수량 구간을 읽지 못함: {text}")
    if out["min"] is not None and out["max"] is not None and out["min"] > out["max"]:
        out["errors"].append("수량 구간이 뒤집힘")
    return out


def parse_tiers(tiers: list[dict], context_currency: str | None = None, site: str | None = None,
                moq: int | None = None) -> dict:
    """수량별 구간가 목록 [{quantity_text, price_text}] 를 읽고 구간끼리 검사한다."""
    res = {"tiers": [], "currency": None, "min": None, "max": None, "status": "ok",
           "errors": [], "reviews": [], "warnings": []}
    for i, t in enumerate(tiers):
        q = parse_quantity(t.get("quantity_text", ""))
        p = parse_price_text(t.get("price_text", ""), context_currency, site)
        res["tiers"].append({"quantity": q, "price": p})
        tag = f"{i+1}번 구간"
        res["errors"] += [f"{tag}: {e}" for e in q["errors"] + p["errors"]]
        res["reviews"] += [f"{tag}: {e}" for e in p["reviews"]]
        res["warnings"] += [f"{tag}: {e}" for e in p["warnings"]]
        if p["kind"] == "range":
            res["reviews"].append(f"{tag}: 구간 가격이 범위로 표시됨")
    curs = {t["price"]["currency"] for t in res["tiers"] if t["price"]["currency"]}
    if len(curs) > 1:
        res["errors"].append(f"구간마다 통화가 다름: {', '.join(sorted(curs))}")
    elif curs:
        res["currency"] = curs.pop()
    ok = [t for t in res["tiers"] if t["quantity"]["min"] is not None and t["price"]["min"] is not None]
    for i in range(1, len(ok)):
        a, b = ok[i - 1], ok[i]
        qa, qb = a["quantity"], b["quantity"]
        tag = f"{i}·{i+1}번 구간"
        if qb["min"] <= qa["min"]:
            res["errors"].append(f"{tag}: 수량 구간 순서가 맞지 않음")
            continue
        if qa["open_ended"]:
            res["errors"].append(f"{tag}: '이상' 구간 뒤에 다른 구간이 있음")
        elif qa["max"] is not None:
            if qa["max"] >= qb["min"]:
                res["errors"].append(f"{tag}: 수량 구간이 겹침 ({qa['max']} ≥ {qb['min']})")
            elif qa["max"] + 1 < qb["min"]:
                res["warnings"].append(f"{tag}: 구간 사이 빈 수량 ({qa['max'] + 1}~{qb['min'] - 1})")
        else:
            res["warnings"].append(f"{i}번 구간 끝 수량이 표시되지 않음 (다음 구간 시작 전까지로 봄)")
        if b["price"]["min"] > a["price"]["min"]:
            res["reviews"].append(f"{tag}: 수량이 늘었는데 단가가 오름 ({a['price']['min']} → {b['price']['min']})")
    prices = [t["price"]["min"] for t in ok] + [t["price"]["max"] for t in ok]
    if prices:
        res["min"], res["max"] = min(prices), max(prices)
    if moq is not None and ok and ok[0]["quantity"]["min"] != moq:
        res["reviews"].append(f"MOQ({moq})와 첫 구간 시작 수량({ok[0]['quantity']['min']})이 다름")
    res["status"] = _status(res)
    return res


def check_plausibility(pmin: float | None, pmax: float | None, currency: str | None,
                       rates: dict[str, float] | None = None) -> dict:
    """원화 환산 상식선 검사. 환율이 인자로 없으면 KRW 외에는 검사하지 않는다(추정 금지)."""
    res = {"krw_min": None, "krw_max": None, "rate": None, "checked": False, "reviews": [], "warnings": []}
    if pmin is None or pmax is None or not currency:
        res["warnings"].append("가격 또는 통화가 없어 상식선 검사 생략")
        return res
    rate = 1.0 if currency == "KRW" else (rates or {}).get(f"{currency}:KRW")
    if rate is None:
        res["warnings"].append(f"{currency}→KRW 환율이 입력되지 않아 상식선 검사 생략")
        return res
    res.update(rate=rate, krw_min=round(pmin * rate), krw_max=round(pmax * rate), checked=True)
    lo, hi = PLAUSIBLE_KRW
    if res["krw_min"] < lo:
        res["reviews"].append(f"원화 환산 최저가 {res['krw_min']:,}원이 {lo:,}원 미만")
    if res["krw_max"] > hi:
        res["reviews"].append(f"원화 환산 최고가 {res['krw_max']:,}원이 {hi:,}원 초과")
    if pmin > 0 and pmax / pmin > MAX_RANGE_RATIO:
        res["reviews"].append(f"최고가가 최저가의 {pmax / pmin:.0f}배 (단위·옵션이 섞였는지 확인)")
    return res


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    results: list[tuple[str, bool]] = []

    def check(name: str, cond: bool) -> None:
        results.append((name, bool(cond)))

    p = parse_price_text
    r = p("US$2.50 - 3.80")
    check("USD 범위", (r["currency"], r["min"], r["max"], r["kind"], r["status"]) == ("USD", 2.5, 3.8, "range", "ok"))
    check("USD 근거=기호", r["currency_basis"] == "symbol")
    r = p("₩3,735 - 4,427")
    check("KRW 쉼표 천 단위", (r["currency"], r["min"], r["max"], r["status"]) == ("KRW", 3735, 4427, "ok"))
    r = p("$2.50-3.80/piece", site="www.alibaba.com")
    check("$ + alibaba.com → USD 사이트 기본값", (r["currency"], r["currency_basis"], r["max"]) == ("USD", "site_default", 3.8))
    r = p("$2.50")
    check("$ 근거 없음 → needs_review", r["currency"] is None and r["status"] == "needs_review")
    r = p("$2.50", context_currency="AUD")
    check("$ + 페이지 설정 AUD", (r["currency"], r["currency_basis"]) == ("AUD", "page_setting"))
    r = p("¥108", site="item.taobao.com")
    check("¥ + taobao → CNY", r["currency"] == "CNY" and r["min"] == 108)
    r = p("¥108", context_currency="JPY")
    check("¥ + 페이지 설정 JPY", r["currency"] == "JPY")
    r = p("¥108", site="www.alibaba.com")
    check("¥ + alibaba.com 설정 없음 → needs_review", r["status"] == "needs_review" and r["currency"] is None)
    r = p("￥108")
    check("전각 ￥ 정규화 후 모호 처리", r["currency"] is None and r["min"] == 108)
    r = p("1.234,56 €")
    check("EUR 점 천 단위·쉼표 소수", (r["currency"], r["min"]) == ("EUR", 1234.56))
    r = p("2,50 - 3,80 €")
    check("EUR 쉼표 소수 범위", (r["min"], r["max"]) == (2.5, 3.8) and r["status"] == "ok")
    r = p("4.427원")
    check("KRW 점 천 단위", (r["currency"], r["min"]) == ("KRW", 4427) and r["warnings"])
    r = p("US$ 3.80 - 2.50")
    check("범위 뒤집힘 → error", r["status"] == "error" and any("뒤집힘" in e for e in r["errors"]))
    r = p("US$0")
    check("0원 → error", r["status"] == "error")
    r = p("US$2.50 KRW")
    check("통화 두 개 → error", r["status"] == "error")
    r = p("₩3,735.5")
    check("KRW 소수 → needs_review", r["status"] == "needs_review")
    r = p("US$1 - 2 - 3")
    check("숫자 3개 → error", r["status"] == "error")
    r = p("CNY 108")
    check("코드 CNY", (r["currency"], r["currency_basis"]) == ("CNY", "code"))
    r = p("RMB 108")
    check("RMB → CNY", r["currency"] == "CNY")
    r = p("１０８元")
    check("전각 숫자·元", (r["currency"], r["min"]) == ("CNY", 108))
    r = p("HK$50")
    check("HK$ 는 USD 아님", r["currency"] == "HKD")
    r = p("US$2.50 3.80")
    check("범위 기호 없음 → needs_review", r["status"] == "needs_review")
    r = p("4,427", context_currency="KRW")
    check("통화 표시 없음 + 페이지 설정", r["currency"] == "KRW" and r["warnings"])
    r = p("")
    check("빈 글자 → error", r["status"] == "error")

    tiers = [{"quantity_text": "100 - 799 pieces", "price_text": "₩4,427"},
             {"quantity_text": "800 - 4999 pieces", "price_text": "₩4,289"},
             {"quantity_text": "5000 - 9999 pieces", "price_text": "₩4,012"},
             {"quantity_text": ">= 10000 pieces", "price_text": "₩3,735"}]
    r = parse_tiers(tiers, moq=100)
    check("구간가 4개 정상", (r["status"], r["currency"], r["min"], r["max"]) == ("ok", "KRW", 3735, 4427))
    check("구간 단위·이상", r["tiers"][0]["quantity"]["unit"] == "pieces" and r["tiers"][3]["quantity"]["open_ended"])
    up = [dict(tiers[0]), dict(tiers[1], price_text="₩4,500")]
    check("수량↑ 단가↑ → needs_review", parse_tiers(up)["status"] == "needs_review")
    ov = [dict(tiers[0]), dict(tiers[1], quantity_text="700 - 4999 pieces")]
    check("구간 겹침 → error", parse_tiers(ov)["status"] == "error")
    mix = [dict(tiers[0]), dict(tiers[1], price_text="US$3.10")]
    check("구간 통화 혼합 → error", parse_tiers(mix)["status"] == "error")
    check("MOQ 불일치 → needs_review", parse_tiers(tiers, moq=50)["status"] == "needs_review")
    gap = [dict(tiers[0]), dict(tiers[1], quantity_text="1000 - 4999 pieces")]
    g = parse_tiers(gap)
    check("빈 구간 → 경고만", g["status"] == "ok" and any("빈 수량" in w for w in g["warnings"]))
    q = parse_quantity("10000개 이상")
    check("한글 '이상' 구간", q["min"] == 10000 and q["open_ended"] and q["unit"] == "개")
    q = parse_quantity("10,000+ pcs")
    check("10,000+ pcs", q["min"] == 10000 and q["open_ended"] and q["unit"] == "pcs")
    after_open = [dict(tiers[3]), {"quantity_text": "20000 - 30000 pieces", "price_text": "₩3,000"}]
    check("'이상' 뒤 구간 → error", parse_tiers(after_open)["status"] == "error")

    c = check_plausibility(50, 60, "KRW")
    check("KRW 50원 → 상식선 위반", c["checked"] and c["reviews"])
    c = check_plausibility(2.5, 3.8, "USD", {"USD:KRW": 1400})
    check("USD 환율 있음 → 통과", c["checked"] and not c["reviews"] and c["krw_max"] == 5320)
    c = check_plausibility(2.5, 3.8, "USD")
    check("환율 없음 → 검사 생략", not c["checked"] and c["warnings"])
    c = check_plausibility(1000, 50000, "KRW")
    check("범위 폭 20배 초과 → 확인", any("배" in x for x in c["reviews"]))

    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    failed = sum(1 for _, ok in results if not ok)
    print(f"\n{len(results) - failed}/{len(results)} PASS")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="가격 글자 → 통화·최저·최고가 + 검사")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--site")
    ap.add_argument("--context-currency")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test or not a.text:
        return self_test()
    print(json.dumps(parse_price_text(a.text, a.context_currency, a.site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
