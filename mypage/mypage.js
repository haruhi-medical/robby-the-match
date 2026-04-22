// mypage.js — HMAC署名URLトークン認証方式（LIFF不要版）
// URL の `?t=<signed-token>` から userId を復元し、セッショントークンに交換する
const WORKER_BASE = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev';
const SESSION_KEY = 'nursrobby_mypage_session';

async function initMypageAuth() {
  // 1. URL に ?t= があればそれで初回認証
  const urlParams = new URLSearchParams(window.location.search);
  const entryToken = urlParams.get('t');
  if (entryToken && window.history && window.history.replaceState) {
    // URLからtoken消して履歴に残さない（ブラウザ履歴・スクショ漏洩対策）
    const clean = window.location.pathname + window.location.hash;
    window.history.replaceState({}, '', clean);
  }

  // 2. 既存セッションがまだ有効なら再利用
  const stored = sessionStorage.getItem(SESSION_KEY);
  if (stored) {
    try {
      const s = JSON.parse(stored);
      if (s.expiresAt > Date.now() && s.sessionToken) {
        return {
          sessionToken: s.sessionToken,
          userId: s.userId,
          displayName: s.displayName,
          resumeUpdatedAt: s.resumeUpdatedAt,
        };
      }
    } catch {}
  }

  // 3. entryToken がなければ認証誘導
  if (!entryToken) {
    document.body.innerHTML = `
      <div class="container">
        <h1>🔒 マイページ認証</h1>
        <div class="card">
          <p>LINEの「マイページ」ボタンからお入りください。</p>
          <p class="muted">有効なリンクは会員登録後にLINEで自動配信されます。</p>
          <a href="https://lin.ee/oUgDB3x" class="btn btn-primary">LINE公式に戻る</a>
        </div>
      </div>`;
    return null;
  }

  // 4. entryToken をサーバーに送ってセッショントークンに交換
  const res = await fetch(WORKER_BASE + '/api/mypage-init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entryToken }),
  });

  if (res.status === 404) {
    document.body.innerHTML = `
      <div class="container">
        <h1>まだ会員登録されていません</h1>
        <div class="card">
          <p>履歴書を作成すると、ナースロビー会員になり、このマイページが使えるようになります。</p>
          <p class="muted">※ 履歴書の作成はLINEの「履歴書を作成する」ボタンからお願いします。</p>
          <a href="https://lin.ee/oUgDB3x" class="btn btn-primary">LINEに戻る</a>
        </div>
      </div>`;
    return null;
  }

  if (res.status === 403) {
    document.body.innerHTML = `
      <div class="container">
        <h1>🔒 リンクの有効期限切れ</h1>
        <div class="card">
          <p>このリンクは期限切れです。LINEで新しいマイページリンクを取得してください。</p>
          <a href="https://lin.ee/oUgDB3x" class="btn btn-primary">LINEに戻る</a>
        </div>
      </div>`;
    return null;
  }

  if (!res.ok) {
    throw new Error(`認証に失敗しました (HTTP ${res.status})`);
  }

  const { sessionToken, userId, displayName, resumeUpdatedAt } = await res.json();
  sessionStorage.setItem(SESSION_KEY, JSON.stringify({
    sessionToken,
    userId,
    displayName,
    resumeUpdatedAt,
    expiresAt: Date.now() + 23 * 60 * 60 * 1000,
  }));

  return { sessionToken, userId, displayName, resumeUpdatedAt };
}

async function apiCall(path, options = {}) {
  const stored = JSON.parse(sessionStorage.getItem(SESSION_KEY) || '{}');
  if (!stored.sessionToken) throw new Error('未認証');
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${stored.sessionToken}`,
  };
  return fetch(WORKER_BASE + path, { ...options, headers });
}

function logout() {
  sessionStorage.removeItem(SESSION_KEY);
  window.location.href = 'https://lin.ee/oUgDB3x';
}
