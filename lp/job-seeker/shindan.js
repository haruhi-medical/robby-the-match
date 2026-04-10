/**
 * ナースロビー — 転職診断UI v6.0 (vanilla JS)
 * 5問構成: 都道府県→サブエリア→施設タイプ→働き方→温度感
 * LINE intake_light フローと完全連動
 */
(function () {
  'use strict';

  /* ── Constants ── */
  var LINE_URL = 'https://lin.ee/oUgDB3x';
  var D = null;
  var A = { pref: '', area: '', ft: '', ws: '', urg: '' };
  var C;
  var currentStep = -1;
  var totalSteps = 5;
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Fetch data ── */
  var dataURL = '';
  try { dataURL = new URL('jobs-summary.json', document.currentScript.src).href; } catch (e) { dataURL = 'jobs-summary.json'; }
  fetch(dataURL).then(function (r) { return r.json(); }).then(function (d) { D = d; }).catch(function () {});

  /* ── SVG Icons ── */
  var _svg = function(d) { return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--sd-teal,#1a9de0)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;">' + d + '</svg>'; };
  var ICONS = {
    pref: _svg('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'),
    area: _svg('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'),
    ft:   _svg('<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
    ws:   _svg('<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>'),
    urg:  _svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
  };

  /* ── Q1: 都道府県 ── */
  var Q_PREF = { k: 'pref', t: '働きたいエリアは？', e: 'shindan_q1', ek: 'prefecture', icon: 'pref', o: [
    { l: '東京都', v: 'tokyo' },
    { l: '神奈川県', v: 'kanagawa' },
    { l: '千葉県', v: 'chiba' },
    { l: '埼玉県', v: 'saitama' },
    { l: 'その他の地域', v: 'other' }
  ]};

  /* ── Q2: サブエリア（都道府県別） ── */
  var SUBAREA = {
    tokyo: [
      { l: '23区', v: 'tokyo_23ku' },
      { l: '多摩地域', v: 'tokyo_tama' },
      { l: 'どこでもOK', v: 'tokyo_included' }
    ],
    kanagawa: [
      { l: '横浜・川崎', v: 'yokohama_kawasaki' },
      { l: '湘南・鎌倉', v: 'shonan_kamakura' },
      { l: '相模原・県央', v: 'sagamihara_kenoh' },
      { l: '横須賀・三浦', v: 'yokosuka_miura' },
      { l: '小田原・県西', v: 'odawara_kensei' },
      { l: 'どこでもOK', v: 'kanagawa_all' }
    ],
    chiba: [
      { l: '船橋・松戸・柏', v: 'chiba_tokatsu' },
      { l: '千葉市・内房', v: 'chiba_uchibo' },
      { l: '成田・印旛', v: 'chiba_inba' },
      { l: '外房・房総', v: 'chiba_sotobo' },
      { l: 'どこでもOK', v: 'chiba_all' }
    ],
    saitama: [
      { l: 'さいたま・南部', v: 'saitama_south' },
      { l: '東部・春日部', v: 'saitama_east' },
      { l: '西部・川越・所沢', v: 'saitama_west' },
      { l: '北部・熊谷', v: 'saitama_north' },
      { l: 'どこでもOK', v: 'saitama_all' }
    ],
    other: [
      { l: '関東の求人を見る', v: 'kanto_all' }
    ]
  };

  /* ── Q3: 施設タイプ ── */
  var Q_FT = { k: 'ft', t: 'どんな職場が気になりますか？', e: 'shindan_q3', ek: 'facility_type', icon: 'ft', o: [
    { l: '急性期病院', v: 'hospital_acute' },
    { l: '回復期病院', v: 'hospital_recovery' },
    { l: '慢性期病院', v: 'hospital_chronic' },
    { l: 'クリニック', v: 'clinic' },
    { l: '訪問看護', v: 'visiting' },
    { l: '介護施設', v: 'care' },
    { l: 'こだわりなし', v: 'any' }
  ]};

  /* ── Q4: 働き方 ── */
  var Q_WS = { k: 'ws', t: '希望の働き方は？', e: 'shindan_q4', ek: 'workstyle', icon: 'ws', o: [
    { l: '日勤のみ', v: 'day' },
    { l: '夜勤ありOK', v: 'twoshift' },
    { l: 'パート・非常勤', v: 'part' },
    { l: '夜勤専従', v: 'night' }
  ]};
  var Q_WS_CLINIC = { k: 'ws', t: '希望の働き方は？', e: 'shindan_q4', ek: 'workstyle', icon: 'ws', o: [
    { l: '常勤（日勤）', v: 'day' },
    { l: 'パート・非常勤', v: 'part' }
  ]};

  /* ── Q5: 温度感 ── */
  var Q_URG = { k: 'urg', t: '今の転職への気持ちは？', e: 'shindan_q5', ek: 'urgency', icon: 'urg', o: [
    { l: 'すぐにでも転職したい', v: 'urgent' },
    { l: 'いい求人があれば', v: 'good' },
    { l: 'まずは情報収集', v: 'info' }
  ]};

  /* ── Dynamic question sequence ── */
  function getSteps() {
    var steps = [Q_PREF];
    // Q2: subarea
    var sub = SUBAREA[A.pref] || SUBAREA.kanagawa;
    steps.push({ k: 'area', t: 'エリアを絞り込み', e: 'shindan_q2', ek: 'area', icon: 'area', o: sub });
    // Q3: facility type
    steps.push(Q_FT);
    // Q4: workstyle (clinic has fewer options)
    steps.push(A.ft === 'clinic' ? Q_WS_CLINIC : Q_WS);
    // Q5: urgency
    steps.push(Q_URG);
    return steps;
  }

  /* ── Micro-feedback ── */
  var FEEDBACK = {
    pref: function (v) {
      var n = { tokyo: '東京都', kanagawa: '神奈川県', chiba: '千葉県', saitama: '埼玉県', other: 'その他' };
      return (n[v] || '') + '、了解！';
    },
    area: function (v) { return 'エリア確認OK！'; },
    ft: function (v) {
      var n = { hospital_acute: '急性期病院', hospital_recovery: '回復期病院', hospital_chronic: '慢性期病院', clinic: 'クリニック', visiting: '訪問看護', care: '介護施設', any: 'こだわりなし' };
      return (n[v] || '') + '、探しますね';
    },
    ws: function (v) {
      if (v === 'day') return '日勤のみ、人気の条件です';
      if (v === 'part') return 'パート求人も豊富です';
      if (v === 'night') return '夜勤専従、高収入が狙えます';
      return 'OK！';
    },
    urg: function (v) {
      if (v === 'urgent') return 'すぐに動きましょう！';
      if (v === 'good') return 'いい求人を厳選しますね';
      if (v === 'info') return 'まずは情報収集から！';
      return 'OK！';
    }
  };

  /* ── Label lookup ── */
  function findLabel(key, val) {
    var allOpts = [Q_PREF].concat([Q_FT, Q_WS, Q_URG]);
    // Also check subareas
    for (var p in SUBAREA) {
      if (SUBAREA.hasOwnProperty(p)) {
        allOpts.push({ o: SUBAREA[p] });
      }
    }
    for (var i = 0; i < allOpts.length; i++) {
      var opts = allOpts[i].o;
      if (opts) {
        for (var j = 0; j < opts.length; j++) {
          if (opts[j].v === val) return opts[j].l;
        }
      }
    }
    return val;
  }

  /* ── Helpers ── */
  function ga(e, p) { if (typeof gtag === 'function') gtag('event', e, p || {}); }

  function el(tag, cls, html, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html) e.innerHTML = html;
    if (attrs) {
      for (var k in attrs) {
        if (attrs.hasOwnProperty(k)) e.setAttribute(k, attrs[k]);
      }
    }
    return e;
  }

  /* ── Ripple effect ── */
  function addRipple(btn, evt) {
    if (reducedMotion) return;
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height);
    var ripple = el('span', 'sd-ripple');
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (evt.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (evt.clientY - rect.top - size / 2) + 'px';
    btn.appendChild(ripple);
    setTimeout(function () { if (ripple.parentNode) ripple.parentNode.removeChild(ripple); }, 500);
  }

  /* ── Progress bar ── */
  function buildProgress(stepIdx) {
    var wrap = el('div', 'shindan-progress-wrap');
    wrap.setAttribute('role', 'progressbar');
    wrap.setAttribute('aria-valuenow', String(stepIdx + 1));
    wrap.setAttribute('aria-valuemin', '1');
    wrap.setAttribute('aria-valuemax', String(totalSteps));
    wrap.setAttribute('aria-label', '質問 ' + (stepIdx + 1) + ' / ' + totalSteps);

    var track = el('div', 'shindan-progress');
    var bar = el('div', 'shindan-progress-bar');
    track.appendChild(bar);
    wrap.appendChild(track);

    var label = el('div', 'shindan-progress-label', (stepIdx + 1) + ' / ' + totalSteps);
    wrap.appendChild(label);

    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bar.style.width = Math.round((stepIdx + 1) / totalSteps * 100) + '%';
      });
    });

    return wrap;
  }

  /* ── Step dots ── */
  function buildDots(stepIdx) {
    var wrap = el('div', 'shindan-dots');
    wrap.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < totalSteps; i++) {
      var dot = el('span', 'shindan-dot' + (i < stepIdx ? ' done' : '') + (i === stepIdx ? ' active' : ''));
      wrap.appendChild(dot);
    }
    return wrap;
  }

  /* ── Skeleton loader ── */
  function showSkeleton() {
    var sk = el('div', 'shindan-skeleton');
    sk.setAttribute('aria-label', '読み込み中');
    for (var i = 0; i < 4; i++) {
      sk.appendChild(el('div', 'shindan-skeleton-line'));
    }
    C.innerHTML = '';
    C.appendChild(sk);
  }

  /* ── Step render ── */
  function step(i) {
    var steps = getSteps();
    if (i >= steps.length) { result(); return; }
    var q = steps[i];
    var prevStep = C.querySelector('.shindan-step');

    function renderNew() {
      C.innerHTML = '';
      currentStep = i;

      var s = el('div', 'shindan-step');
      s.appendChild(buildProgress(i));
      s.appendChild(buildDots(i));

      var icon = ICONS[q.icon] || ICONS.pref;
      var title = el('h3', 'shindan-title',
        '<span class="shindan-title-icon">' + icon + '</span>' + q.t);
      s.appendChild(title);

      var g = el('div', 'shindan-options');
      g.setAttribute('role', 'radiogroup');
      g.setAttribute('aria-label', q.t);

      q.o.forEach(function (o, idx) {
        var b = el('button', 'shindan-btn', o.l, {
          type: 'button',
          role: 'radio',
          'aria-checked': 'false',
          'aria-label': o.l,
          tabindex: idx === 0 ? '0' : '-1'
        });

        b.addEventListener('click', function (evt) {
          A[q.k] = o.v;
          g.querySelectorAll('.shindan-btn').forEach(function (x) {
            x.classList.remove('selected');
            x.setAttribute('aria-checked', 'false');
          });
          b.classList.add('selected');
          b.setAttribute('aria-checked', 'true');
          addRipple(b, evt);

          var p = {};
          p[q.ek] = o.v;
          ga(q.e, p);

          var fbFn = FEEDBACK[q.k];
          var feedbackMsg = fbFn ? fbFn(o.v) : null;

          if (feedbackMsg && !reducedMotion) {
            var existing = s.querySelector('.shindan-feedback');
            if (existing) existing.parentNode.removeChild(existing);
            var fb = el('div', 'shindan-feedback', feedbackMsg);
            s.insertBefore(fb, g);

            setTimeout(function () { step(i + 1); }, 600);
          } else {
            setTimeout(function () { step(i + 1); }, reducedMotion ? 100 : 350);
          }
        });

        g.appendChild(b);
      });

      s.appendChild(g);
      C.appendChild(s);

      var firstBtn = g.querySelector('.shindan-btn');
      if (firstBtn) {
        setTimeout(function () {
          var rect = C.getBoundingClientRect();
          if (rect.top < window.innerHeight && rect.bottom > 0) {
            firstBtn.focus({ preventScroll: true });
          }
        }, reducedMotion ? 0 : 400);
      }

      g.addEventListener('keydown', function (e) {
        var btns = Array.prototype.slice.call(g.querySelectorAll('.shindan-btn'));
        var idx = btns.indexOf(document.activeElement);
        if (idx < 0) return;
        var next = -1;
        if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
          next = (idx + 1) % btns.length;
        } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
          next = (idx - 1 + btns.length) % btns.length;
        } else if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          btns[idx].click();
          return;
        }
        if (next >= 0) {
          e.preventDefault();
          btns.forEach(function (b, bi) { b.tabIndex = bi === next ? 0 : -1; });
          btns[next].focus({ preventScroll: true });
        }
      });
    }

    if (prevStep && !reducedMotion) {
      prevStep.classList.add('slide-out');
      setTimeout(renderNew, 280);
    } else {
      renderNew();
    }
  }

  /* ── Count-up animation ── */
  function countUp(element, target, duration) {
    if (reducedMotion || target === 0) {
      element.textContent = target;
      return;
    }
    var startTime = null;
    function tick(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = Math.round(eased * target);
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  /* ── Job card ── */
  function jobCard(j, isBlurred) {
    var c = el('div', 'shindan-job-card' + (isBlurred ? ' blurred' : ''));
    var tags = [];
    if (j.type) tags.push(j.type);
    if (j.bonus) tags.push('賞与あり');
    if (j.holidays) tags.push('年休' + j.holidays);
    c.innerHTML =
      '<div class="shindan-job-name">' + (j.title || j.name || '非公開求人') + '</div>' +
      '<div class="shindan-job-salary">' + (j.salary || '') + '</div>' +
      (tags.length ? '<div class="shindan-job-tags">' + tags.map(function (t) { return '<span>' + t + '</span>'; }).join('') + '</div>' : '');
    return c;
  }

  /* ── Result screen ── */
  function result() {
    C.innerHTML = '';

    var ar = D && D.areas ? D.areas : D;
    var d = ar && ar[A.area] && ar[A.area].count > 0 ? ar[A.area] : (ar && ar.all ? ar.all : null);

    var WS_TO_JSON = { day: 'day_only', twoshift: 'with_night', part: 'parttime', night: 'night_only' };
    var wsJsonKey = WS_TO_JSON[A.ws] || A.ws;
    var wsData = d && d.by_workstyle && d.by_workstyle[wsJsonKey] ? d.by_workstyle[wsJsonKey] : null;
    var ct = wsData ? wsData.count : (d ? d.count : 0);

    ga('shindan_complete', { match_count: ct, prefecture: A.pref, area: A.area, facility_type: A.ft, workstyle: A.ws, urgency: A.urg });

    var r = el('div', 'shindan-result');

    var pWrap = buildProgress(totalSteps - 1);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var bar = pWrap.querySelector('.shindan-progress-bar');
        if (bar) bar.style.width = '100%';
      });
    });
    r.appendChild(pWrap);
    r.appendChild(buildDots(totalSteps));

    /* Heading */
    var headingText = ct > 0
      ? '条件に合う求人 <strong>' + ct + '件</strong>'
      : '診断完了！';
    var heading = el('h3', 'shindan-result-heading', headingText);
    r.appendChild(heading);

    /* Sample job card */
    if (d && d.sample) {
      r.appendChild(jobCard(d.sample, false));
    }

    /* Blurred cards with overlay */
    if (d && d.blurred && d.blurred.length) {
      var blurWrap = el('div', 'shindan-blur-overlay');
      d.blurred.forEach(function (j) {
        blurWrap.appendChild(jobCard(j, true));
      });
      var blurLabel = el('div', 'shindan-blur-label', 'LINEで全件チェック');
      blurWrap.appendChild(blurLabel);
      r.appendChild(blurWrap);
    }

    /* Summary card */
    var summaryHTML =
      '<div class="shindan-summary-title">あなたの希望条件</div>' +
      '<div class="shindan-summary-items">' +
        '<div>' + ICONS.pref + ' ' + findLabel('pref', A.pref) + ' / ' + findLabel('area', A.area) + '</div>' +
        '<div>' + ICONS.ft + ' ' + findLabel('ft', A.ft) + '</div>' +
        '<div>' + ICONS.ws + ' ' + findLabel('ws', A.ws) + '</div>' +
        '<div>' + ICONS.urg + ' ' + findLabel('urg', A.urg) + '</div>' +
      '</div>' +
      '<div style="margin-top:12px;padding:10px;background:var(--primary-light,#e6f4fb);border-radius:8px;font-size:0.88rem;color:var(--primary,#1a9de0);text-align:center;">' +
        'LINEで診断結果と求人をお届けします' +
      '</div>';
    r.appendChild(el('div', 'shindan-summary', summaryHTML));

    /* CTA → LINE（友だち追加URL直リンク + LIFF フォールバック） */
    var EP = '/lp/job-seeker/liff.html';
    var sid = window.__lineSessionId || '';
    var areaLabel = findLabel('area', A.area);
    var answersJson = encodeURIComponent(JSON.stringify({
      prefecture: A.pref,
      area: A.area,
      areaLabel: areaLabel,
      facilityType: A.ft,
      workstyle: A.ws,
      urgency: A.urg
    }));

    var skipped = window._shindanSkipped;
    window._shindanSkipped = false;

    // 外部ブラウザ → LINE友だち追加URLに直接遷移（LIFFエラー回避）
    // LIFF使えるLINE内ブラウザ → liff.html経由
    var isLineApp = /Line/i.test(navigator.userAgent);
    var ctaURL;
    if (isLineApp) {
      ctaURL = EP + '?session_id=' + sid + '&source=' + (skipped ? 'shindan_skip' : 'shindan') + '&intent=diagnose&answers=' + answersJson;
    } else {
      ctaURL = 'https://lin.ee/oUgDB3x';
    }

    var ctaText = 'LINEで診断結果を受け取る';
    var cta = el('a', 'shindan-cta', '', {
      href: ctaURL,
      target: '_blank',
      rel: 'noopener',
      'aria-label': ctaText
    });
    cta.innerHTML = '<span>' + ctaText + '</span>';
    cta.addEventListener('click', function () {
      ga('click_cta', { source: 'shindan', intent: 'diagnose', page_type: 'paid_lp', session_id: sid, prefecture: A.pref, area: A.area, facility_type: A.ft, workstyle: A.ws, urgency: A.urg });
    });
    r.appendChild(cta);

    var note = el('p', 'shindan-note', '※完全無料・電話なし・いつでもブロックOK');
    r.appendChild(note);

    C.appendChild(r);

    setTimeout(function () {
      r.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
    }, reducedMotion ? 0 : 200);
  }

  /* ── Init ── */
  function init() {
    C = document.getElementById('shindan-container');
    if (!C) return;
    ga('shindan_start');
    if (!D) {
      showSkeleton();
      var attempts = 0;
      var poll = setInterval(function () {
        attempts++;
        if (D || attempts > 20) {
          clearInterval(poll);
          step(0);
        }
      }, 100);
    } else {
      step(0);
    }
  }

  /* ── Lazy init ── */
  function lazyInit() {
    var container = document.getElementById('shindan-container');
    if (!container) return;
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          observer.disconnect();
          init();
        }
      });
    }, { threshold: 0.1, rootMargin: '0px' });
    observer.observe(container);
  }

  /* ── Skip to result ── */
  window.shindanSkip = function () {
    C = document.getElementById('shindan-container');
    if (!C) return;
    A = { pref: 'kanagawa', area: 'yokohama_kawasaki', ft: 'any', ws: 'day', urg: 'info' };
    window._shindanSkipped = true;
    ga('shindan_skip');
    if (!D) {
      showSkeleton();
      var attempts = 0;
      var poll = setInterval(function () {
        attempts++;
        if (D || attempts > 20) {
          clearInterval(poll);
          result();
        }
      }, 100);
    } else {
      result();
    }
    setTimeout(function () {
      C.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', lazyInit);
  } else {
    lazyInit();
  }
})();
