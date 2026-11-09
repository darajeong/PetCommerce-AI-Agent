# W2-A02-03 이미지·리뷰 목록과 사용 범위 점검표

> 담당 A / 검토 B · 선행: A02-02(PR #12), W1-04 v0.1, W1-07 1.1절(2026-11-06 확정)
> 완료 기준(WBS): 상품 3개 모두 이미지·상세 설명·리뷰를 확보하거나 누락 사유를 기록. 권장 기준: 상품별 이미지 5장·리뷰 20개, 출처 연결률과 사용 범위 기록률 100%.
> 작성일: 2026-11-09

## 1. 요약

| 상품 | 이미지 | 상세 설명 | 리뷰 | 실제 원문 처리 | 사용 범위 기록 |
|---|---|---|---|---|---|
| prod-w2-01 (1번 하네스) | 합성 5장 | 합성 1건 | 합성 20개 | 미수집 (`needs_review`), 실제 리뷰 수 13개만 기록 | 25/25 (100%) |
| prod-w2-07 (7번 방석) | 합성 5장 | 합성 1건 | 합성 20개 | 미수집 (`needs_review`), 실제 리뷰 수 0개만 기록 | 25/25 (100%) |
| prod-w2-09 (9번 장난감) | 합성 5장 | 합성 1건 | 합성 20개 | 미수집 (`needs_review`), 실제 리뷰 수 13개만 기록 | 25/25 (100%) |

- W1-07 1.1절에 따라 실제 상품의 이미지·상세 설명·리뷰 원문은 사용 권한이 `needs_review`라 저장·AI 입력·표시하지 않는다. 대신 팀이 상품 유형에 맞춰 새로 쓴 합성 자료(`data_type: test`)로 대체했다.
- 합성 자료는 `docs/poc/samples/a02_build_product.py`의 `SYNTHETIC`에서 만들고, 상품 JSON(`W2-A02-02_PRODUCT_prod-w2-0n.json`)의 `product.images[]`·`product.reviews[]`·`product.description`에 들어 있다.
- 실제 상품의 리뷰 수·평점·판매량(사실 값)은 A02-02 입력표에만 숫자로 기록했다. 리뷰 원문과 작성자 정보는 기록하지 않았다.

## 2. 사용 범위 점검 (W1-07 1.1절 4가지 구분)

W1-04 값: `allowed`(가능) / `prohibited`(불가) / `needs_review`(확인 필요).

| 자료 | 저장 `store` | AI 입력 `ai_input` | 표시 `display` | 판매 콘텐츠 재사용 `resale` | `rights_status` | 근거 |
|---|---|---|---|---|---|---|
| 실제 상품 이미지 | needs_review | needs_review | needs_review | needs_review | needs_review | W1-07 1.1절 기본값. 수집하지 않음 |
| 실제 상세 설명 | needs_review | needs_review | needs_review | needs_review | needs_review | 같음 |
| 실제 리뷰 원문 | needs_review | needs_review | needs_review | needs_review | needs_review | 같음 |
| 실제 평점·판매량·리뷰 수 | allowed | allowed | allowed | needs_review | needs_review | W1-07 1.1절: 사실 값은 사람이 직접 입력 |
| 합성 이미지·설명·리뷰 | allowed | allowed | allowed | prohibited | prohibited | `docs/poc/samples/W2-A02_TEST_PRODUCTS_README.md` (PR #10) |

- 각 행위는 해당 `usage`가 `allowed`일 때만 한다. 합성 자료는 PoC 저장·AI 입력·표시만 하고 판매 콘텐츠로 재사용하지 않는다.
- `rights_status`가 `prohibited`인 것은 `resale`이 `prohibited`라서다(W1-04: 하나라도 `prohibited`면 요약도 `prohibited`).

## 3. prod-w2-01 (1번 하네스)

상품 페이지: https://www.alibaba.com/product-detail/Adjustable-Dog-Lift-Harness-Dog-Sling_1601429812402.html

**이미지** (`product.images[]`)

| image_id | image_no | image_role | url | data_type | usage (store/ai_input/display/resale) |
|---|---|---|---|---|---|
| img-01-01 | 1 | main | `https://example.com/synthetic-images/prod-w2-01-1.jpg` | test | allowed/allowed/allowed/prohibited |
| img-01-02 | 2 | detail | `https://example.com/synthetic-images/prod-w2-01-2.jpg` | test | allowed/allowed/allowed/prohibited |
| img-01-03 | 3 | detail | `https://example.com/synthetic-images/prod-w2-01-3.jpg` | test | allowed/allowed/allowed/prohibited |
| img-01-04 | 4 | detail | `https://example.com/synthetic-images/prod-w2-01-4.jpg` | test | allowed/allowed/allowed/prohibited |
| img-01-05 | 5 | detail | `https://example.com/synthetic-images/prod-w2-01-5.jpg` | test | allowed/allowed/allowed/prohibited |

**상세 설명** (`product.description`)

| description_id | 내용 | data_type | 실제 원문 |
|---|---|---|---|
| desc-prod-w2-01 | 테스트 데이터(합성). 뒷다리가 약한 대형견용 후방 보조 리프트 슬링. 패딩 복부 패널, 긴 손잡이, 조절 가능한 끈. | test | 미수집 (`needs_review`) |

**리뷰** (`product.reviews[]`)

| review_id | text | 한국어 | rating | data_type |
|---|---|---|---|---|
| review-01-01 | Helps my old lab climb the stairs. | 노견 래브라도가 계단 오를 때 도움이 돼요. | 5 | test |
| review-01-02 | Handle is too short for a tall person. | 키 큰 사람에게는 손잡이가 너무 짧아요. | 3 | test |
| review-01-03 | Padding is soft on the belly. | 배 부분 패딩이 부드러워요. | 5 | test |
| review-01-04 | Strap slipped off during a walk. | 산책 중에 끈이 빠졌어요. | 2 | test |
| review-01-05 | Good after my dog's knee surgery. | 강아지 무릎 수술 후에 좋아요. | 5 | test |
| review-01-06 | Too narrow for a 45 kg dog. | 45kg 강아지에게는 폭이 좁아요. | 2 | test |
| review-01-07 | Easy to put on while the dog stands. | 강아지가 서 있을 때 착용시키기 쉬워요. | 4 | test |
| review-01-08 | Velcro wore out in a month. | 한 달 만에 벨크로가 약해졌어요. | 2 | test |
| review-01-09 | Saves my back when lifting. | 들어 올릴 때 허리가 덜 아파요. | 5 | test |
| review-01-10 | Strap slips when the dog turns. | 강아지가 방향을 틀 때 끈이 미끄러져요. | 2 | test |
| review-01-11 | Washes fine by hand. | 손세탁해도 괜찮아요. | 4 | test |
| review-01-12 | Smaller than the size chart. | 사이즈표보다 작아요. | 3 | test |
| review-01-13 | Stitching on the handle is strong. | 손잡이 박음질이 튼튼해요. | 4 | test |
| review-01-14 | My dog walks longer with it. | 이걸로 강아지가 더 오래 걸어요. | 5 | test |
| review-01-15 | Not for daily walking, only support. | 일상 산책용이 아니라 보조용이에요. | 3 | test |
| review-01-16 | Velcro catches dog hair. | 벨크로에 털이 붙어요. | 3 | test |
| review-01-17 | Good price for rehab use. | 재활용으로 가격이 괜찮아요. | 4 | test |
| review-01-18 | Arrived quickly. | 빨리 도착했어요. | 4 | test |
| review-01-19 | Velcro stopped holding after washing. | 세탁 후 벨크로가 잘 안 붙어요. | 2 | test |
| review-01-20 | Would buy a bigger size next time. | 다음엔 더 큰 사이즈로 살 거예요. | 4 | test |

## 4. prod-w2-07 (7번 방석)

상품 페이지: https://www.alibaba.com/product-detail/Wholesale-Washable-Dog-Beds-for-Large_1600570388952.html

**이미지** (`product.images[]`)

| image_id | image_no | image_role | url | data_type | usage (store/ai_input/display/resale) |
|---|---|---|---|---|---|
| img-07-01 | 1 | main | `https://example.com/synthetic-images/prod-w2-07-1.jpg` | test | allowed/allowed/allowed/prohibited |
| img-07-02 | 2 | detail | `https://example.com/synthetic-images/prod-w2-07-2.jpg` | test | allowed/allowed/allowed/prohibited |
| img-07-03 | 3 | detail | `https://example.com/synthetic-images/prod-w2-07-3.jpg` | test | allowed/allowed/allowed/prohibited |
| img-07-04 | 4 | detail | `https://example.com/synthetic-images/prod-w2-07-4.jpg` | test | allowed/allowed/allowed/prohibited |
| img-07-05 | 5 | detail | `https://example.com/synthetic-images/prod-w2-07-5.jpg` | test | allowed/allowed/allowed/prohibited |

**상세 설명** (`product.description`)

| description_id | 내용 | data_type | 실제 원문 |
|---|---|---|---|
| desc-prod-w2-07 | 테스트 데이터(합성). 대형견용 직사각형 침대. 분리 세탁 가능한 커버, 미끄럼 방지 바닥, 섬유 충전재. | test | 미수집 (`needs_review`) |

**리뷰** (`product.reviews[]`)

| review_id | text | 한국어 | rating | data_type |
|---|---|---|---|---|
| review-07-01 | Big enough for my 38 kg dog. | 38kg 강아지에게 충분히 커요. | 5 | test |
| review-07-02 | Filling went flat in three weeks. | 3주 만에 충전재가 납작해졌어요. | 2 | test |
| review-07-03 | Cover is easy to wash. | 커버 세탁이 쉬워요. | 5 | test |
| review-07-04 | Zipper broke on the first wash. | 첫 세탁 때 지퍼가 고장 났어요. | 2 | test |
| review-07-05 | My dog sleeps here all night. | 강아지가 밤새 여기서 자요. | 5 | test |
| review-07-06 | Thinner than expected. | 생각보다 얇아요. | 3 | test |
| review-07-07 | No smell when unpacked. | 포장을 풀 때 냄새가 없어요. | 4 | test |
| review-07-08 | Middle sank after a month. | 한 달 지나니 가운데가 꺼졌어요. | 2 | test |
| review-07-09 | Bottom does not slide on wood floor. | 마루에서 바닥이 미끄러지지 않아요. | 4 | test |
| review-07-10 | Flat in the middle quickly. | 가운데가 금방 납작해져요. | 2 | test |
| review-07-11 | Soft fabric, dog likes it. | 천이 부드러워서 강아지가 좋아해요. | 5 | test |
| review-07-12 | Color a bit different from photo. | 사진과 색이 조금 달라요. | 3 | test |
| review-07-13 | Took two weeks to arrive. | 도착까지 2주 걸렸어요. | 3 | test |
| review-07-14 | Good for an older dog. | 노견에게 좋아요. | 4 | test |
| review-07-15 | Seams look strong. | 이음새가 튼튼해 보여요. | 4 | test |
| review-07-16 | Dog hair sticks to the cover. | 커버에 털이 붙어요. | 3 | test |
| review-07-17 | Zipper got stuck after drying. | 건조 후 지퍼가 걸려요. | 2 | test |
| review-07-18 | Fits in a crate. | 켄넬 안에 들어가요. | 4 | test |
| review-07-19 | Fair price for the size. | 크기 대비 가격이 적당해요. | 4 | test |
| review-07-20 | Would recommend for big dogs. | 대형견에게 추천해요. | 5 | test |

## 5. prod-w2-09 (9번 장난감)

상품 페이지: https://www.alibaba.com/product-detail/Woof-Pupsicle-Long-Lasting-Interactive-Dog_1601391234725.html

**이미지** (`product.images[]`)

| image_id | image_no | image_role | url | data_type | usage (store/ai_input/display/resale) |
|---|---|---|---|---|---|
| img-09-01 | 1 | main | `https://example.com/synthetic-images/prod-w2-09-1.jpg` | test | allowed/allowed/allowed/prohibited |
| img-09-02 | 2 | detail | `https://example.com/synthetic-images/prod-w2-09-2.jpg` | test | allowed/allowed/allowed/prohibited |
| img-09-03 | 3 | detail | `https://example.com/synthetic-images/prod-w2-09-3.jpg` | test | allowed/allowed/allowed/prohibited |
| img-09-04 | 4 | detail | `https://example.com/synthetic-images/prod-w2-09-4.jpg` | test | allowed/allowed/allowed/prohibited |
| img-09-05 | 5 | detail | `https://example.com/synthetic-images/prod-w2-09-5.jpg` | test | allowed/allowed/allowed/prohibited |

**상세 설명** (`product.description`)

| description_id | 내용 | data_type | 실제 원문 |
|---|---|---|---|
| desc-prod-w2-09 | 테스트 데이터(합성). 대형견용 실리콘 간식 공. 음식을 채워 얼려서 사용. 핥기용 요철 표면. | test | 미수집 (`needs_review`) |

**리뷰** (`product.reviews[]`)

| review_id | text | 한국어 | rating | data_type |
|---|---|---|---|---|
| review-09-01 | Keeps my husky busy for 30 minutes. | 허스키가 30분 동안 집중해요. | 5 | test |
| review-09-02 | Torn after one day of chewing. | 하루 씹고 찢어졌어요. | 1 | test |
| review-09-03 | Easy to fill and freeze. | 채워서 얼리기 쉬워요. | 5 | test |
| review-09-04 | Not for strong chewers. | 세게 씹는 강아지용은 아니에요. | 2 | test |
| review-09-05 | Good size for a large mouth. | 입이 큰 강아지에게 맞는 크기예요. | 4 | test |
| review-09-06 | Dishwasher safe, very handy. | 식기세척기 사용 가능해서 편해요. | 4 | test |
| review-09-07 | Hard to clean the inside. | 안쪽 세척이 어려워요. | 3 | test |
| review-09-08 | Small pieces came off when chewed. | 씹으니 작은 조각이 떨어졌어요. | 2 | test |
| review-09-09 | Slows down my dog's eating. | 강아지가 천천히 먹게 돼요. | 5 | test |
| review-09-10 | Silicone smell at first. | 처음에 실리콘 냄새가 나요. | 3 | test |
| review-09-11 | Color faded after washing. | 세척 후 색이 바랬어요. | 3 | test |
| review-09-12 | Great on hot days with frozen yogurt. | 더운 날 얼린 요거트로 좋아요. | 5 | test |
| review-09-13 | Torn in two days by my shepherd. | 셰퍼드가 이틀 만에 찢었어요. | 1 | test |
| review-09-14 | Cheap and works well. | 싸고 잘 작동해요. | 4 | test |
| review-09-15 | Bigger than I expected. | 생각보다 커요. | 4 | test |
| review-09-16 | Safe so far for my retriever. | 리트리버에게 아직은 안전해요. | 4 | test |
| review-09-17 | Pieces broke off, threw it away. | 조각이 떨어져서 버렸어요. | 1 | test |
| review-09-18 | Good for anxious dogs. | 불안해하는 강아지에게 좋아요. | 4 | test |
| review-09-19 | Shipping was fast. | 배송이 빨랐어요. | 4 | test |
| review-09-20 | Average quality. | 품질은 보통이에요. | 3 | test |

## 셀프 점검

- [x] 상품 3개 모두 이미지·상세·리뷰 확보(합성) 또는 누락 사유 기록(실제 원문 `needs_review`)
- [x] 이미지 5장·리뷰 20개 × 3개 상품, 모든 항목에 `source_url`·`data_type`·`usage` 연결
- [x] 사용 범위 표에 빈칸 없음
- [x] `needs_review`·`prohibited` 자료는 판매 콘텐츠 재사용 목록에서 제외
- [ ] 검토 B(다라님)

## 다음 작업

| 작업 | 담당 | 비고 |
|---|---|---|
| A02-03 검토 | B | 검토 끝나면 A02-04 시작 가능 |
| 실제 원문 사용 권한 확인되면 이 표 다시 판정 | A | W1-07 수정 시 |
