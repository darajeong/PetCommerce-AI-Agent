"""A02-04 반복 처리: 실제 상품 3개를 연속 처리하고 대기·재시도·차단·수동 전환을 기록한다.

    python docs/poc/samples/a02_batch_run.py            # 3개 연속 실행 → W2-A02-04_RUN_LOG.json
    python docs/poc/samples/a02_batch_run.py --self-test

상품마다 단계를 차례로 처리한다.
1. access: 자동 접근 결과. W1-07 1.1절에 따라 AI는 상품 페이지에 접속하지 않으므로 다시 실행하지 않고,
   A02-01 검증 결과(PR #13, 2026-11-08)를 차단·수동 대체 경로 근거로 기록한다.
2. facts: 사람이 상품 페이지를 직접 열어 채운 입력표 → W1-04 상품 JSON (a02_build_product.build).
3. normalize: A03-02 정규화 (a03_normalize.normalize). 환율 인자 없음 = PR #12 결과와 같은 조건.
단계가 예외로 실패하면 1회 재시도한다. 그래도 실패하거나 저장·상태 계산에서 예외가 나면 그 상품만
`failed`로 기록하고 다음 상품을 계속 처리한다. 로그는 상품 하나를 끝낼 때마다 파일에 다시 쓴다.
결과 파일이 이미 있고 내용이 다르면 덮어쓰지 않고 경고만 남긴다(`--overwrite`로만 덮어씀).
네트워크 요청이 없어 대기(요청 간격·rate limit)는 발생하지 않으며 0으로 기록한다.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import a02_build_product
import a03_normalize

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


def dump(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def run_product(pid: str, facts: dict[str, str], out_dir: Path | None, overwrite: bool = False) -> dict:
    events = [{"type": t, "step": "access", "detail": d, "source": A02_01} for t, d in ACCESS.get(pid, [])]
    steps, docs, outputs, warnings = [], {}, [], []
    started = now()

    def step(name, fn):
        for attempt in range(1, MAX_RETRY + 2):
            try:
                result = fn()
                steps.append({"step": name, "status": "success", "attempts": attempt, "error": None})
                return result
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                if attempt <= MAX_RETRY:
                    events.append({"type": "retry", "step": name, "detail": err, "source": "this run"})
        steps.append({"step": name, "status": "failed", "attempts": attempt, "error": err})
        return None

    try:  # 저장·상태 계산까지 상품 단위로 가둔다
        steps.append({"step": "access", "status": "manual_fallback" if pid in ACCESS else "not_recorded",
                      "attempts": 0, "error": None})
        docs["product"] = step("facts", lambda: a02_build_product.build(pid, facts))
        if docs["product"] is not None:
            docs["result"] = step("normalize", lambda: a03_normalize.normalize(docs["product"], {}, None, NORMALIZE_AT))

        if out_dir is not None:
            for key, name in (("product", f"W2-A02-02_PRODUCT_{pid}.json"),
                              ("result", f"W2-A03-02_RESULT_{pid.replace('prod-', '')}.json")):
                if docs.get(key) is None:
                    continue
                path, text = out_dir / name, dump(docs[key])
                if path.exists() and path.read_text(encoding="utf-8") != text and not overwrite:
                    warnings.append(f"{name}: 기존 파일과 내용이 달라 덮어쓰지 않음 (--overwrite로만 갱신)")
                    continue
                path.write_text(text, encoding="utf-8")
                outputs.append(f"docs/poc/samples/{name}")

        if any(s["status"] == "failed" for s in steps):
            final = "failed"
        else:
            a02 = docs["product"]["agent_outputs"]["A02"]["status"]
            a03 = docs["result"]["agent_outputs"]["A03"]["status"]
            final = "success" if a02 == a03 == "success" else "partial_success"
    except Exception as e:
        steps.append({"step": "record", "status": "failed", "attempts": 1, "error": f"{type(e).__name__}: {e}"})
        final = "failed"

    return {"product_id": pid, "final_status": final, "started_at": started, "ended_at": now(),
            "counts": {k: sum(e["type"] == k for e in events) for k in COUNT_KEYS},
            "steps": steps, "events": events, "outputs": outputs, "warnings": warnings}


def run_batch(facts: dict[str, dict[str, str]], out_dir: Path | None, log_path: Path,
              overwrite: bool = False) -> dict:
    started = now()
    log = {"run_id": f"run-a02-04-{started[:19].replace(':', '').replace('-', '')}", "task": "A02-04",
           "started_at": started, "ended_at": None, "completed": False, "product_count": len(facts),
           "max_retry": MAX_RETRY, "wait_policy": "네트워크 요청 없음(입력표·로컬 처리만). 대기 발생 0",
           "products": []}
    for pid, f in facts.items():
        log["products"].append(run_product(pid, f, out_dir, overwrite))
        log_path.write_text(dump(log), encoding="utf-8")  # 상품마다 바로 기록: 중간에 죽어도 앞 상품은 남음
    products = log["products"]
    log.update(ended_at=now(), completed=True,
               by_status={s: sum(p["final_status"] == s for p in products) for s in ("success", "partial_success", "failed")},
               totals={k: sum(p["counts"][k] for p in products) for k in COUNT_KEYS},
               warnings_count=sum(len(p["warnings"]) for p in products))  # 0이 아니면 저장 안 된 결과 있음
    log_path.write_text(dump(log), encoding="utf-8")
    # 파일에 실제로 남은 상품 수 (메모리 값이 아니라 다시 읽은 값)
    saved = json.loads(log_path.read_text(encoding="utf-8"))["products"]
    log["final_status_saved"] = sum(p.get("final_status") in ("success", "partial_success", "failed") for p in saved)
    log_path.write_text(dump(log), encoding="utf-8")
    return log


def self_test() -> int:
    fails = 0

    def check(label, cond):
        nonlocal fails
        print(("PASS " if cond else "FAIL ") + label)
        fails += 0 if cond else 1

    base = a02_build_product.read_facts(HERE / "W2-A02-02_FACTS_INPUT.csv")
    real_build, real_norm = a02_build_product.build, a03_normalize.normalize

    def batch(tmp, facts=None, out_dir=None, overwrite=False):
        return run_batch(facts or {k: dict(v) for k, v in base.items()}, out_dir, Path(tmp) / "log.json", overwrite)

    with tempfile.TemporaryDirectory() as tmp:
        try:
            # 1) facts 단계 두 번 다 실패: 그 상품만 failed, 나머지 계속
            facts = {k: dict(v) for k, v in base.items()}
            del facts["prod-w2-07"]["source_url"]
            p = {x["product_id"]: x for x in batch(tmp, facts)["products"]}
            check("facts 실패: 07만 failed", p["prod-w2-07"]["final_status"] == "failed")
            check("facts 실패: 01·09 success", p["prod-w2-01"]["final_status"] == p["prod-w2-09"]["final_status"] == "success")
            check("facts 실패: 재시도 1회·원인 기록", p["prod-w2-07"]["counts"]["retry"] == 1
                  and "KeyError" in p["prod-w2-07"]["steps"][1]["error"])
            check("facts 실패: 정규화 미실행", [s["step"] for s in p["prod-w2-07"]["steps"]] == ["access", "facts"])

            # 2) 첫 시도만 실패 → 재시도 성공 (retry=1, success)
            calls = {"n": 0}

            def flaky(pid, f):
                calls["n"] += 1
                if pid == "prod-w2-01" and calls["n"] == 1:
                    raise OSError("일시 오류(주입)")
                return real_build(pid, f)
            a02_build_product.build = flaky
            p = {x["product_id"]: x for x in batch(tmp)["products"]}
            a02_build_product.build = real_build
            check("재시도 성공: 01 success·retry 1·attempts 2", p["prod-w2-01"]["final_status"] == "success"
                  and p["prod-w2-01"]["counts"]["retry"] == 1 and p["prod-w2-01"]["steps"][1]["attempts"] == 2)

            # 3) normalize 단계 두 번 다 실패
            def bad_norm(doc, *a):
                if doc["product_id"] == "prod-w2-09":
                    raise ValueError("정규화 실패(주입)")
                return real_norm(doc, *a)
            a03_normalize.normalize = bad_norm
            p = {x["product_id"]: x for x in batch(tmp)["products"]}
            a03_normalize.normalize = real_norm
            check("normalize 실패: 09 failed·normalize 단계 기록", p["prod-w2-09"]["final_status"] == "failed"
                  and p["prod-w2-09"]["steps"][-1]["step"] == "normalize" and p["prod-w2-09"]["counts"]["retry"] == 1)

            # 4) 단계 밖 예외(A03 출력에 agent_outputs.A03 없음) → 그 상품만 failed, 배치 계속
            def no_a03(doc, *a):
                res = real_norm(doc, *a)
                if doc["product_id"] == "prod-w2-01":
                    del res["agent_outputs"]["A03"]
                return res
            a03_normalize.normalize = no_a03
            log = batch(tmp)
            a03_normalize.normalize = real_norm
            p = {x["product_id"]: x for x in log["products"]}
            check("상태 계산 예외: 01 failed(record 단계)", p["prod-w2-01"]["final_status"] == "failed"
                  and p["prod-w2-01"]["steps"][-1]["step"] == "record")
            check("상태 계산 예외: 07·09 계속 처리", p["prod-w2-07"]["final_status"] == "partial_success" and p["prod-w2-09"]["final_status"] == "success")

            # 5) 중간에 프로세스가 죽어도 앞 상품은 로그 파일에 남음
            def crash(doc, *a):
                if doc["product_id"] == "prod-w2-09":
                    raise KeyboardInterrupt  # Exception 밖 → 배치 중단을 흉내
                return real_norm(doc, *a)
            a03_normalize.normalize = crash
            try:
                batch(tmp)
            except KeyboardInterrupt:
                pass
            a03_normalize.normalize = real_norm
            saved = json.loads((Path(tmp) / "log.json").read_text(encoding="utf-8"))
            check("중단 시: 앞 상품 2개 파일에 남음·completed false",
                  [x["product_id"] for x in saved["products"]] == ["prod-w2-01", "prod-w2-07"] and saved["completed"] is False)

            # 6) 정상 실행: 파일에서 다시 읽은 저장 수 3, 횟수 기록
            log = batch(tmp)
            check("정상: 파일 기준 최종 상태 저장 3/3", log["final_status_saved"] == 3 and log["completed"])
            check("정상: 4개 횟수 모두 기록·횟수 = 이벤트 수",
                  all(set(x["counts"]) == set(COUNT_KEYS) and sum(x["counts"].values()) == len(x["events"])
                      for x in log["products"]))

            # 7) 기존 결과와 다르면 덮어쓰지 않음
            out = Path(tmp) / "out"
            out.mkdir()
            old = out / "W2-A02-02_PRODUCT_prod-w2-01.json"
            old.write_text("{}\n", encoding="utf-8")
            log = batch(tmp, out_dir=out)
            p = {x["product_id"]: x for x in log["products"]}
            check("덮어쓰기 방지: 기존 파일 유지·경고 기록", old.read_text(encoding="utf-8") == "{}\n"
                  and p["prod-w2-01"]["warnings"] and "docs/poc/samples/W2-A02-02_PRODUCT_prod-w2-01.json" not in p["prod-w2-01"]["outputs"])
            check("덮어쓰기 방지: 배치 warnings_count 1", log["warnings_count"] == 1)
            batch(tmp, out_dir=out, overwrite=True)
            check("--overwrite: 갱신됨", old.read_text(encoding="utf-8") != "{}\n")
        finally:
            a02_build_product.build, a03_normalize.normalize = real_build, real_norm
    print("결과:", "PASS" if not fails else f"FAIL {fails}건")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="A02-04 실제 상품 3개 연속 실행")
    ap.add_argument("--facts", type=Path, default=HERE / "W2-A02-02_FACTS_INPUT.csv")
    ap.add_argument("--out-dir", type=Path, default=HERE)
    ap.add_argument("--log", type=Path, default=HERE / "W2-A02-04_RUN_LOG.json")
    ap.add_argument("--overwrite", action="store_true", help="기존 결과 파일과 내용이 달라도 덮어씀")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    log = run_batch(a02_build_product.read_facts(a.facts), a.out_dir, a.log, a.overwrite)
    for p in log["products"]:
        print(f"{p['product_id']}: {p['final_status']} {p['counts']}" + (f" 경고 {p['warnings']}" if p["warnings"] else ""))
    print(f"합계 {log['totals']}, 최종 상태 저장(파일 기준) {log['final_status_saved']}/{log['product_count']}, 경고 {log['warnings_count']}")
    return 2 if log["warnings_count"] else 0  # 경고(미저장 결과) 있으면 정상 종료로 보이지 않게


if __name__ == "__main__":
    sys.exit(main())
