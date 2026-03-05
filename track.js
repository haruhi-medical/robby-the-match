// ナースロビー 軽量アクセス解析 (自前トラッキング)
// GA4/Clarityに加え、API経由で直接データ取得可能
(function() {
  var endpoint = "https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/track";
  var page = location.pathname;
  var referrer = document.referrer || "";

  function send(event) {
    var data = JSON.stringify({ page: page, referrer: referrer, event: event || "pageview" });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([data], { type: "application/json" }));
    } else {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", endpoint, true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(data);
    }
  }

  // ページビュー送信
  send("pageview");

  // グローバル関数として公開（chat.jsから呼べるように）
  window.__nrTrack = send;
})();
