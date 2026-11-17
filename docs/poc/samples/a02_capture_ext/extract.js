/*
 * A02 상세페이지 사실 값 추출 함수 (a02_capture_ext v0.1.0, 2026-11-17)
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
  const VERSION = '0.1.0';
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
    return u.replace(/\?.*$/, '').replace(/_(\d+x\d+|Q\d+)[^/]*$/i, '');
  };

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
               reviewCount: null, images: [], tiers: null, attrs: null, options: null };
  const isNum = (x) => (typeof x === 'number' && isFinite(x)) || (typeof x === 'string' && /^\d[\d,]*(\.\d+)?$/.test(x.trim()));
  const pick = (o, re) => Object.keys(o).find((k) => re.test(k));

  function inspectKey(k, x, path) {
    if (typeof x === 'string') {
      const t = clean(x);
      if (/^(subject|productTitle|productName)$/i.test(k) && t.length >= 8 && t.length <= 300 && !pd.title) pd.title = { v: t, p: path };
      else if (/^title$/i.test(k) && t.length >= 8 && t.length <= 300 && !pd.titleWeak) pd.titleWeak = { v: t, p: path };
      if (/^(currency|currencyCode|currencyType|localCurrency|curr)$/i.test(k) && /^[A-Z]{3}$/.test(t)) pd.currency[t] = (pd.currency[t] || 0) + 1;
      if (/^(companyName|supplierName|sellerName|shopName|storeName)$/i.test(k) && t.length >= 2 && t.length <= 200 && !pd.supplier) pd.supplier = { v: t, p: path };
      if (/\.(jpe?g|png|webp)(\?|_|$)/i.test(t) && /^(https?:)?\/\//i.test(t) && /image|img|media|gallery|pic|photo/i.test(path) && pd.images.length < 60) pd.images.push(t);
    }
    if (isNum(x)) {
      const n = Number(String(x).replace(/,/g, ''));
      if (/^(moq|minOrder|minOrderQuantity|minimumOrderQuantity|minOrderQty)$/i.test(k) && pd.moq == null && n > 0) pd.moq = { v: n, p: path };
      if (/^(soldCount|salesVolume|tradeCount|orderCount|sold|saleCount)$/i.test(k) && pd.sold == null) pd.sold = { v: n, p: path };
      if (/^(averageStar|ratingValue|rating|productScore|reviewScore|avgStar)$/i.test(k) && pd.rating == null && n >= 0 && n <= 5) pd.rating = { v: n, p: path };
      if (/^(reviewCount|totalReviews|commentCount|reviewNum|reviewsCount)$/i.test(k) && pd.reviewCount == null) pd.reviewCount = { v: n, p: path };
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
    // 속성 (이름·값 쌍)
    if (!pd.attrs && arr.length >= 2) {
      const PAIRS = [['attrName', 'attrValue'], ['propertyName', 'propertyValue'], ['name', 'value'], ['key', 'value'], ['label', 'value']];
      for (const [kn, kv] of PAIRS) {
        if (kn === 'name' || kn === 'key' || kn === 'label') { if (!/propert|attr|spec|param/i.test(path)) continue; }
        const rows = objs.filter((o) => typeof o[kn] === 'string' && (typeof o[kv] === 'string' || typeof o[kv] === 'number'))
          .map((o) => ({ name: clean(o[kn]), value: clean(o[kv]) }))
          .filter((r) => r.name.length >= 1 && r.name.length <= 40 && r.value.length >= 1 && r.value.length <= 120);
        if (rows.length >= 2 && rows.length >= objs.length * 0.8) { pd.attrs = { v: rows.slice(0, MAX_ATTR), p: path }; break; }
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
  const docTitle = clean(document.title).replace(/\s*[-|]\s*(Buy|Alibaba\.com).*$/i, '');

  const domPrices = [];
  document.querySelectorAll('[class*="price" i]').forEach((el) => {
    if (domPrices.length >= MAX_PRICE_TEXT) return;
    const t = clean(el.innerText);
    if (t.length > 80) return;
    const m = t.match(PRICE_RE);
    if (m && !domPrices.includes(clean(m[0]))) domPrices.push(clean(m[0]));
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
  const soldM = bodyText.match(/([\d,]+)\s*(?:sold|판매됨|개 판매|건 판매)/i);
  const reviewM = bodyText.match(/([\d,]+)\s*(?:reviews?|리뷰|후기|상품평)/i);
  const ratingM = bodyText.match(/(\d(?:\.\d)?)\s*\/\s*5(?!\d)/);

  let domCurrency = null;
  document.querySelectorAll('[class*="currency" i]').forEach((el) => {
    if (domCurrency) return;
    const m = clean(el.innerText).match(new RegExp('\\b(' + CODES + ')\\b'));
    if (m) domCurrency = m[1] === 'RMB' ? 'CNY' : m[1];
  });

  const galleryImgs = [];
  document.querySelectorAll('[class*="gallery" i] img,[class*="main-image" i] img,[class*="slider" i] img,[class*="thumb" i] img,[class*="image-view" i] img,[class*="media" i] img').forEach((img) => {
    galleryImgs.push(img.currentSrc || img.getAttribute('src') || img.getAttribute('data-src'));
  });
  debug.strategies.push('dom');

  // ---------------------------------------------------------------- 4. 우선순위대로 고르기
  const first = (...cands) => cands.find((c) => c && c[0] != null && c[0] !== '') || [null, null];
  const pdCur = Object.entries(pd.currency).sort((a, b) => b[1] - a[1])[0];
  const [nameV, nameS] = first([ld.name, 'jsonld'], pd.title && [pd.title.v, `page_data:${pd.title.p}`],
    h1 && [clean(h1.innerText), 'dom:h1'], [ogTitle, 'dom:og:title'], pd.titleWeak && [pd.titleWeak.v, `page_data:${pd.titleWeak.p}`], [docTitle, 'dom:title']);
  const [priceV, priceS] = first([ld.prices[0], 'jsonld'], [domPrices[0], 'dom:price']);
  const [moqV, moqS] = first(pd.moq && [String(pd.moq.v), `page_data:${pd.moq.p}`], moqM && [clean(moqM[0]), 'text']);
  const [supV, supS] = first(pd.supplier && [pd.supplier.v, `page_data:${pd.supplier.p}`], [domSupplier, 'dom:supplier']);
  const [soldV, soldS] = first(pd.sold && [String(pd.sold.v), `page_data:${pd.sold.p}`], soldM && [soldM[1].replace(/,/g, ''), 'text']);
  const [rateV, rateS] = first([ld.rating, 'jsonld'], pd.rating && [String(pd.rating.v), `page_data:${pd.rating.p}`], ratingM && [ratingM[1], 'text']);
  const [revV, revS] = first([ld.reviewCount, 'jsonld'], pd.reviewCount && [String(pd.reviewCount.v), `page_data:${pd.reviewCount.p}`], reviewM && [reviewM[1].replace(/,/g, ''), 'text']);
  const [curV, curS] = first(pdCur && [pdCur[0], 'page_data'], [domCurrency, 'dom:currency']);

  const imgs = [];
  [...ld.images, ...pd.images, meta('og:image'), ...galleryImgs].forEach((u) => {
    const n = normImg(u);
    if (n && !imgs.includes(n) && imgs.length < MAX_IMG) imgs.push(n);
  });
  const tiers = pd.tiers || (domTiers.length ? domTiers : []);
  const attrs = pd.attrs ? pd.attrs.v : [...domAttrs].map(([name, value]) => ({ name, value }));

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
    },
    price_tiers: tiers,
    price_texts: [...ld.prices, ...domPrices].slice(0, MAX_PRICE_TEXT),
    attributes: attrs,
    attributes_source: pd.attrs ? `page_data:${pd.attrs.p}` : attrSource,
    options: pd.options ? pd.options.v : [],
    options_source: pd.options ? `page_data:${pd.options.p}` : null,
    image_urls: imgs,
    image_usage: 'needs_review',
    not_collected: ['HTML 본문', '상품 설명 원문', '리뷰 원문', '이미지 파일', '쿠키·계정 정보'],
    debug,
  };
}
