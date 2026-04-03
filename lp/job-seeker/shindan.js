/**
 * ナースロビー — 転職診断UI v5.0 (vanilla JS)
 * 3問構成: エリア→働き方→温度感
 *
 * REQUIRED: Add to LP <head> before closing tag:
 *   <link rel="stylesheet" href="shindan.css">
 */
(function () {
  'use strict';

  /* ── Constants ── */
  var LINE_URL = 'https://lin.ee/oUgDB3x';
  var D = null;
  var A = { a: '', w: '', t: '' };
  var C; // container element
  var currentStep = -1;
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Fetch data ── */
  var dataURL = '';
  try { dataURL = new URL('jobs-summary.json', document.currentScript.src).href; } catch (e) { dataURL = 'jobs-summary.json'; }
  fetch(dataURL).then(function (r) { return r.json(); }).then(function (d) { D = d; }).catch(function () {});

  /* ── Questions ── */
  var _svg = function(d) { return '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--sd-teal,#1a7f64)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;">' + d + '</svg>'; };
  var ICONS = [
    _svg('<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>'),
    _svg('<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
    _svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
  ];
  var Q = [
    { k: 'a', t: '希望のエリアは？', e: 'shindan_q1', ek: 'area', o: [
      { l: '横浜・川崎', v: 'yokohama_kawasaki' },
      { l: '湘南・鎌倉', v: 'shonan_kamakura' },
      { l: '小田原・県西', v: 'odawara_kensei' },
      { l: '相模原・県央', v: 'sagamihara_kenoh' },
      { l: '横須賀・三浦', v: 'yokosuka_miura' }
    ]},
    { k: 'w', t: '希望の働き方は？', e: 'shindan_q2', ek: 'workstyle', o: [
      { l: '日勤のみ', v: 'day_only' },
      { l: '夜勤ありOK', v: 'with_night' },
      { l: 'パート・非常勤', v: 'parttime' },
      { l: '夜勤専従', v: 'night_only' }
    ]},
    { k: 't', t: '転職の温度感は？', e: 'shindan_q3', ek: 'timing', o: [
      { l: 'すぐにでも', v: 'urgent' },
      { l: 'いい求人があれば', v: 'good' },
      { l: 'まずは情報収集', v: 'info' }
    ]}
  ];

  /* ── Micro-feedback messages ── */
  var FEEDBACK = {
    'a': function (v) {
      var names = { yokohama_kawasaki: '横浜・川崎', shonan_kamakura: '湘南・鎌倉', odawara_kensei: '小田原・県西', sagamihara_kenoh: '相模原・県央', yokosuka_miura: '横須賀・三浦' };
      return (names[v] || '') + 'エリア、了解！';
    },
    'w': function (v) {
      if (v === 'day_only') return '日勤のみ、人気の条件です';
      if (v === 'parttime') return 'パート求人も豊富です';
      if (v === 'night_only') return '夜勤専従、高収入が狙えます';
      return 'OK！';
    },
    't': function (v) {
      if (v === 'urgent') return 'すぐに動きましょう！';
      if (v === 'good') return 'いい求人を厳選しますね';
      if (v === 'info') return 'まずは情報収集から！';
      return 'OK！';
    }
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

      // ボタン選択肢UI
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

    ga('shindan_complete', { match_count: ct, area: A.a, workstyle: A.w, timing: A.t });

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

    /* Heading with count-up */
    var headlineText = 'あなたにマッチする求人';
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
        '<div>' + ICONS[0] + ' ' + findLabel(0, A.a) + '</div>' +
        '<div>' + ICONS[1] + ' ' + findLabel(1, A.w) + '</div>' +
        '<div>' + ICONS[2] + ' ' + findLabel(2, A.t) + '</div>' +
      '</div>';
    r.appendChild(el('div', 'shindan-summary', summaryHTML));

    /* CTA */
    var ctaText = A.t === 'info' ? 'まずは情報だけ受け取る' : 'LINEで求人を受け取る';
    var skipped = window._shindanSkipped;
    window._shindanSkipped = false;

    // Build LINE URL via shared endpoint
    var EP = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-start';
    var sid = window.__lineSessionId || '';
    var areaLabel = '';
    var areaOpts = Q[0].o;
    for (var ai = 0; ai < areaOpts.length; ai++) {
      if (areaOpts[ai].v === A.a) { areaLabel = areaOpts[ai].l; break; }
    }
    var workstyleMap = { day_only: 'day', with_night: 'twoshift', parttime: 'part', night_only: 'night' };
    var answersJson = encodeURIComponent(JSON.stringify({
      area: A.a,
      areaLabel: areaLabel || A.a,
      workstyle: workstyleMap[A.w] || A.w,
      urgency: A.t
    }));
    var ctaURL;
    if (skipped) {
      ctaURL = EP + '?session_id=' + sid + '&source=shindan_skip&intent=diagnose&page_type=paid_lp&answers=' + answersJson;
    } else {
      ctaURL = EP + '?session_id=' + sid + '&source=shindan&intent=diagnose&page_type=paid_lp&answers=' + answersJson;
    }

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
      ga('click_cta', { source: 'shindan', intent: 'diagnose', page_type: 'paid_lp', session_id: sid, area: A.a, workstyle: A.w, timing: A.t });
    });

    r.appendChild(cta);

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

  /* ── Skip to result (診断スキップ) ── */
  window.shindanSkip = function () {
    C = document.getElementById('shindan-container');
    if (!C) return;
    A = { a: 'yokohama_kawasaki', w: 'day_only', t: 'info' };
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
