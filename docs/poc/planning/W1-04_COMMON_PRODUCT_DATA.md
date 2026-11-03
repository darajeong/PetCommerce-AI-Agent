# W1-04 공통 상품 데이터 구조 v0.1

> 상태: **리뷰 수정안 / Mock 계약 테스트 재실행 / 검토 담당 A 재확인 대기**
> 기준: PetCommerce AI Agent WBS v1.2 · W1-04
> 주 담당: E · 검토 담당: A
> 작업 목표: A02 원본(`product`)과 A03 번역·정규화 결과(`normalized_data`)를 B01·B02·B04가 정의된 경로와 타입으로 읽도록 한다.
> 범위: PoC용 JSON 계약. DB 테이블/API 구현 및 운영환경 성능 보장은 W6 이후 별도 작업이다.

## 1. 식별자·버전·공통 원칙

| 필드 | 타입 | 필수 | 예시·의미 |
|---|---|---|---|
| `schema_version` | string | 예 | `0.1` — JSON 계약 버전 |
| `product_id` | string | 예 | `prod-demo-001` — 상품 식별자, 실행이 바뀌어도 유지 |
| `category_id` | string | 예 | `pet_bedding` — 분류 코드(초기 PoC 임시값) |
| `run.run_id` | string | 예 | `run-demo-001` — 상품 처리 **전체 실행** ID |
| `run.job_id` | string 또는 null | 조건부 | `null` — 비동기 작업 ID, 큐 작업이 없으면 null. 아키텍처의 `job_id`와 구분 |
| `run.status` | enum | 예 | `success` — 전체 실행 상태 |
| `run.started_at`, `run.ended_at` | ISO 8601 string 또는 null | 예 | 실행 시작·종료 시각 |
| `input_version` | integer(≥1) | 예 | `1` — 이번 실행이 읽은 공통 상품 데이터 스냅샷 버전 |
| `source_version` | integer(≥1) | 예 | `1` — 원본 데이터 스냅샷 버전 |
| `agent_outputs.<ID>.result_version` | integer(≥1) | 해당 Agent 실행 시 | `1` — 해당 Agent의 출력 버전 |

- `run_id`는 하나의 상품 처리 흐름을 묶는다. `job_id`는 백그라운드 실행 단위가 생길 때 따로 발급하며, **같은 값으로 가정하지 않는다**. W5의 아키텍처 확정 시 명명과 대응을 최종 승인한다.
- `input_version`, `source_version`, `result_version`은 별개의 개념이다. 재실행으로 입력이나 출력이 바뀌면 기존 결과를 덮어쓰지 않고 새 버전을 만든다.
- 모든 Agent는 같은 `product_id`, `run.run_id`, `input_version`을 참조한다. Agent별 결과는 `agent_outputs.<Agent ID>`에 저장한다.
- **원본 변경 주체:** A02 또는 관리자 수동 입력(E04 승인·이력 경유)만 **새 `source_version`**을 생성할 수 있다. A03·B01·B02·B04·B05·C02는 원본을 읽기만 하며 변경할 수 없다. 원본 정정 시 사유·승인자·변경시각과 이전 버전 참조를 남긴다.
- PoC 예시 URL·상품·이미지·리뷰·환율·분석 결과는 **전부 합성 Mock 데이터**다. 실제 판매 상품·권리·가격·안전 정보를 주장하지 않는다.

## 2. A02 상품 원본 스키마: `product`

`product` 안에는 다른 Agent가 바로 사용할 **값**을 두고, 출처·Mock 여부·누락 사유는 같은 경로를 키로 갖는 `field_meta` 및 `missing_fields`에 둔다. 배열의 개별 항목은 자체 `data_type`과 `source_url`도 갖는다. 이 방식은 `product.description` 등의 경로를 별도 변환 없이 읽게 해준다.

| 경로 | 타입 | 필수* | 예시 |
|---|---|---|---|
| `product.source_url` | string(URL) | 예 | `https://example.com/items/sample-001` |
| `product.platform` | string | 예 | `mock_catalog` / 실제 값 예: `taobao`, `alibaba` |
| `product.collection_method` | enum(`auto`,`manual`,`mock`) | 예 | `mock` |
| `product.collected_at` | ISO 8601 string | 예 | `2026-11-02T10:00:00+09:00` |
| `product.original_name` | string 또는 null | 예 | `Large Pet Mat` |
| `product.description` | string 또는 null | 예 | `Soft washable pet mat. Size 800 x 600 mm.` |
| `product.description_id` | string | 예 | `desc-001` — 설명문 근거 참조 ID |
| `product.original_price.amount` | number 또는 null | 예 | `100.0` |
| `product.original_price.currency` | string(ISO 통화코드) 또는 null | 예 | `CNY` |
| `product.options[]` | object[] | 예 | `{"option_id":"opt-01","name":"size","value":"L"}` |
| `product.dimensions` | object 또는 null | 예 | `{"length":800,"width":600,"height":100,"unit":"mm"}` |
| `product.weight` | object 또는 null | 예 | `{"value":2.5,"unit":"kg"}` |
| `product.material` | string[] 또는 null | 예 | `["polyester"]` |
| `product.recommended_pet_weight_max` | number 또는 null | 예 | `null` — 확인 안 된 하중은 추정 금지 |
| `product.sales_count` | integer 또는 null | 예 | `null` |
| `product.rating` | number 또는 null | 예 | `4.5` |
| `product.shipping` | object 또는 null | 예 | `{"method":"standard","fee":null,"currency":"CNY"}` |
| `product.supplier` | object 또는 null | 예 | `{"supplier_id":"sup-001","name":"Demo Seller"}` |
| `product.images[]` | object[] | 예 | 이미지별 ID·번호·URL·용도별 권한·출처 |
| `product.reviews[]` | object[] | 예 | 리뷰별 ID·원문·평점·용도별 권한·출처 |

\* **필수**는 JSON **키가 존재해야 한다는 뜻**이다. 원본에서 값을 얻지 못하면 `null` 또는 `[]`로 두고 `missing_fields`에 구체적인 누락 경로와 사유를 남긴다. 무조건 실제 값이 있어야 PoC가 성공한다는 뜻은 아니다.

**이미지 항목:** `image_id:string`, `image_no:integer`, `image_role:enum(main,detail,other)`, `url:string`, `source_url:string`, `rights_status:enum(usable,needs_review,prohibited)`, `usage:object`, `usage_policy_url:string|null`, `usage_checked_at:ISO 8601 string|null`, `data_type:enum(actual,test,mock)`를 요구한다. `image_role`은 대표·상세·기타 이미지를 구분한다.

**리뷰 항목:** `review_id:string`, `text:string`, `rating:number|null`, `source_url:string`, `rights_status:enum(usable,needs_review,prohibited)`, `usage:object`, `usage_policy_url:string|null`, `usage_checked_at:ISO 8601 string|null`, `data_type:enum(actual,test,mock)`를 요구한다. 리뷰 단위 누락도 `missing_fields` 경로(예: `product.reviews[0].rating`)로 기록한다.

**용도별 권한(이미지·리뷰 공통):** `usage.store`(저장), `usage.ai_input`(AI 분석 입력), `usage.display`(결과 화면 표시), `usage.resale`(판매 콘텐츠 재사용) 네 필수 키의 값은 각각 `allowed`, `prohibited`, `needs_review` 중 하나다. `resale`은 **자료를 판매 콘텐츠에 재사용**한다는 뜻이며 상품 재판매 허가가 아니다. 근거 정책 URL은 `usage_policy_url`, 확인 일시는 `usage_checked_at`에 기록한다. 확인 전 기본값은 네 용도 모두 `needs_review`, 정책 URL·확인 일시는 `null`이다. 사용 조건이 미확인된 자료를 판매 콘텐츠에 재사용하지 않는다. 각 사용 행위는 해당 용도가 `allowed`일 때만 허용한다.

**권리 요약 일치 규칙:** 네 용도 중 하나라도 `prohibited`이면 `rights_status=prohibited`, 네 용도가 전부 `allowed`이면 `rights_status=usable`, 그 외는 `rights_status=needs_review`여야 한다. `rights_status`는 요약 정보이며 개별 용도의 사용 허용을 대신하지 않는다. 요약과 용도별 판정이 불일치하면 검증 실패 처리한다.

**필드별 출처:** `field_meta`의 키는 실제 JSON 경로다(예: `product.description`). 값은 `data_type`, `source_url`, `source_id`, `collected_at`을 포함한다. 값이 null인 경우에도 `field_meta`를 유지하며 `missing_fields`에 누락 원인을 추가한다. `product.images[]`와 `product.reviews[]`는 개별 항목의 `data_type` 및 출처를 우선한다. 동일 데이터에서 실제와 Mock의 혼합이 가능하되 혼합 사실을 감추지 않는다.

**누락 사유 코드 (5종):** `source_missing`(원본 정보 없음), `login_required`(로그인 필요), `access_restricted`(접근 제한), `collection_failed`(수집 실패), `manual_review_required`(수동 확인 필요). `missing_fields[]`의 항목은 `{ "field_path": string, "reason": enum, "next_action": string }` 형태다. 사용 권한 미확인은 `usage.*=needs_review`와 요약 `rights_status=needs_review`로 별도 관리한다.

## 3. A02 → B01·B02·B04 직접 사용 관계

| Agent | **직접 읽는 JSON 경로** | 처리 내용 | 결과 위치 |
|---|---|---|---|
| A03 | `product.original_name`, `product.description`, `product.reviews[].text`, `product.original_price`, `product.dimensions`, `product.weight`, `product.options[]` | 번역·정규화 | 데이터: `normalized_data` / 상태·근거·버전 봉투: `agent_outputs.A03` |
| **B01** | **`product.images[]`, `product.description`, `normalized_data.translated_description`** | 이미지와 번역 설명 비교, 원문 설명과 근거 연결 | `agent_outputs.B01` |
| **B02** | **`product.reviews[].text`, `product.reviews[].rating`, `normalized_data.translated_reviews[]`** | 번역 리뷰 분석, `review_id`로 원문·평점·근거 연결 | `agent_outputs.B02` |
| **B04** | **`product.dimensions`, `product.weight`, `product.material`, `product.reviews[]`, `product.recommended_pet_weight_max`, `normalized_data.normalized_dimensions`, `normalized_data.normalized_weight`** | 정규화된 크기·무게로 평가하고 원본·리뷰와 근거 비교(정보 부족 표시) | `agent_outputs.B04` |
| B05 | `agent_outputs.B01.result`, `agent_outputs.B02.result`, `agent_outputs.B04.result`, `product.original_price` | 점수·등급 계산 | `agent_outputs.B05` |
| C02 | `product`, `normalized_data`, `agent_outputs.B01/B02/B04/B05` | 상세페이지·주의사항 | `agent_outputs.C02` |
| E04 | `run`, `agent_outputs`, `approval`, `errors` | 실행 상태·승인·오류 관리 | 실행 이력 |

**검증 조건:** A02가 만든 원본 `product`를 다른 키 이름으로 복사·재가공하지 않고 위 경로로 읽을 수 있어야 한다. A03가 만드는 번역·정규화 결과는 `normalized_data`의 정의된 경로로 읽는다. 누락 시 Agent는 추측으로 채우지 않고 누락 사유를 참조해 `needs_review` 또는 `partial_success`를 반환한다.

**선행 데이터 조건:** B01·B02·B04는 A03의 관련 번역·정규화 결과를 읽고 `product` 원본은 근거·변환 전후 비교에 사용한다. A03 결과가 없거나 필수 변환이 실패한 경우 원본만으로 정상 판정을 확정하지 않는다.

## 4. A03 정규화·번역 규칙

`normalized_data`가 **번역·정규화 내용의 기준 저장 위치**이며 원본 `product`는 수정하지 않는다. `agent_outputs.A03`은 상태·오류·근거·버전 봉투이며 `result`에는 `normalized_data`의 참조(예: 스냅샷 버전)만 저장한다. A 담당자는 W2 A03에서 이 봉투 샘플을 추가한다.

- `translated_name`, `translated_description`, `translated_reviews[]`(각 `review_id`, `translated_text`)를 저장한다. `review_id`가 `product.reviews[]`와 일치해야 한다.
- `normalized_data.normalized_dimensions`는 `{length, width, height, unit:"cm"}`(길이·폭·높이는 number 또는 null), `normalized_data.normalized_weight`는 `{value, unit:"kg"}`(무게는 number 또는 null)로 저장한다. 각 숫자는 `conversions[]`에서 대응 원본 `field_path`(`product.dimensions.length/width/height`, `product.weight.value`)와 연결된다. 이미 기준 단위인 값도 변환 전후가 같음을 기록한다.
- `conversions[]`의 각 항목은 `field_path`, `original_value`, `original_unit`, `normalized_value`, `normalized_unit`, `conversion_rate`(사용 시), `rate_source`, `converted_at`을 기록한다.
- 예를 들어 가격은 CNY → KRW 환산값, 크기는 mm → cm 변환값을 **원본과 함께** 남긴다. 환율이 실측이 아닌 경우 `data_type:mock`을 표시하고 실제 가격 결정에는 사용하지 않는다.
- **v0.2 예정(W2 초, A03-02 착수 전):** 소재·권장 체중 정규화(권장 체중 단위 정의 포함), 중복·누락 표시 기준, 변환 불가 사유·검증 범위, `usage_checked_at`의 ISO 8601 형식 검사를 A 담당자의 A03·A02 작업과 함께 확정한다.

## 5. Agent 공통 출력 봉투(envelope)

각 Agent의 `agent_outputs.<Agent ID>`는 다음 필드를 동일한 이름과 타입으로 사용한다.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `run_id`, `product_id`, `agent_id` | string | 예 | 실행·상품·Agent 식별 |
| `input_version`, `result_version` | integer | 예 | 읽은 입력 버전 / 저장한 결과 버전 |
| `status` | enum | 예 | 아래 상태 코드 중 실행 단계에 맞는 값 |
| `result` | object | 예 | Agent 고유 결과; 실패 시 빈 객체 허용 |
| `evidence_ids` | string[] | 예 | `evidence[]` 상세 근거 ID 참조 |
| `warnings` | string[] | 예 | 사람 확인이 필요한 제약·경고 |
| `errors` | object[] | 예 | 표준 오류 구조(없으면 빈 배열) |
| `retry_count` | integer(≥0) | 예 | 자동 재시도 횟수 |
| `started_at`, `ended_at` | ISO 8601 string 또는 null | 예 | 실행 시각 |
| `data_type` | enum(`actual`,`test`,`mock`) | 예 | **결과 자체의** 생성 환경. 개별 원본의 실제/Mock 여부는 `field_meta`·배열 항목을 따른다. |

**상태 코드 10종:** `pending`(대기), `running`(실행 중), `success`(성공), `partial_success`(부분 성공), `failed`(실패), `needs_review`(검토 필요), `approval_pending`(승인 대기), `approved`(승인 완료), `rejected`(반려), `on_hold`(보류).

- **전체 실행 상태**: `run.status` — 전체 흐름의 현재 상태.
- **단계 상태**: 각 `agent_outputs.<Agent ID>.status` — 해당 단계의 처리 상태.
- **승인 상태**: `approval.status` — `not_requested`, `approval_pending`, `approved`, `rejected`만 사용. 실행 상태와 혼용 금지.
- `errors[]` 항목은 `agent_id`, `stage`, `error_type`, `cause`, `auto_retryable`, `retry_count`, `manual_fallback_possible`, `mock_fallback_possible`, `next_action`을 기록한다. 네트워크·API의 일시 오류만 최대 2회 자동 재시도하며 인증·접근 제한은 자동 재시도하지 않는다.

## 6. 근거·승인 구조

**`evidence[]` 항목:** `evidence_id`, `target_path`, `source_type`(`image`,`review`,`description`,`product_field`), `source_id`, `quote_or_value`, `source_url`.

- 판단 또는 수치가 들어간 `result`의 중요 주장마다 `evidence_id`를 연결한다. 식별자는 `product.images[].image_id`, `product.reviews[].review_id`, `product.description_id` 또는 `product.<field>`의 원본 필드를 참조한다.
- 검증 시 모든 참조 ID가 존재하는지 검사한다. 중요한 주장에 근거가 없으면 승인하지 않는다.

**`approval` 필드:** `status`, `target_version`, `approver`, `approved_at`, `reason`. 승인 실행 전에 `target_version`을 `agent_id:result_version` 형태로 지정하고 현재 결과 버전과 일치하는지 확인한다. 이전 버전 승인을 새 버전에 재사용하지 않는다. 승인 이력에는 시간·승인자·사유를 남긴다.

## 7. PoC 예시와 검증 방법

- JSON 예시: [`samples/W1-04_SAMPLE_PRODUCT.json`](../samples/W1-04_SAMPLE_PRODUCT.json)
- 검증 스크립트: [`samples/validate_w1_04.py`](../samples/validate_w1_04.py) — Python 표준 라이브러리만 사용한다.
- 테스트 실행(프로젝트 루트): `python docs/poc/samples/validate_w1_04.py`
- 의도적 오류 검출 실행: `python docs/poc/samples/validate_w1_04.py --self-test`
- A02의 `agent_outputs.A02.result`는 원본 저장 여부와 버전 기록용 메타데이터다. 실제 상품 원본은 `product`에 저장하므로 A02의 `evidence_ids`는 빈 배열일 수 있다.
- 합성 Mock JSON에서 A02 → B01·B02·B04 데이터 필드 호환성과 근거·상태·버전 구조를 점검했으며, 의도적 오류 **18종**이 검출되는 것을 확인했다. 수정 후 로컬 실행 로그를 PR 증빙으로 첨부한다.
- 알려진 한계: `normalized_data.conversions[]`의 원본·변환 메타데이터는 기본적인 경로·값·단위 대응을 검사하나 변환의 의미·환율 진실성까지 보장하지 않는다. W2 A03 또는 v0.2에서 보강한다.
- B05·C02 샘플 데이터와 연계 검증은 v0.2 또는 해당 Agent PoC에서 추가한다.
- 주의: 이 검증은 **샘플 데이터 형식과 참조 연결**만 확인한다. 실제 상품 3건, 원본 권한 및 Agent의 실제 처리 품질 검증은 W2~W5 작업이다.

## 8. WBS W1-04 완료 체크리스트

- [x] 공통 상품 ID, 실행 ID, 비동기 job ID 대응 관계 정의
- [x] 상품명·설명·가격·배송·공급처·이미지·리뷰 등 필드/타입/필수 여부 정의
- [x] A02 → B01/B02/B04 필드 단위 사용 관계 정의
- [x] 원본 변경 가능 주체·버전/수동 입력 규칙 정의
- [x] 실제·테스트·Mock 정보와 누락 사유를 필드·항목 단위로 기록하는 규칙 정의
- [x] Agent 출력·실행 상태·근거·오류·승인 구조 정의
- [x] 합성 샘플 JSON 작성
- [x] 수정본 로컬 샘플 검증 및 오류 주입 테스트 실행(로그 별도 첨부)
- [ ] 검토 담당 A 리뷰·승인

**판정:** 리뷰 수정안(Mock 샘플 구조 및 의도적 오류 18종 검출 통과, A 재검토·승인 대기). W1-08 공통 실행 환경과 W2 A01-01 상품 검색 결과에서 필요해지는 필드가 있으면 근거와 함께 v0.2로 변경한다.