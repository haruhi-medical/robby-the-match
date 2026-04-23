// mypage.js — HMAC署名URLトークン認証方式（LIFF不要版）
// 毎回 /api/mypage-init を叩いて最新データを取得する（localStorage はセッション継続用のみ）
const WORKER_BASE = 'https://robby-the-match-api.robby-the-robot-2026.workers.dev';
const SESSION_KEY = 'nursrobby_mypage_session';

// SVG icon set — auth.html のデザイン言語に揃える（絵文字禁止）
const MYPAGE_ICONS = {
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  wifiOff: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="1" y1="1" x2="23" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/><path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/><path d="M10.71 5.05A16 16 0 0 1 22.58 9"/><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>',
  userPlus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
};

function renderMypageNotice({ icon, title, bodyHtml, primary, secondary, detail }) {
  // 既存の通知ブロックを除去（再表示対応）
  const prev = document.getElementById('mypageNotice');
  if (prev) prev.remove();
  // body直下の要素のうち site-header と script 以外を非表示
  // （edit.html等のhero/form構造、loading/app、sticky submit-bar等を全部隠す）
  Array.from(document.body.children).forEach(el => {
    if (el.tagName === 'SCRIPT' || el.tagName === 'NOSCRIPT') return;
    if (el.classList && el.classList.contains('site-header')) return;
    if (el.id === 'mypageNotice') return;
    el.style.display = 'none';
  });

  const main = document.createElement('main');
  main.id = 'mypageNotice';
  main.className = 'container';
  main.innerHTML = `
    <div class="page-title-area">
      <div class="page-title">${MYPAGE_ICONS[icon] || ''}${title}</div>
    </div>
    <div class="card">
      ${bodyHtml || ''}
      ${detail ? `<pre style="font-size:0.72rem;background:#F3F4F6;color:#374151;padding:10px 12px;border-radius:8px;overflow-x:auto;margin:14px 0 0;white-space:pre-wrap;word-break:break-all;">${detail}</pre>` : ''}
      <div style="display:flex; flex-direction:column; gap:10px; margin-top:18px;">
        ${primary ? `<a href="${primary.href}" class="btn btn-primary" style="width:100%; justify-content:center;"${primary.onClick ? ` onclick="${primary.onClick}"` : ''}>${primary.label}</a>` : ''}
        ${secondary ? `<a href="${secondary.href}" class="btn btn-outline" style="width:100%; justify-content:center;"${secondary.onClick ? ` onclick="${secondary.onClick}"` : ''}>${secondary.label}</a>` : ''}
      </div>
    </div>`;
  // site-header の直後に挿入（あれば）
  const header = document.querySelector('.site-header');
  if (header && header.parentNode) {
    header.parentNode.insertBefore(main, header.nextSibling);
  } else {
    document.body.appendChild(main);
  }
}

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
    renderMypageNotice({
      icon: 'lock',
      title: 'マイページ認証',
      bodyHtml: `
        <p style="margin-bottom:10px;">LINEの「マイページ」ボタンからお入りください。</p>
        <p class="muted" style="font-size:0.85rem;">有効なリンクは会員登録後にLINEで自動配信されます。</p>`,
      primary: { href: 'https://lin.ee/oUgDB3x', label: 'LINE公式に戻る' },
    });
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
    renderMypageNotice({
      icon: 'wifiOff',
      title: '通信エラー',
      bodyHtml: `
        <p style="margin-bottom:10px;">サーバーに接続できませんでした。</p>
        <p class="muted" style="font-size:0.85rem;">LINEアプリ内ブラウザで発生する場合は、右上「︙」→「他のアプリで開く」→ Safari をお試しください。</p>`,
      detail,
      primary: { href: 'javascript:void(0)', label: '再読み込み', onClick: 'location.reload()' },
      secondary: { href: 'https://lin.ee/oUgDB3x', label: 'LINEに戻る' },
    });
    return null;
  }

  if (res.status === 404) {
    // 退会済み or 未登録
    localStorage.removeItem(SESSION_KEY);
    renderMypageNotice({
      icon: 'userPlus',
      title: 'まだ会員登録されていません',
      bodyHtml: `
        <p style="margin-bottom:10px;">履歴書を作成すると、ナースロビー会員になり、このマイページが使えるようになります。</p>
        <p class="muted" style="font-size:0.85rem;">履歴書の作成は LINE の「履歴書を作成する」ボタンからお願いします。</p>`,
      primary: { href: 'https://lin.ee/oUgDB3x', label: 'LINEに戻る' },
    });
    return null;
  }

  if (res.status === 403) {
    // セッション期限切れ → localStorage をクリアして再認証誘導
    localStorage.removeItem(SESSION_KEY);
    renderMypageNotice({
      icon: 'clock',
      title: 'リンクの有効期限切れ',
      bodyHtml: `
        <p style="margin-bottom:10px;">このリンクは期限切れです。</p>
        <p class="muted" style="font-size:0.85rem;">LINEで新しいマイページリンクを取得してください。</p>`,
      primary: { href: 'https://lin.ee/oUgDB3x', label: 'LINEに戻る' },
    });
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
