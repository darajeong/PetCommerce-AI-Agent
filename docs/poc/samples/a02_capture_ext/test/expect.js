// 시험 페이지용: 추출 결과를 기대값과 비교해 PASS/FAIL 을 페이지 아래에 표시한다.
function a02RenderChecks(result, checks) {
  const raw = JSON.stringify(result);
  const all = [...checks,
    ['설명 원문·계정 정보가 결과에 없음', !/FIXTURE DESCRIPTION|should-not-appear|fixture-secret-login/.test(raw)],
    ['source_url 에 쿼리·해시 없음', !/[?#]/.test(result.source_url)],
    ['이미지는 주소만, usage = needs_review', result.image_usage === 'needs_review' && result.image_urls.every((u) => /^https:\/\//.test(u))]];
  let pass = 0;
  const ul = document.createElement('ul');
  ul.id = 'a02-test-checks';
  all.forEach(([name, ok]) => {
    if (ok) pass++;
    const li = document.createElement('li');
    li.textContent = `[${ok ? 'PASS' : 'FAIL'}] ${name}`;
    ul.appendChild(li);
  });
  const h = document.createElement('h2');
  h.id = 'a02-test-summary';
  h.textContent = `${pass}/${all.length} PASS`;
  const pre = document.createElement('pre');
  pre.id = 'a02-test-out';
  pre.textContent = JSON.stringify(result, null, 2);
  document.body.append(h, ul, pre);
}
