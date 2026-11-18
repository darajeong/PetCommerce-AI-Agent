/*
 * A02 상세페이지 사실 값 추출 함수 (a02_capture_ext v0.4.0, 2026-11-18)
 *
 * - 사람이 직접 연 상품 상세페이지에서, 사람이 확장 프로그램 버튼을 눌렀을 때 한 번만 실행된다.
 * - 네트워크 요청을 보내지 않고, 다른 페이지를 열거나 이동하지 않는다. 이미 화면에 그려진 DOM 과
 *   페이지에 이미 들어 있는 데이터만 읽는다.
 * - 가져오는 것: 사실 값(상품명·가격 글자·수량 구간·MOQ·속성·옵션·공급처·판매량·평점·리뷰 수)과
 *   이미지 "주소". 이미지 주소의 usage 는 W1-07 1.1절에 따라 needs_review 로 다룬다.
 * - 가져오지 않는 것: HTML 본문, 상품 설명 원문, 리뷰 원문, 이미지 파일, 쿠키·계정 정보.
 *
 * chrome.scripting.executeScript({func}) 로 넘기므로 함수 하나 안에 모든 도우미가 들어 있어야 한다.
 * 시험용 페이지(test/)에서는 pageUrlOverride 로 상품 URL 을 흉내 낸다.
 */
function a02ExtractFacts(pageUrlOverride) {
  const VERSION = '0.4.0';
  const MAX_ATTR = 60, MAX_IMG = 20, MAX_PRICE_TEXT = 20, MAX_NODES = 40000;
  const href = pageUrlOverride || location.href;
  const url = new URL(href);
  const clean = (s) => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
  const debug = { strategies: [], page_data_roots: {}, notes: [] };

  const CODES = 'USD|KRW|CNY|EUR|JPY|GBP|HKD|CAD|AUD|RMB';
  const PRICE_RE = new RegExp(
    '(?:US\\$|HK\\$|CA\\$|AU\\$|CN¥|JP¥|(?:' + CODES + ')\\s?|[$₩￦€£¥￥])\\s?\\d[\\d.,]*' +
    '(?:\\s?[-–~]\\s?(?:[$₩￦€£¥￥]\\s?)?\\d[\\d.,]*)?(?:\\s?(?:원|元|円))?' +
    '|\\d[\\d.,]*(?:\\s?[-–~]\\s?\\d[\\d.,]*)?\\s?(?:원|元|円)');
  const QTY_UNITS = '(?:pieces?|pcs|pc|sets?|units?|pairs?|boxes|box|bags?|rolls?|개|세트|쌍|박스|장|매|件|个)';
  const QTY_RE = new RegExp('^(?:≥|>=|>)?\\s*\\d[\\d,]*\\s*(?:(?:-|–|~|to)\\s*\\d[\\d,]*)?\\s*' + QTY_UNITS +
    '?\\s*(?:\\+|이상|or more)?$', 'i');
  const isQtyLabel = (t) => QTY_RE.test(t) && /[A-Za-z가-힣件个]|[-–~]|≥|>=|\+/.test(t);
  const SKIP_KEY = /user|buyer|login|member|account|token|cookie|email|phone|mobile|session|csrf|address|passport|nick|password/i;

  const field = (value, source) => ({ value: value == null || value === '' ? null : String(value), source: value == null || value === '' ? null : source });
  const normImg = (u) => {
    if (!u || typeof u !== 'string') return null;
    u = u.trim();
    if (u.startsWith('//')) u = 'https:' + u;
    if (!/^https?:\/\//i.test(u)) return null;
    if (/sprite|icon|logo|avatar|flag|placeholder|loading/i.test(u)) return null;
    if (/\/imgextra\/|-tps-\d+-\d+/i.test(u)) return null;   // 사이트 화면용 배너·아이콘 (상품 이미지 아님)
    return u.replace(/\?.*$/, '').replace(/_(\d+x\d+|Q\d+)[^/]*$/i, '');
  };
  // 같은 이미지가 다른 CDN 주소로 두 번 나오는 경우(…/kf/파일명) 하나로 본다
  const imgKey = (u) => { const m = u.match(/\/kf\/([^/?#]+)$/); return m ? 'kf:' + m[1] : u; };
  // 제목 끝의 사이트 문구(" - Buy … on Alibaba.com") 제거
  // 앞뒤에 빈칸이 있는 " - "만 본다 ("Long-Lasting" 같은 낱말 속 하이픈에서 자르지 않도록)
  const stripTitle = (t) => (t == null ? t : clean(t)
    .replace(/\s+[-|]\s+(?:Buy\b.*?|[^-|]*?)\s*on Alibaba\.com$/i, '').replace(/\s+[-|]\s+Buy\b.*$/i, ''));

  // ---------------------------------------------------------------- 1. JSON-LD (구조화 데이터)
  const ld = { name: null, prices: [], images: [], rating: null, reviewCount: null, brand: null };
  document.querySelectorAll('script[type="application/ld+json"]').forEach((s) => {
    let j;
    try { j = JSON.parse(s.textContent); } catch (e) { return; }
    const items = Array.isArray(j) ? j : (j && j['@graph']) || [j];
    items.forEach((x) => {
      if (!x || !/Product/i.test([].concat(x['@type'] || '').join(','))) return;
      ld.name = ld.name || x.name || null;
      [].concat(x.image || []).forEach((im) => ld.images.push(typeof im === 'string' ? im : im && im.url));
      [].concat(x.offers || []).forEach((o) => {
        if (!o) return;
        const cur = o.priceCurrency || '';
        if (o.lowPrice != null && o.highPrice != null) ld.prices.push(`${cur} ${o.lowPrice} - ${o.highPrice}`.trim());
        else if (o.price != null) ld.prices.push(`${cur} ${o.price}`.trim());
      });
      if (x.aggregateRating) {
        ld.rating = x.aggregateRating.ratingValue ?? null;
        ld.reviewCount = x.aggregateRating.reviewCount ?? x.aggregateRating.ratingCount ?? null;
      }
      ld.brand = (x.brand && (x.brand.name || x.brand)) || null;
    });
  });
  if (ld.name || ld.prices.length) debug.strategies.push('jsonld');

  // ---------------------------------------------------------------- 2. 페이지에 이미 들어 있는 데이터
  const pd = { title: null, titleWeak: null, currency: {}, moq: null, supplier: null, sold: null, rating: null,
               reviewCount: null, images: [], tiers: null, attrs: { v: [], p: [] }, options: null,
               hasProductReview: false, hasStoreReview: false, priceCands: [], shipCands: [] };
  const KNOWN_CUR = new RegExp('^(' + CODES + ')$');
  const isNum = (x) => (typeof x === 'number' && isFinite(x)) || (typeof x === 'string' && /^\d[\d,]*(\.\d+)?$/.test(x.trim()));
  const pick = (o, re) => Object.keys(o).find((k) => re.test(k));

  function inspectKey(k, x, path) {
    if (/productReview/i.test(path)) pd.hasProductReview = true;
    if (/storeReview|sellerReview|shopReview|companyReview/i.test(path)) pd.hasStoreReview = true;
    // 가격 후보: 키 이름에 price 가 들어간 짧은 값 (샘플가·배송비는 뺌). 사람이 팝업에서 고르고, 다음 규칙 조정의 근거로 쓴다
    if (/price/i.test(k) && !/sample|shipping|freight|logistic|i18n/i.test(path) && pd.priceCands.length < 40
        && (typeof x === 'string' || typeof x === 'number')) {
      const t = clean(x);
      if (/\d/.test(t) && t.length <= 60) pd.priceCands.push({ path, value: t });
    }
    // 배송 후보: 배송·물류 경로의 짧은 값 (규칙 조정용, 화면 배송 상자 글자가 기본)
    if (/shipping|freight|logistic|delivery/i.test(path) && !/i18n/i.test(path) && pd.shipCands.length < 30
        && (typeof x === 'string' || typeof x === 'number')) {
      const t = clean(x);
      if (t && t.length <= 80 && !/^https?:|^\/\//i.test(t)) pd.shipCands.push({ path, value: t });
    }
    if (typeof x === 'string') {
      const t = clean(x);
      if (/^(subject|productTitle|productName)$/i.test(k) && t.length >= 8 && t.length <= 300 && !pd.title) pd.title = { v: t, p: path };
      else if (/^title$/i.test(k) && t.length >= 8 && t.length <= 300 && !pd.titleWeak) pd.titleWeak = { v: t, p: path };
      if (/currency|^curr$/i.test(k) && KNOWN_CUR.test(t)) { const c = t === 'RMB' ? 'CNY' : t; pd.currency[c] = (pd.currency[c] || 0) + 1; }
      if (/^(companyName|supplierName|sellerName|shopName|storeName)$/i.test(k) && t.length >= 2 && t.length <= 200 && !pd.supplier) pd.supplier = { v: t, p: path };
      if (/\.(jpe?g|png|webp)(\?|_|$)/i.test(t) && /^(https?:)?\/\//i.test(t) && /image|img|media|gallery|pic|photo/i.test(path) && pd.images.length < 60) pd.images.push(t);
    }
    if (isNum(x)) {
      const n = Number(String(x).replace(/,/g, ''));
      if (/^(moq|minOrder|minOrderQuantity|minimumOrderQuantity|minOrderQty)$/i.test(k) && pd.moq == null && n > 0) pd.moq = { v: n, p: path };
      const storeish = /store|seller|company|supplier|shop/i.test(path);   // 공급업체·스토어 값은 상품 값으로 쓰지 않음
      if (/^(soldCount|salesVolume|tradeCount|orderCount|sold|saleCount|soldQuantity|salesCount|totalSold)$/i.test(k) && pd.sold == null && !storeish) pd.sold = { v: n, p: path };
      if (/^(averageStar|ratingValue|rating|productScore|reviewScore|avgStar)$/i.test(k) && pd.rating == null && n >= 0 && n <= 5 && !storeish) pd.rating = { v: n, p: path };
      if (/^(reviewCount|totalReviews|commentCount|reviewNum|reviewsCount)$/i.test(k) && pd.reviewCount == null && !storeish) pd.reviewCount = { v: n, p: path };
    }
  }

  function inspectArray(arr, path) {
    const objs = arr.filter((x) => x && typeof x === 'object' && !Array.isArray(x));
    if (!objs.length || objs.length !== arr.length) return;
    // 수량별 구간가
    if (!pd.tiers && arr.length <= 10) {
      const rows = objs.map((o) => {
        const kMin = pick(o, /^(min|start|begin)[A-Za-z]*(quant|qty|num|amount|count)|^min$|^beginAmount$/i);
        const kMax = pick(o, /^(max|end)[A-Za-z]*(quant|qty|num|amount|count)|^max$|^endAmount$/i);
        const kTxt = pick(o, /formatPrice|priceText|displayPrice|priceStr|formattedPrice/i);
        const kNum = pick(o, /^(price|dollarPrice|localPrice|unitPrice)$/i);
        const kCur = pick(o, /^(currency|currencyCode)$/i);
        if (!kMin || !(kTxt || kNum) || !isNum(o[kMin])) return null;
        const max = kMax && isNum(o[kMax]) ? Number(o[kMax]) : null;
        const qMin = Number(String(o[kMin]).replace(/,/g, ''));
        return {
          quantity_text: max && max > 0 && max >= qMin ? `${qMin} - ${max}` : `>= ${qMin}`,
          price_text: kTxt && typeof o[kTxt] === 'string' ? clean(o[kTxt]) : `${kCur ? o[kCur] + ' ' : ''}${o[kNum]}`,
          source: `page_data:${path}`,
        };
      });
      if (rows.every(Boolean)) pd.tiers = rows;
    }
    // 속성 (이름·값 쌍): 기본 속성·포장 정보처럼 여러 배열에 나뉘어 있으면 모두 모은다
    if (pd.attrs.v.length < MAX_ATTR && arr.length >= 1 && !/sku|track|spm|abtest|i18n|lang/i.test(path)) {
      const PAIRS = [['attrName', 'attrValue'], ['propertyName', 'propertyValue'], ['name', 'value'], ['key', 'value'], ['label', 'value']];
      for (const [kn, kv] of PAIRS) {
        if (kn === 'name' || kn === 'key' || kn === 'label') { if (!/propert|attr|spec/i.test(path)) continue; }
        const rows = objs.filter((o) => typeof o[kn] === 'string' && (typeof o[kv] === 'string' || typeof o[kv] === 'number'))
          .map((o) => ({ name: clean(o[kn]), value: clean(o[kv]) }))
          .filter((r) => r.name.length >= 1 && r.name.length <= 40 && r.value.length >= 1 && r.value.length <= 120);
        if (rows.length && rows.length >= objs.length * 0.8 && (rows.length >= 2 || kn === 'attrName' || kn === 'propertyName')) {
          const have = new Set(pd.attrs.v.map((r) => r.name));
          const add = rows.filter((r) => !have.has(r.name));
          if (add.length) { pd.attrs.v.push(...add.slice(0, MAX_ATTR - pd.attrs.v.length)); pd.attrs.p.push(path); }
          break;
        }
      }
    }
    // 옵션 (SKU)
    if (!pd.options && /sku|option|variant/i.test(path)) {
      const rows = objs.map((o) => {
        const kn = pick(o, /^(name|attrName|propertyName|skuPropertyName|title)$/i);
        const kv = pick(o, /^(values|valueList|attrValues|skuPropertyValues|propertyValues|list)$/i);
        if (!kn || !kv || typeof o[kn] !== 'string' || !Array.isArray(o[kv])) return null;
        const vals = o[kv].map((v) => (typeof v === 'string' ? v : v && (v.name || v.value || v.valueName || v.propertyValueDisplayName)))
          .filter((v) => typeof v === 'string').map(clean).filter(Boolean);
        return vals.length ? { name: clean(o[kn]), values: vals.slice(0, 30) } : null;
      });
      if (rows.length && rows.every(Boolean)) pd.options = { v: rows, p: path };
    }
  }

  function walk(root, rootName) {
    const queue = [[root, rootName, 0]];
    const seen = new WeakSet();
    let i = 0;
    while (i < queue.length && i < MAX_NODES) {
      const [v, path, depth] = queue[i++];
      if (!v || typeof v !== 'object' || seen.has(v) || depth > 10) continue;
      if (typeof Node !== 'undefined' && v instanceof Node) continue;
      seen.add(v);
      if (Array.isArray(v)) {
        inspectArray(v, path);
        v.slice(0, 200).forEach((x, j) => { if (x && typeof x === 'object') queue.push([x, `${path}[${j}]`, depth + 1]); });
        continue;
      }
      let keys;
      try { keys = Object.keys(v).slice(0, 300); } catch (e) { continue; }
      for (const k of keys) {
        if (SKIP_KEY.test(k)) continue;
        let x;
        try { x = v[k]; } catch (e) { continue; }
        inspectKey(k, x, `${path}.${k}`);
        if (x && typeof x === 'object') queue.push([x, `${path}.${k}`, depth + 1]);
      }
    }
  }

  ['detailData', '__INIT_DATA__', '_PAGE_DATA_', 'runParams', '__NEXT_DATA__', '__NUXT__', 'pageData'].forEach((name) => {
    let root;
    try { root = window[name]; } catch (e) { return; }
    if (!root || typeof root !== 'object') return;
    try { debug.page_data_roots[name] = Object.keys(root).filter((k) => !SKIP_KEY.test(k)).slice(0, 40); } catch (e) { /* 무시 */ }
    walk(root, name);
  });
  if (Object.keys(debug.page_data_roots).length) debug.strategies.push('page_data');

  // ---------------------------------------------------------------- 3. 화면(DOM)
  const bodyText = document.body ? document.body.innerText || '' : '';
  const meta = (p) => { const m = document.querySelector(`meta[property="${p}"],meta[name="${p}"]`); return m ? m.getAttribute('content') : null; };
  const h1 = document.querySelector('h1');
  const ogTitle = meta('og:title');
  const docTitle = clean(document.title).replace(/\s+[-|]\s+(Buy|Alibaba\.com).*$/i, '');

  const domPrices = [];
  document.querySelectorAll('[class*="price" i]').forEach((el) => {
    if (domPrices.length >= MAX_PRICE_TEXT) return;
    const t = clean(el.innerText);
    if (t.length > 80) return;
    const m = t.match(PRICE_RE);
    if (m && !domPrices.includes(clean(m[0]))) domPrices.push(clean(m[0]));
  });
  // 화면의 가격 글자 후보: 클래스 이름과 상관없이 가격 모양의 짧은 글자 (예: "₩10,250 - 11,772")
  const domPriceCands = [];
  document.querySelectorAll('body *').forEach((el) => {
    if (domPriceCands.length >= 20 || el.children.length > 1 || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName)) return;
    const t = clean(el.textContent);
    if (!t || t.length > 40) return;
    const m = t.match(PRICE_RE);
    if (m && t.length - m[0].length <= 12 && !domPriceCands.some((c) => c.text === clean(m[0]))) {
      domPriceCands.push({ text: clean(m[0]), hint: String(el.getAttribute('class') || '').slice(0, 40) });
    }
  });

  const domTiers = [];
  document.querySelectorAll('body *').forEach((el) => {
    if (domTiers.length >= 10 || el.children.length > 0 || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName)) return;
    const t = clean(el.textContent);
    if (!t || t.length > 40 || !isQtyLabel(t)) return;
    let box = el.parentElement;
    for (let up = 0; box && up < 3; up++, box = box.parentElement) {
      const txt = clean(box.innerText);
      const others = [...box.querySelectorAll('*')].filter((c) => c !== el && c.children.length === 0 && isQtyLabel(clean(c.textContent)));
      if (others.length) break;
      const m = txt.replace(t, ' ').match(PRICE_RE);
      if (m) { domTiers.push({ quantity_text: t, price_text: clean(m[0]), source: 'dom:tier' }); break; }
    }
  });

  const moqM = bodyText.match(/(?:Min\.?\s*order(?:\s*quantity)?|MOQ|최소\s*주문(?:\s*수량|량)?)\s*[:：]?\s*([\d,]+)\s*([A-Za-z가-힣]+)?/i);

  const domAttrs = new Map();
  const addAttr = (n, v, max) => {
    n = clean(n).replace(/[:：]\s*$/, ''); v = clean(v);
    if (domAttrs.size >= max || !n || !v || n.length > 40 || v.length > 120 || /^\d+$/.test(n) || domAttrs.has(n)) return;
    domAttrs.set(n, v);
  };
  document.querySelectorAll('[class*="attr" i],[class*="propert" i],[class*="spec" i],[id*="attr" i],[class*="param" i]').forEach((box) => {
    box.querySelectorAll('*').forEach((row) => {
      if (row.children.length !== 2) return;
      const [a, b] = row.children;
      if (a.children.length > 2 || b.children.length > 2) return;
      const ta = clean(a.innerText), tb = clean(b.innerText);
      if (ta && tb && ta.length <= 40 && tb.length <= 120) addAttr(ta, tb, MAX_ATTR);
    });
  });
  let attrSource = domAttrs.size ? 'dom:attribute-block' : null;
  if (!domAttrs.size) {
    document.querySelectorAll('tr').forEach((tr) => { const c = tr.querySelectorAll('th,td'); if (c.length === 2) addAttr(c[0].innerText, c[1].innerText, MAX_ATTR); });
    document.querySelectorAll('dl').forEach((dl) => { const dt = dl.querySelectorAll('dt'), dd = dl.querySelectorAll('dd'); dt.forEach((d, k) => dd[k] && addAttr(d.innerText, dd[k].innerText, MAX_ATTR)); });
    if (domAttrs.size) attrSource = 'dom:table-fallback';
  }

  let domSupplier = null;
  const supA = document.querySelector('a[href*=".en.alibaba.com"]');
  if (supA && clean(supA.innerText).length >= 2) domSupplier = clean(supA.innerText);
  if (!domSupplier) {
    const el = document.querySelector('[class*="company-name" i],[class*="companyName" i],[class*="supplier-name" i],[class*="shop-name" i]');
    if (el && clean(el.innerText).length >= 2 && clean(el.innerText).length <= 200) domSupplier = clean(el.innerText);
  }
  const soldM = bodyText.match(/([\d,]+)\s*(?:sold|판매됨|(?:개|건)\s*판매|판매(?!하))/i);
  const reviewM = bodyText.match(/([\d,]+)\s*(?:reviews?|리뷰|후기|상품평)/i);
  // "5.0 (13 리뷰)"·"5.0 · 13 reviews" 형태만 상품 평점으로 본다. "4.9/5" 처럼 "/" 뒤 숫자는 스토어 평가일 수 있어 쓰지 않음
  const ratingM = bodyText.match(/(?<![\/\d.,])(\d(?:\.\d)?)(?![\d.,])(?:\s*[(·•|]\s*|\s+)\(?\s*([\d,]+)\s*(?:개\s*)?(?:리뷰|reviews?)(?![A-Za-z])/i);

  let domCurrency = null;
  const curOf = (t) => { const m = t.match(new RegExp('(?:^|[\\s\\-–/·|:])(' + CODES + ')$')); return m ? (m[1] === 'RMB' ? 'CNY' : m[1]) : null; };
  document.querySelectorAll('[class*="currency" i]').forEach((el) => {
    if (domCurrency) return;
    const m = clean(el.innerText).match(new RegExp('\\b(' + CODES + ')\\b'));
    if (m) domCurrency = m[1] === 'RMB' ? 'CNY' : m[1];
  });
  if (!domCurrency) {   // 머리글의 언어·통화 표시 (예: "한국어-KRW", "English-USD")
    for (const el of document.querySelectorAll('header *, [class*="header" i] *, [class*="lang" i], [class*="locale" i]')) {
      if (el.children.length) continue;
      const t = clean(el.textContent);
      if (t && t.length <= 24 && (domCurrency = curOf(t))) break;
    }
  }

  // 배송 상자: "Shipping"/"배송" 제목이나 "… Logistics" 글자에서 위로 올라가며 배송 내용이 담긴 작은 상자 글자를 찾는다
  // (배송 방법·배송비·도착 예정일. 배송지·수량에 따라 바뀌는 값이라 해석은 변환 스크립트가 하고, 여기서는 글자를 그대로 둔다)
  let shipText = null;
  const SHIP_HEAD = /^(shipping|shipping & delivery|배송|배송 정보)$/i;
  const SHIP_BODY = /logistics|shipping fee|free shipping|delivery|배송비|무료 배송|배송/i;
  for (const el of document.querySelectorAll('body *')) {
    if (el.children.length || /^(SCRIPT|STYLE|NOSCRIPT)$/.test(el.tagName)) continue;
    const t = clean(el.textContent);
    if (!t || !(SHIP_HEAD.test(t) || /Logistics$/i.test(t))) continue;
    let box = el.parentElement;
    for (let up = 0; box && up < 5; up++, box = box.parentElement) {
      const bt = clean(box.innerText);
      if (bt.length > 600) break;
      if (bt.length > 30 && SHIP_BODY.test(bt.replace(t, ''))) { shipText = bt; break; }
    }
    if (shipText) break;
  }

  const galleryImgs = [];
  document.querySelectorAll('[class*="gallery" i] img,[class*="main-image" i] img,[class*="slider" i] img,[class*="thumb" i] img,[class*="image-view" i] img,[class*="media" i] img').forEach((img) => {
    galleryImgs.push(img.currentSrc || img.getAttribute('src') || img.getAttribute('data-src'));
  });
  debug.strategies.push('dom');

  // ---------------------------------------------------------------- 4. 우선순위대로 고르기
  const first = (...cands) => cands.find((c) => c && c[0] != null && c[0] !== '') || [null, null];
  const pdCur = Object.entries(pd.currency).sort((a, b) => b[1] - a[1])[0];
  const [nameV, nameS] = first([stripTitle(ld.name), 'jsonld'], pd.title && [stripTitle(pd.title.v), `page_data:${pd.title.p}`],
    h1 && [stripTitle(h1.innerText), 'dom:h1'], [stripTitle(ogTitle), 'dom:og:title'],
    pd.titleWeak && [stripTitle(pd.titleWeak.v), `page_data:${pd.titleWeak.p}`], [docTitle, 'dom:title']);
  const [curV, curS] = first(pdCur && [pdCur[0], 'page_data'], [domCurrency, 'dom:currency']);
  // 수량별 구간가가 없는 상품(범위가·할인가)은 화면 표시 통화의 가격 후보를 JSON-LD(사이트 기준 통화)보다 먼저 쓴다
  const tiersFound = !!(pd.tiers || domTiers.length);
  const SYM = { KRW: /₩|￦|KRW|원/, USD: /US\$|USD|\$/, CNY: /CN¥|CNY|RMB|元|¥/, EUR: /€|EUR/, JPY: /JP¥|JPY|円|¥/ };
  const dispRe = curV && SYM[curV];
  // 할인 전 정가·시장가 같은 후보는 뒤로 미룬다 (화면의 판매가를 먼저)
  const notOriginal = (c) => !/original|origin|before|market|retail|strike|listPrice|was/i.test(c.path);
  const pdPool = dispRe ? pd.priceCands.filter((c) => !/ladder/i.test(c.path) && notOriginal(c) && dispRe.test(c.value) && PRICE_RE.test(c.value)) : [];
  // 할인 중이면 화면에 크게 보이는 할인가(…Promotion…)를 먼저 쓴다 (11/18 방석: pricePromotionRangeText)
  const pdDisp = pdPool.find((c) => /promotion|discount/i.test(c.path)) || pdPool[0];
  const domDisp = dispRe && domPriceCands.find((c) => dispRe.test(c.text));
  const [priceV, priceS] = tiersFound
    ? first([ld.prices[0], 'jsonld'], [domPrices[0], 'dom:price'])
    : first(pdDisp && [pdDisp.value, `page_data:${pdDisp.path}`], domDisp && [domDisp.text, 'dom:price-candidate'],
      [ld.prices[0], 'jsonld'], [domPrices[0], 'dom:price']);
  const [moqV, moqS] = first(pd.moq && [String(pd.moq.v), `page_data:${pd.moq.p}`], moqM && [clean(moqM[0]), 'text']);
  const [supV, supS] = first(pd.supplier && [pd.supplier.v, `page_data:${pd.supplier.p}`], [domSupplier, 'dom:supplier']);
  const [soldV, soldS] = first(pd.sold && [String(pd.sold.v), `page_data:${pd.sold.p}`], soldM && [soldM[1].replace(/,/g, ''), 'text']);
  // 페이지 데이터에 스토어 평가만 있고 상품 리뷰가 없으면, 화면 글자에서 찾은 평점·리뷰 수도 스토어 값일 수 있어 쓰지 않는다
  const storeOnly = pd.hasStoreReview && !pd.hasProductReview;
  if (storeOnly) debug.notes.push('상품 리뷰 없음으로 봄: 페이지 데이터에 스토어 평가만 있음 (평점·리뷰 수 비움)');
  // 페이지 데이터에 리뷰 정보가 있는데 상품 평점이 없으면 화면 글자에서도 평점을 찾지 않는다 (스토어 평점을 잡지 않도록)
  const pdReviewKnown = pd.hasProductReview || pd.hasStoreReview;
  const [rateV, rateS] = first([ld.rating, 'jsonld'], pd.rating && [String(pd.rating.v), `page_data:${pd.rating.p}`],
    !pdReviewKnown && ratingM && [ratingM[1], 'text']);
  // 상품 평점이 없으면(리뷰가 없는 상품) 화면 글자의 "N reviews"는 스토어 리뷰 수일 가능성이 커서 쓰지 않는다 (11/18 방석 사례)
  const textReviewOk = !storeOnly && rateV != null;
  if (!storeOnly && rateV == null && (ratingM || reviewM)) debug.notes.push('상품 평점이 없어 화면 글자의 리뷰 수를 쓰지 않음 (스토어 리뷰 수일 수 있음)');
  const [revV, revS] = first([ld.reviewCount, 'jsonld'], pd.reviewCount && [String(pd.reviewCount.v), `page_data:${pd.reviewCount.p}`],
    textReviewOk && ratingM && [ratingM[2].replace(/,/g, ''), 'text'], textReviewOk && reviewM && [reviewM[1].replace(/,/g, ''), 'text']);

  const imgs = [];
  const imgSeen = new Set();
  [...ld.images, ...pd.images, meta('og:image'), ...galleryImgs].forEach((u) => {
    const n = normImg(u);
    if (!n || imgSeen.has(imgKey(n)) || imgs.length >= MAX_IMG) return;
    imgSeen.add(imgKey(n));
    imgs.push(n);
  });
  const tiers = pd.tiers || (domTiers.length ? domTiers : []);
  // 페이지 데이터 속성 + 화면 속성 블록. 페이지 데이터가 있으면 화면에서는 포장·무게·판매 단위 같은 칸만 더한다
  // (옵션 버튼 "Gray | Brown" 같은 두 칸짜리 줄이 속성으로 섞이지 않도록)
  const DOM_ATTR_OK = /package|gross|weight|dimension|selling\s*unit|포장|중량|무게|치수|판매\s*단위/i;
  const attrs = [...pd.attrs.v];
  for (const [name, value] of domAttrs) {
    if (attrs.length < MAX_ATTR && !attrs.some((a) => a.name === name) && (!pd.attrs.v.length || DOM_ATTR_OK.test(name))) {
      attrs.push({ name, value });
    }
  }
  const attrSources = [...pd.attrs.p.map((p) => `page_data:${p}`),
    ...(attrs.length > pd.attrs.v.length && attrSource ? [attrSource] : [])];

  const d = new Date();
  const pad = (n) => String(Math.abs(Math.trunc(n))).padStart(2, '0');
  const off = -d.getTimezoneOffset();
  const capturedAt = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
    `${off >= 0 ? '+' : '-'}${pad(off / 60)}:${pad(off % 60)}`;
  if (!tiers.length && !priceV) debug.notes.push('가격을 찾지 못함: 팝업에서 직접 입력하거나 page_data_roots 를 보고 추출 규칙을 맞춰야 함');
  if (!attrs.length) debug.notes.push('속성 표를 찾지 못함');

  return {
    capture_version: '0.1',
    tool: { name: 'a02_capture_ext', version: VERSION },
    source_url: url.origin + url.pathname,
    host: url.hostname,
    platform: /(^|\.)alibaba\.com$/i.test(url.hostname) ? 'alibaba' : 'unknown',
    page_kind: /\/product-detail\//.test(url.pathname) ? 'product_detail' : 'other',
    captured_at: capturedAt,
    fields: {
      original_name: field(nameV, nameS),
      price_text: field(priceV, priceS),
      moq_text: field(moqV, moqS),
      supplier_name: field(supV, supS),
      sales_count: field(soldV, soldS),
      rating: field(rateV, rateS),
      review_count: field(revV, revS),
      currency_setting: field(curV, curS),
      shipping_text: field(shipText, 'dom:shipping-box'),
    },
    price_tiers: tiers,
    price_texts: [...ld.prices, ...domPrices].slice(0, MAX_PRICE_TEXT),
    price_candidates: { page_data: pd.priceCands.slice(0, 25), dom: domPriceCands },
    shipping_candidates: pd.shipCands,
    attributes: attrs,
    attributes_source: attrSources.length ? attrSources.join('; ') : null,
    options: pd.options ? pd.options.v : [],
    options_source: pd.options ? `page_data:${pd.options.p}` : null,
    image_urls: imgs,
    image_usage: 'needs_review',
    not_collected: ['HTML 본문', '상품 설명 원문', '리뷰 원문', '이미지 파일', '쿠키·계정 정보'],
    debug,
  };
}
