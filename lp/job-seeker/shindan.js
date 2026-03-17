/**
 * 神奈川ナース転職 — 転職診断UI v4.0 (vanilla JS)
 * 7問構成: エリア→年代→看護師歴→職種→働き方→重視点→時期
 *
 * REQUIRED: Add to LP <head> before closing tag:
 *   <link rel="stylesheet" href="shindan.css">
 */
(function () {
  'use strict';

  /* ── Constants ── */
  var LINE_URL = 'https://lin.ee/oUgDB3x';
  var D = null;
  var A = { a: '', age: '', exp: '', s: '', w: '', c: '', t: '' };
  var C; // container element
  var currentStep = -1;
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Fetch data ── */
  var dataURL = '';
  try { dataURL = new URL('jobs-summary.json', document.currentScript.src).href; } catch (e) { dataURL = 'jobs-summary.json'; }
  fetch(dataURL).then(function (r) { return r.json(); }).then(function (d) { D = d; }).catch(function () {});

  /* ── Questions ── */
  var ICONS = ['📍', '🗓️', '📋', '🩺', '🏥', '💡', '📅'];
  var Q = [
    { k: 'a', t: '希望のエリアは？', e: 'shindan_q1', ek: 'area', o: [
      { l: '横浜・川崎', v: 'yokohama_kawasaki' },
      { l: '湘南・鎌倉', v: 'shonan_kamakura' },
      { l: '小田原・県西', v: 'odawara_seisho' },
      { l: '相模原・県央', v: 'sagamihara_kenoh' },
      { l: '横須賀・三浦', v: 'yokosuka_miura' }
    ]},
    { k: 'age', t: 'あなたの年代は？', e: 'shindan_q2', ek: 'age', o: [
      { l: '20代', v: '20s' },
      { l: '30代', v: '30s' },
      { l: '40代', v: '40s' },
      { l: '50代以上', v: '50s' }
    ]},
    { k: 'exp', t: '看護師歴はどのくらい？', e: 'shindan_q3', ek: 'exp', o: [
      { l: '1〜3年', v: '1to3' },
      { l: '3〜5年', v: '3to5' },
      { l: '5〜10年', v: '5to10' },
      { l: '10年以上', v: '10plus' },
      { l: 'ブランクあり', v: 'blank' }
    ]},
    { k: 's', t: 'あなたの職種は？', e: 'shindan_q4', ek: 'shikaku', o: [
      { l: '正看護師', v: 'kango' },
      { l: '准看護師', v: 'junkango' },
      { l: '助産師', v: 'josanshi' },
      { l: '保健師', v: 'hokenshi' }
    ]},
    { k: 'w', t: '希望の働き方は？', e: 'shindan_q5', ek: 'workstyle', o: [
      { l: '常勤（日勤のみ）', v: 'day_only' },
      { l: '常勤（夜勤あり）', v: 'with_night' },
      { l: 'パート・非常勤', v: 'parttime' },
      { l: '夜勤専従', v: 'night_only' }
    ]},
    { k: 'c', t: '一番大事にしたいことは？', e: 'shindan_q6', ek: 'concern', o: [
      { l: '給与アップ', v: 'salary' },
      { l: '休日・プライベート', v: 'holidays' },
      { l: '人間関係・職場の雰囲気', v: 'atmosphere' },
      { l: '通勤のしやすさ', v: 'commute' },
      { l: 'スキルアップ', v: 'skillup' }
    ]},
    { k: 't', t: '転職の温度感は？', e: 'shindan_q7', ek: 'timing', o: [
      { l: 'すぐにでも', v: 'urgent' },
      { l: '3ヶ月以内', v: '3months' },
      { l: '半年以内', v: '6months' },
      { l: '情報収集中', v: 'info' }
    ]}
  ];

  /* ── Micro-feedback messages ── */
  var FEEDBACK = {
    'a': function (v) {
      var names = { yokohama_kawasaki: '横浜・川崎', shonan_kamakura: '湘南・鎌倉', odawara_seisho: '小田原・県西', sagamihara_kenoh: '相模原・県央', yokosuka_miura: '横須賀・三浦' };
      return (names[v] || '') + 'エリア、了解！';
    },
    'age': function (v) {
      if (v === '20s') return '転職のゴールデンタイムです';
      if (v === '30s') return '市場価値が高い年代です';
      if (v === '40s') return '経験を活かせる求人を探します';
      return 'キャリアを活かせる求人を探します';
    },
    'exp': function (v) {
      if (v === '1to3') return '成長できる環境を探しますね';
      if (v === '3to5') return '経験を武器に条件アップが狙えます';
      if (v === '5to10') return '経験が武器になる時期です';
      if (v === '10plus') return 'ベテランの経験は大きな強みです';
      if (v === 'blank') return 'ブランクOKの求人もあります';
      return 'OK！';
    },
    's': function () { return 'OK！'; },
    'w': function (v) {
      if (v === 'day_only') return '日勤のみ、人気の条件です';
      if (v === 'parttime') return 'パート求人も豊富です';
      return 'OK！';
    },
    'c': function (v) {
      if (v === 'salary') return '給与、しっかり比較します';
      if (v === 'atmosphere') return '職場の雰囲気、大事ですよね';
      if (v === 'holidays') return 'プライベート重視、わかります';
      return 'チェックしますね';
    },
    't': function (v) {
      if (v === 'urgent') return 'すぐに動きましょう！';
      if (v === '3months') return '余裕を持って探せますね';
      if (v === 'info') return 'まずは情報収集から！';
      return 'OK！';
    }
  };

  /* ── Concern-based result headlines ── */
  var CONCERN_HEADLINES = {
    salary: '給与アップが狙える求人',
    holidays: '年間休日120日以上の求人',
    atmosphere: '働きやすさ◎の求人',
    commute: 'エリア駅チカの求人',
    skillup: '教育体制充実の求人'
  };

  /* ── Age × Experience personalization messages ── */
  var AGE_EXP_MSG = {
    '20s_1to3': 'キャリアの土台を作るチャンスです',
    '20s_3to5': '経験を積みながら条件アップが狙える年代です',
    '20s_5to10': '20代で豊富な経験は大きな強みです',
    '20s_10plus': '貴重なキャリアです。選べる立場にあります',
    '20s_blank': '20代なら復帰のハードルは低いです',
    '30s_1to3': '30代からでも十分キャリアアップできます',
    '30s_3to5': '転職市場で最も需要が高い年代・経験です',
    '30s_5to10': '即戦力として引く手あまたの条件です',
    '30s_10plus': '転職市場で最も需要が高い年代です',
    '30s_blank': '経験がある分、復帰後も即戦力です',
    '40s_1to3': '人生経験を活かせる職場を探します',
    '40s_3to5': '経験を活かした職場選びができる年代です',
    '40s_5to10': '管理職・指導職のチャンスが豊富です',
    '40s_10plus': '管理職・専門職求人が多数あります',
    '40s_blank': '経験豊富な方の復帰を歓迎する職場があります',
    '50s_1to3': '意欲を評価する求人があります',
    '50s_3to5': '即戦力として歓迎される求人が豊富です',
    '50s_5to10': '即戦力として歓迎される求人が豊富です',
    '50s_10plus': 'ベテランとして重宝される年代です',
    '50s_blank': '経験を活かして復帰できる職場を探します'
  };

  /* ── Label lookup for summary card ── */
  function findLabel(qIdx, val) {
    var opts = Q[qIdx] && Q[qIdx].o;
    if (!opts) return val;
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].v === val) return opts[i].l;
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
    var total = Q.length;
    var wrap = el('div', 'shindan-progress-wrap');
    wrap.setAttribute('role', 'progressbar');
    wrap.setAttribute('aria-valuenow', String(stepIdx + 1));
    wrap.setAttribute('aria-valuemin', '1');
    wrap.setAttribute('aria-valuemax', String(total));
    wrap.setAttribute('aria-label', '質問 ' + (stepIdx + 1) + ' / ' + total);

    var track = el('div', 'shindan-progress');
    var bar = el('div', 'shindan-progress-bar');
    track.appendChild(bar);
    wrap.appendChild(track);

    var label = el('div', 'shindan-progress-label', (stepIdx + 1) + ' / ' + total);
    wrap.appendChild(label);

    // Animate bar after paint
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bar.style.width = Math.round((stepIdx + 1) / total * 100) + '%';
      });
    });

    return wrap;
  }

  /* ── Step dots ── */
  function buildDots(stepIdx) {
    var wrap = el('div', 'shindan-dots');
    wrap.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < Q.length; i++) {
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
    var q = Q[i];
    var prevStep = C.querySelector('.shindan-step');

    function renderNew() {
      C.innerHTML = '';
      currentStep = i;

      var s = el('div', 'shindan-step');
      s.appendChild(buildProgress(i));
      s.appendChild(buildDots(i));

      var title = el('h3', 'shindan-title',
        '<span class="shindan-title-icon">' + ICONS[i] + '</span>' + q.t);
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

          // Show micro-feedback if available
          var fbFn = FEEDBACK[q.k];
          var feedbackMsg = fbFn ? fbFn(o.v) : null;

          if (feedbackMsg && !reducedMotion) {
            // Insert feedback toast above options
            var existing = s.querySelector('.shindan-feedback');
            if (existing) existing.parentNode.removeChild(existing);
            var fb = el('div', 'shindan-feedback', feedbackMsg);
            s.insertBefore(fb, g);

            setTimeout(function () {
              if (i < Q.length - 1) {
                step(i + 1);
              } else {
                result();
              }
            }, 600);
          } else {
            var delay = reducedMotion ? 100 : 350;
            setTimeout(function () {
              if (i < Q.length - 1) {
                step(i + 1);
              } else {
                result();
              }
            }, delay);
          }
        });

        g.appendChild(b);
      });

      s.appendChild(g);
      C.appendChild(s);

      // Auto-focus first option (only when user has scrolled to shindan)
      var firstBtn = g.querySelector('.shindan-btn');
      if (firstBtn) {
        setTimeout(function () {
          var rect = C.getBoundingClientRect();
          if (rect.top < window.innerHeight && rect.bottom > 0) {
            firstBtn.focus({ preventScroll: true });
          }
        }, reducedMotion ? 0 : 400);
      }

      // Keyboard navigation
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
          btns.forEach(function (b, i) { b.tabIndex = i === next ? 0 : -1; });
          btns[next].focus({ preventScroll: true });
        }
      });
    }

    // Slide out previous step, then render new
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
    var start = 0;
    var startTime = null;
    function tick(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      // Ease out cubic
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = Math.round(eased * target);
      element.textContent = current;
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
    var d = ar && ar[A.a] && ar[A.a].count > 0 ? ar[A.a] : (ar && ar.all ? ar.all : null);

    // Get workstyle-filtered data
    var ws = d && d.by_workstyle && d.by_workstyle[A.w] ? d.by_workstyle[A.w] : null;
    var ct = ws ? ws.count : (d ? d.count : 0);
    var sn = ws ? ws.salary_min : (d ? d.salary_min : 200);
    var sx = ws ? ws.salary_max : (d ? d.salary_max : 450);

    ga('shindan_complete', { match_count: ct, area: A.a, age: A.age, exp: A.exp, shikaku: A.s, workstyle: A.w, concern: A.c, timing: A.t });

    var r = el('div', 'shindan-result');

    /* Progress (complete) */
    var pWrap = buildProgress(Q.length - 1);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var bar = pWrap.querySelector('.shindan-progress-bar');
        if (bar) bar.style.width = '100%';
      });
    });
    r.appendChild(pWrap);

    var dots = buildDots(Q.length); // all done
    r.appendChild(dots);

    /* Age × Experience personalization message */
    var aeKey = A.age + '_' + A.exp;
    var aeMsg = AGE_EXP_MSG[aeKey];
    if (aeMsg) {
      r.appendChild(el('p', 'shindan-age-message', aeMsg));
    }

    /* Heading with count-up — personalized by concern */
    var headlineText = CONCERN_HEADLINES[A.c] || 'あなたにマッチする求人';
    var heading = el('h3', 'shindan-result-heading',
      headlineText + ' <strong><span class="shindan-count-num" aria-live="polite">0</span>件</strong>');
    r.appendChild(heading);

    /* Salary range — salary_min/max は千円単位の月給 (parttime is hourly) */
    var salaryHTML;
    if (A.w === 'parttime') {
      salaryHTML = '時給 <strong>' + sn + '〜' + sx + '円</strong>';
    } else {
      var snMan = Math.round(sn / 10);
      var sxMan = Math.round(sx / 10);
      salaryHTML = '月給 <strong>' + snMan + '〜' + sxMan + '万円</strong>';
    }
    r.appendChild(el('div', 'shindan-salary-range', salaryHTML));

    /* Urgent badge */
    if (A.t === 'urgent') {
      var badge = el('div', 'shindan-badge', '急募求人あり', { 'aria-label': '急募求人あり' });
      r.appendChild(badge);
    }

    /* Sample card */
    if (d && d.sample) {
      r.appendChild(jobCard(d.sample, false));
    }

    /* Blurred cards with overlay */
    if (d && d.blurred && d.blurred.length) {
      var blurWrap = el('div', 'shindan-blur-overlay');
      d.blurred.forEach(function (j) {
        blurWrap.appendChild(jobCard(j, true));
      });
      var blurLabel = el('div', 'shindan-blur-label', '🔒 LINEで全件チェック');
      blurWrap.appendChild(blurLabel);
      r.appendChild(blurWrap);
    }

    /* Diagnostic summary card */
    var summaryHTML =
      '<div class="shindan-summary-title">あなたの診断結果</div>' +
      '<div class="shindan-summary-items">' +
        '<div>📍 ' + findLabel(0, A.a) + '</div>' +
        '<div>🗓️ ' + findLabel(1, A.age) + '</div>' +
        '<div>📋 ' + findLabel(2, A.exp) + '</div>' +
        '<div>🩺 ' + findLabel(3, A.s) + '</div>' +
        '<div>🏥 ' + findLabel(4, A.w) + '</div>' +
        '<div>💡 ' + findLabel(5, A.c) + '</div>' +
        '<div>📅 ' + findLabel(6, A.t) + '</div>' +
      '</div>';
    r.appendChild(el('div', 'shindan-summary', summaryHTML));

    /* CTA */
    var ctaText = A.t === 'info' ? 'まずは情報だけ受け取る' : 'LINEで求人を受け取る';
    var utmContent = encodeURIComponent(A.s + '_' + A.a + '_' + A.age + '_' + A.exp + '_' + A.w + '_' + A.c + '_' + A.t);
    var ctaURL = LINE_URL + '?utm_source=lp&utm_medium=shindan&utm_content=' + utmContent;

    var cta = el('a', 'shindan-cta', '', {
      href: ctaURL,
      target: '_blank',
      rel: 'noopener',
      'aria-label': ctaText + ' — LINEで友だち追加'
    });

    // LINE icon SVG
    cta.innerHTML =
      '<svg class="shindan-cta-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 5.82 2 10.5c0 2.83 1.67 5.33 4.27 6.92L5.5 21l3.6-1.97C10.03 19.34 11 19.5 12 19.5c5.52 0 10-3.82 10-8.5S17.52 2 12 2zm-2.5 11h-2v-1h2v1zm0-2h-2v-1h2v1zm3.25 2h-2v-1h2v1zm0-2h-2v-1h2v1zm3.25 2h-2v-1h2v1zm0-2h-2v-1h2v1z" fill="currentColor"/></svg>' +
      '<span>' + ctaText + '</span>';

    cta.addEventListener('click', function () {
      ga('shindan_line_click', { area: A.a, age: A.age, exp: A.exp, shikaku: A.s, workstyle: A.w, concern: A.c, timing: A.t });
      if (typeof fbq === 'function') fbq('track', 'Lead');
    });

    r.appendChild(cta);

    /* 引き継ぎコード生成 */
    var codeEl = el('div', 'shindan-handoff-code');
    codeEl.innerHTML = '引き継ぎコード生成中...';
    codeEl.style.cssText = 'text-align:center;padding:12px;margin-top:12px;background:#f0f8ff;border-radius:8px;font-size:0.95em;color:#333;';
    r.appendChild(codeEl);

    fetch('/api/web-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        area: A.a,
        age: A.age,
        experience: A.exp,
        specialty: A.s,
        workstyle: A.w,
        concern: A.c,
        timing: A.t,
      })
    }).then(function(res) { return res.json(); })
    .then(function(data) {
      if (data.code && codeEl) {
        codeEl.innerHTML = '引き継ぎコード: <strong style="font-size:1.3em;letter-spacing:2px;">' + data.code + '</strong><br><span style="font-size:0.8em;color:#666;">LINEに登録後、このコードを送ると診断結果が引き継がれます</span>';
      }
    }).catch(function() {
      if (codeEl) codeEl.innerHTML = '';
    });

    C.appendChild(r);

    /* Trigger count-up after render */
    var countEl = r.querySelector('.shindan-count-num');
    if (countEl) {
      setTimeout(function () { countUp(countEl, ct, 1200); }, reducedMotion ? 0 : 300);
    }

    /* Smooth scroll to results */
    setTimeout(function () {
      r.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'center' });
    }, reducedMotion ? 0 : 200);
  }

  /* ── Init ── */
  function init() {
    C = document.getElementById('shindan-container');
    if (!C) return;

    ga('shindan_start');

    // Show skeleton briefly if data not loaded yet
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

  /* ── Lazy init: 診断セクションがビューポートに入ったら初期化 ── */
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', lazyInit);
  } else {
    lazyInit();
  }
})();
