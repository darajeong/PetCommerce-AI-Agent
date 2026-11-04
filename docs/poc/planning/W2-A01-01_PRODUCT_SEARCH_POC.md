# W2-A01-01 상품 검색 PoC 통합 기록

## 1. 기본 정보

| 항목 | 내용 |
|---|---|
| PoC ID | A01-01 |
| 담당 | E |
| 검토 | D |
| 실행일 | 2026-11-03 (KST) |
| 데이터 구분 | 실제 공개 페이지 / AI 검색 도구 경유 관찰 / 자동 HTTP 요청 |
| 출처 기록 | `W2-A01-01_LIVE_RESULT.json`, `W2-A01-01_HTTP_RESULT.json`, `W2-A01-01_REPORT.md`, `W2-A01-01_LIVE_REPORT.md` |

이 문서의 내용은 위 기존 기록에서만 가져왔다. 기록에 없는 항목은 "근거 없음"으로 적었다.

## 2. 판정

| 대상 | 판정 |
|---|---|
| Alibaba.com | 조건부. 후보 URL 5건을 AI 검색 도구 경유로 관찰(상세 미확인, 시각 일괄 기록). 사람이 2026-11-04에 URL 5건을 열어 확인했다(5건 모두 O, 존재와 유형만 확인). 자동 수집 불가(W1-07 초안)와의 관계는 팀 결정 기록을 따른다. |
| 타오바오 | 외부 제약. W1-07 초안상 자동 수집은 사전 서면 허가 필요. 검색 시 로그인 요구가 사람 확인으로 확인되었다(아래 '사람 확인 결과' 참고). |
| 1688 | 외부 제약. W1-07 초안상 자동 수집 금지. 비로그인 열람은 가능하나 자동 수집은 금지(W1-07 초안). 사람이 열람한 범위만 확인했다(아래 '사람 확인 결과' 참고). |
| 로그인 전후 비교 | 보류 |
| 카테고리·가격 필터 | 보류 |

### 사람 확인 결과 (2026-11-04)
사람이 브라우저(비로그인, 시크릿 창)로 확인, 검색어 `大型犬胸背带` 1회:
- 타오바오: 홈 화면은 로그인 없이 표시. 검색 시 로그인 요구 화면(비밀번호·문자 로그인)이 뜨고 결과 영역은 표시되지 않음. 로그인·인증 시도 없음.
- 1688: 홈 화면과 검색 결과가 로그인 없이 표시. 결과 화면 캡처 1장만 확보했고 개별 상품은 열람하지 않음.
- 캡처는 로컬 보관(저장소 미포함).

## 3. 후보 5건

- 관찰 방법: AI 검색 도구 경유 관찰(공개 wholesale 목록 페이지 기준). 상세 미확인, 확인 시각 일괄 기록. 사람이 2026-11-04에 후보 5건의 URL을 각각 열어 존재와 유형(하네스)만 확인했다. 옵션·규격·리뷰는 확인하지 않았다.
- 확인 시각: 2026-11-03T14:44:35+09:00 (5건 동일, 개별 시각 아님)
- 목록 페이지(source_url): `https://www.alibaba.com/wholesale/large-dog-harness-soft-adjustable.html`
- 5건 모두 하네스(dog harness) 유형이다.
- 통화: 모두 `$` 기호만 확인했고 USD로 명시된 근거는 없다.

| # | url | 목록 제목 | 표시 가격 | detail_observation | 사람 확인(2026-11-04) | 비고 |
|---|---|---|---|---|---|---|
| 1 | https://www.alibaba.com/product-detail/Adjustable-Dog-Lift-Harness-Dog-Sling_1601429812402.html | Adjustable Dog Lift Harness Dog Sling for Large Dogs | 2.70-3.20 | empty_body | O | 하네스. 상세 미확인 |
| 2 | https://www.alibaba.com/product-detail/Reflective-No-Choke-Pet-Oxford-Vest_62319506552.html | Reflective No Choke Pet Oxford Vest Harness | 4.33-5.87 | empty_body | O | 하네스. 상세 미확인 |
| 3 | https://www.alibaba.com/product-detail/Adjustable-MOLLE-Tactical-Dog-Vest-Harness_1601919542060.html | Adjustable Reflective Quick Release MOLLE Tactical Dog Vest Harness | 5.50-5.90 | tool_cache_miss | O | 하네스. 상세 미확인 |
| 4 | https://www.alibaba.com/product-detail/MIDEPET-Factory-Wholesale-Non-Stop-Dog_1601174812743.html | MIDEPET Non Stop Dog Wear Harness | 1.17-4.18 | empty_body | O | 하네스. 상세 미확인 |
| 5 | https://www.alibaba.com/product-detail/Soft-Padded-Adjustable-Reflective-No-Pull_11000021320298.html | Soft-Padded Adjustable Reflective No-Pull Harness | 2.92-3.90 | tool_cache_miss | O | 하네스. 상세 미확인 |

제목은 목록에 표시된 짧은 설명 라벨이며 상품 상세 페이지에서 확인한 값이 아니다. 각 건의 verification 값은 "listing title/price and outbound URL observed; detail information not confirmed"이다.

**제외 1건**
- url: `https://www.alibaba.com/product-detail/Custom-logo-Reusable-Soft-Silicone-Ear_1601345098399.html`
- 사유: 목록 제목과 URL 슬러그 불일치. 후보 수에 포함하지 않았다.

## 4. 요청 기록

### 자동 HTTP 요청 (`HTTP_RESULT.json`, 2026-11-03 KST)

| 시각 | 도메인 | 경로 종류 | 상태 코드 |
|---|---|---|---|
| 14:46:15.418 | s.taobao.com | 검색(`/search?q=`) | 200 |
| 14:46:15.484 | www.alibaba.com | 검색(`/trade/search?SearchText=`) | 200 |
| 14:46:16.236 | s.1688.com | 검색(`/selloffer/offer_search.htm?keywords=`) | 200 |

- 요청 횟수: 3회 (플랫폼당 1회)
- 요청 간격: 약 0.07초, 약 0.75초
- robots.txt 확인 기록: 없음
- AI 검색 도구 경유 요청 횟수: 근거 없음

## 5. HTTP 200의 의미

응답 수신, 내용 미확인(상품 목록인지 로그인 페이지인지 구분 기록 없음). 이 요청들로는 상품 데이터, 로그인 요구, CAPTCHA 여부를 판단할 수 없다.

AI 검색 도구가 타오바오·1688 페이지를 열지 못한 기록(`LIVE_RESULT.json`)은 도구 오류이며, 플랫폼의 차단·로그인 요구를 관찰한 기록이 아니다.

## 6. 미확인·한계

- 후보 유형이 하네스 하나뿐이다. A02·B04-02에 필요한 서로 다른 유형 3개가 아직 없다.
- 상세 정보 미확인.
- 확인 시각은 일괄 기록이며 개별 확인 시각이 아니다.
- 로그인 전후 차이: 비로그인 상태만 확인(타오바오는 검색 시 로그인 요구, 1688은 결과 표시). 로그인 후 상태는 미확인. 지역·세션 제한, 카테고리·가격 필터 적용 여부: 미확인.
- 통화(USD) 명시 근거 없음.

## 7. 대체 경로 (W1-07)

수동 입력 → JSON·CSV 테스트 데이터

## 8. 후속 (사람이 수행)

1. 후보 5개를 브라우저로 열어 확인한다. 완료(2026-11-04)
2. 타오바오·1688 접근 화면을 캡처한다. 완료(2026-11-04)
3. 방석·장난감 후보를 수동으로 확보한다.
4. 팀 결정 기록을 PR #3에 남긴다.
