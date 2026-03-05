// ========================================
// ナースロビー - Chat Widget v5.0
// LINE誘導特化 - 2問→ティーザー→LINE CTA
// ========================================

(function () {
  "use strict";

  // --------------------------------------------------
  // Configuration
  // --------------------------------------------------
  var CHAT_CONFIG = {
    brandName: typeof CONFIG !== "undefined" ? CONFIG.BRAND_NAME : "ナースロビー",
    workerEndpoint: typeof CONFIG !== "undefined" ? CONFIG.API.workerEndpoint : "",
    hospitals: typeof CONFIG !== "undefined" ? CONFIG.HOSPITALS : [],
  };

  // --------------------------------------------------
  // 年収データ（透明な計算式で信頼感を出す）
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

  // 経験年数別の基本給補正（万円加算）
  var EXP_ADJUSTMENT = {
    "1年未満": 0, "1〜3年": 1, "3〜5年": 3, "5〜10年": 5, "10年以上": 8,
  };

  // --------------------------------------------------
  // Pre-scripted flow data（2ステップ: エリア → 関心事）
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
    // 関心事: 看護師転職理由の実態に基づく順序
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
    // エリア別の施設数（BOT表示件数 / DB全体件数）
    areaFacilityCounts: {
      yokohama: 10,
      kawasaki: 5,
      sagamihara: 3,
      yokosuka_miura: 3,
      shonan_east: 2,
      shonan_west: 8,
      kenoh: 1,
      kensei: 12,
      undecided: 44,
    },
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
    // Conversational flow state (v5: 2-step + teaser)
    phase: "greeting", // "greeting" | "area" | "concern" | "teaser" | "experience_extra" | "done"
    area: null,
    concern: null,
    experience: null,
    // Salary calculation results
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
      // Expire after 24 hours
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

    // Event listeners
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

    // Auto-dismiss after 12 seconds
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
    if (chatState.isOpen) {
      closeChat();
    } else {
      openChat();
    }
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
    els.toggle.classList.add("active");
    els.toggle.querySelector(".chat-toggle-icon").textContent = "\u2715";

    // Remove peek if visible
    var peek = document.getElementById("chatPeek");
    if (peek) peek.remove();

    // Try to restore previous session
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
  // Web→LINE 引き継ぎコード取得
  // --------------------------------------------------
  var handoffCode = null;
  var handoffCodeRequested = false;

  function requestHandoffCode(callback) {
    if (handoffCode) {
      if (callback) callback(handoffCode);
      return;
    }
    if (handoffCodeRequested) {
      if (callback) callback(null);
      return;
    }
    handoffCodeRequested = true;

    if (!isAPIAvailable()) {
      handoffCodeRequested = false;
      if (callback) callback(null);
      return;
    }

    var salaryEst = chatState.salaryBreakdown ? {
      min: chatState.salaryBreakdown.annualMin,
      max: chatState.salaryBreakdown.annualMax,
    } : null;

    var facilitiesShown = [];
    var cards = document.querySelectorAll(".facility-card-name");
    for (var i = 0; i < cards.length && i < 5; i++) {
      facilitiesShown.push(cards[i].textContent.split("（")[0]);
    }

    fetch(CHAT_CONFIG.workerEndpoint + "/api/web-session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sessionId: chatState.sessionId,
        area: chatState.area || null,
        concern: chatState.concern || null,
        experience: chatState.experience || null,
        salaryEstimate: salaryEst,
        facilitiesShown: facilitiesShown,
      }),
    }).then(function (res) {
      if (res.ok) return res.json();
      return null;
    }).then(function (data) {
      handoffCodeRequested = false;
      if (data && data.code) {
        handoffCode = data.code;
        if (callback) callback(handoffCode);
      } else {
        if (callback) callback(null);
      }
    }).catch(function () {
      handoffCodeRequested = false;
      if (callback) callback(null);
    });
  }

  function buildHandoffCodeHtml(code) {
    if (!code) return "";
    return '<div class="chat-handoff-code">' +
      '<div class="handoff-code-label">相談内容を引き継ぐ場合は、LINEで以下のコードを送ってください（任意）</div>' +
      '<div class="handoff-code-value" id="handoffCodeValue">' + escapeHtml(code) + '</div>' +
      '<button class="handoff-code-copy" onclick="(function(){var v=document.getElementById(\'handoffCodeValue\');if(v&&navigator.clipboard){navigator.clipboard.writeText(v.textContent.trim());var b=event.target;b.textContent=\'コピーしました\';setTimeout(function(){b.textContent=\'コードをコピー\'},2000)}})()">コードをコピー</button>' +
      '<div class="handoff-code-note">コードなしでもLINE追加だけでOKです</div>' +
      '</div>';
  }

  // --------------------------------------------------
  // 年収計算（透明な計算式で信頼感を出す）
  // --------------------------------------------------
  function calculateSalary(area, experience, concern) {
    var data = SALARY_TABLE[area] || SALARY_TABLE.undecided;
    var expAdj = EXP_ADJUSTMENT[experience] || 0;

    // 基本給（経験年数で補正）
    var baseMin = data.base.min + expAdj;
    var baseMax = data.base.max + expAdj;
    var baseMid = Math.round((baseMin + baseMax) / 2);

    // 夜勤手当（月額）
    var nightMonthly = Math.round(data.nightPer * data.nightCount / 10000 * 10) / 10;

    // 資格手当（概算）
    var certMonthly = 1.5; // 万円

    // 月収
    var monthlyMin = baseMin + nightMonthly + certMonthly;
    var monthlyMax = baseMax + nightMonthly + certMonthly;
    var monthlyMid = Math.round((monthlyMin + monthlyMax) / 2 * 10) / 10;

    // 年収（月給×12 + 賞与）
    var annualMin = Math.round(monthlyMin * 12 + baseMid * data.bonus);
    var annualMax = Math.round(monthlyMax * 12 + baseMid * data.bonus);
    var annualMid = Math.round((annualMin + annualMax) / 2);

    var breakdown = {
      baseMin: baseMin,
      baseMax: baseMax,
      baseMid: baseMid,
      nightPer: data.nightPer,
      nightCount: data.nightCount,
      nightMonthly: nightMonthly,
      certMonthly: certMonthly,
      monthlyMin: monthlyMin,
      monthlyMax: monthlyMax,
      monthlyMid: monthlyMid,
      bonusMonths: data.bonus,
      annualMin: annualMin,
      annualMax: annualMax,
      annualMid: annualMid,
    };

    chatState.salaryBreakdown = breakdown;
    return breakdown;
  }

  // --------------------------------------------------
  // 年収レンジ計算（経験年数なし — ティーザー用）
  // --------------------------------------------------
  function calculateSalaryRange(area) {
    var data = SALARY_TABLE[area] || SALARY_TABLE.undecided;
    // 経験年数の最小(0)〜最大(+8)を考慮した幅広レンジ
    var nightMonthly = Math.round(data.nightPer * data.nightCount / 10000 * 10) / 10;
    var certMonthly = 1.5;
    var monthlyMin = data.base.min + nightMonthly + certMonthly;
    var monthlyMax = data.base.max + 8 + nightMonthly + certMonthly; // 10年以上の+8万
    var baseMidMin = Math.round((data.base.min + data.base.max) / 2);
    var baseMidMax = Math.round((data.base.min + 8 + data.base.max + 8) / 2);
    var annualMin = Math.round(monthlyMin * 12 + baseMidMin * data.bonus);
    var annualMax = Math.round(monthlyMax * 12 + baseMidMax * data.bonus);
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

    if (!chatState.done) {
      resumeFlow();
    }
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
  // Conversational Flow（v5: 2ステップ + ティーザー）
  // --------------------------------------------------
  function startConversation() {
    chatState.phase = "greeting";
    setInputVisible(false);

    showTyping();
    setTimeout(function () {
      hideTyping();
      addMessage("ai", "こんにちは！ナースロビーです。\n\n30秒で、あなたのエリアの年収相場がわかります。名前や電話番号の入力は不要です。");

      setTimeout(function () {
        showTyping();
        setTimeout(function () {
          hideTyping();
          addMessage("ai", "まず、どのエリアで働きたいですか？");
          chatState.phase = "area";
          updateProgress(1, 2);
          showButtonGroup(PRESCRIPTED.areas, handleAreaSelect);
          saveState();
        }, 250);
      }, 300);
    }, 400);
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
      addMessage("ai", areaName + "エリアですね！\n\n候補を絞り込むために、今一番気になっていることを教えてください。");
      updateProgress(2, 2);
      showButtonGroup(PRESCRIPTED.concerns, handleConcernSelect);
      saveState();
    }, 300);
  }

  // --------------------------------------------------
  // Step 2: 関心事選択 → ティーザーへ
  // --------------------------------------------------
  function handleConcernSelect(value, label) {
    chatState.concern = value;
    trackEvent("chat_concern_selected", { concern: value });
    removeButtonGroup();
    addMessage("user", label);

    // 選択した関心事に合わせたフィードバック
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
      var feedbackText = selectedConcern ? selectedConcern.feedback : "";
      addMessage("ai", feedbackText + "\n\n条件に合う施設を検索しています...");
      removeProgress();
      chatState.phase = "teaser";
      saveState();

      setTimeout(function () {
        deliverTeaser();
      }, 500);
    }, 300);
  }

  // --------------------------------------------------
  // ティーザー表示: 年収レンジ + 施設1件 + LINE CTA
  // --------------------------------------------------
  function deliverTeaser() {
    var matches = findMatchingHospitals(chatState.area);
    var areaName = getAreaDisplayName(chatState.area);
    var salaryRange = calculateSalaryRange(chatState.area);
    var facilityCount = PRESCRIPTED.areaFacilityCounts[chatState.area] || matches.length;

    // 引き継ぎコードを先行取得（LINE遷移時にすぐ表示できるように）
    requestHandoffCode(function () {});

    showTyping();
    setTimeout(function () {
      hideTyping();

      // 年収レンジメッセージ
      addMessage("ai", areaName + "エリアの看護師の年収相場は " + salaryRange.annualMin + "〜" + salaryRange.annualMax + " 万円です。");

      setTimeout(function () {
        // 施設1件だけカード表示
        if (matches.length > 0) {
          showSingleFacilityCard(matches[0], facilityCount);
        }

        setTimeout(function () {
          // LINE誘導メッセージ
          addMessage("ai", "LINEでは、AIがあなたの経験年数やライフスタイルをヒアリングして、" + facilityCount + "件の中からピッタリの病院をマッチングします。");

          setTimeout(function () {
            // 2ボタンCTA
            showTeaserCTA();
            saveState();
          }, 400);
        }, 400);
      }, 300);
    }, 350);
  }

  // --------------------------------------------------
  // 施設1件カード（ティーザー用）
  // --------------------------------------------------
  function showSingleFacilityCard(hospital, totalCount) {
    var h = hospital;
    var container = document.createElement("div");
    container.className = "chat-facility-cards";

    var card = document.createElement("div");
    card.className = "chat-facility-card chat-facility-card--info";

    var isReferral = h.referral === true;
    var badgeHtml = isReferral
      ? '<div class="facility-card-badge facility-card-badge--referral">直接ご紹介できます</div>'
      : '<div class="facility-card-badge facility-card-badge--info">参考情報</div>';

    // Enriched tags
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

    card.innerHTML =
      badgeHtml +
      '<div class="facility-card-name">' + escapeHtml(h.displayName) + '</div>' +
      enrichedTagsHtml +
      '<div class="facility-card-details">' +
        '<span>' + escapeHtml(h.salary || "") + '</span>' +
        '<span>' + escapeHtml(h.holidays || "") + '</span>' +
      '</div>';

    container.appendChild(card);

    if (totalCount > 1) {
      var more = document.createElement("div");
      more.className = "facility-card-more";
      more.textContent = "他にも " + (totalCount - 1) + " 件の施設があります";
      container.appendChild(more);
    }

    els.body.appendChild(container);
    scrollToBottom();
  }

  // --------------------------------------------------
  // ティーザーCTA（LINE or もう少し教えて）
  // --------------------------------------------------
  function showTeaserCTA() {
    var options = [
      { label: "LINEでAI診断を受ける", value: "line", isLine: true },
      { label: "もう少し教えて", value: "more", isLine: false },
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
        var codeMsg = handoffCode
          ? "\n\nLINE追加後に「HPのコードがある」を選んで、以下のコードを送ると今の情報を引き継げます。コードなしでも大丈夫です！"
          : "";
        addMessage("ai", "ありがとうございます！\n\nLINEではAIがもう少し詳しくヒアリングして、あなたにピッタリの病院をマッチングします。まずはAIの質問に答えるだけでOKです！" + codeMsg);
        chatState.phase = "done";
        chatState.done = true;
        showLineCard();
        saveState();
      }, 300);
    } else {
      // 「もう少し教えて」→ 経験年数を聞く
      trackEvent("chat_more_detail", { area: chatState.area, concern: chatState.concern });
      chatState.phase = "experience_extra";
      showTyping();
      setTimeout(function () {
        hideTyping();
        addMessage("ai", "もう少し詳しくお出ししますね！\n\n看護師としてのご経験年数を教えてください。");
        showButtonGroup(PRESCRIPTED.experiences, handleExperienceExtraSelect);
        saveState();
      }, 300);
    }
  }

  // --------------------------------------------------
  // 「もう少し教えて」→ 経験年数 → 詳細表示 → 再LINE CTA
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
      addMessage("ai", fb + "\n\n詳しい年収シミュレーションと施設情報をお出しします。");
      saveState();

      setTimeout(function () {
        deliverDetailedResults();
      }, 500);
    }, 300);
  }

  // --------------------------------------------------
  // 詳細結果: 年収内訳 + 施設3件 + 再LINE CTA
  // --------------------------------------------------
  function deliverDetailedResults() {
    var salary = calculateSalary(chatState.area, chatState.experience, chatState.concern);
    var areaName = getAreaDisplayName(chatState.area);

    showTyping();
    setTimeout(function () {
      hideTyping();
      addMessage("ai", areaName + "エリア・" + chatState.experience + "の年収シミュレーション結果です。");

      setTimeout(function () {
        showSalaryBreakdownCard(salary);

        setTimeout(function () {
          var matches = findMatchingHospitals(chatState.area);
          if (matches.length > 0) {
            addMessage("ai", "条件に合いそうな施設をご紹介します。");
            setTimeout(function () {
              showFacilityCards(matches);

              setTimeout(function () {
                showFinalLineCTA();
                saveState();
              }, 500);
            }, 300);
          } else {
            showFinalLineCTA();
            saveState();
          }
        }, 400);
      }, 300);
    }, 350);
  }

  // --------------------------------------------------
  // 年収内訳カード（透明な計算式で信頼感を出す）
  // --------------------------------------------------
  function showSalaryBreakdownCard(salary) {
    var card = document.createElement("div");
    card.className = "chat-salary-breakdown";
    // 日勤のみの年収も計算
    var dayOnlyMonthlyMin = salary.baseMin + salary.certMonthly;
    var dayOnlyMonthlyMax = salary.baseMax + salary.certMonthly;
    var dayOnlyAnnualMin = Math.round(dayOnlyMonthlyMin * 12 + salary.baseMid * salary.bonusMonths);
    var dayOnlyAnnualMax = Math.round(dayOnlyMonthlyMax * 12 + salary.baseMid * salary.bonusMonths);

    // パート時給（概算: 月給÷160時間）
    var hourlyMin = Math.round(salary.baseMin * 10000 / 160 / 50) * 50;
    var hourlyMax = Math.round(salary.baseMax * 10000 / 160 / 50) * 50;

    // concern=workstyle or blank の場合は日勤のみを先に見せる
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
        '<div class="salary-bd-item">' +
          '<span class="salary-bd-label">基本給</span>' +
          '<span class="salary-bd-value">月' + salary.baseMin + '〜' + salary.baseMax + '万円</span>' +
        '</div>' +
        '<div class="salary-bd-item">' +
          '<span class="salary-bd-label">夜勤手当</span>' +
          '<span class="salary-bd-value">月' + salary.nightMonthly + '万円<span class="salary-bd-detail">（' + (salary.nightPer / 10000).toFixed(1) + '万×' + salary.nightCount + '回）</span></span>' +
        '</div>' +
        '<div class="salary-bd-item">' +
          '<span class="salary-bd-label">資格手当等</span>' +
          '<span class="salary-bd-value">月' + salary.certMonthly + '万円</span>' +
        '</div>' +
        '<div class="salary-bd-item">' +
          '<span class="salary-bd-label">賞与</span>' +
          '<span class="salary-bd-value">' + salary.bonusMonths + 'ヶ月分</span>' +
        '</div>' +
      '</div>' +
      mainBlock +
      '<div class="salary-bd-item" style="margin-top:4px">' +
        '<span class="salary-bd-label">パート時給目安</span>' +
        '<span class="salary-bd-value">' + hourlyMin.toLocaleString() + '〜' + hourlyMax.toLocaleString() + '円/時</span>' +
      '</div>' +
      '<div class="salary-bd-note">※施設・勤務形態により変動します。LINEのAI診断でさらに精度の高い結果が出ます</div>';

    els.body.appendChild(card);
    scrollToBottom();
    trackEvent("chat_salary_breakdown_shown", { annual_mid: salary.annualMid, area: chatState.area });
  }

  // --------------------------------------------------
  // 施設カード表示（3件 — 「もう少し教えて」時）
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

      // ユーザーの関心事に合わせたハイライト
      var highlightTag = "";
      if (chatState.concern === "salary") {
        highlightTag = h.salary;
      } else if (chatState.concern === "nightshift") {
        highlightTag = h.nightShift ? "夜勤: " + h.nightShift : "夜勤情報なし";
      } else if (chatState.concern === "environment") {
        var envParts = [];
        if (h.nurseCount) envParts.push("看護師" + h.nurseCount + "名");
        if (h.features && h.features.indexOf("教育") !== -1) envParts.push("教育体制あり");
        if (h.features && h.features.indexOf("ブランク") !== -1) envParts.push("ブランクOK");
        highlightTag = envParts.length > 0 ? envParts.join("・") : (h.features ? h.features.split("・")[0] : "");
      } else if (chatState.concern === "workstyle") {
        var wsParts = [];
        if (h.type && (h.type.indexOf("慢性期") !== -1 || h.type.indexOf("回復期") !== -1)) wsParts.push("日勤のみ相談可");
        wsParts.push(h.holidays || "");
        if (h.nightShift) wsParts.push("夜勤: " + h.nightShift);
        highlightTag = wsParts.filter(function(s){return s;}).join("・");
      } else if (chatState.concern === "blank") {
        var blParts = [];
        if (h.features && h.features.indexOf("ブランク") !== -1) blParts.push("ブランクOK");
        if (h.features && h.features.indexOf("教育") !== -1) blParts.push("教育体制充実");
        if (h.nursingRatio) blParts.push("配置 " + h.nursingRatio);
        highlightTag = blParts.length > 0 ? blParts.join("・") : "詳細はLINEでお伝えできます";
      } else {
        highlightTag = h.features ? h.features.split("・")[0] : "";
      }

      var badgeHtml = isReferral
        ? '<div class="facility-card-badge facility-card-badge--referral">直接ご紹介できます</div>'
        : '<div class="facility-card-badge facility-card-badge--info">参考情報</div>';

      // Enriched tags
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

      // Stats
      var statsItems = [];
      if (h.ambulanceCount && h.ambulanceCount > 0) {
        statsItems.push("救急車 年" + h.ambulanceCount.toLocaleString() + "台");
      }
      if (h.doctorCount && h.doctorCount > 0) {
        statsItems.push("医師" + h.doctorCount + "名");
      }
      var statsHtml = "";
      if (statsItems.length > 0) {
        statsHtml = '<div class="facility-card-stats">';
        for (var s = 0; s < statsItems.length; s++) {
          statsHtml += '<span>' + escapeHtml(statsItems[s]) + '</span>';
        }
        statsHtml += '</div>';
      }

      // Data source
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
        sourceHtml +
        '<div class="facility-card-notify">LINEのAI診断でさらに詳しく</div>';

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

  // --------------------------------------------------
  // 最終LINE CTA（「もう少し教えて」後）
  // --------------------------------------------------
  function showFinalLineCTA() {
    chatState.phase = "done";
    chatState.done = true;
    chatState.lineCtaShown = true;

    showTyping();
    setTimeout(function () {
      hideTyping();
      var codeMsg = handoffCode
        ? "\n\nLINE追加後に「HPのコードがある」を選んで、以下のコードを送ると今の情報を引き継げます。コードなしでも大丈夫です！"
        : "";
      addMessage("ai", "LINEではAIがさらに詳しく分析して、あなたにピッタリの病院を見つけます。まずはAIの質問に答えるだけでOKです！" + codeMsg);

      setTimeout(function () {
        showLineCard();
        saveState();
      }, 400);
    }, 400);
  }

  // --------------------------------------------------
  // LINE Card
  // --------------------------------------------------
  function showLineCard() {
    requestHandoffCode(function (code) {
      var card = document.createElement("div");
      card.className = "chat-line-card";
      card.innerHTML =
        buildHandoffCodeHtml(code) +
        '<a href="https://lin.ee/oUgDB3x" target="_blank" rel="noopener" class="chat-line-card-btn" id="chatLineMainBtn">' +
          'LINEでAIマッチングを受ける' +
        '</a>' +
        '<div class="chat-line-card-trust">' +
          '<span>完全無料</span><span>AIが即分析</span><span>あなたの費用ゼロ</span>' +
        '</div>';

      els.body.appendChild(card);
      scrollToBottom();

      var btn = document.getElementById("chatLineMainBtn");
      if (btn) {
        btn.addEventListener("click", function () {
          trackEvent("chat_line_card_click", { phase: chatState.phase, handoff_code: code || "none" });
        });
      }
    });
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
      avatar.textContent = "R";
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
  // Button Group Rendering
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
        // Staggered animation
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

    if (!area || area === "undecided" || area === "other") {
      return hospitals;
    }

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
    // concern別ソート（紹介可能を先に + concern適合度でソート）
    var concern = chatState.concern;
    result.sort(function (a, b) {
      // 紹介可能を先に
      if (a.referral && !b.referral) return -1;
      if (!a.referral && b.referral) return 1;
      // workstyle: 慢性期・回復期（日勤のみ可能性高い）を優先
      if (concern === "workstyle") {
        var aDay = (a.type && (a.type.indexOf("慢性期") !== -1 || a.type.indexOf("回復期") !== -1)) ? 1 : 0;
        var bDay = (b.type && (b.type.indexOf("慢性期") !== -1 || b.type.indexOf("回復期") !== -1)) ? 1 : 0;
        if (aDay !== bDay) return bDay - aDay;
      }
      // blank: ブランクOK・教育体制ありを優先
      if (concern === "blank") {
        var aBlank = (a.features && a.features.indexOf("ブランク") !== -1) ? 1 : 0;
        var bBlank = (b.features && b.features.indexOf("ブランク") !== -1) ? 1 : 0;
        if (aBlank !== bBlank) return bBlank - aBlank;
      }
      // salary: 大規模・高給施設を優先（病床数でソート）
      if (concern === "salary") {
        return (b.beds || 0) - (a.beds || 0);
      }
      // nightshift: 夜勤負担軽い施設（回復期・慢性期・二交代）を優先
      if (concern === "nightshift") {
        var aNight = (a.nightShift && a.nightShift.indexOf("二交代") !== -1) ? 1 : 0;
        var bNight = (b.nightShift && b.nightShift.indexOf("二交代") !== -1) ? 1 : 0;
        if (aNight !== bNight) return bNight - aNight;
      }
      // environment: 教育体制あり・看護師数多い施設を優先
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
  // API availability check (for handoff code)
  // --------------------------------------------------
  function isAPIAvailable() {
    return CHAT_CONFIG.workerEndpoint && CHAT_CONFIG.workerEndpoint.length > 0;
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
