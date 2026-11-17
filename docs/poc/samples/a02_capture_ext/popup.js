// A02 사실 값 추출 팝업 (a02_capture_ext v0.1.0)
// 버튼을 누를 때만 현재 탭에서 extract.js 의 a02ExtractFacts 를 한 번 실행한다. 자동 실행·페이지 이동 없음.

// W1-07 1.1절: PoC 내부 검증 상품 3개로 한정. 상품을 바꾸려면 팀 합의 후 이 목록을 고친다.
const PRODUCTS = [
  ['prod-w2-01', '01 · 대형견 리프트 하네스'],
  ['prod-w2-07', '07 · 대형견 방석'],
  ['prod-w2-09', '09 · 간식 공 장난감'],
];
const FIELDS = ['original_name', 'price_text', 'currency_setting', 'moq_text', 'supplier_name', 'sales_count', 'rating', 'review_count'];
const $ = (id) => document.getElementById(id);
let tab = null;
let mode = null;
let extracted = null;

function pageMode(u) {
  if (/(^|\.)alibaba\.com$/i.test(u.hostname) && u.pathname.includes('/product-detail/')) return 'alibaba';
  if (u.protocol === 'file:' && /a02_capture_ext\/test\//i.test(u.pathname.replace(/\\/g, '/'))) return 'test';
  return null;
}

function say(text, kind = '') {
  $('msg').textContent = text;
  $('msg').className = 'msg ' + kind;
}

const tiersToText = (t) => (t || []).map((r) => `${r.quantity_text} | ${r.price_text}`).join('\n');
const attrsToText = (a) => (a || []).map((r) => `${r.name}: ${r.value}`).join('\n');
const optsToText = (o) => (o || []).map((r) => `${r.name} = ${r.values.join(' / ')}`).join('\n');
const lines = (s) => s.split('\n').map((x) => x.trim()).filter(Boolean);
const textToTiers = (s) => lines(s).map((l) => { const i = l.lastIndexOf('|'); return { quantity_text: l.slice(0, i).trim(), price_text: l.slice(i + 1).trim() }; })
  .filter((r) => r.quantity_text && r.price_text);
const textToAttrs = (s) => lines(s).map((l) => { const i = l.search(/[:：]/); return i < 0 ? null : { name: l.slice(0, i).trim(), value: l.slice(i + 1).trim() }; })
  .filter((r) => r && r.name && r.value);
const textToOpts = (s) => lines(s).map((l) => { const i = l.indexOf('='); return i < 0 ? null : { name: l.slice(0, i).trim(), values: l.slice(i + 1).split('/').map((v) => v.trim()).filter(Boolean) }; })
  .filter((r) => r && r.name && r.values.length);

function render(r) {
  extracted = r;
  $('form').hidden = false;
  for (const k of FIELDS) {
    const f = r.fields[k] || { value: null, source: null };
    $('f_' + k).value = f.value || '';
    $('s_' + k).textContent = f.source ? `찾은 곳: ${f.source}` : '못 찾음 → 페이지를 보고 직접 입력하거나 비워 두기';
  }
  $('t_tiers').value = tiersToText(r.price_tiers);
  $('s_tiers').textContent = r.price_tiers.length ? `찾은 곳: ${r.price_tiers[0].source}` : '못 찾음';
  $('t_attrs').value = attrsToText(r.attributes);
  $('s_attrs').textContent = r.attributes_source ? `찾은 곳: ${r.attributes_source}` : '못 찾음';
  $('t_options').value = optsToText(r.options);
  $('s_options').textContent = r.options_source ? `찾은 곳: ${r.options_source}` : '못 찾음 → 직접 입력';
  $('imgSummary').textContent = `이미지 주소 ${r.image_urls.length}개 (파일은 저장 안 함, usage: needs_review)`;
  $('imgList').replaceChildren(...r.image_urls.map((u) => { const li = document.createElement('li'); li.textContent = u; return li; }));
  $('debug').textContent = JSON.stringify({ strategies: r.debug.strategies, page_data_roots: r.debug.page_data_roots, notes: r.debug.notes, price_texts: r.price_texts }, null, 2);
  $('save').disabled = false;
}

function collect() {
  const out = JSON.parse(JSON.stringify(extracted));
  const edited = [...(out.edited_fields || [])];   // 팝업을 다시 열었을 때 앞서 고친 칸 유지
  for (const k of FIELDS) {
    const v = $('f_' + k).value.trim();
    if (v !== (out.fields[k].value || '')) {
      out.fields[k] = { value: v || null, source: v ? 'human_edit' : null, auto_value: out.fields[k].value };
      edited.push(k);
    }
  }
  const tiers = textToTiers($('t_tiers').value);
  if ($('t_tiers').value.trim() !== tiersToText(out.price_tiers)) {
    out.price_tiers = tiers.map((t) => ({ ...t, source: 'human_edit' }));
    edited.push('price_tiers');
  }
  if ($('t_attrs').value.trim() !== attrsToText(out.attributes)) {
    out.attributes = textToAttrs($('t_attrs').value);
    out.attributes_source = 'human_edit';
    edited.push('attributes');
  }
  if ($('t_options').value.trim() !== optsToText(out.options)) {
    out.options = textToOpts($('t_options').value);
    out.options_source = 'human_edit';
    edited.push('options');
  }
  out.product_id = $('pid').value;
  out.collector = $('collector').value.trim() || null;
  out.capture_mode = mode;
  out.edited_fields = [...new Set(edited)];
  out.method_note = '사람이 페이지를 열고 버튼을 눌러 추출, 저장 전 사람이 값 확인 (W1-07: 페이지 열기·탐색 자동화 없음)';
  return out;
}

async function remember() {
  if (!extracted) return;
  try {
    await chrome.storage.session.set({ a02_last: { url: tab.url, pid: $('pid').value, collector: $('collector').value, extracted: collect() } });
  } catch (e) { /* 저장 실패해도 팝업은 동작 */ }
}

async function init() {
  $('pid').replaceChildren(...PRODUCTS.map(([v, t]) => { const o = document.createElement('option'); o.value = v; o.textContent = `${v} (${t})`; return o; }));
  [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  let u = null;
  try { u = new URL(tab.url); } catch (e) { /* chrome:// 등 */ }
  mode = u ? pageMode(u) : null;
  $('pageUrl').textContent = u ? u.hostname + u.pathname : '(주소 없음)';
  if (!mode) {
    $('extract').disabled = true;
    say('알리바바 상품 상세페이지(/product-detail/)에서만 쓸 수 있습니다. 페이지를 직접 연 뒤 다시 눌러 주세요.', 'warn');
  } else if (mode === 'test') {
    say('시험 페이지 모드입니다 (실제 상품 아님).', 'warn');
  }
  try {
    const { a02_last: last } = await chrome.storage.session.get('a02_last');
    if (last && last.url === tab.url && last.extracted) {
      $('pid').value = last.pid;
      $('collector').value = last.collector;
      render(last.extracted);
      say('이 페이지에서 마지막으로 추출한 값을 다시 불러왔습니다.', '');
    }
  } catch (e) { /* 무시 */ }
}

$('extract').addEventListener('click', async () => {
  say('추출 중…');
  try {
    const [inj] = await chrome.scripting.executeScript({ target: { tabId: tab.id }, world: 'MAIN', func: a02ExtractFacts, args: [null] });
    const r = inj && inj.result;
    if (!r) throw new Error('결과 없음');
    if (mode === 'test') r.platform = 'test';
    render(r);
    const missing = FIELDS.filter((k) => !r.fields[k].value).length;
    say(`추출 완료. 못 찾은 칸 ${missing}개, 수량 구간 ${r.price_tiers.length}개, 속성 ${r.attributes.length}개. 페이지와 대조한 뒤 저장하세요.`, missing ? 'warn' : 'ok');
    remember();
  } catch (e) {
    say('추출 실패: ' + e.message, 'bad');
  }
});

$('save').addEventListener('click', async () => {
  const data = collect();
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
  const filename = `petcommerce_a02/${data.product_id}_capture_${stamp}.json`;
  try {
    await chrome.downloads.download({
      url: 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(data, null, 2)),
      filename, conflictAction: 'uniquify', saveAs: false,
    });
    say(`저장했습니다: 다운로드/${filename}`, 'ok');
  } catch (e) {
    say('저장 실패: ' + e.message, 'bad');
  }
});

document.addEventListener('input', remember);
init();
