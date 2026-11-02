# W1-08 공통 실행 환경 및 협업 규칙

## 1. 목적

PetCommerce AI Agent 프로젝트에서 팀원들이 동일한 기준으로 PoC를 실행하고 결과를 기록할 수 있도록 공통 실행 환경과 협업 규칙을 정의한다.

- 작업 ID: W1-08
- 주 담당: E
- 검토 담당: B
- 문서 상태: v0.1 초안
- 완료 기준: 다른 팀원이 샘플 PoC를 재현할 수 있어야 함

## 2. 개발 환경

### 2.1 확인된 로컬 환경

| 항목 | 버전 및 환경 |
|---|---|
| 운영체제 | Windows |
| Python | 3.14.6 |
| Git | 2.55.0.windows.3 |
| pip | 26.1.2 |
| 터미널 | PowerShell |
| 가상환경 | .venv |

Python 3.14.6은 현재 로컬 검증 환경이며 팀 공통 권장 버전으로 확정된 것은 아니다. W5 기술 스택 확정 전 LangGraph·Celery 등 주요 의존성의 Python 버전 호환성을 확인하고 팀 공통 버전을 결정한다.


### 2.2 저장소 및 실행 환경 준비

```powershell
git clone https://github.com/darajeong/PetCommerce-AI-Agent.git
cd PetCommerce-AI-Agent

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python --version
```

Python 패키지는 추후 팀 공통 의존성 파일을 확정한 뒤 설치한다.

## 3. 보안 및 인증 정보 관리

- API 키, 비밀번호, 인증 토큰은 GitHub에 업로드하지 않는다.
- 실제 인증 정보는 `.env` 등 Git에서 제외된 파일에 보관한다.
- `.gitignore`에 `.venv/`, `.env`, `__pycache__/` 등을 등록한다.
- 공유가 필요한 환경변수 이름은 `.env.example`에 작성하되 실제 값은 포함하지 않는다.
- 외부 플랫폼 접근 권한과 수집 가능 여부는 W1-07 점검 결과를 따른다.
- API 키나 인증 토큰이 실수로 커밋되면 즉시 해당 키를 폐기·재발급하고, 유출 범위를 확인한다. 파일이나 커밋 이력에서 삭제하는 것만으로는 안전하지 않다.
- W1-07에서 점검하는 외부 플랫폼 테스트 계정의 비밀번호·인증 토큰도 문서 및 실행 로그에 직접 기록하지 않는다.


## 4. Git 협업 및 리뷰 규칙

1. 최신 `main`에서 작업 브랜치를 생성한다.
2. 주 담당자는 담당 작업의 별도 브랜치에서 개발한다. 검토 담당자는 팀 합의에 따라 기존 PR 브랜치에서 검토 및 필요한 수정을 진행한다.
3. 실행 결과를 확인하고 커밋 및 Push한다.
4. GitHub Pull Request를 생성한다.
5. WBS에 지정된 검토 담당자의 확인을 받는다.
6. 튜터 확인 후 Merge한다.

리뷰와 승인 전에는 임의로 `main`에 병합하지 않는다.

## 5. PoC 파일 및 결과 관리

기존 `docs/poc/planning/`은 계획 문서 저장 위치로 유지한다.


W1-08의 샘플 실행 코드와 결과 JSON은 `docs/poc/samples/`에 저장한다.

W1-08의 실행 절차 및 검증 기록은 본 문서 6장에 작성한다.

다른 PoC의 공통 기록 경로와 형식은 W1-06 담당자 산출물 및 팀 합의 후 확정한다.


모든 PoC 실행 기록에는 다음 정보를 포함한다.

- PoC ID 및 담당자
- 실행 날짜와 환경
- 사용한 입력 데이터
- 실행 절차 및 명령어
- 출력 결과와 오류
- 실제 데이터 / 테스트 데이터 / Mock 데이터 구분
- 판정 및 후속 작업



## 6. 샘플 PoC 재현 검증

### 6.1 검증 목적

Python 공통 실행 환경에서 Mock 상품 데이터를 검사하고 JSON 결과를 저장할 수 있는지 확인한다.

본 테스트는 실행 환경 검증용으로, W1-04 공통 상품 데이터 계약의 전체 검증을 대체하지 않는다.

### 6.2 검증 파일

- 실행 코드: `docs/poc/samples/w1_08_smoke.py`
- 결과 파일: `docs/poc/samples/W1-08_SMOKE_RESULT.json`
- 입력 데이터: 스크립트에 정의된 Mock 상품 데이터
- 외부 라이브러리: 없음 (Python 표준 라이브러리만 사용)

### 6.3 팀원 재현 방법

**최초 실행 준비 (PR 브랜치 검토 시)**

아래 명령어는 W1-08 브랜치를 GitHub에 Push한 이후 사용할 수 있다.

```powershell
git clone https://github.com/darajeong/PetCommerce-AI-Agent.git
cd PetCommerce-AI-Agent
git switch feature/w1-08-common-execution-env
```

GitHub에서 PR이 Merge된 이후에는 `main`을 사용하므로 별도 브랜치 전환이 필요하지 않다.

가상환경 `.venv`는 최초 실행 시 한 번만 생성하면 된다. 이미 존재하면 생성 명령어를 생략하고 활성화한다.

저장소 최상위 폴더에서 실행한다.

**1. Windows PowerShell 가상환경 활성화**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS·Linux 환경은 다음 명령어를 사용한다.

```bash
source .venv/bin/activate
```

**2. 샘플 실행 및 결과 저장**

**주의:** 아래 결과 저장 명령어는 작성자 E의 최초 실행 증빙 생성용이다. 검토 담당 B는 기존 JSON을 덮어쓰지 않도록 6.6절의 독립 재현 명령어를 사용한다. 실행 정책 오류 시 대체 명령어를 사용할 때도 결과 저장 경로를 별도로 지정한다.

```powershell
python docs/poc/samples/w1_08_smoke.py --output docs/poc/samples/W1-08_SMOKE_RESULT.json
```

**3. 저장된 JSON 검증**

```powershell
python -m json.tool docs/poc/samples/W1-08_SMOKE_RESULT.json
```

**기대 결과**

```json
{
  "poc_id": "W1-08",
  "test_type": "environment_smoke_test",
  "result": "pass",
  "judgement": "성공",
  "product_id": "mock-product-001",
  "data_type": "mock",
  "missing_fields": []
}
```

실제 출력에는 `executed_at`, `python_version`, `platform`도 포함된다.

실행 시각과 환경 정보는 실행자마다 달라질 수 있다. 공통 검증 항목이 동일하고 `result`가 `pass`이면 기본 테스트에 성공한 것으로 본다.

**PowerShell 실행 정책 오류가 발생할 경우**

가상환경 활성화 대신 다음처럼 전용 Python 실행 파일을 직접 사용할 수 있다.

```powershell
.\.venv\Scripts\python.exe docs/poc/samples/w1_08_smoke.py --output docs/poc/samples/W1-08_SMOKE_RESULT.json
```

### 6.4 로컬 PoC 실행 기록

| 항목 | 기록 |
|---|---|
| PoC ID | W1-08 |
| 담당 | E |
| 목표 | 공통 Python 실행 환경 검증 |
| 실행일 | 2026-11-02 |
| 실행 시각 (UTC) | 2026-11-02T08:02:49.535815+00:00 |
| 운영체제 | Windows 11 |
| Python 버전 | 3.14.6 |
| 입력 | Mock 상품 데이터 1건 |
| 실행 절차 | Python 스크립트 실행 후 JSON 파일 저장 및 형식 검증 |
| 실행 결과 | pass |
| 검증 판정 | 성공 (환경 스모크 테스트 기준) |
| 오류 | 발견되지 않음 |
| 다음 작업 | B 담당자 독립 재현 검증, W1-06 확정 양식과 대조, W1-07 정책 반영 |

`성공`은 W1-08 환경 스모크 테스트의 판정이며 W1-03 공식 PoC 판정의 확정을 의미하지 않는다.

### 6.5 완료 점검

- [x] 공통 실행 방법 문서화
- [x] Mock 샘플 코드 작성
- [x] 로컬 실행 성공
- [x] 결과 JSON 저장
- [x] 실행 시각 및 환경 정보 기록
- [x] JSON 형식 검증
- [x] 샘플 실행 기록 작성
- [ ] W1-06 확정 양식과 대조
- [ ] W1-07 권한·정책 점검 결과 반영
- [ ] 다른 팀원의 독립 재현 검증

### 6.6 남은 검증

검토 담당 B는 별도 환경에서 6.3절의 준비 단계와 가상환경 활성화를 수행한 뒤, 아래 독립 재현 명령어로 실행하고 결과를 비교한다.

W1-06 및 W1-07의 담당자 산출물이 준비되면 공통 기록 항목과 인증·접근 정책을 확인하여 반영한다.

팀원 재현 결과가 확인되기 전까지 W1-08을 최종 완료로 판정하지 않는다.

검토 담당 B는 기존 `W1-08_SMOKE_RESULT.json`을 덮어쓰지 않도록 별도 경로에 결과를 저장한다.

Windows PowerShell 기준 독립 재현 명령어:

```powershell
python docs/poc/samples/w1_08_smoke.py --output "$env:TEMP\W1-08_SMOKE_RESULT_B.json"
python -m json.tool "$env:TEMP\W1-08_SMOKE_RESULT_B.json"
```

이 방법은 결과 파일을 프로젝트 저장소 외부에 생성하므로 기존 실행 증빙을 변경하지 않는다.

#### 6.6.1 PR 검토 및 수정 절차

1. E 담당자가 W1-08 작업 브랜치에서 PR을 생성한다.
2. B 담당자는 기존 PR 브랜치의 샘플을 독립 실행하고 최초 검증 결과를 확인한다.
3. B 담당자는 검증 결과를 6.7절에 기록하고 필요한 코드·문서를 직접 수정한다.
4. 코드 또는 실행 절차를 수정했다면 변경된 최종 버전으로 다시 실행하고 재검증 결과를 6.7절에 기록한다.
5. B 담당자는 수정 사항을 동일한 PR 브랜치에 커밋·Push하여 기존 PR을 업데이트한다.
6. B 담당자의 검토와 수정 후 재검증이 완료되면 동일한 PR을 튜터님께 전달한다.
7. 튜터님 승인 후 Merge하며 별도의 검토용 PR은 생성하지 않는다.

검토자는 기존 E 담당자의 실행 증빙 JSON을 유지하며, 독립 재현 결과는 6.7절에 별도로 기록한다.

동일 브랜치에 Push할 권한이 없는 경우 B가 수정 사항을 전달하고 E가 기존 PR 브랜치에 반영한다. 이후 B가 최종 버전을 다시 검증한다.

### 6.7 B 담당자 독립 재현 기록

| 항목 | B 담당자 기록 |
|---|---|
| 실행자 / 실행일 | 검증 대기 |
| 운영체제 / Python 버전 | 검증 대기 |
| 실행 시각 (`executed_at`) | 검증 대기 |
| 실행 결과 (`result`) | 검증 대기 |
| 기대 결과와 일치 여부 | 검증 대기 |
| 막힌 지점 및 오류 | 검증 대기 |
| 수정한 코드·문서 | 검증 대기 |
| 수정 후 재실행 결과 | 검증 대기 |
| 문서 개선 제안 | 검증 대기 |

B 담당자는 별도 경로에 저장한 JSON에서 `executed_at`, `python_version`, `platform`, `result`를 확인하여 검증 기록에 반영한다.

코드나 실행 절차를 변경하지 않았다면 수정 후 재실행 결과에 '변경 없음'으로 기록한다.

독립 재현 및 필요한 재검증이 완료되기 전까지 W1-08을 최종 완료로 처리하지 않는다.

## 7. 연계 및 미확정 사항

| 관련 작업 | 연계 내용 | 현재 상태 |
|---|---|---|
| W1-04 | 공통 상품 데이터 구조 및 식별자 규칙 | PR #1 검토 대기 |
| W1-06 | PoC 실행 기록 공식 양식 | 담당자 산출물 확인 필요 |
| W1-07 | 외부 플랫폼 API·권한·인증 정책 | 담당자 산출물 확인 필요 |

W1-08의 샘플 코드는 공통 Python 실행 환경 확인용이며, W1-04 전체 데이터 계약을 검증하지 않는다.

W1-06·W1-07 공식 산출물이 확정되면 기록 형식과 인증 정책을 대조하여 필요한 내용을 반영한다.

WBS v1.2에 따른 W1-08 완료 기준은 다른 팀원의 샘플 재현 성공이며, 현재는 검토 대기 상태다.
