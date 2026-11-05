# W2-A01-01 상품 검색 PoC 통합 기록

## 1. 기본 정보

| 항목 | 내용 |
|---|---|
| PoC ID | A01-01 |
| 담당 | E |
| 검토 | D |
| 실행일 | 2026-11-03 (KST), 추가 조사 2026-11-05 |
| 데이터 구분 | 실제 공개 페이지 / AI 검색 도구 경유 관찰(2026-11-03, 2026-11-05) / 자동 HTTP 요청 / 사람 직접 확인(2026-11-04, 2026-11-05) |
| 출처 기록 | `W2-A01-01_LIVE_RESULT.json`, `W2-A01-01_HTTP_RESULT.json`, `W2-A01-01_REPORT.md`, `W2-A01-01_LIVE_REPORT.md` (원본 기록은 로컬 보관, 저장소 미포함) |

이 문서의 내용은 위 기존 기록에서만 가져왔다. 기록에 없는 항목은 "근거 없음"으로 적었다.

## 2. 판정

| 대상 | 판정 |
|---|---|
| Alibaba.com | 조건부. 후보 URL 5건을 AI 검색 도구 경유로 관찰(상세 미확인, 시각 일괄 기록). 사람이 2026-11-04에 URL 5건을 열어 확인했다(5건 모두 O, 존재와 유형만 확인). 자동 수집 불가(W1-07 초안)와의 관계는 팀 결정 기록을 따른다. 2026-11-05에 방석·장난감 후보 6건을 추가했다(§3). |
| 타오바오 | 외부 제약. W1-07 초안상 자동 수집은 사전 서면 허가 필요. 검색 시 로그인 요구가 사람 확인으로 확인되었다(아래 '사람 확인 결과' 참고). |
| 1688 | 외부 제약. W1-07 초안상 자동 수집 금지. 비로그인 열람은 가능하나 자동 수집은 금지(W1-07 초안). 사람이 열람한 범위만 확인했다(아래 '사람 확인 결과' 참고). |
| 로그인 전후 비교 | 보류 |
| 카테고리·가격 필터 | 보류 |

### 사람 확인 결과 (2026-11-04)
사람이 브라우저(비로그인, 시크릿 창)로 확인, 검색어 `大型犬胸背带` 1회:
- 타오바오: 홈 화면은 로그인 없이 표시. 검색 시 로그인 요구 화면(비밀번호·문자 로그인)이 뜨고 결과 영역은 표시되지 않음. 로그인·인증 시도 없음.
- 1688: 홈 화면과 검색 결과가 로그인 없이 표시. 결과 화면 캡처 1장만 확보했고 개별 상품은 열람하지 않음.
- 캡처는 로컬 보관(저장소 미포함).

## 3. 후보 11건 (하네스 5, 방석 3, 장난감 3)

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
| 6 | https://www.alibaba.com/product-detail/Gray-Pet-Cushion-Mattress-Rectangular-Quilted_1601917372981.html | Gray Pet Cushion Mattress Rectangular Quilted Dog Bed for Medium Large Pets Wholesale Supplier | $14.04-26.91 | tool_cache_miss(검색 도구 링크 조회 시도, 상세 미확인) | O | 방석(매트리스). 판매량: 미표시. 상품 평점: 미표시. 출처 B, 시각 B1 |
| 7 | https://www.alibaba.com/product-detail/Wholesale-Washable-Dog-Beds-for-Large_1600570388952.html | Wholesale Washable Dog Beds for Large Dogs Mattress Comfortable and Warming Rectangle | $8.23-9.46 | empty_body(검색 도구 링크 조회 시도, 상세 미확인) | O | 방석(직사각형 매트리스). 판매량: 미표시. 상품 평점: 미표시. 출처 B, 시각 B2 |
| 8 | https://www.alibaba.com/product-detail/Wholesale-Custom-Faux-Fur-Solid-Modern_1601609680769.html | Wholesale Custom Faux Fur Solid Modern Fashion Classic Warm Calm Large Dog Sofa Bed for Large Dogs | $2.69-8.85 | tool_cache_miss(검색 도구 링크 조회 시도, 상세 미확인) | O | 방석(소파형). 판매량: 1 sold. 상품 평점: 미표시. 출처 B, 시각 B3 |
| 9 | https://www.alibaba.com/product-detail/Woof-Pupsicle-Long-Lasting-Interactive-Dog_1601391234725.html | Long-Lasting Interactive Dog Toy Ball Freeze Treats Toy Eco-Friendly Food Grade Silicone Dog Chew Lick Toys for Large Dogs | $1.85-3.70 | empty_body(검색 도구 링크 조회 시도, 상세 미확인) | O | 장난감(씹기·핥기용 공). 판매량: 3,609 sold. 상품 평점: 미표시. 출처 T, 시각 T1 |
| 10 | https://www.alibaba.com/product-detail/Customization-Concave-Convex-Texture-EVA-Large_1601639168945.html | Custom Concave-Convex Texture EVA Dog Toys Large Bite Stick Floatable Pet Chew Toys for Large Dog Training and Throwing Game | $1.80-2.20 | empty_body(검색 도구 링크 조회 시도, 상세 미확인) | O | 장난감(씹는 막대). 판매량: 129 sold. 상품 평점: 미표시. 출처 T, 시각 T2 |
| 11 | https://www.alibaba.com/product-detail/Dog-Chew-Bones-For-Aggressive-Chewers_1601055834113.html | Dog Chew Bones for Aggressive Chewers Large Breed Real Beef Flavor Durable Dog Chew Toys Nearly Indestructible Tough Dog Toys | $2.25-2.50 | empty_body(검색 도구 링크 조회 시도, 상세 미확인) | O | 장난감(뼈 모양 씹기용). 판매량: 미표시(2 views는 조회수). 상품 평점: 미표시. 출처 T, 시각 T3 |

신규 후보 6~11번 사람 확인 날짜는 2026-11-05이다(표 머리글의 2026-11-04는 기존 1~5번에만 적용). 사람이 2026-11-05에 6건 모두 브라우저에서 직접 열어 정상 열림 및 상품 유형을 확인하고 O로 기록했다. 확인 범위는 URL 접근 및 상품 유형에 한정하며, 상세 정보 수집 완료나 대형견 안전성 검증 완료를 의미하지 않는다. 아래 검색 도구 관찰 기록은 사람 확인 전 당시 상태로 보존한다.

제목은 목록에 표시된 짧은 설명 라벨이며 상품 상세 페이지에서 확인한 값이 아니다. 각 건의 verification 값은 "listing title/price and outbound URL observed; detail information not confirmed"이다.

**제외 1건**
- url: `https://www.alibaba.com/product-detail/Custom-logo-Reusable-Soft-Silicone-Ear_1601345098399.html`
- 사유: 목록 제목과 URL 슬러그 불일치. 후보 수에 포함하지 않았다.

### 2026-11-05 추가 조사: 검색 출처·확인 시각·한계

아래는 2026-11-05의 신규 6~11번에만 적용되는 추가 기록이다. 기존 제목·설명·판정·한계·후속 문구와 사람 확인(2026-11-04)은 기존 1~5번 조사 시점의 기록으로 보존했다. 신규 후보의 URL·가격 등은 검색 도구 관찰로 확보했고 사람 확인(2026-11-05)은 위 표에 기록했으며, 이번 문서 정리 과정에서는 재검색·재조회하지 않았다.

- 방법: 공개 웹 검색 도구 `web.run`의 검색 결과와 공개 목록 텍스트 관찰. URL 확보는 이 도구 관찰로 했고, 사람이 2026-11-05에 6건을 브라우저로 직접 열어 존재와 유형만 확인했다(O). 이 결과를 A02·B04-02의 검증 완료나 PoC 성공으로 처리하지 않는다.
- 검색어: `large dog bed`, `large dog cushion`, `large dog chew toy`, `durable dog toy for large dogs`에 Alibaba.com 상품 경로 조건을 붙여 검색했다. 후속으로 대형견 bed/chew와 관찰한 목록 제목을 이용해 검색했다. 검색 결과에서 아래 공개 목록을 찾고 해당 목록의 상품 링크 연결 대상을 검색 도구로 확인했다. URL 슬러그나 상품 ID를 추측해 만들지 않았다.
- 출처 B: [Bulk Dog Beds 공개 목록](https://www.alibaba.com/picks/bulk-dog-beds.html), 관찰 응답 완료 시각 `2026-11-05T09:54:02+09:00`. 도구 캐시 표시는 `Crawled: 6 days ago`. 6번은 Gray Pet Cushion, 7번은 Washable Dog Beds for Large Dogs, 8번은 Faux Fur Large Dog Sofa Bed 항목이다.
- 출처 T: [Large chew toy 공개 목록](https://www.alibaba.com/wholesale/large-chew-toy.html), 관찰 응답 완료 시각 `2026-11-05T09:53:38+09:00`. 도구 캐시 표시는 `Crawled: 3 months ago`. 9번은 Long-Lasting Interactive Dog Toy Ball, 10번은 EVA Bite Stick, 11번은 Dog Chew Bones 항목이다.

| 시각 ID | 후보 | 상품 링크 조회 응답 완료 시각(KST) | 검색 도구 관찰 결과 |
|---|---|---|---|
| B1 | 6 | 2026-11-05T09:54:13+09:00 | 연결 대상 상품 URL 노출, Cache miss. 상세 내용 미확인 |
| B2 | 7 | 2026-11-05T09:54:28+09:00 | 연결 대상 상품 URL 노출, 본문 0줄. 상세 내용 미확인 |
| B3 | 8 | 2026-11-05T09:54:43+09:00 | 연결 대상 상품 URL 노출, Cache miss. 상세 내용 미확인 |
| T1 | 9 | 2026-11-05T09:54:57+09:00 | 연결 대상 상품 URL 노출, 본문 0줄. 상세 내용 미확인 |
| T2 | 10 | 2026-11-05T09:55:14+09:00 | 연결 대상 상품 URL 노출, 본문 0줄. 상세 내용 미확인 |
| T3 | 11 | 2026-11-05T09:55:29+09:00 | 연결 대상 상품 URL 노출, 본문 0줄. 상세 내용 미확인 |

- 신규 6~11번 verification: `공개 목록의 제목·표시 가격·상품 링크 연결 대상 URL 관찰; 상세 내용 및 현재 페이지 유효성 미확인; 수동 확인 대기`. 링크 조회를 실제 시도했으므로 `detail_observation`에는 미시도 대신 도구가 반환한 오류/빈 본문을 기록했다. 위 verification 값의 "수동 확인 대기"는 도구 관찰 당시 상태이며, 이후 사람이 2026-11-05에 브라우저로 직접 열어 존재와 유형을 확인했다(O).
- 상품 유형은 목록 제목의 `Medium Large Pets`, `Large Dogs`, `Large Breed` 및 방석/매트리스·씹기 장난감 표현으로 분류했다. 실제 크기·하중·재질·내구성·안전성은 미확인이다. `Durable`, `Indestructible` 등은 관찰된 상품명의 표현일 뿐 성능 검증 결과가 아니다.
- 가격은 출처 B/T의 목록 관찰 응답을 기준으로 그대로 기록했다. 통화는 `$` 기호만 보였으며 USD 명시는 미확인이다. 옵션별 단가·수량 조건·배송비·세금·할인가 유효성은 미확인이다. 검색 요약과 목록 캐시의 가격·판매량이 달랐으므로 서로 섞지 않았다. 예: 9번 검색 요약은 `$1.66-3.33`, `3,405 sold`였으나 표는 출처 T의 `$1.85-3.70`, `3,609 sold`를 사용한다.
- `미표시`는 이번 도구가 반환한 목록 범위에서 표시되지 않았다는 뜻이며, 실시간 사이트에도 없다는 뜻은 아니다. B의 7번·8번 옆 `4.7/5.0 (143)`, `4.5/5.0 (15)` 및 T의 9~11번 옆 `4.8/5.0 (65)`, `4.9/5.0 (51)`, `4.8/5.0 (35)`는 공급업체와 연결된 평점으로 보여 상품 평점으로 전사하지 않았다. 평점 대상은 사람이 추가 확인해야 한다. 리뷰 내용은 조회·저장하지 않았다.
- 기존 1~5번 및 신규 6~11번의 상품 ID·URL은 서로 중복되지 않는다. 서로 다른 URL이 같은 실물 상품인지까지는 확인하지 못했다.
- 이번 Alibaba.com URL 열람 도구 입력은 공개 목록 3개(1개 Cache miss, 2개 텍스트 반환)와 상품 링크 6개로 총 9개다. 상품 링크 조회는 순차 실행했고 응답 후 10초 이상 기다렸다. 초기 목록 2개는 같은 도구 호출에 넣어 내부 요청 간격을 확인할 수 없다. 검색 도구의 실제 플랫폼 요청 수·캐시 사용·내부 재시도·요청 간격은 공개되지 않으므로 W1-07의 요청 수·간격 준수를 완전히 검증했다고 주장하지 않는다. 추가 플랫폼 열람은 중단했다. 스크립트 직접 HTTP 수집, 브라우저 자동화, 로그인·인증·CAPTCHA 처리, 쿠키·세션 재사용, 프록시·헤더 위장은 수행하지 않았다. 도구 오류·빈 본문을 플랫폼 차단이나 로그인 요구로 해석하지 않는다.
- 이미지 파일·상세 설명·리뷰는 수집하거나 저장하지 않았다. 검색 도구가 반환한 목록의 최소 정보만 문서에 기록했다.

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
- AI 검색 도구 경유 요청 횟수: 2026-11-03분은 근거 없음. 2026-11-05분은 §3 추가 조사 참고(공개 목록 3개, 상품 링크 6개)

## 5. HTTP 200의 의미

응답 수신, 내용 미확인(상품 목록인지 로그인 페이지인지 구분 기록 없음). 이 요청들로는 상품 데이터, 로그인 요구, CAPTCHA 여부를 판단할 수 없다.

AI 검색 도구가 타오바오·1688 페이지를 열지 못한 기록(`LIVE_RESULT.json`)은 도구 오류이며, 플랫폼의 차단·로그인 요구를 관찰한 기록이 아니다.

## 6. 미확인·한계

- 후보 유형은 하네스 5건(1~5번)과 방석·장난감 6건(6~11번)이다. 6~11번도 상세 정보는 확인하지 않았으며, 선정 3개의 유형 구성은 A01-02에서 정한다.
- 상세 정보 미확인.
- 확인 시각은 일괄 기록이며 개별 확인 시각이 아니다.
- 로그인 전후 차이: 비로그인 상태만 확인(타오바오는 검색 시 로그인 요구, 1688은 결과 표시). 로그인 후 상태는 미확인. 지역·세션 제한, 카테고리·가격 필터 적용 여부: 미확인.
- 통화(USD) 명시 근거 없음.

## 7. 대체 경로 (W1-07)

수동 입력 → JSON·CSV 테스트 데이터

## 8. 후속 (사람이 수행)

1. 후보 5개를 브라우저로 열어 확인한다. 완료(2026-11-04)
2. 타오바오·1688 접근 화면을 캡처한다. 완료(2026-11-04)
3. 방석·장난감 후보 6건: URL은 검색 도구 관찰로 확보하고 사람이 브라우저로 열어 확인한다. 완료(2026-11-05)
4. 팀 결정 기록을 PR #3에 남긴다.
