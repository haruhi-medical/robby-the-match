// mypage.js — HMAC署名URLトークン認証方式（LIFF不要版）
// 毎回 /api/mypage-init を叩いて最新データを取得する（localStorage はセッション継続用のみ）
const WORKER_BASE = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev';
const SESSION_KEY = 'nursrobby_mypage_session';

async function initMypageAuth() {
  // 1. URL に ?t= があればそれで認証（初回 or 新規会員化後のリダイレクト）
  const urlParams = new URLSearchParams(window.location.search);
  const entryToken = urlParams.get('t');
  if (entryToken && window.history && window.history.replaceState) {
    const clean = window.location.pathname + window.location.hash;
    window.history.replaceState({}, '', clean);
  }

  // 2. 既存 sessionToken を localStorage から取得（認証継続用）
  let existingSessionToken = null;
  const stored = localStorage.getItem(SESSION_KEY);
  if (stored) {
    try {
      const s = JSON.parse(stored);
      if (s.expiresAt > Date.now() && s.sessionToken) {
        existingSessionToken = s.sessionToken;
      }
    } catch {}
  }

  // 3. 認証情報がなければ誘導
  if (!entryToken && !existingSessionToken) {
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

  // 4. mypage-init を毎回叩いて最新の会員情報を取得
  const body = entryToken ? { entryToken } : { sessionToken: existingSessionToken };
  let res;
  try {
    res = await fetch(WORKER_BASE + '/api/mypage-init', {
      method: 'POST',
      mode: 'cors',
      credentials: 'omit',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } catch (netErr) {
    // Load failed 等の fetch エラーを詳細化
    const detail = `${netErr.name || 'Error'}: ${netErr.message || String(netErr)}`;
    document.body.innerHTML = `
      <div class="container">
        <h1>🔌 通信エラー</h1>
        <div class="card">
          <p>サーバーに接続できませんでした。</p>
          <pre style="font-size:0.75rem;background:#f5f5f5;padding:8px;border-radius:6px;overflow-x:auto;">${detail}</pre>
          <p class="muted">LINEアプリ内ブラウザで発生する場合は、右上「︙」→「他のアプリで開く」→ Safari をお試しください。</p>
          <a href="https://lin.ee/oUgDB3x" class="btn btn-outline">LINEに戻る</a>
          <button onclick="location.reload()" class="btn btn-primary">再読み込み</button>
        </div>
      </div>`;
    return null;
  }

  if (res.status === 404) {
    // 退会済み or 未登録
    localStorage.removeItem(SESSION_KEY);
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
    // セッション期限切れ → localStorage をクリアして再認証誘導
    localStorage.removeItem(SESSION_KEY);
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
  // 最新情報で localStorage 上書き
  localStorage.setItem(SESSION_KEY, JSON.stringify({
    sessionToken,
    userId,
    displayName,
    resumeUpdatedAt,
    expiresAt: Date.now() + 23 * 60 * 60 * 1000,
  }));

  return { sessionToken, userId, displayName, resumeUpdatedAt };
}

async function apiCall(path, options = {}) {
  const stored = JSON.parse(localStorage.getItem(SESSION_KEY) || '{}');
  if (!stored.sessionToken) throw new Error('未認証');
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${stored.sessionToken}`,
  };
  return fetch(WORKER_BASE + path, { ...options, headers });
}

function logout() {
  localStorage.removeItem(SESSION_KEY);
  window.location.href = 'https://lin.ee/oUgDB3x';
}
