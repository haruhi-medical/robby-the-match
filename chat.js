// ========================================
// 神奈川ナース転職 - Chat Widget v5.1
// LINE誘導特化 - 2問→診断結果→LINE CTA
// 「すげー！」体験を作る
// ========================================

(function () {
  "use strict";

  // --------------------------------------------------
  // Configuration
  // --------------------------------------------------
  var CHAT_CONFIG = {
    brandName: typeof CONFIG !== "undefined" ? CONFIG.BRAND_NAME : "神奈川ナース転職",
    hospitals: typeof CONFIG !== "undefined" ? CONFIG.HOSPITALS : [],
  };

  // --------------------------------------------------
  // 年収データ
  // --------------------------------------------------
  var SALARY_TABLE = {
    yokohama:       { base: { min: 27, max: 35 }, nightPer: 12000, nightCount: 4, bonus: 4.0 },
    kawasaki:       { base: { min: 27, max: 34 }, nightPer: 12000, nightCount: 4, bonus: 4.0 },
    sagamihara:     { base: { min: 26, max: 33 }, nightPer: 11000, nightCount: 4, bonus: 3.8 },
    yokosuka_miura: { base: { min: 26, max: 33 }, nightPer: 11000, nightCount: 4, bonus: 3.8 },
    shonan_east:    { base: { min: 26, max: 33 }, nightPer: 11000, nightCount: 5, bonus: 4.0 },
    shonan_west:    { base: { min: 25, max: 32 }, nightPer: 11000, nightCount: 4, bonus: 3.8 },
    kenoh:          { base: { min: 25, max: 32 }, nightPer: 11000, nightCount: 4, bonus: 3.8 },
    kensei:         { base: { min: 24, max: 30 }, nightPer: 10000, nightCount: 4, bonus: 3.5 },
    undecided:      { base: { min: 25, max: 31 }, nightPer: 10500, nightCount: 4, bonus: 3.7 },
  };

  var EXP_ADJUSTMENT = {
    "1年未満": 0, "1〜3年": 1, "3〜5年": 3, "5〜10年": 5, "10年以上": 8,
  };

  // --------------------------------------------------
  // Pre-scripted flow data
  // --------------------------------------------------
  var PRESCRIPTED = {
    areas: [
      { label: "横浜市", value: "yokohama" },
      { label: "川崎市", value: "kawasaki" },
      { label: "相模原市", value: "sagamihara" },
      { label: "横須賀・鎌倉・三浦", value: "yokosuka_miura" },
      { label: "湘南東部（藤沢・茅ヶ崎）", value: "shonan_east" },
      { label: "湘南西部（平塚・秦野・伊勢原）", value: "shonan_west" },
      { label: "県央（厚木・海老名・大和）", value: "kenoh" },
      { label: "県西（小田原・南足柄・箱根）", value: "kensei" },
      { label: "まだ決めていない", value: "undecided" },
    ],
    areaLabels: {
      yokohama: "横浜",
      kawasaki: "川崎",
      sagamihara: "相模原",
      yokosuka_miura: "横須賀・三浦",
      shonan_east: "湘南東部",
      shonan_west: "湘南西部",
      kenoh: "県央",
      kensei: "県西",
      undecided: "神奈川県",
    },
    areaCities: {
      yokohama: ["横浜"],
      kawasaki: ["川崎"],
      sagamihara: ["相模原"],
      yokosuka_miura: ["横須賀", "鎌倉", "逗子", "三浦", "葉山"],
      shonan_east: ["藤沢", "茅ヶ崎", "寒川"],
      shonan_west: ["平塚", "秦野", "伊勢原", "大磯", "二宮"],
      kenoh: ["厚木", "海老名", "座間", "綾瀬", "大和", "愛川"],
      kensei: ["小田原", "南足柄", "開成", "大井", "中井", "松田", "山北", "箱根", "真鶴", "湯河原"],
    },
    concerns: [
      { label: "職場の雰囲気・人間関係", value: "environment", feedback: "転職理由の第1位。実際の雰囲気は外から見えにくいですよね" },
      { label: "夜勤の負担", value: "nightshift", feedback: "体調やプライベートへの影響が大きいですよね" },
      { label: "お給料・待遇", value: "salary", feedback: "同じ経験年数でも施設により月3〜5万円の差があります" },
      { label: "勤務時間の柔軟さ（日勤のみ・時短等）", value: "workstyle", feedback: "ライフスタイルに合った働き方、大切ですよね" },
      { label: "ブランクからの復帰", value: "blank", feedback: "復帰への不安は誰にでもあります。受入れ体制の整った施設を探しましょう" },
    ],
    experiences: [
      { label: "1年未満", value: "1年未満" },
      { label: "1〜3年", value: "1〜3年" },
      { label: "3〜5年", value: "3〜5年" },
      { label: "5〜10年", value: "5〜10年" },
      { label: "10年以上", value: "10年以上" },
    ],
  };

  // 関心事別のインサイト（「すげー」感を出す具体的な情報）
  var CONCERN_INSIGHTS = {
    environment: "このエリアでは、教育体制が充実している施設や看護師の定着率が高い施設をピックアップしました。実際の人間関係や雰囲気は、LINEで元人事担当の目線からお伝えできます。",
    nightshift: "夜勤の負担は施設タイプで大きく変わります。二交代制の施設や、夜勤回数が少ない施設を優先的に表示しています。",
    salary: "このエリアの給与水準は施設の規模や機能で差があります。大規模病院ほど基本給が高い傾向ですが、中小病院は夜勤手当や住宅手当で補っているケースも。",
    workstyle: "日勤のみ・時短勤務の受け入れは、回復期・慢性期の施設が比較的柔軟です。該当する施設を優先的に表示しています。",
    blank: "ブランクからの復帰に理解のある施設を優先表示しています。教育体制や受入れ体制が整った施設なら、安心して復帰できます。",
  };

  // --------------------------------------------------
  // GA4 Event Tracking
  // --------------------------------------------------
  function trackEvent(eventName, params) {
    if (typeof gtag === "function") {
      try { gtag("event", eventName, params || {}); } catch (e) { /* ignore */ }
    }
  }

  // --------------------------------------------------
  // State
  // --------------------------------------------------
  function generateSessionId() {
    return "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 9);
  }

  var chatState = {
    isOpen: false,
    messages: [],
    sessionId: generateSessionId(),
    done: false,
    isTyping: false,
    lineCtaShown: false,
    peekShown: false,
    peekDismissed: false,
    phase: "greeting", // "greeting" | "area" | "concern" | "teaser" | "experience_extra" | "done"
    area: null,
    concern: null,
    experience: null,
    salaryBreakdown: null,
  };

  // --------------------------------------------------
  // localStorage persistence
  // --------------------------------------------------
  var STORAGE_KEY = "nurserobby_chat";

  function saveState() {
    try {
      var toSave = {
        messages: chatState.messages,
        sessionId: chatState.sessionId,
        phase: chatState.phase,
        area: chatState.area,
        concern: chatState.concern,
        experience: chatState.experience,
        done: chatState.done,
        lineCtaShown: chatState.lineCtaShown,
        salaryBreakdown: chatState.salaryBreakdown,
        savedAt: Date.now(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
    } catch (e) { /* storage full or disabled */ }
  }

  function loadState() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (!data || !data.savedAt) return false;
      if (Date.now() - data.savedAt > 24 * 60 * 60 * 1000) {
        localStorage.removeItem(STORAGE_KEY);
        return false;
      }
      chatState.messages = data.messages || [];
      chatState.sessionId = data.sessionId || chatState.sessionId;
      chatState.phase = data.phase || "greeting";
      chatState.area = data.area || null;
      chatState.concern = data.concern || null;
      chatState.experience = data.experience || null;
      chatState.done = data.done || false;
      chatState.lineCtaShown = data.lineCtaShown || false;
      chatState.salaryBreakdown = data.salaryBreakdown || null;
      return true;
    } catch (e) {
      return false;
    }
  }

  // --------------------------------------------------
  // DOM References
  // --------------------------------------------------
  var els = {};

  // --------------------------------------------------
  // Initialization
  // --------------------------------------------------
  function init() {
    els = {
      toggle: document.getElementById("chatToggle"),
      window: document.getElementById("chatWindow"),
      body: document.getElementById("chatBody"),
      input: document.getElementById("chatInput"),
      sendBtn: document.getElementById("chatSendBtn"),
      closeBtn: document.getElementById("chatCloseBtn"),
      minimizeBtn: document.getElementById("chatMinimizeBtn"),
      chatView: document.getElementById("chatView"),
    };

    if (!els.toggle || !els.window) return;

    els.toggle.addEventListener("click", toggleChat);
    els.closeBtn.addEventListener("click", closeChat);
    if (els.minimizeBtn) els.minimizeBtn.addEventListener("click", closeChat);

    // iOS virtual keyboard handling
    if (window.visualViewport) {
      var lastVPHeight = window.visualViewport.height;
      window.visualViewport.addEventListener("resize", function () {
        if (!chatState.isOpen || window.innerWidth > 640) return;
        var vpHeight = window.visualViewport.height;
        if (vpHeight !== lastVPHeight) {
          lastVPHeight = vpHeight;
          els.window.style.height = vpHeight + "px";
          scrollToBottom();
        }
      });
      window.visualViewport.addEventListener("scroll", function () {
        if (!chatState.isOpen || window.innerWidth > 640) return;
        els.window.style.top = window.visualViewport.offsetTop + "px";
      });
    }

    // Escape key to close + focus trap
    document.addEventListener("keydown", function (e) {
      if (!chatState.isOpen) return;
      if (e.key === "Escape") {
        e.preventDefault();
        closeChat();
        return;
      }
      if (e.key === "Tab") {
        var focusable = els.window.querySelectorAll(
          'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])'
        );
        var visible = [];
        for (var i = 0; i < focusable.length; i++) {
          if (focusable[i].offsetParent !== null) visible.push(focusable[i]);
        }
        if (visible.length === 0) return;
        var first = visible[0];
        var last = visible[visible.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) { e.preventDefault(); last.focus(); }
        } else {
          if (document.activeElement === last) { e.preventDefault(); first.focus(); }
        }
      }
    });

    // Hide text input area (button-only interaction)
    setInputVisible(false);

    // Proactive peek message after 30 seconds
    setTimeout(function () {
      if (!chatState.isOpen && !chatState.peekDismissed) {
        showPeekMessage();
      }
    }, 30000);
  }

  // --------------------------------------------------
  // Proactive Peek Message
  // --------------------------------------------------
  function showPeekMessage() {
    if (chatState.peekShown || chatState.isOpen) return;
    chatState.peekShown = true;

    var peek = document.createElement("div");
    peek.className = "chat-peek";
    peek.id = "chatPeek";
    var peekMessages = [
      "今の職場、このまま続けて大丈夫かな…<br><strong>って思ったことありませんか？</strong>",
      "2つの質問だけで、<br><strong>あなたの年収相場が分かります</strong>",
      "看護師の求人、<br><strong>個人情報なしで探せます</strong>",
    ];
    var peekMsg = peekMessages[Math.floor(Math.random() * peekMessages.length)];
    peek.innerHTML =
      '<div class="chat-peek-text">' + peekMsg + '</div>' +
      '<button class="chat-peek-close" aria-label="閉じる">&times;</button>';

    els.toggle.parentElement.insertBefore(peek, els.toggle);

    peek.querySelector(".chat-peek-text").addEventListener("click", function () {
      peek.remove();
      trackEvent("chat_peek_click");
      openChat();
    });

    peek.querySelector(".chat-peek-close").addEventListener("click", function (e) {
      e.stopPropagation();
      chatState.peekDismissed = true;
      peek.classList.add("chat-peek-hiding");
      setTimeout(function () { peek.remove(); }, 300);
    });

    trackEvent("chat_peek_shown");

    setTimeout(function () {
      var el = document.getElementById("chatPeek");
      if (el && !chatState.isOpen) {
        el.classList.add("chat-peek-hiding");
        setTimeout(function () { if (el.parentElement) el.remove(); }, 300);
      }
    }, 12000);
  }

  // --------------------------------------------------
  // Toggle / Open / Close
  // --------------------------------------------------
  function toggleChat() {
    if (chatState.isOpen) { closeChat(); } else { openChat(); }
  }

  function lockBodyScroll() {
    if (window.innerWidth <= 640) {
      chatState._savedScrollY = window.pageYOffset || document.documentElement.scrollTop;
      document.body.classList.add("chat-open-mobile");
      document.body.style.top = "-" + chatState._savedScrollY + "px";
    }
  }

  function unlockBodyScroll() {
    if (document.body.classList.contains("chat-open-mobile")) {
      document.body.classList.remove("chat-open-mobile");
      document.body.style.top = "";
      window.scrollTo(0, chatState._savedScrollY || 0);
    }
  }

  function openChat() {
    chatState.isOpen = true;
    els.window.classList.add("open");
    lockBodyScroll();
    trackEvent("chat_open");
    if (window.__nrTrack) window.__nrTrack("chat_open");
    if (typeof fbq !== "undefined") fbq("trackCustom", "ChatOpen", {content_name: "AIチャット開始"});
    els.toggle.classList.add("active");
    els.toggle.querySelector(".chat-toggle-icon").textContent = "\u2715";

    var peek = document.getElementById("chatPeek");
    if (peek) peek.remove();

    var restored = false;
    if (chatState.messages.length === 0) {
      restored = loadState();
    }

    if (restored && chatState.messages.length > 0) {
      restoreChatView();
      showResumeNotice();
    } else if (chatState.messages.length === 0) {
      setInputVisible(false);
      startConversation();
    } else {
      showChatView();
    }
  }

  function closeChat() {
    chatState.isOpen = false;
    els.window.classList.remove("open");
    unlockBodyScroll();
    els.window.style.height = "";
    els.window.style.top = "";
    els.toggle.classList.remove("active");
    els.toggle.querySelector(".chat-toggle-icon").textContent = "\uD83D\uDCAC";
    els.toggle.focus();
    saveState();
  }

  // --------------------------------------------------
  // セッション復帰通知
  // --------------------------------------------------
  function showResumeNotice() {
    if (!chatState.messages.length) return;
    var notice = document.createElement("div");
    notice.className = "chat-resume-notice";
    notice.innerHTML = '<span>前回の続きから再開しています</span>';
    els.body.appendChild(notice);
    scrollToBottom();
    setTimeout(function () {
      notice.classList.add("chat-resume-hiding");
      setTimeout(function () { if (notice.parentElement) notice.remove(); }, 500);
    }, 3000);
  }

  // --------------------------------------------------
  // 年収計算
  // --------------------------------------------------
  function calculateSalary(area, experience) {
    var data = SALARY_TABLE[area] || SALARY_TABLE.undecided;
    var expAdj = EXP_ADJUSTMENT[experience] || 0;
    var baseMin = data.base.min + expAdj;
    var baseMax = data.base.max + expAdj;
    var baseMid = Math.round((baseMin + baseMax) / 2);
    var nightMonthly = Math.round(data.nightPer * data.nightCount / 10000 * 10) / 10;
    var certMonthly = 1.5;
    var monthlyMin = baseMin + nightMonthly + certMonthly;
    var monthlyMax = baseMax + nightMonthly + certMonthly;
    var annualMin = Math.round(monthlyMin * 12 + baseMid * data.bonus);
    var annualMax = Math.round(monthlyMax * 12 + baseMid * data.bonus);

    var breakdown = {
      baseMin: baseMin, baseMax: baseMax, baseMid: baseMid,
      nightPer: data.nightPer, nightCount: data.nightCount, nightMonthly: nightMonthly,
      certMonthly: certMonthly, monthlyMin: monthlyMin, monthlyMax: monthlyMax,
      bonusMonths: data.bonus, annualMin: annualMin, annualMax: annualMax,
      annualMid: Math.round((annualMin + annualMax) / 2),
    };
    chatState.salaryBreakdown = breakdown;
    return breakdown;
  }

  // 経験年数なしの年収レンジ（ティーザー用）— 3〜5年を中央値として計算
  function calculateSalaryRange(area) {
    var data = SALARY_TABLE[area] || SALARY_TABLE.undecided;
    var midAdj = 3; // 3〜5年の補正値を中央値として使う
    var nightMonthly = Math.round(data.nightPer * data.nightCount / 10000 * 10) / 10;
    var certMonthly = 1.5;
    var baseMin = data.base.min + midAdj;
    var baseMax = data.base.max + midAdj;
    var baseMid = Math.round((baseMin + baseMax) / 2);
    var monthlyMin = baseMin + nightMonthly + certMonthly;
    var monthlyMax = baseMax + nightMonthly + certMonthly;
    var annualMin = Math.round(monthlyMin * 12 + baseMid * data.bonus);
    var annualMax = Math.round(monthlyMax * 12 + baseMid * data.bonus);
    return { annualMin: annualMin, annualMax: annualMax };
  }

  // --------------------------------------------------
  // プログレスバー
  // --------------------------------------------------
  function updateProgress(step, total) {
    var existing = document.getElementById("chatProgressBar");
    if (existing) existing.remove();

    var bar = document.createElement("div");
    bar.className = "chat-progress-bar";
    bar.id = "chatProgressBar";
    var pct = Math.round((step / total) * 100);
    bar.innerHTML =
      '<div class="progress-track"><div class="progress-fill" style="width:' + pct + '%"></div></div>' +
      '<div class="progress-label">' + step + ' / ' + total + '</div>';

    var header = els.window.querySelector(".chat-header");
    if (header && header.nextSibling) {
      header.parentElement.insertBefore(bar, header.nextSibling);
    }
  }

  function removeProgress() {
    var existing = document.getElementById("chatProgressBar");
    if (existing) existing.remove();
  }

  function showChatView() {
    if (els.chatView) els.chatView.classList.remove("hidden");
    requestAnimationFrame(function () { scrollToBottom(); });
  }

  function restoreChatView() {
    var savedMessages = chatState.messages.slice();
    chatState.messages = [];
    els.body.innerHTML = "";
    for (var i = 0; i < savedMessages.length; i++) {
      addMessage(savedMessages[i].role, savedMessages[i].content, true);
    }
    showChatView();
    setInputVisible(false);
    if (!chatState.done) { resumeFlow(); }
  }

  function resumeFlow() {
    switch (chatState.phase) {
      case "area":
        showButtonGroup(PRESCRIPTED.areas, handleAreaSelect);
        break;
      case "concern":
        showButtonGroup(PRESCRIPTED.concerns, handleConcernSelect);
        break;
      case "teaser":
        deliverTeaser();
        break;
      case "experience_extra":
        showButtonGroup(PRESCRIPTED.experiences, handleExperienceExtraSelect);
        break;
      default:
        break;
    }
  }

  // --------------------------------------------------
  // Conversational Flow
  // --------------------------------------------------
  function startConversation() {
    chatState.phase = "greeting";
    setInputVisible(false);

    showTyping();
    setTimeout(function () {
      hideTyping();
      addMessage("ai", "こんにちは！神奈川ナース転職のAI相談役、ロビーです。\n\n2つだけ質問させてください。あなたのエリアの年収相場と、条件に合いそうな施設をAIが分析します。\n\n名前や電話番号は一切不要。30秒で終わります。");

      setTimeout(function () {
        showTyping();
        setTimeout(function () {
          hideTyping();
          addMessage("ai", "まず、どのエリアで働きたいですか？");
          chatState.phase = "area";
          updateProgress(1, 2);
          showButtonGroup(PRESCRIPTED.areas, handleAreaSelect);
          saveState();
        }, 600);
      }, 800);
    }, 700);
  }

  // --------------------------------------------------
  // Step 1: エリア選択
  // --------------------------------------------------
  function handleAreaSelect(value, label) {
    chatState.area = value;
    trackEvent("chat_area_selected", { area: value });
    removeButtonGroup();
    addMessage("user", label);

    chatState.phase = "concern";

    showTyping();
    setTimeout(function () {
      hideTyping();
      var areaName = getAreaDisplayName(value);
      addMessage("ai", areaName + "エリアですね！\n\nあと1つだけ。今一番気になっていることを教えてください。");
      updateProgress(2, 2);
      showButtonGroup(PRESCRIPTED.concerns, handleConcernSelect);
      saveState();
    }, 600);
  }

  // --------------------------------------------------
  // Step 2: 関心事選択 → 診断結果へ
  // --------------------------------------------------
  function handleConcernSelect(value, label) {
    chatState.concern = value;
    trackEvent("chat_concern_selected", { concern: value });
    removeButtonGroup();
    addMessage("user", label);

    var selectedConcern = null;
    for (var i = 0; i < PRESCRIPTED.concerns.length; i++) {
      if (PRESCRIPTED.concerns[i].value === value) {
        selectedConcern = PRESCRIPTED.concerns[i];
        break;
      }
    }

    showTyping();
    setTimeout(function () {
      hideTyping();
      var feedbackText = selectedConcern ? selectedConcern.feedback + "。" : "";
      addMessage("ai", feedbackText + "\n\nAIが分析中です...");
      removeProgress();
      chatState.phase = "teaser";
      saveState();

      // 「分析中」の間を少し長く取って期待感を演出
      setTimeout(function () {
        deliverTeaser();
      }, 1200);
    }, 600);
  }

  // --------------------------------------------------
  // 診断結果: 年収 + 3施設 + インサイト + LINE CTA
  // --------------------------------------------------
  function deliverTeaser() {
    var matches = findMatchingHospitals(chatState.area);
    var areaName = getAreaDisplayName(chatState.area);
    var salaryRange = calculateSalaryRange(chatState.area);

    showTyping();
    setTimeout(function () {
      hideTyping();

      // 診断結果ヘッダー
      addMessage("ai", "診断結果が出ました！");

      setTimeout(function () {
        // 年収レンジカード（ティーザー版）
        showSalaryRangeCard(areaName, salaryRange);

        setTimeout(function () {
          // 関心事に合わせたインサイト
          var insight = CONCERN_INSIGHTS[chatState.concern] || "";
          addMessage("ai", insight);

          setTimeout(function () {
            // 施設3件カード表示（ここが「すげー！」ポイント）
            showFacilityCards(matches);

            setTimeout(function () {
              // LINE CTA
              addMessage("ai", "ここまでの情報は一般的なデータからの分析です。\n\nLINEでは、経験年数やライフスタイルに合わせて、AIがもっと正確にマッチングします。あなた専用の結果をお届けしますよ。");

              setTimeout(function () {
                showTeaserCTA();
                saveState();
              }, 800);
            }, 1000);
          }, 800);
        }, 800);
      }, 600);
    }, 600);
  }

  // --------------------------------------------------
  // 年収レンジカード（ティーザー版 — 経験年数不問）
  // --------------------------------------------------
  function showSalaryRangeCard(areaName, salaryRange) {
    var card = document.createElement("div");
    card.className = "chat-salary-breakdown";
    card.innerHTML =
      '<div class="salary-bd-header">' + areaName + 'エリア 年収相場（中堅クラス）</div>' +
      '<div class="salary-bd-total">' +
        '<span class="salary-bd-total-label">推定年収</span>' +
        '<span class="salary-bd-total-value">' + salaryRange.annualMin + '〜' + salaryRange.annualMax + '万円</span>' +
      '</div>' +
      '<div class="salary-bd-note">※経験3〜5年・夜勤あり想定。経験年数で変動します</div>';

    els.body.appendChild(card);
    scrollToBottom();
    trackEvent("chat_salary_range_shown", { area: chatState.area });
  }

  // --------------------------------------------------
  // 施設カード表示（3件 — 関心事に合わせたハイライト）
  // --------------------------------------------------
  function showFacilityCards(matches) {
    if (!matches || matches.length === 0) return;

    var showCount = Math.min(matches.length, 3);
    var container = document.createElement("div");
    container.className = "chat-facility-cards";

    for (var i = 0; i < showCount; i++) {
      var h = matches[i];
      var isReferral = h.referral === true;
      var card = document.createElement("div");
      card.className = "chat-facility-card" + (isReferral ? " chat-facility-card--referral" : " chat-facility-card--info");

      var highlightTag = getHighlightForConcern(h, chatState.concern);

      var badgeHtml = isReferral
        ? '<div class="facility-card-badge facility-card-badge--referral">直接ご紹介できます</div>'
        : '<div class="facility-card-badge facility-card-badge--info">参考情報</div>';

      var enrichedTags = [];
      if (h.nursingRatio) enrichedTags.push(h.nursingRatio);
      if (h.emergencyLevel) enrichedTags.push(h.emergencyLevel);
      if (h.ownerType) enrichedTags.push(h.ownerType);
      if (h.dpcHospital) enrichedTags.push("DPC対象");
      var enrichedTagsHtml = "";
      if (enrichedTags.length > 0) {
        enrichedTagsHtml = '<div class="facility-card-tags">';
        for (var t = 0; t < enrichedTags.length; t++) {
          enrichedTagsHtml += '<span class="facility-card-tag">' + escapeHtml(enrichedTags[t]) + '</span>';
        }
        enrichedTagsHtml += '</div>';
      }

      var statsItems = [];
      if (h.ambulanceCount && h.ambulanceCount > 0) statsItems.push("救急車 年" + h.ambulanceCount.toLocaleString() + "台");
      if (h.doctorCount && h.doctorCount > 0) statsItems.push("医師" + h.doctorCount + "名");
      var statsHtml = "";
      if (statsItems.length > 0) {
        statsHtml = '<div class="facility-card-stats">';
        for (var s = 0; s < statsItems.length; s++) {
          statsHtml += '<span>' + escapeHtml(statsItems[s]) + '</span>';
        }
        statsHtml += '</div>';
      }

      var sourceHtml = "";
      if (h.dataSource || h.lastUpdated) {
        var sourceText = "出典: " + (h.dataSource || "公開情報");
        if (h.lastUpdated) sourceText += "（" + h.lastUpdated + "）";
        sourceHtml = '<div class="facility-card-source">' + escapeHtml(sourceText) + '</div>';
      }

      card.innerHTML =
        badgeHtml +
        '<div class="facility-card-name">' + escapeHtml(h.displayName) + '</div>' +
        enrichedTagsHtml +
        '<div class="facility-card-highlight">' + escapeHtml(highlightTag) + '</div>' +
        '<div class="facility-card-details">' +
          '<span>' + escapeHtml(h.salary || "") + '</span>' +
          '<span>' + escapeHtml(h.holidays || "") + '</span>' +
        '</div>' +
        statsHtml +
        sourceHtml;

      container.appendChild(card);
    }

    if (matches.length > showCount) {
      var more = document.createElement("div");
      more.className = "facility-card-more";
      more.textContent = "他にも " + (matches.length - showCount) + " 件の施設があります";
      container.appendChild(more);
    }

    els.body.appendChild(container);
    scrollToBottom();
  }

  function getHighlightForConcern(h, concern) {
    if (concern === "salary") {
      return h.salary || "";
    } else if (concern === "nightshift") {
      return h.nightShift ? "夜勤: " + h.nightShift : "夜勤情報なし";
    } else if (concern === "environment") {
      var envParts = [];
      if (h.nurseCount) envParts.push("看護師" + h.nurseCount + "名");
      if (h.features && h.features.indexOf("教育") !== -1) envParts.push("教育体制あり");
      if (h.features && h.features.indexOf("ブランク") !== -1) envParts.push("ブランクOK");
      return envParts.length > 0 ? envParts.join("・") : (h.features ? h.features.split("・")[0] : "");
    } else if (concern === "workstyle") {
      var wsParts = [];
      if (h.type && (h.type.indexOf("慢性期") !== -1 || h.type.indexOf("回復期") !== -1)) wsParts.push("日勤のみ相談可");
      wsParts.push(h.holidays || "");
      if (h.nightShift) wsParts.push("夜勤: " + h.nightShift);
      return wsParts.filter(function(s){return s;}).join("・");
    } else if (concern === "blank") {
      var blParts = [];
      if (h.features && h.features.indexOf("ブランク") !== -1) blParts.push("ブランクOK");
      if (h.features && h.features.indexOf("教育") !== -1) blParts.push("教育体制充実");
      if (h.nursingRatio) blParts.push("配置 " + h.nursingRatio);
      return blParts.length > 0 ? blParts.join("・") : "";
    }
    return h.features ? h.features.split("・")[0] : "";
  }

  // --------------------------------------------------
  // ティーザーCTA
  // --------------------------------------------------
  function showTeaserCTA() {
    var options = [
      { label: "LINEでAI診断を受ける", value: "line", isLine: true },
      { label: "もう少し詳しく見たい", value: "more", isLine: false },
    ];

    var container = document.createElement("div");
    container.className = "chat-quick-replies";
    container.id = "chatButtonGroup";

    for (var i = 0; i < options.length; i++) {
      (function (opt) {
        var btn = document.createElement("button");
        btn.className = "chat-quick-reply" + (opt.isLine ? " chat-quick-reply-line" : "");
        btn.textContent = opt.label;
        btn.addEventListener("click", function () {
          removeButtonGroup();
          addMessage("user", opt.label);
          handleTeaserChoice(opt.value);
        });
        container.appendChild(btn);
      })(options[i]);
    }

    els.body.appendChild(container);
    scrollToBottom();
  }

  function handleTeaserChoice(choice) {
    if (choice === "line") {
      trackEvent("chat_line_click", { phase: "teaser", area: chatState.area, concern: chatState.concern });
      showTyping();
      setTimeout(function () {
        hideTyping();
        addMessage("ai", "LINEではAIがもう少し詳しくヒアリングして、あなたにピッタリの病院をマッチングします。\n\nAIの質問に答えるだけでOK。しつこい電話は一切ありません。");
        chatState.phase = "done";
        chatState.done = true;

        setTimeout(function () {
          showLineCard();
          saveState();
        }, 600);
      }, 600);
    } else {
      trackEvent("chat_more_detail", { area: chatState.area, concern: chatState.concern });
      chatState.phase = "experience_extra";
      showTyping();
      setTimeout(function () {
        hideTyping();
        addMessage("ai", "では、もう少し正確にシミュレーションしますね。\n\n看護師としてのご経験年数を教えてください。");
        showButtonGroup(PRESCRIPTED.experiences, handleExperienceExtraSelect);
        saveState();
      }, 600);
    }
  }

  // --------------------------------------------------
  // 「もう少し詳しく」→ 経験年数 → 年収内訳 → 再LINE CTA
  // --------------------------------------------------
  function handleExperienceExtraSelect(value, label) {
    chatState.experience = value;
    trackEvent("chat_experience_selected", { experience: value });
    removeButtonGroup();
    addMessage("user", label);

    var expFeedbacks = {
      "1年未満": "新人さんでも受け入れてくれる職場は意外とたくさんありますよ。",
      "1〜3年": "基本スキルが身についた時期ですね。選べる職場の幅が広がっています。",
      "3〜5年": "一通りできる頃ですね。リーダー経験があれば転職市場で強みになります。",
      "5〜10年": "ベテランですね。あなたの経験があれば好条件の求人が狙えます。",
      "10年以上": "豊富なご経験ですね。管理職や専門ポジションも含めて探せます。",
    };

    showTyping();
    setTimeout(function () {
      hideTyping();
      var fb = expFeedbacks[value] || "";
      addMessage("ai", fb + "\n\nあなた専用の年収シミュレーションを計算しています...");
      saveState();

      setTimeout(function () {
        deliverDetailedResults();
      }, 1000);
    }, 600);
  }

  function deliverDetailedResults() {
    var salary = calculateSalary(chatState.area, chatState.experience);
    var areaName = getAreaDisplayName(chatState.area);

    showTyping();
    setTimeout(function () {
      hideTyping();
      addMessage("ai", areaName + "エリア・経験" + chatState.experience + "のシミュレーション結果です。");

      setTimeout(function () {
        showSalaryBreakdownCard(salary);

        setTimeout(function () {
          showFinalLineCTA();
          saveState();
        }, 1000);
      }, 600);
    }, 600);
  }

  // --------------------------------------------------
  // 年収内訳カード（経験年数指定版）
  // --------------------------------------------------
  function showSalaryBreakdownCard(salary) {
    var card = document.createElement("div");
    card.className = "chat-salary-breakdown";
    var dayOnlyMonthlyMin = salary.baseMin + salary.certMonthly;
    var dayOnlyMonthlyMax = salary.baseMax + salary.certMonthly;
    var dayOnlyAnnualMin = Math.round(dayOnlyMonthlyMin * 12 + salary.baseMid * salary.bonusMonths);
    var dayOnlyAnnualMax = Math.round(dayOnlyMonthlyMax * 12 + salary.baseMid * salary.bonusMonths);
    var hourlyMin = Math.round(salary.baseMin * 10000 / 160 / 50) * 50;
    var hourlyMax = Math.round(salary.baseMax * 10000 / 160 / 50) * 50;

    var showDayFirst = (chatState.concern === "workstyle" || chatState.concern === "blank");

    var mainBlock = showDayFirst
      ? '<div class="salary-bd-total">' +
          '<span class="salary-bd-total-label">推定年収（日勤のみ）</span>' +
          '<span class="salary-bd-total-value">' + dayOnlyAnnualMin + '〜' + dayOnlyAnnualMax + '万円</span>' +
        '</div>' +
        '<div class="salary-bd-item" style="margin-top:8px;padding-top:8px;border-top:1px solid #E5E0D5">' +
          '<span class="salary-bd-label">夜勤ありの場合</span>' +
          '<span class="salary-bd-value">' + salary.annualMin + '〜' + salary.annualMax + '万円</span>' +
        '</div>'
      : '<div class="salary-bd-total">' +
          '<span class="salary-bd-total-label">推定年収</span>' +
          '<span class="salary-bd-total-value">' + salary.annualMin + '〜' + salary.annualMax + '万円</span>' +
        '</div>' +
        '<div class="salary-bd-item" style="margin-top:8px;padding-top:8px;border-top:1px solid #E5E0D5">' +
          '<span class="salary-bd-label">日勤のみの場合</span>' +
          '<span class="salary-bd-value">' + dayOnlyAnnualMin + '〜' + dayOnlyAnnualMax + '万円</span>' +
        '</div>';

    card.innerHTML =
      '<div class="salary-bd-header">年収シミュレーション（' + getAreaDisplayName(chatState.area) + '・' + chatState.experience + '）</div>' +
      '<div class="salary-bd-items">' +
        '<div class="salary-bd-item"><span class="salary-bd-label">基本給</span><span class="salary-bd-value">月' + salary.baseMin + '〜' + salary.baseMax + '万円</span></div>' +
        '<div class="salary-bd-item"><span class="salary-bd-label">夜勤手当</span><span class="salary-bd-value">月' + salary.nightMonthly + '万円<span class="salary-bd-detail">（' + (salary.nightPer / 10000).toFixed(1) + '万×' + salary.nightCount + '回）</span></span></div>' +
        '<div class="salary-bd-item"><span class="salary-bd-label">資格手当等</span><span class="salary-bd-value">月' + salary.certMonthly + '万円</span></div>' +
        '<div class="salary-bd-item"><span class="salary-bd-label">賞与</span><span class="salary-bd-value">' + salary.bonusMonths + 'ヶ月分</span></div>' +
      '</div>' +
      mainBlock +
      '<div class="salary-bd-item" style="margin-top:4px"><span class="salary-bd-label">パート時給目安</span><span class="salary-bd-value">' + hourlyMin.toLocaleString() + '〜' + hourlyMax.toLocaleString() + '円/時</span></div>' +
      '<div class="salary-bd-note">※施設・勤務形態により変動します</div>';

    els.body.appendChild(card);
    scrollToBottom();
    trackEvent("chat_salary_breakdown_shown", { annual_mid: salary.annualMid, area: chatState.area });
  }

  // --------------------------------------------------
  // 最終LINE CTA
  // --------------------------------------------------
  function showFinalLineCTA() {
    chatState.phase = "done";
    chatState.done = true;
    chatState.lineCtaShown = true;

    showTyping();
    setTimeout(function () {
      hideTyping();
      addMessage("ai", "ここまでは一般データからの分析です。\n\nLINEでは、AIがさらに詳しくヒアリングして、あなたの条件にピッタリの病院を見つけます。しつこい電話は一切ありません。");

      setTimeout(function () {
        showLineCard();
        saveState();
      }, 600);
    }, 600);
  }

  // --------------------------------------------------
  // LINE Card
  // --------------------------------------------------
  function showLineCard() {
    var card = document.createElement("div");
    card.className = "chat-line-card";
    card.innerHTML =
      '<a href="https://lin.ee/oUgDB3x" target="_blank" rel="noopener" class="chat-line-card-btn" id="chatLineMainBtn">' +
        'LINEでAIマッチングを受ける' +
      '</a>' +
      '<div class="chat-line-card-trust">' +
        '<span>完全無料</span><span>AIが即分析</span><span>電話なし</span>' +
      '</div>';

    els.body.appendChild(card);
    scrollToBottom();

    var btn = document.getElementById("chatLineMainBtn");
    if (btn) {
      btn.addEventListener("click", function () {
        trackEvent("chat_line_card_click", { phase: chatState.phase });
        if (window.__nrTrack) window.__nrTrack("line_click");
        if (typeof fbq !== "undefined") fbq("track", "Lead", {content_name: "LINE友だち追加", content_category: "看護師転職", value: 1, currency: "JPY"});
      });
    }
  }

  // --------------------------------------------------
  // Messages
  // --------------------------------------------------
  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function addMessage(role, content, skipSave) {
    chatState.messages.push({ role: role, content: content });

    var msgEl = document.createElement("div");
    msgEl.className = "chat-message " + role;

    if (role === "ai") {
      var avatar = document.createElement("div");
      avatar.className = "chat-msg-avatar";
      avatar.textContent = "NR";
      msgEl.appendChild(avatar);
    }

    var bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.innerHTML = escapeHtml(content).replace(/\n/g, "<br>");
    msgEl.appendChild(bubble);

    els.body.appendChild(msgEl);
    scrollToBottom();

    if (!skipSave) saveState();
  }

  // --------------------------------------------------
  // Button Group
  // --------------------------------------------------
  function showButtonGroup(options, handler) {
    var container = document.createElement("div");
    container.className = "chat-quick-replies";
    container.id = "chatButtonGroup";

    for (var i = 0; i < options.length; i++) {
      (function (opt, idx) {
        var btn = document.createElement("button");
        btn.className = "chat-quick-reply";
        btn.textContent = (opt.emoji ? opt.emoji + " " : "") + opt.label;
        btn.style.animationDelay = (idx * 0.06) + "s";
        btn.addEventListener("click", function () {
          handler(opt.value, opt.label);
        });
        container.appendChild(btn);
      })(options[i], i);
    }

    els.body.appendChild(container);
    scrollToBottom();
  }

  function removeButtonGroup() {
    var group = document.getElementById("chatButtonGroup");
    if (group) group.remove();
  }

  function setInputVisible(visible) {
    var inputArea = els.input ? els.input.parentElement : null;
    if (inputArea) {
      inputArea.style.display = visible ? "flex" : "none";
      scrollToBottom();
    }
  }

  // --------------------------------------------------
  // Hospital Matching
  // --------------------------------------------------
  function findMatchingHospitals(area) {
    var hospitals = CHAT_CONFIG.hospitals;
    if (!hospitals || hospitals.length === 0) {
      return [
        { displayName: "小田原市立病院（小田原市・417床）", salary: "月給28〜38万円", holidays: "年間休日120日以上", nightShift: "あり（三交代制）", commute: "小田原駅バス10分", features: "2026年新築移転予定" },
        { displayName: "東海大学医学部付属病院（伊勢原市・804床）", salary: "月給29〜38万円", holidays: "年間休日120日以上", nightShift: "あり（三交代制）", commute: "伊勢原駅バス10分", features: "県西最大規模" },
        { displayName: "海老名総合病院（海老名市・479床）", salary: "月給29〜38万円", holidays: "年間休日115日以上", nightShift: "あり（二交代制）", commute: "海老名駅徒歩7分", features: "救命救急センター" },
      ];
    }

    if (!area || area === "undecided" || area === "other") return hospitals;

    var cities = PRESCRIPTED.areaCities && PRESCRIPTED.areaCities[area];
    if (!cities || cities.length === 0) return hospitals;

    var filtered = [];
    for (var i = 0; i < hospitals.length; i++) {
      if (!hospitals[i].displayName) continue;
      for (var c = 0; c < cities.length; c++) {
        if (hospitals[i].displayName.indexOf(cities[c]) !== -1) {
          filtered.push(hospitals[i]);
          break;
        }
      }
    }

    var result = filtered.length > 0 ? filtered : hospitals;
    var concern = chatState.concern;
    result.sort(function (a, b) {
      if (a.referral && !b.referral) return -1;
      if (!a.referral && b.referral) return 1;
      if (concern === "workstyle") {
        var aDay = (a.type && (a.type.indexOf("慢性期") !== -1 || a.type.indexOf("回復期") !== -1)) ? 1 : 0;
        var bDay = (b.type && (b.type.indexOf("慢性期") !== -1 || b.type.indexOf("回復期") !== -1)) ? 1 : 0;
        if (aDay !== bDay) return bDay - aDay;
      }
      if (concern === "blank") {
        var aBlank = (a.features && a.features.indexOf("ブランク") !== -1) ? 1 : 0;
        var bBlank = (b.features && b.features.indexOf("ブランク") !== -1) ? 1 : 0;
        if (aBlank !== bBlank) return bBlank - aBlank;
      }
      if (concern === "salary") return (b.beds || 0) - (a.beds || 0);
      if (concern === "nightshift") {
        var aNight = (a.nightShift && a.nightShift.indexOf("二交代") !== -1) ? 1 : 0;
        var bNight = (b.nightShift && b.nightShift.indexOf("二交代") !== -1) ? 1 : 0;
        if (aNight !== bNight) return bNight - aNight;
      }
      if (concern === "environment") {
        var aEnv = (a.features && a.features.indexOf("教育") !== -1) ? 1 : 0;
        var bEnv = (b.features && b.features.indexOf("教育") !== -1) ? 1 : 0;
        if (aEnv !== bEnv) return bEnv - aEnv;
        return (b.beds || 0) - (a.beds || 0);
      }
      return 0;
    });
    return result;
  }

  function getAreaDisplayName(areaValue) {
    return (PRESCRIPTED.areaLabels && PRESCRIPTED.areaLabels[areaValue]) || areaValue || "";
  }

  // --------------------------------------------------
  // Typing Indicator
  // --------------------------------------------------
  function showTyping() {
    chatState.isTyping = true;

    var typing = document.createElement("div");
    typing.className = "chat-typing";
    typing.id = "chatTypingIndicator";

    var avatar = document.createElement("div");
    avatar.className = "chat-msg-avatar";
    avatar.textContent = "R";
    typing.appendChild(avatar);

    var dots = document.createElement("div");
    dots.className = "chat-typing-dots";
    dots.innerHTML = "<span></span><span></span><span></span>";
    typing.appendChild(dots);

    els.body.appendChild(typing);
    scrollToBottom();
  }

  function hideTyping() {
    chatState.isTyping = false;
    var indicator = document.getElementById("chatTypingIndicator");
    if (indicator) indicator.remove();
    scrollToBottom();
  }

  // --------------------------------------------------
  // Utilities
  // --------------------------------------------------
  function scrollToBottom() {
    if (scrollToBottom._t1) clearTimeout(scrollToBottom._t1);
    if (scrollToBottom._t2) clearTimeout(scrollToBottom._t2);
    if (scrollToBottom._t3) clearTimeout(scrollToBottom._t3);

    function doScroll() {
      if (!els.body) return;
      if (els.body.offsetParent === null) return;
      els.body.style.scrollBehavior = "auto";
      els.body.scrollTop = els.body.scrollHeight;
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(doScroll);
    });
    scrollToBottom._t1 = setTimeout(doScroll, 80);
    scrollToBottom._t2 = setTimeout(doScroll, 250);
    scrollToBottom._t3 = setTimeout(doScroll, 450);
  }

  // --------------------------------------------------
  // Initialize
  // --------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
