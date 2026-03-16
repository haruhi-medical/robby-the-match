#!/usr/bin/env node
/**
 * generate_worker_facilities.js
 *
 * config.js の HOSPITALS 配列から api/worker_facilities.js を生成する
 *
 * Usage: node scripts/generate_worker_facilities.js
 */

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '..', 'config.js');
const OUTPUT_PATH = path.join(__dirname, '..', 'api', 'worker_facilities.js');

// ========== config.js を読み込んで HOSPITALS を抽出 ==========
const configContent = fs.readFileSync(CONFIG_PATH, 'utf8');

// HOSPITALS配列を抽出（正規表現でJSオブジェクトリテラルをパース）
// config.jsはES moduleではないので、evalで読み込む
const configScript = configContent.replace('const CONFIG = {', 'module.exports = {');
// 一時ファイルに書き出してrequire
const tmpPath = path.join(__dirname, '__tmp_config.js');
fs.writeFileSync(tmpPath, configScript);
const CONFIG = require(tmpPath);
fs.unlinkSync(tmpPath);

const hospitals = CONFIG.HOSPITALS;
console.log(`config.js から ${hospitals.length} 施設を読み込みました`);

// ========== displayName から市区町村名を抽出 ==========
function extractCity(displayName) {
  // パターン: "病院名（横浜市金沢区・671床）" or "病院名（小田原市・417床）"
  const match = displayName.match(/（([^）]+)）/);
  if (!match) return null;
  const info = match[1];
  // "横浜市金沢区・671床" → "横浜市"
  // "小田原市・417床" → "小田原市"
  // "松田町・296床" → "松田町"
  // "三浦市・136床" → "三浦市"
  const cityMatch = info.match(/^(.+?[市区町村])(?:[区・]|$)/);
  if (!cityMatch) return null;
  let city = cityMatch[1];
  // "横浜市金沢区" → "横浜市", "川崎市幸区" → "川崎市"
  if (city.match(/^(.+市).+区$/)) {
    city = city.match(/^(.+市)/)[1];
  }
  return city;
}

// ========== 市区町村名 → FACILITY_DATABASE/AREA_METADATA のキー名にマッピング ==========
const CITY_TO_AREA_KEY = {
  "小田原市": "小田原市",
  "南足柄市": "南足柄市・開成町・大井町・松田町・山北町",
  "箱根町": "小田原市",  // 箱根は小田原エリアに含める
  "湯河原町": "小田原市",  // 湯河原も小田原エリアに含める
  "松田町": "南足柄市・開成町・大井町・松田町・山北町",
  "大井町": "南足柄市・開成町・大井町・松田町・山北町",
  "開成町": "南足柄市・開成町・大井町・松田町・山北町",
  "山北町": "南足柄市・開成町・大井町・松田町・山北町",
  "平塚市": "平塚市",
  "秦野市": "秦野市",
  "伊勢原市": "伊勢原市",
  "藤沢市": "藤沢市",
  "茅ヶ崎市": "茅ヶ崎市",
  "寒川町": "茅ヶ崎市",  // 寒川は茅ヶ崎エリアに含める
  "大磯町": "大磯町・二宮町",
  "二宮町": "大磯町・二宮町",
  "海老名市": "海老名市",
  "厚木市": "厚木市",
  "大和市": "大和市・座間市・綾瀬市",
  "座間市": "大和市・座間市・綾瀬市",
  "綾瀬市": "大和市・座間市・綾瀬市",
  "愛川町": "厚木市",  // 愛川は厚木エリアに含める
  "清川村": "厚木市",  // 清川は厚木エリアに含める
  "横浜市": "横浜市",
  "川崎市": "川崎市",
  "相模原市": "相模原市",
  "横須賀市": "横須賀市",
  "鎌倉市": "鎌倉市",
  "三浦市": "三浦市",
  "逗子市": "横須賀市",  // 逗子は横須賀エリアに含める
  "葉山町": "横須賀市",  // 葉山は横須賀エリアに含める
};

// ========== commute文字列から最寄り駅名を抽出 ==========
function extractStation(commute) {
  if (!commute) return null;
  const match = commute.match(/^(.+?駅)/);
  return match ? match[1] : null;
}

// ========== salary文字列からmin/maxを抽出 ==========
function parseSalary(salaryStr) {
  if (!salaryStr) return { min: null, max: null };
  // "月給27〜35万円（目安）" → { min: 270000, max: 350000 }
  const match = salaryStr.match(/(\d+)[〜~](\d+)万円/);
  if (!match) return { min: null, max: null };
  return {
    min: parseInt(match[1]) * 10000,
    max: parseInt(match[2]) * 10000,
  };
}

// ========== holidays文字列から数値を抽出 ==========
function parseHolidays(holidaysStr) {
  if (!holidaysStr) return null;
  const match = holidaysStr.match(/(\d+)/);
  return match ? parseInt(match[1]) : null;
}

// ========== nightShift文字列から交代制タイプを抽出 ==========
function parseNightShiftType(nightShiftStr) {
  if (!nightShiftStr) return null;
  if (nightShiftStr.includes("三交代")) return "三交代制";
  if (nightShiftStr.includes("二交代")) return "二交代制";
  return null;
}

// ========== type文字列からfunctions配列を生成 ==========
function parseTypeFunctions(typeStr) {
  if (!typeStr) return [];
  return typeStr.split("・").map(t => t.trim());
}

// ========== ownerType を英語に変換 ==========
function normalizeOwnerType(ownerType) {
  const map = {
    "公立": "public",
    "県立": "public",
    "市立": "public",
    "公的": "public_interest",
    "公立大学法人": "public",
    "赤十字": "red_cross",
    "済生会": "public_interest",
    "国立病院機構": "national",
    "独立行政法人JCHO": "jcho",
    "JCHO": "jcho",
    "学校法人": "university",
    "医療法人": "private",
    "社会福祉法人": "social_welfare",
    "社会医療法人": "private",
    "地方独立行政法人": "public",
    "医療法人社団": "private",
  };
  return map[ownerType] || "private";
}

// ========== emergencyLevel を数値に変換 ==========
function parseEmergencyLevel(level) {
  if (!level) return null;
  if (level.includes("三次") || level === "三次救急") return 3;
  if (level.includes("二次") || level === "二次救急") return 2;
  if (level.includes("一次") || level === "一次救急") return 1;
  return null;
}

// ========== features + type からmatchingTagsを生成 ==========
function generateMatchingTags(hospital) {
  const tags = [];
  const type = hospital.type || "";
  const features = hospital.features || "";
  const beds = hospital.beds || 0;

  // 病床機能
  if (type.includes("高度急性期")) tags.push("高度急性期");
  if (type.includes("急性期")) tags.push("急性期");
  if (type.includes("回復期")) tags.push("回復期");
  if (type.includes("慢性期")) tags.push("慢性期");
  if (type.includes("精神科")) tags.push("精神科");
  if (type.includes("ケアミックス")) tags.push("ケアミックス");

  // 救急レベル
  const emergencyLevel = parseEmergencyLevel(hospital.emergencyLevel);
  if (emergencyLevel === 3) tags.push("三次救急", "救命救急");
  else if (emergencyLevel === 2) tags.push("二次救急");

  // 所有者タイプ
  const ownerType = hospital.ownerType || "";
  if (["公立", "県立", "市立", "公立大学法人", "地方独立行政法人"].includes(ownerType)) tags.push("公立病院");
  if (ownerType === "赤十字") tags.push("赤十字");
  if (ownerType === "国立病院機構") tags.push("国立病院機構");
  if (["学校法人"].includes(ownerType)) tags.push("大学病院");

  // 規模
  if (beds >= 500) tags.push("大規模病院");
  else if (beds >= 200) tags.push("中規模病院");
  else tags.push("小規模病院");

  // 看護配置
  if (hospital.nursingRatio === "7:1") tags.push("7対1看護");
  if (hospital.nursingRatio === "10:1") tags.push("10対1看護");

  // features からタグ抽出
  const featureKeywords = {
    "救命救急": "救命救急",
    "ICU": "ICU",
    "NICU": "NICU",
    "HCU": "HCU",
    "リハビリ": "リハビリ充実",
    "回復期リハ": "回復期リハビリ",
    "災害拠点": "災害拠点",
    "がん診療": "がん診療",
    "教育体制充実": "教育体制充実",
    "地域医療支援": "地域医療支援病院",
    "退院支援": "退院支援充実",
    "訪問看護": "訪問看護",
    "緩和ケア": "緩和ケア",
    "ホスピス": "緩和ケア",
    "透析": "透析",
    "循環器": "循環器",
    "脳外科": "脳外科",
    "整形外科": "整形外科",
    "心臓": "心臓血管",
    "産婦人科": "産婦人科",
    "周産期": "周産期",
    "小児": "小児科",
    "精神科": "精神科",
    "認知症": "認知症",
    "地域密着": "地域密着",
    "ブランクOK": "ブランクOK",
    "駅近": "駅近",
    "駅徒歩": "駅近",
    "残業少なめ": "残業少なめ",
    "日勤のみ相談可": "日勤のみ相談可",
    "福利厚生充実": "福利厚生充実",
    "新築": "新築移転",
    "紹介可能": "紹介可能",
    "DPC": "DPC",
    "特定機能病院": "特定機能病院",
    "徳洲会": "徳洲会グループ",
    "IMSグループ": "IMSグループ",
    "済生会": "済生会",
  };

  for (const [keyword, tag] of Object.entries(featureKeywords)) {
    if (features.includes(keyword) && !tags.includes(tag)) {
      tags.push(tag);
    }
  }

  // referral
  if (hospital.referral) {
    if (!tags.includes("紹介可能")) tags.push("紹介可能");
  }

  return tags;
}

// ========== 駅名→座標マッピング（既存のものを保持 + 新規追加） ==========
const STATION_COORDINATES = {
  "小田原駅": { lat: 35.2564, lng: 139.1551 },
  "鴨宮駅": { lat: 35.2687, lng: 139.176 },
  "国府津駅": { lat: 35.276, lng: 139.205 },
  "足柄駅": { lat: 35.248, lng: 139.123 },
  "螢田駅": { lat: 35.267, lng: 139.137 },
  "富水駅": { lat: 35.274, lng: 139.125 },
  "秦野駅": { lat: 35.3737, lng: 139.2192 },
  "東海大学前駅": { lat: 35.366, lng: 139.254 },
  "鶴巻温泉駅": { lat: 35.369, lng: 139.27 },
  "渋沢駅": { lat: 35.38, lng: 139.19 },
  "平塚駅": { lat: 35.328, lng: 139.3497 },
  "大磯駅": { lat: 35.312, lng: 139.311 },
  "藤沢駅": { lat: 35.338, lng: 139.487 },
  "辻堂駅": { lat: 35.335, lng: 139.448 },
  "湘南台駅": { lat: 35.39, lng: 139.468 },
  "善行駅": { lat: 35.358, lng: 139.463 },
  "六会日大前駅": { lat: 35.377, lng: 139.461 },
  "藤沢本町駅": { lat: 35.347, lng: 139.478 },
  "茅ヶ崎駅": { lat: 35.334, lng: 139.404 },
  "北茅ヶ崎駅": { lat: 35.349, lng: 139.401 },
  "香川駅": { lat: 35.357, lng: 139.378 },
  "二宮駅": { lat: 35.299, lng: 139.255 },
  "大雄山駅": { lat: 35.33, lng: 139.11 },
  "開成駅": { lat: 35.335, lng: 139.148 },
  "和田河原駅": { lat: 35.323, lng: 139.121 },
  "相模金子駅": { lat: 35.309, lng: 139.159 },
  "新松田駅": { lat: 35.340, lng: 139.143 },
  "伊勢原駅": { lat: 35.395, lng: 139.314 },
  "本厚木駅": { lat: 35.441, lng: 139.365 },
  "愛甲石田駅": { lat: 35.412, lng: 139.327 },
  "海老名駅": { lat: 35.447, lng: 139.391 },
  "さがみ野駅": { lat: 35.459, lng: 139.401 },
  "横浜駅": { lat: 35.4657, lng: 139.6224 },
  "新横浜駅": { lat: 35.5076, lng: 139.6173 },
  "金沢八景駅": { lat: 35.3333, lng: 139.621 },
  "阪東橋駅": { lat: 35.4367, lng: 139.6317 },
  "元町・中華街駅": { lat: 35.4423, lng: 139.6505 },
  "鶴見駅": { lat: 35.5059, lng: 139.6745 },
  "藤が丘駅": { lat: 35.5413, lng: 139.5171 },
  "みなとみらい駅": { lat: 35.4577, lng: 139.6326 },
  "追浜駅": { lat: 35.3176, lng: 139.6213 },
  "三ツ沢上町駅": { lat: 35.4752, lng: 139.6103 },
  "センター南駅": { lat: 35.5445, lng: 139.5738 },
  "川崎駅": { lat: 35.5308, lng: 139.6996 },
  "宮前平駅": { lat: 35.5774, lng: 139.5858 },
  "武蔵小杉駅": { lat: 35.5764, lng: 139.6593 },
  "新百合ヶ丘駅": { lat: 35.6037, lng: 139.5079 },
  "高津駅": { lat: 35.5994, lng: 139.6161 },
  "相模大野駅": { lat: 35.5291, lng: 139.4371 },
  "橋本駅": { lat: 35.5949, lng: 139.3458 },
  "横須賀中央駅": { lat: 35.2786, lng: 139.6706 },
  "大船駅": { lat: 35.3505, lng: 139.5341 },
  // 新規追加
  "箱根湯本駅": { lat: 35.2327, lng: 139.1056 },
  "下曽我駅": { lat: 35.2814, lng: 139.1783 },
  "松田駅": { lat: 35.3407, lng: 139.1435 },
  "鶴間駅": { lat: 35.4917, lng: 139.4604 },
  "相武台前駅": { lat: 35.4887, lng: 139.4095 },
  "大和駅": { lat: 35.4828, lng: 139.4607 },
  "中央林間駅": { lat: 35.5117, lng: 139.4446 },
  "南林間駅": { lat: 35.4976, lng: 139.4537 },
  "かしわ台駅": { lat: 35.4493, lng: 139.3995 },
  "シーサイドライン市大医学部駅": { lat: 35.3398, lng: 139.6181 },
  "京急久里浜駅": { lat: 35.2304, lng: 139.7055 },
  "衣笠駅": { lat: 35.2648, lng: 139.6515 },
  "三浦海岸駅": { lat: 35.1914, lng: 139.6432 },
  "三崎口駅": { lat: 35.1807, lng: 139.6262 },
  "鎌倉駅": { lat: 35.319, lng: 139.5505 },
  "弘明寺駅": { lat: 35.4273, lng: 139.6113 },
  "戸塚駅": { lat: 35.3988, lng: 139.5335 },
  "東戸塚駅": { lat: 35.4099, lng: 139.5563 },
  "あざみ野駅": { lat: 35.5674, lng: 139.5534 },
  "長津田駅": { lat: 35.5279, lng: 139.4947 },
  "中山駅": { lat: 35.5083, lng: 139.5418 },
  "十日市場駅": { lat: 35.5146, lng: 139.5202 },
  "瀬谷駅": { lat: 35.4623, lng: 139.4895 },
  "二俣川駅": { lat: 35.4571, lng: 139.5233 },
  "上大岡駅": { lat: 35.4068, lng: 139.5968 },
  "日吉駅": { lat: 35.5535, lng: 139.6466 },
  "港南台駅": { lat: 35.3862, lng: 139.5717 },
  "たまプラーザ駅": { lat: 35.5698, lng: 139.5549 },
  "上星川駅": { lat: 35.4645, lng: 139.5784 },
  "洋光台駅": { lat: 35.3806, lng: 139.6027 },
  "屏風浦駅": { lat: 35.3876, lng: 139.6077 },
  "杉田駅": { lat: 35.3735, lng: 139.6207 },
  "能見台駅": { lat: 35.3512, lng: 139.6177 },
  "磯子駅": { lat: 35.3975, lng: 139.6176 },
  "溝の口駅": { lat: 35.5991, lng: 139.6111 },
  "百合ヶ丘駅": { lat: 35.5951, lng: 139.5157 },
  "鹿島田駅": { lat: 35.5564, lng: 139.6755 },
  "登戸駅": { lat: 35.6165, lng: 139.5695 },
  "向ヶ丘遊園駅": { lat: 35.6121, lng: 139.5608 },
  "元住吉駅": { lat: 35.5624, lng: 139.6547 },
  "鈴木町駅": { lat: 35.5319, lng: 139.7043 },
  "小島新田駅": { lat: 35.5186, lng: 139.7434 },
  "中野島駅": { lat: 35.6245, lng: 139.5498 },
  "北里大学病院前バス停": { lat: 35.5392, lng: 139.3835 },
  "小田急相模原駅": { lat: 35.5145, lng: 139.4311 },
  "相模原駅": { lat: 35.5764, lng: 139.3734 },
  "古淵駅": { lat: 35.5366, lng: 139.4151 },
  "緑が丘駅": { lat: 35.329, lng: 139.648 },
  "田浦駅": { lat: 35.293, lng: 139.637 },
};

// ========== AREA_METADATA ==========
const AREA_METADATA = {
  "小田原市": {
    areaId: "odawara",
    medicalRegion: "kensei",
    population: "約18.6万人",
    majorStations: ["小田原駅（JR東海道線・小田急線・東海道新幹線・箱根登山鉄道・大雄山線）"],
    commuteToYokohama: "約60分（JR東海道線）",
    nurseAvgSalary: "月給28〜38万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 13, clinics: 139, nursingHomes: 45 },
    demandLevel: "非常に高い",
    demandNote: "県西の基幹病院が集中。小田原市立病院（417床）の新築移転予定に伴い人材需要が高まる。",
    livingInfo: "新幹線停車駅で都心通勤も可能。箱根・湯河原の温泉地にも近く生活環境が魅力。",
    defaultCoords: { lat: 35.2564, lng: 139.1551 },
  },
  "秦野市": {
    areaId: "hadano",
    medicalRegion: "shonan_west",
    population: "約16万人",
    majorStations: ["秦野駅（小田急小田原線）", "東海大学前駅（小田急小田原線）", "渋沢駅（小田急小田原線）"],
    commuteToYokohama: "約50分（小田急線）",
    nurseAvgSalary: "月給27〜36万円",
    ptAvgSalary: "月給24〜31万円",
    facilityCount: { hospitals: 8, clinics: 91, nursingHomes: 32 },
    demandLevel: "高い",
    demandNote: "秦野赤十字病院（312床）を中心に安定した看護師需要。地域密着型の医療機関が多い。",
    livingInfo: "丹沢山系の自然環境と住宅地が共存。物価が比較的安く、子育て環境に人気。",
    defaultCoords: { lat: 35.3737, lng: 139.2192 },
  },
  "平塚市": {
    areaId: "hiratsuka",
    medicalRegion: "shonan_west",
    population: "約25.6万人",
    majorStations: ["平塚駅（JR東海道線）"],
    commuteToYokohama: "約30分（JR東海道線）",
    nurseAvgSalary: "月給28〜37万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 9, clinics: 173, nursingHomes: 56 },
    demandLevel: "非常に高い",
    demandNote: "平塚共済病院（400床）を筆頭に急性期病院が充実。人口規模に比して看護師需要が大きい。",
    livingInfo: "海と山の両方にアクセスでき、自然と都市機能のバランスが良い。横浜通勤も現実的。",
    defaultCoords: { lat: 35.328, lng: 139.3497 },
  },
  "藤沢市": {
    areaId: "fujisawa",
    medicalRegion: "shonan_east",
    population: "約44万人",
    majorStations: ["藤沢駅（JR東海道線・小田急江ノ島線・江ノ電）", "辻堂駅（JR東海道線）", "湘南台駅（小田急・相鉄・横浜市営地下鉄）"],
    commuteToYokohama: "約20分（JR東海道線）",
    nurseAvgSalary: "月給29〜38万円",
    ptAvgSalary: "月給26〜33万円",
    facilityCount: { hospitals: 16, clinics: 409, nursingHomes: 84 },
    demandLevel: "非常に高い",
    demandNote: "藤沢市民病院（536床）・湘南藤沢徳洲会病院（419床）など大規模病院が集中。看護師需要が県内屈指。",
    livingInfo: "湘南のブランドエリア。海沿いのライフスタイルが人気。東京・横浜通勤も便利。",
    defaultCoords: { lat: 35.338, lng: 139.487 },
  },
  "茅ヶ崎市": {
    areaId: "chigasaki",
    medicalRegion: "shonan_east",
    population: "約24.4万人",
    majorStations: ["茅ヶ崎駅（JR東海道線・相模線）", "北茅ヶ崎駅（JR相模線）"],
    commuteToYokohama: "約25分（JR東海道線）",
    nurseAvgSalary: "月給28〜37万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 6, clinics: 144, nursingHomes: 40 },
    demandLevel: "高い",
    demandNote: "茅ヶ崎市立病院（401床）が地域の中核。市内の高齢化に伴い訪問看護需要も増加。",
    livingInfo: "海辺の穏やかな暮らし。サーフィン文化。駅前は商業施設も充実しバランスの良い環境。",
    defaultCoords: { lat: 35.334, lng: 139.404 },
  },
  "大磯町・二宮町": {
    areaId: "oiso_ninomiya",
    medicalRegion: "shonan_west",
    population: "約6万人（合計）",
    majorStations: ["大磯駅（JR東海道線）", "二宮駅（JR東海道線）"],
    commuteToYokohama: "約40分（JR東海道線）",
    nurseAvgSalary: "月給27〜35万円",
    ptAvgSalary: "月給24〜31万円",
    facilityCount: { hospitals: 1, clinics: 16, nursingHomes: 8 },
    demandLevel: "やや高い",
    demandNote: "大磯プリンスホテル跡地の再開発を含め、高齢者向け医療施設の需要が増加傾向。",
    livingInfo: "湘南発祥の地。海と山の自然環境。閑静な住宅地で子育てにも適する。東海道線で通勤可。",
    defaultCoords: { lat: 35.306, lng: 139.283 },
  },
  "南足柄市・開成町・大井町・松田町・山北町": {
    areaId: "minamiashigara_kaisei_oi",
    medicalRegion: "kensei",
    population: "約9.5万人（合計）",
    majorStations: ["大雄山駅（伊豆箱根鉄道大雄山線）", "開成駅（小田急小田原線）", "松田駅（JR御殿場線・小田急小田原線）", "山北駅（JR御殿場線）"],
    commuteToYokohama: "約70分（大雄山線+小田急線）",
    nurseAvgSalary: "月給26〜35万円",
    ptAvgSalary: "月給24〜30万円",
    facilityCount: { hospitals: 6, clinics: 30, nursingHomes: 12 },
    demandLevel: "高い",
    demandNote: "足柄上病院（296床）が地域の中核。中山間地域の医療アクセス確保のため看護師需要が安定。",
    livingInfo: "豊かな自然と低い生活コスト。小田原・新松田から小田急線で都心アクセスも可能。子育て支援充実。",
    defaultCoords: null,
  },
  "伊勢原市": {
    areaId: "isehara",
    medicalRegion: "shonan_west",
    population: "約10.1万人",
    majorStations: ["伊勢原駅（小田急小田原線）"],
    commuteToYokohama: "約45分（小田急線）",
    nurseAvgSalary: "月給28〜38万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 3, clinics: 57, nursingHomes: 25 },
    demandLevel: "非常に高い",
    demandNote: "東海大学医学部付属病院（804床・看護師1,117名）は県西最大の医療機関。常時大量採用。",
    livingInfo: "大山の自然と大学のある学園都市。小田急線で新宿60分、物価も手頃。",
    defaultCoords: { lat: 35.395, lng: 139.314 },
  },
  "厚木市": {
    areaId: "atsugi",
    medicalRegion: "kenoh",
    population: "約22.4万人",
    majorStations: ["本厚木駅（小田急小田原線）", "愛甲石田駅（小田急小田原線）"],
    commuteToYokohama: "約40分（小田急線）",
    nurseAvgSalary: "月給28〜37万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 12, clinics: 135, nursingHomes: 50 },
    demandLevel: "非常に高い",
    demandNote: "厚木市立病院（347床）と東名厚木病院（289床）を中心に看護師需要が旺盛。リハビリ系施設も多い。",
    livingInfo: "本厚木駅周辺は商業施設充実。新宿まで55分。丹沢の自然も近く子育て環境も良好。",
    defaultCoords: { lat: 35.441, lng: 139.365 },
  },
  "海老名市": {
    areaId: "ebina",
    medicalRegion: "kenoh",
    population: "約14万人",
    majorStations: ["海老名駅（小田急線・相鉄線・JR相模線）"],
    commuteToYokohama: "約30分（相鉄線）",
    nurseAvgSalary: "月給29〜38万円",
    ptAvgSalary: "月給26〜33万円",
    facilityCount: { hospitals: 9, clinics: 170, nursingHomes: 40 },
    demandLevel: "非常に高い",
    demandNote: "海老名総合病院（479床・看護師570名・PT56名）は県央唯一の救命救急センターで常時大量採用。年間救急車7,700台超。人口増加中で需要拡大。",
    livingInfo: "3路線利用可能で交通利便性抜群。横浜まで30分、新宿まで50分。駅前再開発でららぽーと・ビナウォークなど商業施設充実。子育て世代に人気。",
    defaultCoords: { lat: 35.447, lng: 139.391 },
  },
  "大和市・座間市・綾瀬市": {
    areaId: "yamato_zama_ayase",
    medicalRegion: "kenoh",
    population: "約47万人（合計）",
    majorStations: ["大和駅（小田急江ノ島線・相鉄本線）", "中央林間駅（小田急江ノ島線・東急田園都市線）", "相武台前駅（小田急小田原線）"],
    commuteToYokohama: "約25分（相鉄線）",
    nurseAvgSalary: "月給27〜37万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 15, clinics: 350, nursingHomes: 80 },
    demandLevel: "非常に高い",
    demandNote: "大和市立病院（403床）・座間総合病院（352床）を中核に中規模病院が多数。人口密度が高く看護師需要旺盛。",
    livingInfo: "都心・横浜へのアクセス良好。住宅地として発展し商業施設も充実。比較的手頃な家賃。",
    defaultCoords: { lat: 35.4828, lng: 139.4607 },
  },
  "横浜市": {
    areaId: "yokohama",
    medicalRegion: "yokohama",
    population: "約377万人",
    majorStations: ["横浜駅（JR・京急・東急・みなとみらい線・相鉄・横浜市営地下鉄）", "新横浜駅（JR東海道新幹線・JR横浜線・横浜市営地下鉄）"],
    commuteToYokohama: "市内",
    nurseAvgSalary: "月給28〜38万円",
    ptAvgSalary: "月給26〜34万円",
    facilityCount: { hospitals: 130, clinics: 4200, nursingHomes: 600 },
    demandLevel: "非常に高い",
    demandNote: "県内最大の医療集積地。大学病院・救命救急センター多数。常に大量の看護師需要。",
    livingInfo: "日本第二の都市。充実した交通網・商業施設・文化施設。都心へのアクセスも良好。",
    defaultCoords: { lat: 35.4657, lng: 139.6224 },
  },
  "川崎市": {
    areaId: "kawasaki",
    medicalRegion: "kawasaki",
    population: "約154万人",
    majorStations: ["川崎駅（JR東海道線・京浜東北線・南武線）", "武蔵小杉駅（JR南武線・横須賀線・東急東横線）", "新百合ヶ丘駅（小田急線）"],
    commuteToYokohama: "約10〜20分（JR東海道線）",
    nurseAvgSalary: "月給28〜39万円",
    ptAvgSalary: "月給26〜34万円",
    facilityCount: { hospitals: 56, clinics: 1400, nursingHomes: 250 },
    demandLevel: "非常に高い",
    demandNote: "聖マリアンナ医大（955床）を筆頭に大規模病院が多数。人口増加中で看護師需要は旺盛。",
    livingInfo: "東京・横浜の中間に位置し交通至便。武蔵小杉エリアを中心に再開発が進む。",
    defaultCoords: { lat: 35.5308, lng: 139.6996 },
  },
  "相模原市": {
    areaId: "sagamihara",
    medicalRegion: "sagamihara",
    population: "約72万人",
    majorStations: ["相模大野駅（小田急線）", "橋本駅（JR横浜線・相模線・京王相模原線）"],
    commuteToYokohama: "約40分（小田急線・JR横浜線）",
    nurseAvgSalary: "月給27〜39万円",
    ptAvgSalary: "月給25〜33万円",
    facilityCount: { hospitals: 36, clinics: 700, nursingHomes: 150 },
    demandLevel: "非常に高い",
    demandNote: "北里大学病院（1135床）は県内最大規模。救命救急センター。教育体制充実で新卒にも人気。",
    livingInfo: "政令指定都市。橋本エリアはリニア中央新幹線の新駅が予定され注目度上昇中。",
    defaultCoords: { lat: 35.5291, lng: 139.4371 },
  },
  "横須賀市": {
    areaId: "yokosuka",
    medicalRegion: "yokosuka_miura",
    population: "約38万人",
    majorStations: ["横須賀中央駅（京急本線）", "横須賀駅（JR横須賀線）"],
    commuteToYokohama: "約30分（京急本線）",
    nurseAvgSalary: "月給28〜38万円",
    ptAvgSalary: "月給25〜32万円",
    facilityCount: { hospitals: 18, clinics: 300, nursingHomes: 80 },
    demandLevel: "高い",
    demandNote: "横須賀共済病院（740床）が地域の中核。米軍基地関連の医療需要もある。",
    livingInfo: "海に囲まれた自然環境。京急で横浜・品川へ直通。三浦半島の温暖な気候。",
    defaultCoords: { lat: 35.2786, lng: 139.6706 },
  },
  "鎌倉市": {
    areaId: "kamakura",
    medicalRegion: "yokosuka_miura",
    population: "約17万人",
    majorStations: ["大船駅（JR東海道線・横須賀線・湘南モノレール）", "鎌倉駅（JR横須賀線・江ノ電）"],
    commuteToYokohama: "約20分（JR東海道線）",
    nurseAvgSalary: "月給29〜38万円",
    ptAvgSalary: "月給26〜33万円",
    facilityCount: { hospitals: 8, clinics: 200, nursingHomes: 40 },
    demandLevel: "高い",
    demandNote: "湘南鎌倉総合病院（669床）は徳洲会グループの旗艦病院。24時間365日救急。",
    livingInfo: "歴史と自然が共存する人気エリア。大船駅周辺は商業施設も充実。",
    defaultCoords: { lat: 35.3505, lng: 139.5341 },
  },
  "三浦市": {
    areaId: "miura",
    medicalRegion: "yokosuka_miura",
    population: "約4万人",
    majorStations: ["三崎口駅（京急久里浜線）", "三浦海岸駅（京急久里浜線）"],
    commuteToYokohama: "約60分（京急線）",
    nurseAvgSalary: "月給26〜35万円",
    ptAvgSalary: "月給24〜31万円",
    facilityCount: { hospitals: 3, clinics: 30, nursingHomes: 15 },
    demandLevel: "高い",
    demandNote: "三浦市立病院（136床）が地域唯一の急性期病院。高齢化率高く医療需要は安定。",
    livingInfo: "三浦半島の先端に位置。温暖な気候と豊かな海産物。自然を満喫できる環境。",
    defaultCoords: { lat: 35.1807, lng: 139.6262 },
  },
};

// ========== 施設データの変換 ==========
const facilityDb = {};

for (const h of hospitals) {
  const city = extractCity(h.displayName);
  if (!city) {
    console.warn(`WARNING: 市区町村名を抽出できませんでした: ${h.displayName}`);
    continue;
  }

  const areaKey = CITY_TO_AREA_KEY[city];
  if (!areaKey) {
    console.warn(`WARNING: エリアキーが見つかりません: ${city} (${h.displayName})`);
    continue;
  }

  if (!facilityDb[areaKey]) facilityDb[areaKey] = [];

  // displayNameから病院名だけを抽出
  const nameMatch = h.displayName.match(/^(.+?)（/);
  const name = nameMatch ? nameMatch[1] : h.displayName;

  const salary = parseSalary(h.salary);
  const station = extractStation(h.commute);
  const stationCoords = station ? STATION_COORDINATES[station] : null;

  const facility = {
    name: name,
    type: h.type,
    beds: h.beds || 0,
    wardCount: null,
    functions: parseTypeFunctions(h.type),
    nurseCount: h.nurseCount || null,
    ptCount: null,
    features: h.features || "",
    access: h.commute || "",
    nightShiftType: parseNightShiftType(h.nightShift),
    annualHolidays: parseHolidays(h.holidays),
    salaryMin: salary.min,
    salaryMax: salary.max,
    ptSalaryMin: null,
    ptSalaryMax: null,
    educationLevel: (h.features && h.features.includes("教育体制充実")) ? "充実" : "あり",
    matchingTags: generateMatchingTags(h),
    lat: stationCoords ? stationCoords.lat : null,
    lng: stationCoords ? stationCoords.lng : null,
    nearestStation: station,
    nursingRatio: h.nursingRatio || null,
    emergencyLevel: parseEmergencyLevel(h.emergencyLevel),
    ownerType: normalizeOwnerType(h.ownerType),
    dpcHospital: (h.features && (h.features.includes("DPC") || h.features.includes("特定機能病院"))) || false,
  };

  // referral: true のみ追加フラグ
  if (h.referral) {
    facility.referral = true;
  }

  facilityDb[areaKey].push(facility);
}

// ========== 出力生成 ==========
const timestamp = new Date().toISOString();
let totalFacilities = 0;
for (const arr of Object.values(facilityDb)) totalFacilities += arr.length;

let output = `// ==========================================
// 神奈川ナース転職 - 施設データベース（自動生成）
// Generated: ${timestamp}
// Source: config.js (${Object.keys(facilityDb).length}エリア, ${totalFacilities}施設)
// Generator: scripts/generate_worker_facilities.js
// ==========================================

`;

// STATION_COORDINATES
output += `// 駅座標データ（Haversine距離計算用）\nconst STATION_COORDINATES = ${JSON.stringify(STATION_COORDINATES, null, 2)};\n\n`;

// AREA_METADATA
output += `// エリアメタデータ\nconst AREA_METADATA = ${JSON.stringify(AREA_METADATA, null, 2)};\n\n`;

// FACILITY_DATABASE
output += `// 全施設データベース\nconst FACILITY_DATABASE = ${JSON.stringify(facilityDb, null, 2)};\n\n`;

// export
output += `export { FACILITY_DATABASE, AREA_METADATA, STATION_COORDINATES };\n`;

fs.writeFileSync(OUTPUT_PATH, output, 'utf8');
console.log(`\n✅ ${OUTPUT_PATH} を生成しました`);
console.log(`   エリア数: ${Object.keys(facilityDb).length}`);
console.log(`   施設数: ${totalFacilities}`);

// エリアごとの施設数を表示
for (const [area, facilities] of Object.entries(facilityDb)) {
  console.log(`   ${area}: ${facilities.length}施設`);
}
