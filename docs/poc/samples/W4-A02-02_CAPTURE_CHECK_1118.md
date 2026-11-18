# A02-02 확장 프로그램 추출 검사 보고서

- 생성: 2026-11-18 10:10
- 추출본: prod-w2-01_capture_20261118-1007.json, prod-w2-07_capture_20261118-1007.json, prod-w2-09_capture_20261118-1007.json
- 환율: 입력 없음 (KRW 외 상식선 검사 생략)
- 빈칸은 확장이 못 찾은 값이다. a02_build_product.py에서 `manual_review_required`(사람 확인 전)로 처리된다.
- 이미지는 주소만 추출본에 남기고 입력표에는 넣지 않았다 (W1-07 1.1절, usage = needs_review).

## prod-w2-01

- 출처: https://www.alibaba.com/product-detail/Adjustable-Dog-Lift-Harness-Dog-Sling_1601429812402.html
- 추출 시각: 2026-11-18 10:07 · 방식: alibaba
- 사람이 고친 칸: 없음 · 이미지 주소 8개

### 가격 검사

- 판정: **ok** (수량별 구간가)
- 통화: KRW (근거: symbol)
- 최저~최고: 3690 ~ 4373 · MOQ 100

| 수량 | 가격 | 읽은 값 | 판정 |
|---|---|---|---|
| 100 - 799 | ₩4,373 | 100~799 · 4373 KRW | ok |
| 800 - 4999 | ₩4,236 | 800~4999 · 4236 KRW | ok |
| 5000 - 9999 | ₩3,963 | 5000~9999 · 3963 KRW | ok |
| >= 10000 | ₩3,690 | 10000 이상 · 3690 KRW | ok |

- 참고:
  - 가격 글자 'USD 2.7'(jsonld)는 화면 구간가(KRW)와 통화가 달라 입력표에 쓰지 않음 (사이트 기준 통화 값으로 보임)
- 원화 상식선: 3,690원 ~ 4,373원 (환율 1)

### 빈칸 (사람 확인 필요)

- length, weight, product_use
- 속성 'Breed Size: Large, Medium, Small'에 대형 표기 있음 → large_dog_label 판단 참고 (입력표에는 사람이 기록)
- 대형견 표기 '예' 자동 기록 (근거: 제목, 속성 'Breed Size: Large, Medium, Small')
- 물류 'Alibaba.com Logistics'는 배송 상자 글자가 아니라 page_data:logisticsFtType에서 읽음

### 사람 입력값과 비교 (일치 11/16)

| 항목 | 사람 입력 | 확장 추출 | 결과 |
|---|---|---|---|
| original_name | Adjustable Dog Lift Harness Dog Sling for Large Dogs | Adjustable Dog Lift Harness Dog Sling For Large Dogs Hind Leg Soft Rehab Harness For Weak Rear Legs Helps Injured Disabled | 불일치 |
| price_min | 3735 | 3690 | 불일치 |
| price_max | 4427 | 4373 | 불일치 |
| currency | KRW | KRW | 일치 |
| options | 색상=1종 | Color=Black; Size=Multiple Size | 불일치 |
| length | 없음 | · | 일치 (둘 다 없음) |
| width | 없음 | · | 일치 (둘 다 없음) |
| height | 없음 | · | 일치 (둘 다 없음) |
| weight | 없음 | · | 일치 (둘 다 없음) |
| material | 폴리아미드;폴리에스터 | polyamide;Polyester | 일치 |
| sales_count | 7 | 8 | 불일치 |
| rating | 5.0 | 5 | 일치 |
| review_count | 13 | 13 | 일치 |
| supplier_name | Chaozhou Chaoan Ikitchen Stainless Steel Co., Ltd. | Chaozhou Chaoan Ikitchen Stainless Steel Co., Ltd. | 일치 |
| package_size | 20x25x15 cm | 20X25X15 cm | 일치 |
| package_weight | 1.5 kg | 1.5 kg | 일치 |

## prod-w2-07

- 출처: https://www.alibaba.com/product-detail/Wholesale-Washable-Dog-Beds-for-Large_1600570388952.html
- 추출 시각: 2026-11-18 10:07 · 방식: alibaba
- 사람이 고친 칸: 없음 · 이미지 주소 12개

### 가격 검사

- 판정: **ok** (가격 글자)
- 통화: KRW (근거: symbol)
- 최저~최고: 10125 ~ 11628 · MOQ 10
- 원화 상식선: 10,125원 ~ 11,628원 (환율 1)

### 빈칸 (사람 확인 필요)

- weight, sales_count, rating, review_count, product_use
- 크기 속성 'M, L'을 치수로 읽지 못해 빈칸 (옵션 사이즈일 수 있음)
- 대형견 표기 '예' 자동 기록 (근거: 제목)
- 배송비 할인 폭이 큼 (₩28,092 → ₩766). 첫 주문 할인 같은 조건인지 사람 확인

### 사람 입력값과 비교 (일치 11/16)

| 항목 | 사람 입력 | 확장 추출 | 결과 |
|---|---|---|---|
| original_name | Wholesale Washable Dog Beds for Large Dogs Mattress Comfortable and Warming Rectangle | Wholesale Washable Dog Beds For Large Dogs Mattress Comfortable And Warming Rectangle | 일치 |
| price_min | 10250 | 10125 | 불일치 |
| price_max | 11772 | 11628 | 불일치 |
| currency | KRW | KRW | 일치 |
| options | 색상=회색, 갈색; 크기=M 54*43*18/13cm, L 67*50*18/13cm | Color=Gray/Brown; Size=M: 54*43*18/13cm/L: 67*50*18/13cm | 불일치 |
| length | 67 | 67 | 일치 |
| width | 50 | 50 | 일치 |
| height | 18 | 18 | 일치 |
| weight | 없음 | · | 일치 (둘 다 없음) |
| material | 벨벳 | Velvet | 불일치 |
| sales_count | 없음 | · | 일치 (둘 다 없음) |
| rating | 없음 | · | 일치 (둘 다 없음) |
| review_count | 0 | · | 확장 못 찾음 |
| supplier_name | Dalian Usmile Pet Technology Co., Ltd. | Dalian Usmile Pet Technology Co., Ltd. | 일치 |
| package_size | 18x10x5 cm | 18X10X5 cm | 일치 |
| package_weight | 0.8 kg | 0.8 kg | 일치 |

## prod-w2-09

- 출처: https://www.alibaba.com/product-detail/Woof-Pupsicle-Long-Lasting-Interactive-Dog_1601391234725.html
- 추출 시각: 2026-11-18 10:07 · 방식: alibaba
- 사람이 고친 칸: 없음 · 이미지 주소 11개

### 가격 검사

- 판정: **ok** (가격 글자)
- 통화: KRW (근거: symbol)
- 최저~최고: 2528 ~ 5056 · MOQ 200
- 원화 상식선: 2,528원 ~ 5,056원 (환율 1)

### 빈칸 (사람 확인 필요)

- length, weight, product_use
- 대형견 표기 '예' 자동 기록 (근거: 제목)
- 물류 'Alibaba.com Logistics'는 배송 상자 글자가 아니라 page_data:logisticsFtType에서 읽음

### 사람 입력값과 비교 (일치 13/16)

| 항목 | 사람 입력 | 확장 추출 | 결과 |
|---|---|---|---|
| original_name | Long-Lasting Interactive Dog Toy Ball Freeze Treats Toy Eco-Friendly Food Grade Silicone Dog Chew Lick Toys for Large Dogs | Long-lasting Interactive Dog Toy Ball Freeze Treats Toy Eco-friendly Food Grade Silicone Dog Chew Lick Toys For Large Dogs | 일치 |
| price_min | 2535 | 2528 | 불일치 |
| price_max | 5069 | 5056 | 불일치 |
| currency | KRW | KRW | 일치 |
| options | 색상=녹색, 노란색 | Color=Green/Yellow(silicone Treat Tray) | 불일치 |
| length | 없음 | · | 일치 (둘 다 없음) |
| width | 없음 | · | 일치 (둘 다 없음) |
| height | 없음 | · | 일치 (둘 다 없음) |
| weight | 없음 | · | 일치 (둘 다 없음) |
| material | 식품 등급 실리콘 | Food Grade Silicone;Silicone | 일치 |
| sales_count | 1157 | 1157 | 일치 |
| rating | 5.0 | 5 | 일치 |
| review_count | 13 | 13 | 일치 |
| supplier_name | Dongguan Wellfine Silicone Products Co., Ltd. | Dongguan Wellfine Silicone Products Co., Ltd. | 일치 |
| package_size | 10x10x9 cm | 10X10X9 cm | 일치 |
| package_weight | 0.35 kg | 0.35 kg | 일치 |

