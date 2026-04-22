const LIFF_ID = '2009683996-7pCYfOP7';
const WORKER_BASE = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev';
const SESSION_KEY = 'nursrobby_mypage_session';

async function initMypageAuth() {
  try {
    await liff.init({ liffId: LIFF_ID });
  } catch (e) {
    console.error('[Mypage] LIFF init failed:', e);
    window.location.href = '/mypage/auth.html';
    return null;
  }

  if (!liff.isLoggedIn()) {
    liff.login({ redirectUri: window.location.href });
    return null;
  }

  const stored = sessionStorage.getItem(SESSION_KEY);
  if (stored) {
    try {
      const { sessionToken, userId, expiresAt, displayName, resumeUpdatedAt } = JSON.parse(stored);
      if (expiresAt > Date.now()) {
        return { sessionToken, userId, displayName, resumeUpdatedAt };
      }
    } catch {}
  }

  const profile = await liff.getProfile();
  const userId = profile.userId;

  const res = await fetch(WORKER_BASE + '/api/mypage-init', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId }),
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

  if (!res.ok) {
    throw new Error('認証に失敗しました');
  }

  const { sessionToken, displayName, resumeUpdatedAt } = await res.json();
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
  liff.logout();
  window.location.href = 'https://lin.ee/oUgDB3x';
}
