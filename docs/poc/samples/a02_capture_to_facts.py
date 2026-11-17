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
    "package_size": r"package size|포장 크기|패키지 크기",
    "package_weight": r"gross weight|포장 총?중량|총중량",
}
DIM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?\s*(mm|cm|m|inches|inch|in)\b", re.I)
WEIGHT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|g|lbs|lb|oz)\b", re.I)
NUMERIC_KEYS = {"price_min", "price_max", "sales_count", "rating", "review_count", "length", "width", "height", "weight"}
COMPARE_KEYS = ["original_name", "price_min", "price_max", "currency", "options", "length", "width", "height", "weight",
                "material", "sales_count", "rating", "review_count", "supplier_name", "package_size", "package_weight"]


def num_str(x: float | None) -> str:
    if x is None:
        return ""
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def find_attr(attrs: list[dict], key: str) -> str | None:
    rule = re.compile(ATTR_RULES[key], re.I)
    return next((a["value"] for a in attrs if rule.search(a["name"].strip())), None)


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
    v["original_name"] = g("original_name")

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
    if pr and pr["status"] != "error" and pr.get("min") is not None:
        v["price_min"], v["price_max"] = num_str(pr["min"]), num_str(pr["max"])
        v["currency"] = pr["currency"] or ""
        if kind == "tiers":
            v["price_note"] = "구간가 " + " / ".join(f"{t['quantity']['raw']} {t['price']['raw']}" for t in pr["tiers"])
        else:
            v["price_note"] = f"가격 글자 {pr['raw']}"
        if moq:
            v["price_note"] += f" (MOQ {moq})"
    plaus = check_plausibility(pr["min"] if pr else None, pr["max"] if pr else None, pr["currency"] if pr else None, rates)
    rep.update(price=pr, price_kind=kind, plausibility=plaus, moq=moq)

    # ---- 옵션·속성
    v["options"] = "; ".join(f"{o['name']}={'/'.join(o['values'])}" for o in cap.get("options") or [])
    attrs = cap.get("attributes") or []
    mat = find_attr(attrs, "material")
    if mat:
        v["material"] = ";".join(m.strip() for m in re.split(r"[;,/]|\band\b", mat) if m.strip())
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

    # ---- 그 밖의 사실 값
    for k in ("sales_count", "rating", "review_count"):
        v[k] = g(k).replace(",", "")
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
        check("01 배송·대형견 표기는 빈칸 (사람 판단)", not v1.get("shipping_method") and not v1.get("large_dog_label"))
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
