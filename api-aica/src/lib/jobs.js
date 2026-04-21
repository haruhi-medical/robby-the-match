/**
 * 求人検索ライブラリ
 * 既存の nurse-robby-db (jobs テーブル) を読み取り専用で参照
 */

/** エリアキー → 市区町村リスト */
const AREA_CITY_MAP = {
  yokohama_kawasaki: ["横浜市", "川崎市"],
  shonan_kamakura: ["藤沢市", "茅ヶ崎市", "鎌倉市", "逗子市", "葉山町", "寒川町"],
  sagamihara_kenoh: ["相模原市", "厚木市", "海老名市", "座間市", "綾瀬市", "大和市", "愛川町"],
  yokosuka_miura: ["横須賀市", "三浦市"],
  odawara_kensei: [
    "小田原市", "南足柄市", "箱根町", "湯河原町", "真鶴町", "松田町", "山北町",
    "大井町", "開成町", "中井町", "二宮町", "大磯町", "平塚市", "秦野市", "伊勢原市",
  ],
  kanagawa_all: [],
  kanto_all: [],
  undecided: [],
};

/** エリアキー → 都道府県 */
const AREA_PREF_MAP = {
  yokohama_kawasaki: "神奈川県",
  shonan_kamakura: "神奈川県",
  sagamihara_kenoh: "神奈川県",
  yokosuka_miura: "神奈川県",
  odawara_kensei: "神奈川県",
  kanagawa_all: "神奈川県",
};

/** Quick Reply ラベル → エリアキー */
const AREA_LABEL_TO_KEY = {
  "横浜・川崎": "yokohama_kawasaki",
  "湘南・鎌倉": "shonan_kamakura",
  "相模原・県央": "sagamihara_kenoh",
  "横須賀・三浦": "yokosuka_miura",
  "小田原・県西": "odawara_kensei",
  "どこでもOK": "kanagawa_all",
  "神奈川県外も": "kanto_all",
};

/** 働き方ラベル → SQLフィルタ種別 */
const WORKSTYLE_LABEL_TO_KEY = {
  "日勤のみ": "day",
  "夜勤月2-3回なら可": "twoshift_light",
  "夜勤ありOK": "twoshift",
  "パート・非常勤": "part",
  "夜勤専従": "night",
};

/**
 * プロファイルから求人を検索
 * @param {object} params
 * @param {object} params.profile  profile_json の内容
 * @param {object} params.db       env.NURSE_DB (D1)
 * @param {number} [params.limit=3]
 * @returns {Promise<Array>} jobs
 */
export async function searchJobs({ profile, db, limit = 3 }) {
  const areaKey = AREA_LABEL_TO_KEY[profile.area] || "kanagawa_all";
  const cities = AREA_CITY_MAP[areaKey] || [];
  const pref = AREA_PREF_MAP[areaKey] || "神奈川県";
  const workstyleKey = WORKSTYLE_LABEL_TO_KEY[profile.workstyle] || null;

  let sql = `SELECT kjno, employer, title, rank, score, area, prefecture,
    work_location, salary_form, salary_min, salary_max, salary_display,
    bonus_text, holidays, emp_type, station_text, shift1, shift2,
    description, welfare FROM jobs WHERE 1=1
    AND (emp_type IS NULL OR emp_type NOT LIKE '%派遣%')
    AND (title IS NULL OR title NOT LIKE '%派遣%')`;
  const bind = [];

  if (cities.length > 0) {
    sql += ` AND (${cities.map(() => "work_location LIKE ?").join(" OR ")})`;
    cities.forEach((c) => bind.push(`%${c}%`));
    sql += " AND prefecture = ?";
    bind.push(pref);
  } else if (pref) {
    sql += " AND prefecture = ?";
    bind.push(pref);
  }

  // 働き方フィルタ
  if (workstyleKey === "day") {
    sql += " AND (title IS NULL OR title NOT LIKE '%夜勤%')";
  } else if (workstyleKey === "part") {
    sql += " AND emp_type LIKE '%パート%'";
  } else if (workstyleKey === "night") {
    sql += " AND (title LIKE '%夜勤%' OR title LIKE '%二交代%')";
  } else if (workstyleKey === "twoshift_light") {
    // 軽め夜勤: 明示的な"夜勤専従"は除外
    sql += " AND (title IS NULL OR title NOT LIKE '%夜勤専従%')";
  }

  sql += " ORDER BY score DESC LIMIT ?";
  bind.push(limit);

  try {
    const result = await db.prepare(sql).bind(...bind).all();
    return result.results || [];
  } catch (err) {
    console.error("[jobs] query failed:", err.message);
    return [];
  }
}

/** 求人票の「1行」を key-value 形式で返す Flex box */
function jobRow(label, value) {
  if (!value) return null;
  return {
    type: "box",
    layout: "baseline",
    spacing: "sm",
    contents: [
      { type: "text", text: label, size: "xs", color: "#999999", flex: 3 },
      { type: "text", text: String(value), size: "xs", color: "#333333", flex: 7, wrap: true },
    ],
  };
}

/** D1 の job レコード → Flex bubble（最初から全項目表示版・mega） */
export function jobToFlexBubble(job) {
  const employer = (job.employer || "病院/施設").slice(0, 40);
  const title = (job.title || "").slice(0, 60);

  // 給与
  let salaryStr = job.salary_display || "";
  if (!salaryStr && (job.salary_min || job.salary_max)) {
    const min = job.salary_min ? `${Math.round(job.salary_min / 10000)}万円` : "";
    const max = job.salary_max ? `${Math.round(job.salary_max / 10000)}万円` : "";
    salaryStr = min + (max ? "〜" + max : "〜");
  }

  const location = (job.work_location || "").replace(/^(神奈川県|東京都|千葉県|埼玉県)/, "") || null;
  const station = job.station_text || null;
  const shifts = [job.shift1, job.shift2].filter(Boolean).join(" / ") || null;
  const holidays = job.holidays ? `年${job.holidays}日` : null;

  // 説明文・福利厚生は長いので 180 字で切って、続きは postback ボタン
  const descRaw = (job.description || "").trim();
  const welfareRaw = (job.welfare || "").trim();
  const MAX_DESC = 180;
  const desc = descRaw.length > MAX_DESC ? descRaw.slice(0, MAX_DESC) + "…" : descRaw;
  const welfare = welfareRaw.length > MAX_DESC ? welfareRaw.slice(0, MAX_DESC) + "…" : welfareRaw;
  const hasMore = descRaw.length > MAX_DESC || welfareRaw.length > MAX_DESC;

  const bodyContents = [
    {
      type: "text",
      text: employer,
      weight: "bold",
      size: "md",
      wrap: true,
      color: "#1a9de0",
    },
    title
      ? { type: "text", text: title, size: "xs", color: "#666666", wrap: true, margin: "xs" }
      : null,
    { type: "separator", margin: "md" },
    {
      type: "box",
      layout: "vertical",
      spacing: "sm",
      margin: "md",
      contents: [
        jobRow("給与", salaryStr),
        jobRow("賞与", job.bonus_text),
        jobRow("所在地", location),
        jobRow("最寄駅", station),
        jobRow("雇用形態", job.emp_type),
        jobRow("勤務体系", shifts),
        jobRow("休日", holidays),
      ].filter(Boolean),
    },
    welfare ? { type: "separator", margin: "md" } : null,
    welfare
      ? {
          type: "box",
          layout: "vertical",
          margin: "md",
          contents: [
            { type: "text", text: "待遇・福利厚生", size: "xs", color: "#999999" },
            { type: "text", text: welfare, size: "xs", color: "#333333", wrap: true, margin: "xs" },
          ],
        }
      : null,
    desc ? { type: "separator", margin: "md" } : null,
    desc
      ? {
          type: "box",
          layout: "vertical",
          margin: "md",
          contents: [
            { type: "text", text: "仕事内容", size: "xs", color: "#999999" },
            { type: "text", text: desc, size: "xs", color: "#333333", wrap: true, margin: "xs" },
          ],
        }
      : null,
    { type: "separator", margin: "md" },
    {
      type: "text",
      text: `求人番号: ${job.kjno || "-"}`,
      size: "xxs",
      color: "#cccccc",
      margin: "md",
    },
  ].filter(Boolean);

  const footerContents = [];
  if (hasMore) {
    footerContents.push({
      type: "button",
      style: "link",
      height: "sm",
      action: {
        type: "postback",
        label: "全文を見る",
        data: `job_detail:${job.kjno || ""}`,
        displayText: `${employer}の全文を見る`,
      },
    });
  }
  footerContents.push({
    type: "button",
    style: "primary",
    color: "#06C755",
    height: "sm",
    action: {
      type: "message",
      label: "この求人に進む",
      text: `${employer}に進みたい`,
    },
  });

  return {
    type: "bubble",
    size: "mega",
    body: {
      type: "box",
      layout: "vertical",
      spacing: "sm",
      contents: bodyContents,
    },
    footer: {
      type: "box",
      layout: "vertical",
      spacing: "sm",
      contents: footerContents,
    },
  };
}

/** kjno で求人1件を取得 */
export async function getJobByKjno(db, kjno) {
  if (!kjno) return null;
  try {
    return await db.prepare(`SELECT * FROM jobs WHERE kjno = ? LIMIT 1`).bind(kjno).first();
  } catch (err) {
    console.error("[jobs] getByKjno failed:", err.message);
    return null;
  }
}

/** 求人レコードを「全項目」整形テキストに変換（LINE1メッセージ内表示用） */
export function formatJobDetail(job) {
  if (!job) return "この求人の詳細情報が見つかりませんでした。";
  const sections = [];

  sections.push(`◇ ${job.employer || "施設名不明"}`);

  if (job.title) sections.push(`【求人タイトル】\n${job.title}`);

  // 給与
  const salaryLines = [];
  if (job.salary_display) salaryLines.push(job.salary_display);
  if (job.salary_min || job.salary_max) {
    const min = job.salary_min ? `${Math.round(job.salary_min / 10000)}万円` : "";
    const max = job.salary_max ? `${Math.round(job.salary_max / 10000)}万円` : "";
    if (min || max) salaryLines.push(`範囲: ${min}${max ? "〜" + max : "〜"}`);
  }
  if (job.salary_form) salaryLines.push(`支給形態: ${job.salary_form}`);
  if (job.bonus_text) salaryLines.push(`賞与: ${job.bonus_text}`);
  if (salaryLines.length) sections.push(`【給与】\n${salaryLines.join("\n")}`);

  // 所在地・最寄駅
  const locLines = [];
  if (job.work_location) locLines.push(job.work_location);
  if (job.station_text) locLines.push(job.station_text);
  if (locLines.length) sections.push(`【所在地・最寄駅】\n${locLines.join("\n")}`);

  // 雇用形態
  if (job.emp_type) sections.push(`【雇用形態】\n${job.emp_type}`);

  // 勤務体系
  const shifts = [job.shift1, job.shift2].filter(Boolean).join("\n");
  if (shifts) sections.push(`【勤務体系】\n${shifts}`);

  // 休日
  if (job.holidays) sections.push(`【休日】\n${job.holidays}日/年`);

  // 待遇・福利厚生
  if (job.welfare) sections.push(`【待遇・福利厚生】\n${job.welfare}`);

  // 求人詳細
  if (job.description) sections.push(`【求人詳細】\n${job.description}`);

  // 管理情報
  if (job.kjno) sections.push(`【求人番号】\n${job.kjno}`);
  if (job.prefecture || job.area) {
    sections.push(`【エリア区分】\n${[job.prefecture, job.area].filter(Boolean).join(" / ")}`);
  }

  sections.push("---\n気になる点や質問があれば、そのままメッセージでお聞きください。");
  return sections.join("\n\n");
}

/** 複数求人 → Flex Carousel Message */
export function jobsToFlexCarousel(jobs) {
  if (!jobs || jobs.length === 0) return null;
  return {
    type: "flex",
    altText: `求人${jobs.length}件ご提案`,
    contents: {
      type: "carousel",
      contents: jobs.map(jobToFlexBubble),
    },
  };
}
