#!/usr/bin/env node
import { chromium } from 'playwright';

async function main() {
  console.log('🌐 ブラウザ起動（email認証方式）...');

  const browser = await chromium.launchPersistentContext(
    '/tmp/netlify-pw-profile3',
    { headless: false, slowMo: 300, viewport: { width: 1280, height: 900 } }
  );
  const page = await browser.newPage();

  // Netlifyログインページ
  await page.goto('https://app.netlify.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3000);

  const bodyText = await page.textContent('body');
  if (bodyText.includes('Log in with email')) {
    console.log('📧 「Log in with email」をクリック...');
    await page.click('a:has-text("Log in with email"), button:has-text("Log in with email")');
    await page.waitForTimeout(3000);

    // メールアドレス入力
    const email = 'robby.the.robot.2026@gmail.com';
    console.log(`📧 メールアドレス入力: ${email}`);

    try {
      await page.fill('input[type="email"], input[name="email"]', email);
      await page.waitForTimeout(1000);

      // ログインボタンをクリック
      const submitBtn = page.locator('button[type="submit"], button:has-text("Log in"), button:has-text("Email me a login link"), button:has-text("Send")').first();
      if (await submitBtn.isVisible({ timeout: 3000 })) {
        await submitBtn.click();
        console.log('✅ マジックリンクを送信しました！');
        console.log('📧 robby.the.robot.2026@gmail.com にメールが届きます。');
        console.log('   メール内のリンクをクリックしてログインしてください。');
        console.log('   ログイン後、自動的にunpauseを実行します（3分待機）...');
      }
    } catch (e) {
      // パスワードフォームかもしれない
      console.log('パスワード入力が必要かも:', e.message);
    }

    await page.screenshot({ path: '/tmp/netlify_email.png' });
    console.log('📸 /tmp/netlify_email.png');

    // ログイン完了を待つ
    try {
      await page.waitForURL('**/app.netlify.com/teams/**', { timeout: 180000 });
      console.log('✅ ログイン成功！');
    } catch (e) {
      // ダッシュボードかチーム画面になっているかチェック
      const currentUrl = page.url();
      console.log(`📍 現在URL: ${currentUrl}`);
      if (currentUrl.includes('app.netlify.com') && !currentUrl.includes('login')) {
        console.log('✅ ログインできた可能性あり');
      } else {
        console.log('⚠️  ログインタイムアウト');
        await page.screenshot({ path: '/tmp/netlify_timeout.png' });
        await browser.close();
        return;
      }
    }
  } else {
    console.log('✅ 既にログイン済み');
  }

  // サイトページへ
  console.log('📍 サイトページへ...');
  await page.goto('https://app.netlify.com/projects/delicate-kataifi-1a74cb', {
    waitUntil: 'domcontentloaded', timeout: 60000
  });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: '/tmp/netlify_dashboard2.png', fullPage: true });

  // ボタン一覧
  const allButtons = await page.$$eval('button, a, [role="button"]', els =>
    els.map(el => ({
      tag: el.tagName,
      text: el.textContent.trim().substring(0, 100),
      visible: el.offsetParent !== null,
    })).filter(e => e.text.length > 0 && e.visible)
  );
  console.log('🔍 ボタン一覧:');
  allButtons.forEach(b => console.log(`   [${b.tag}] ${b.text}`));

  // Resume/Unpause探索+クリック
  const targets = ['Resume', 'Unpause', 'Restore', 'Reactivate', 'Enable', 'Upgrade'];
  let clicked = false;
  for (const target of targets) {
    try {
      const btn = page.locator(`button:has-text("${target}"), a:has-text("${target}")`).first();
      if (await btn.isVisible({ timeout: 2000 })) {
        console.log(`✅ 「${target}」クリック！`);
        await btn.click();
        clicked = true;
        await page.waitForTimeout(5000);
        // 確認ダイアログ
        for (const c of ['Confirm', 'Yes', 'OK', 'Resume', 'Continue']) {
          try {
            const cb = page.locator(`button:has-text("${c}")`).first();
            if (await cb.isVisible({ timeout: 2000 })) {
              await cb.click();
              await page.waitForTimeout(3000);
              break;
            }
          } catch (e) {}
        }
        break;
      }
    } catch (e) {}
  }

  await page.screenshot({ path: '/tmp/netlify_final3.png', fullPage: true });
  console.log(clicked ? '✅ 操作完了！' : '⚠️  ボタン見つからず');
  await page.waitForTimeout(3000);
  await browser.close();
  console.log('🏁 完了');
}

main().catch(err => { console.error('エラー:', err.message); process.exit(1); });
