/**
 * 神奈川ナース転職 — 転職診断UI v2.0 (vanilla JS)
 *
 * REQUIRED: Add to LP <head> before closing tag:
 *   <link rel="stylesheet" href="shindan.css">
 */
(function () {
  'use strict';

  /* ── Constants ── */
  var LINE_URL = 'https://lin.ee/oUgDB3x';
  var D = null;
  var A = { s: '', a: '', t: '' };
  var C; // container element
  var currentStep = -1;
  var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Fetch data ── */
  var dataURL = '';
  try { dataURL = new URL('jobs-summary.json', document.currentScript.src).href; } catch (e) { dataURL = 'jobs-summary.json'; }
  fetch(dataURL).then(function (r) { return r.json(); }).then(function (d) { D = d; }).catch(function () {});

  /* ── Questions ── */
  var ICONS = ['🩺', '📍', '📅'];
  var Q = [
    { k: 's', t: 'あなたの職種は？', e: 'shindan_q1', ek: 'shikaku', o: [
      { l: '正看護師', v: 'kango' }, { l: '准看護師', v: 'junkango' },
      { l: '助産師', v: 'josanshi' }, { l: '保健師', v: 'hokenshi' }
    ]},
    { k: 'a', t: '希望エリアは？', e: 'shindan_q2', ek: 'area', o: [
      { l: '横浜・川崎', v: 'yokohama_kawasaki' }, { l: '湘南・鎌倉', v: 'shonan_kamakura' },
      { l: '小田原・西湘', v: 'odawara_seisho' }, { l: '相模原・県央', v: 'sagamihara_kenoh' },
      { l: '横須賀・三浦', v: 'yokosuka_miura' }
    ]},
    { k: 't', t: '転職したい時期は？', e: 'shindan_q3', ek: 'timing', o: [
      { l: 'すぐにでも', v: 'urgent' }, { l: '3ヶ月以内', v: '3months' },
      { l: '半年以内', v: '6months' }, { l: '情報収集中', v: 'info' }
    ]}
  ];

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
    wrap.setAttribute('aria-valuemax', '3');
    wrap.setAttribute('aria-label', '質問 ' + (stepIdx + 1) + ' / 3');

    var track = el('div', 'shindan-progress');
    var bar = el('div', 'shindan-progress-bar');
    track.appendChild(bar);
    wrap.appendChild(track);

    var label = el('div', 'shindan-progress-label', (stepIdx + 1) + ' / 3');
    wrap.appendChild(label);

    // Animate bar after paint
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        bar.style.width = Math.round((stepIdx + 1) / 3 * 100) + '%';
      });
    });

    return wrap;
  }

  /* ── Step dots ── */
  function buildDots(stepIdx) {
    var wrap = el('div', 'shindan-dots');
    wrap.setAttribute('aria-hidden', 'true');
    for (var i = 0; i < 3; i++) {
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

          var delay = reducedMotion ? 100 : 350;
          setTimeout(function () {
            if (i < 2) {
              step(i + 1);
            } else {
              result();
            }
          }, delay);
        });

        g.appendChild(b);
      });

      s.appendChild(g);
      C.appendChild(s);

      // Auto-focus first option
      var firstBtn = g.querySelector('.shindan-btn');
      if (firstBtn) {
        setTimeout(function () { firstBtn.focus(); }, reducedMotion ? 0 : 400);
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
          btns[next].focus();
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
    var ct = d ? d.count : 0;
    var sn = d ? d.salary_min : 350;
    var sx = d ? d.salary_max : 550;

    ga('shindan_complete', { match_count: ct, area: A.a, shikaku: A.s });

    var r = el('div', 'shindan-result');

    /* Progress (complete) */
    var pWrap = buildProgress(2);
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var bar = pWrap.querySelector('.shindan-progress-bar');
        if (bar) bar.style.width = '100%';
      });
    });
    r.appendChild(pWrap);

    var dots = buildDots(3); // all done
    r.appendChild(dots);

    /* Heading with count-up */
    var heading = el('h3', 'shindan-result-heading',
      'あなたにマッチする求人 <strong><span class="shindan-count-num" aria-live="polite">0</span>件</strong>');
    r.appendChild(heading);

    /* Salary range */
    r.appendChild(el('div', 'shindan-salary-range',
      '年収 <strong>' + sn + '〜' + sx + '万円</strong>'));

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

    /* CTA */
    var ctaText = A.t === 'info' ? 'まずは情報だけ受け取る' : 'LINEで求人を受け取る';
    var utmContent = encodeURIComponent(A.s + '_' + A.a + '_' + A.t);
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
      ga('shindan_line_click', { area: A.a, shikaku: A.s, timing: A.t });
      if (typeof fbq === 'function') fbq('track', 'Lead');
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
