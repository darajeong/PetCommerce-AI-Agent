"""A02-04 반복 처리: 실제 상품 3개를 연속 처리하고 대기·재시도·차단·수동 전환을 기록한다.

    python docs/poc/samples/a02_batch_run.py            # 3개 연속 실행 → W2-A02-04_RUN_LOG.json
    python docs/poc/samples/a02_batch_run.py --self-test

상품마다 단계를 차례로 처리한다.
1. access: 자동 접근 결과. W1-07 1.1절에 따라 AI는 상품 페이지에 접속하지 않으므로 다시 실행하지 않고,
   A02-01 검증 결과(PR #13, 2026-11-08)를 차단·수동 대체 경로 근거로 기록한다.
2. facts: 사람이 상품 페이지를 직접 열어 채운 입력표 → W1-04 상품 JSON (a02_build_product.build).
3. normalize: A03-02 정규화 (a03_normalize.normalize). 환율 인자 없음 = PR #12 결과와 같은 조건.
단계가 예외로 실패하면 1회 재시도하고, 그래도 실패하면 그 상품만 `failed`로 저장하고 다음 상품을 계속 처리한다.
네트워크 요청이 없어 대기(요청 간격·rate limit)는 발생하지 않으며 0으로 기록한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from a02_build_product import build, read_facts
from a03_normalize import normalize

HERE = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
NORMALIZE_AT = "2026-11-07T12:00:00+09:00"  # PR #12 A03-02 결과와 같은 변환 시각
MAX_RETRY = 1

# A02-01 접근·로그인 검증(PR #13, B, 2026-11-08) 결과. 검토 전 결과 기준.
A02_01 = "docs/poc/planning/W2-A02-01_ACCESS_LOGIN_REPORT.md (PR #13)"
ACCESS = {
    "prod-w2-01": [("block", "비로그인 헤드리스: HTTP 200 후 보안 확인 문구 감지, access_restricted"),
                   ("block", "일반 크롬: 비정상 트래픽 안내, 사람이 직접 슬라이더 인증 후 열림"),
                   ("manual_switch", "자동 수집 대신 사람이 상품 페이지를 열어 입력표에 사실 값 기록")],
    "prod-w2-07": [("block", "비로그인 헤드리스: HTTP 200 후 보안 확인 문구 감지, access_restricted"),
                   ("manual_switch", "자동 수집 대신 사람이 상품 페이지를 열어 입력표에 사실 값 기록")],
    "prod-w2-09": [("block", "비로그인 헤드리스: HTTP 200 후 보안 확인 문구 감지, access_restricted"),
                   ("manual_switch", "자동 수집 대신 사람이 상품 페이지를 열어 입력표에 사실 값 기록")],
}
COUNT_KEYS = ("wait", "retry", "block", "manual_switch")


def now() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


def run_product(pid: str, facts: dict[str, str], out_dir: Path | None) -> dict:
    events = [{"type": t, "step": "access", "detail": d, "source": A02_01} for t, d in ACCESS.get(pid, [])]
    steps, docs = [], {}

    def step(name, fn):
        for attempt in range(1, MAX_RETRY + 2):
            try:
                result = fn()
                steps.append({"step": name, "status": "success", "attempts": attempt, "error": None})
                return result
            except Exception as e:  # 단계 실패를 상품 단위로 가둔다
                err = f"{type(e).__name__}: {e}"
                if attempt <= MAX_RETRY:
                    events.append({"type": "retry", "step": name, "detail": err, "source": "this run"})
        steps.append({"step": name, "status": "failed", "attempts": attempt, "error": err})
        return None

    started = now()
    steps.append({"step": "access", "status": "manual_fallback" if pid in ACCESS else "not_recorded",
                  "attempts": 0, "error": None})
    docs["product"] = step("facts", lambda: build(pid, facts))
    if docs["product"] is not None:
        docs["result"] = step("normalize", lambda: normalize(docs["product"], {}, None, NORMALIZE_AT))

    outputs = []
    if out_dir is not None:
        for key, name in (("product", f"W2-A02-02_PRODUCT_{pid}.json"), ("result", f"W2-A03-02_RESULT_{pid.replace('prod-', '')}.json")):
            if docs.get(key) is not None:
                (out_dir / name).write_text(json.dumps(docs[key], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                outputs.append(f"docs/poc/samples/{name}")

    if any(s["status"] == "failed" for s in steps):
        final = "failed"
    else:
        a02 = docs["product"]["agent_outputs"]["A02"]["status"]
        a03 = docs["result"]["agent_outputs"]["A03"]["status"]
        final = "success" if a02 == a03 == "success" else "partial_success"
    return {"product_id": pid, "final_status": final, "started_at": started, "ended_at": now(),
            "counts": {k: sum(e["type"] == k for e in events) for k in COUNT_KEYS},
            "steps": steps, "events": events, "outputs": outputs}


def run_batch(facts: dict[str, dict[str, str]], out_dir: Path | None) -> dict:
    started = now()
    products = [run_product(pid, f, out_dir) for pid, f in facts.items()]
    totals = {k: sum(p["counts"][k] for p in products) for k in COUNT_KEYS}
    by_status = {s: sum(p["final_status"] == s for p in products) for s in ("success", "partial_success", "failed")}
    return {"run_id": f"run-a02-04-{started[:19].replace(':', '').replace('-', '')}", "task": "A02-04",
            "started_at": started, "ended_at": now(), "product_count": len(products),
            "final_status_saved": sum(bool(p["final_status"]) for p in products),
            "by_status": by_status, "totals": totals, "max_retry": MAX_RETRY,
            "wait_policy": "네트워크 요청 없음(입력표·로컬 처리만). 대기 발생 0",
            "products": products}


def self_test() -> int:
    """부분 실패: 가운데 상품의 입력을 망가뜨려도 나머지 2개가 끝까지 처리되는지 확인한다."""
    fails = 0

    def check(label, cond):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + label)
        fails += 0 if cond else 1

    facts = read_facts(HERE / "W2-A02-02_FACTS_INPUT.csv")
    broken = dict(facts["prod-w2-07"])
    del broken["source_url"]  # build()가 KeyError로 실패
    facts["prod-w2-07"] = broken
    log = run_batch(facts, out_dir=None)
    p = {x["product_id"]: x for x in log["products"]}
    check("3개 모두 최종 상태 저장", log["final_status_saved"] == 3)
    check("망가진 상품만 failed", p["prod-w2-07"]["final_status"] == "failed")
    check("실패 후 다음 상품 계속 처리", p["prod-w2-09"]["final_status"] == "success")
    check("앞 상품 영향 없음", p["prod-w2-01"]["final_status"] == "success")
    check("실패 단계 재시도 1회 기록", p["prod-w2-07"]["counts"]["retry"] == MAX_RETRY)
    check("실패 원인 기록", "KeyError" in (p["prod-w2-07"]["steps"][1]["error"] or ""))
    check("실패 상품은 정규화 미실행", [s["step"] for s in p["prod-w2-07"]["steps"]] == ["access", "facts"])
    check("모든 상품 4개 횟수 기록", all(set(x["counts"]) == set(COUNT_KEYS) for x in log["products"]))
    check("횟수 = 이벤트 수", all(sum(x["counts"].values()) == len(x["events"]) for x in log["products"]))
    print("결과:", "PASS" if not fails else f"FAIL {fails}건")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="A02-04 실제 상품 3개 연속 실행")
    ap.add_argument("--facts", type=Path, default=HERE / "W2-A02-02_FACTS_INPUT.csv")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    ap.add_argument("--log", type=Path, default=HERE / "W2-A02-04_RUN_LOG.json")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    log = run_batch(read_facts(a.facts), a.out_dir)
    a.log.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for p in log["products"]:
        print(f"{p['product_id']}: {p['final_status']} {p['counts']}")
    print(f"합계 {log['totals']}, 최종 상태 저장 {log['final_status_saved']}/{log['product_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
