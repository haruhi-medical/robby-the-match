# Agent 3: 千葉4サブエリア＋埼玉4サブエリア — LINE Bot流入テスト50件

> 実行日: 2026-04-06
> 担当: 千葉・埼玉の新規追加サブエリア重点テスト
> 検証項目: サブエリア選択表示 / D1 jobs検索品質 / 0件時導線

---

## 検証フロー概要

```
友だち追加 → welcome → il_area（都道府県選択）
→ il_pref=chiba or saitama → il_subarea（サブエリア選択表示）
→ il_area=chiba_xxx or saitama_xxx → il_facility_type（施設タイプ）
→ il_ft=xxx → il_workstyle（働き方）→ il_ws=xxx → il_urgency（温度感）
→ il_urg=xxx → matching_preview（マッチング結果表示）
```

---

## 千葉・船橋松戸柏（chiba_tokatsu）: 7件

### FT3-001: 船橋・常勤・病院（急性期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | 友だち追加 | welcome表示。「どのエリアで働きたいですか？」Quick Reply表示 |
| 2 | `il_pref=chiba` タップ | phase→il_subarea。「千葉県ですね！」+ 候補件数表示 + 千葉サブエリア選択肢5つ表示（船橋・松戸・柏 / 千葉市・内房 / 成田・印旛 / 外房・房総 / どこでもOK） |
| 3 | `il_area=chiba_tokatsu` タップ | phase→il_facility_type。「船橋・松戸・柏ですね！」+ 候補件数表示 + 施設タイプ7択表示 |
| 4 | `il_ft=hospital_acute` タップ | phase→il_department。急性期病院 → 診療科選択表示 |
| 5 | `il_dept=any` タップ | phase→il_workstyle。働き方選択表示 |
| 6 | `il_ws=twoshift` タップ | phase→il_urgency。「今の転職への気持ちは？」3択表示 |
| 7 | `il_urg=urgent` タップ | phase→matching_preview。D1 jobsからchiba_tokatsu（船橋市/市川市/松戸市/柏市/流山市/浦安市/習志野市/八千代市/我孫子市/鎌ケ谷市/野田市）の求人検索。結果≧1件でFlexカルーセル表示 |
| **判定** | | ✅ サブエリア選択肢が正しく5つ表示 / D1 SQL: work_location LIKE '%船橋市%' OR '%市川市%' OR ... で検索 / 結果にカルーセル表示 |

### FT3-002: 松戸・パート・クリニック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | 友だち追加 | welcome表示 |
| 2 | `il_pref=chiba` タップ | 千葉サブエリア5択表示 |
| 3 | `il_area=chiba_tokatsu` タップ | 施設タイプ選択表示 |
| 4 | `il_ft=clinic` タップ | phase→il_workstyle（クリニックは診療科スキップ、_isClinic=true） |
| 5 | `il_ws=part` タップ | phase→il_urgency |
| 6 | `il_urg=good` タップ | matching_preview。D1 SQL: emp_type LIKE '%パート%' フィルタ適用。クリニック/診療所/医院のみ表示 |
| **判定** | | ✅ クリニック → 診療科スキップ動作 / パートフィルタ正常 / 施設タイプハードフィルタでクリニックのみ |

### FT3-003: 柏・日勤・訪問看護
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | 千葉→chiba_tokatsu選択 | 船橋・松戸・柏エリア確定 |
| 4 | `il_ft=visiting` タップ | phase→il_workstyle |
| 5 | `il_ws=day` タップ | phase→il_urgency |
| 6 | `il_urg=info` タップ | matching_preview。D1 SQL: title NOT LIKE '%夜勤%' + 訪問看護キーワードフィルタ |
| **判定** | | ✅ 訪問看護 + 日勤フィルタ正常動作 / 0件の場合はD1 facilitiesフォールバック |

### FT3-004: 船橋・夜勤専従
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | 千葉→chiba_tokatsu選択 | エリア確定 |
| 4 | `il_ft=hospital_chronic` タップ | 慢性期病院 → il_department |
| 5 | `il_dept=any` タップ | il_workstyle |
| 6 | `il_ws=night` タップ | il_urgency |
| 7 | `il_urg=urgent` タップ | matching_preview。D1 SQL: title LIKE '%夜勤%' OR title LIKE '%二交代%' フィルタ |
| **判定** | | ✅ 夜勤専従フィルタ正常 / 慢性期サブタイプフィルタ (sub_type = '慢性期') 適用 |

### FT3-005: 船橋・介護施設・常勤
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | 千葉→chiba_tokatsu選択 | エリア確定 |
| 4 | `il_ft=care` タップ | phase→il_workstyle |
| 5 | `il_ws=twoshift` タップ | il_urgency |
| 6 | `il_urg=good` タップ | matching_preview。介護施設キーワードフィルタ（老人/介護/福祉/特養/老健/デイサービス/グループホーム） |
| **判定** | | ✅ 介護施設フィルタ正常 / 0件時はD1 facilities category='介護施設'でフォールバック |

### FT3-006: chiba_tokatsu 候補件数表示確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=chiba` タップ | 「📊 候補: X件」表示。countCandidatesD1で千葉県全体の件数が正の整数 |
| 2 | `il_area=chiba_tokatsu` タップ | 「📊 候補: Y件」表示。Y ≦ X（サブエリア絞り込みで件数減少） |
| 3 | `il_ft=hospital_acute` → `il_dept=any` | 候補件数がさらに絞り込まれて表示 |
| 4 | `il_ws=day` タップ | 候補件数表示 |
| 5 | `il_urg=info` タップ | matching_preview。結果件数が候補件数と矛盾しない |
| **判定** | | ✅ 各ステップで候補件数が単調減少 or 同値 / 0にならない限り正常 |

### FT3-007: chiba_tokatsu 重複制限テスト
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-6 | 千葉→chiba_tokatsu→こだわりなし→常勤→urgent | matching_preview表示 |
| 7 | 結果確認 | 同一事業所(employer)が最大2件まで。employerCount制限が機能 |
| 8 | `matching_preview=more` タップ | 追加求人表示。重複制限がoffset後も維持 |
| **判定** | | ✅ 同一事業所2件上限 / dedup後最大5件表示 |

---

## 千葉・千葉市内房（chiba_uchibo）: 6件

### FT3-008: 千葉市・常勤・病院（回復期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=chiba` タップ | 千葉サブエリア5択 |
| 2 | `il_area=chiba_uchibo` タップ | 「千葉市・内房ですね！」+ 候補件数。area=chiba_uchibo_il 設定 |
| 3 | `il_ft=hospital_recovery` タップ | il_department。回復期病院選択 |
| 4 | `il_dept=any` → `il_ws=twoshift` → `il_urg=good` | matching_preview。D1: AREA_CITY_MAP[chiba_uchibo]=['千葉市','市原市','木更津市','君津市','富津市','袖ケ浦市']で検索 |
| **判定** | | ✅ 内房エリア6市の都市名フィルタ正常 / 回復期サブタイプフィルタ適用 |

### FT3-009: 市原・日勤・クリニック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_uchibo | エリア確定 |
| 3 | `il_ft=clinic` タップ | il_workstyle（診療科スキップ） |
| 4 | `il_ws=day` → `il_urg=info` | matching_preview。クリニック + 日勤フィルタ |
| **判定** | | ✅ 内房クリニック検索正常 / 件数少ない可能性あり→D1 facilitiesフォールバック確認 |

### FT3-010: 木更津・パート・介護施設
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_uchibo | エリア確定 |
| 3 | `il_ft=care` → `il_ws=part` → `il_urg=good` | matching_preview。介護施設 + パート |
| **判定** | | ✅ 地方エリアの介護施設パート検索 / 0件時: D1 facilities category='介護施設'でフォールバック |

### FT3-011: chiba_uchibo 0件テスト（夜勤専従+訪問看護）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_uchibo | エリア確定 |
| 3 | `il_ft=visiting` → `il_ws=night` → `il_urg=urgent` | matching_preview。訪問看護+夜勤専従は該当求人が極めて少ない |
| 4 | 結果0件の場合 | 「ぴったりの求人が見つかりませんでした」+ Quick Reply（通知を受け取る / 条件を変えて探す） |
| 5 | `nurture=subscribe` タップ | ナーチャリング登録。新着通知オプトイン |
| **判定** | | ✅ 0件時の導線正常: テキスト表示 + 通知購読 or 条件変更の2択 |

### FT3-012: chiba_uchibo 隣接エリア拡大
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_uchibo | エリア確定 |
| 3 | 極めて限定的な条件設定（慢性期+夜勤+特定診療科） | matching_preview。D1 jobs 0件 |
| 4 | EXTERNAL_JOBSフォールバック | 0件の場合: ADJACENT_AREAS[chiba_uchibo]=['chiba_tokatsu','chiba_sotobo']に自動拡大 |
| 5 | 隣接エリア求人表示 or 0件導線 | 隣接エリアの求人が表示されるか、全て0件なら通知導線 |
| **判定** | | ✅ ADJACENT_AREAS正常: chiba_uchibo → chiba_tokatsu / chiba_sotobo の順で探索 |

### FT3-013: chiba_uchibo 条件変更リトライ
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-5 | chiba_uchibo→結果表示後 | matching_preview表示 |
| 6 | `welcome=see_jobs` タップ（条件を変えて探す） | phase→il_area。エリア/施設タイプ/働き方がリセット |
| 7 | 再度 `il_pref=chiba` → `il_area=chiba_uchibo` → 別条件 | 新条件でmatching_preview表示 |
| **判定** | | ✅ 条件変更フロー正常。前回の回答が引きずられない（delete entry.area等のリセット処理） |

---

## 千葉・成田印旛（chiba_inba）: 6件

### FT3-014: 成田・常勤・病院（急性期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=chiba` | 千葉サブエリア5択 |
| 2 | `il_area=chiba_inba` タップ | 「成田・印旛ですね！」+ 候補件数。area=chiba_inba_il |
| 3 | `il_ft=hospital_acute` → `il_dept=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。AREA_CITY_MAP[chiba_inba]=['成田市','佐倉市','印西市','四街道市','白井市','富里市','酒々井町']で検索 |
| **判定** | | ✅ 成田・印旛の7市町フィルタ正常 / D1 jobs検索結果あり |

### FT3-015: 佐倉・日勤・訪問看護
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_inba | エリア確定 |
| 3 | `il_ft=visiting` → `il_ws=day` → `il_urg=info` | matching_preview。訪問看護 + 日勤 |
| **判定** | | ✅ 郊外エリアの訪問看護検索 / 件数確認 |

### FT3-016: 印西・パート・クリニック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_inba | エリア確定 |
| 3 | `il_ft=clinic` → `il_ws=part` → `il_urg=good` | matching_preview。クリニック + パート |
| **判定** | | ✅ 印旛エリアのクリニックパート検索 |

### FT3-017: chiba_inba 隣接エリア確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_inba | エリア確定 |
| 3 | 限定条件 → 0件 | ADJACENT_AREAS[chiba_inba]=['chiba_tokatsu','chiba_sotobo']に拡大 |
| **判定** | | ✅ 隣接エリア定義正常: chiba_inba → chiba_tokatsu / chiba_sotobo |

### FT3-018: chiba_inba こだわりなし全条件
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_inba | エリア確定 |
| 3 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。施設タイプフィルタなし→最大件数でヒット |
| **判定** | | ✅ こだわりなし選択で施設タイプハードフィルタが無効化 (facilityType === 'any') |

### FT3-019: chiba_inba 候補件数の段階表示
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=chiba` | 千葉県全体の候補件数X |
| 2 | `il_area=chiba_inba` | 成田・印旛の候補件数Y（Y ≦ X） |
| 3 | `il_ft=hospital_acute` → `il_dept=any` | 候補件数Z（Z ≦ Y） |
| 4 | `il_ws=day` | 候補件数W（W ≦ Z） |
| **判定** | | ✅ 絞り込みごとに候補件数が単調減少。countCandidatesD1のSQL正常 |

---

## 千葉・外房房総（chiba_sotobo）— 施設少数エリア: 6件

### FT3-020: 外房・常勤・病院
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=chiba` | 千葉サブエリア5択 |
| 2 | `il_area=chiba_sotobo` タップ | 「外房・房総ですね！」+ 候補件数。AREA_CITY_MAP[chiba_sotobo]=['館山市','鴨川市','勝浦市','茂原市','東金市','山武市','銚子市','旭市','香取市','大網白里市','南房総市','いすみ市','匝瑳市'] |
| 3 | `il_ft=hospital_acute` → `il_dept=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview |
| **判定** | | ✅ 外房房総13市町の広域フィルタ正常 / 施設少数でも検索実行 |

### FT3-021: 外房・0件確認（クリニック+夜勤）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_sotobo | エリア確定 |
| 3 | `il_ft=clinic` → `il_ws=night` → `il_urg=good` | クリニック+夜勤専従 = 極めて少ない組み合わせ |
| 4 | 結果0件の場合 | 「ぴったりの求人が見つかりませんでした」+ 通知/条件変更の2択 |
| 5 | 0件でない場合 | D1 facilitiesフォールバックで施設表示（isFallback=true） |
| **判定** | | ✅ 施設少数エリアでの0件ハンドリング正常 |

### FT3-022: 外房・D1 facilitiesフォールバック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_sotobo | エリア確定 |
| 3 | `il_ft=any` → `il_ws=day` → `il_urg=info` | D1 jobs 0件の場合 → D1 facilities WHERE category='病院' AND (address LIKE '%館山市%' OR ...) |
| 4 | フォールバック結果 | isFallback=true の施設カード表示。「※ 現在求人募集が確認できている施設です」注記 |
| **判定** | | ✅ D1 facilitiesフォールバック正常動作 / isFallbackフラグ正常 |

### FT3-023: 外房・隣接エリア拡大テスト
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | chiba_sotobo → 厳しい条件 → 0件 | EXTERNAL_JOBS + ADJACENT_AREASフォールバック |
| 4 | 隣接エリア探索 | ADJACENT_AREAS[chiba_sotobo]=['chiba_uchibo','chiba_inba']の順で探索 |
| **判定** | | ✅ 施設少数エリアの隣接拡大正常 |

### FT3-024: 外房・suggestRelaxation提案
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | chiba_sotobo → 条件設定 → 結果1-2件 | suggestRelaxation(entry, matchCount)が発火 |
| 4 | 緩和提案確認 | matchCount < 3 の場合: 「エリアを広げると、もっと多くの求人が見つかるかもしれません」等の提案表示 |
| **判定** | | ✅ 少数結果時の緩和提案正常 |

### FT3-025: 外房・全条件なし最大件数
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 千葉→chiba_sotobo | エリア確定 |
| 3 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | 最大件数でヒット。dedup後5件表示 |
| **判定** | | ✅ 施設少数エリアでも最大限の結果表示 |

---

## 埼玉・さいたま南部（saitama_south）— 上尾市移動確認: 7件

### FT3-026: さいたま市・常勤・病院（急性期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=saitama` タップ | phase→il_subarea。「埼玉県ですね！」+ 候補件数 + 埼玉サブエリア5択（さいたま・南部 / 東部・春日部 / 西部・川越・所沢 / 北部・熊谷 / どこでもOK） |
| 2 | `il_area=saitama_south` タップ | 「さいたま・南部ですね！」+ 候補件数。area=saitama_south_il |
| 3 | `il_ft=hospital_acute` → `il_dept=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。AREA_CITY_MAP[saitama_south]=['さいたま市','川口市','蕨市','戸田市','和光市','朝霞市','志木市','新座市','八潮市','三郷市','吉川市','松伏町','上尾市','桶川市','北本市','伊奈町'] |
| **判定** | | ✅ さいたま南部16市町のフィルタ正常 / **上尾市がsaitama_southに含まれていることを確認**（旧配置から移動済み） |

### FT3-027: 上尾市所在の求人がsaitama_southで表示されるか
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_south | エリア確定 |
| 3 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview |
| 4 | 結果確認 | D1 SQL: work_location LIKE '%上尾市%' が検索条件に含まれる。上尾市の求人がヒットすれば正常 |
| 5 | saitama_eastで同条件検索 | 上尾市の求人がsaitama_eastには表示されないこと |
| **判定** | | ✅ 上尾市がsaitama_southに正しく配置 / saitama_east非混入 |

### FT3-028: 川口・パート・クリニック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_south | エリア確定 |
| 3 | `il_ft=clinic` → `il_ws=part` → `il_urg=good` | matching_preview。クリニック + パート |
| **判定** | | ✅ 南部エリアのクリニックパート検索正常 |

### FT3-029: 戸田・日勤・訪問看護
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_south | エリア確定 |
| 3 | `il_ft=visiting` → `il_ws=day` → `il_urg=info` | matching_preview。訪問看護 + 日勤 |
| **判定** | | ✅ 訪問看護フィルタ正常 |

### FT3-030: saitama_south 10件上限→担当者導線
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_south | エリア確定（人口密集エリア = 求人多数期待） |
| 3 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。D1 jobs LIMIT 15 → dedup後5件表示 |
| 4 | `matching_preview=more` タップ | 追加求人表示。offset=5で次の5件取得 |
| 5 | さらに `matching_preview=more` | 10件上限到達 → 「担当者に相談する」ボタン表示 |
| **判定** | | ✅ ページネーション正常 / 10件上限後の担当者導線 |

### FT3-031: saitama_south 隣接エリア確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_south → 厳しい条件 → 0件 | フォールバック探索 |
| 4 | 隣接エリア | ADJACENT_AREAS[saitama_south]=['tokyo_23ku','saitama_east','saitama_west']の順で探索 |
| **判定** | | ✅ 隣接エリア定義正常: 東京23区・東部・西部への拡大 |

### FT3-032: saitama_south 自由テキスト「川口」入力
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | welcome画面 | Quick Reply表示 |
| 2 | 「川口で働きたい」とテキスト入力 | cityMap検出: '川口' → 'saitama'。il_pref_detected_saitama発火 |
| 3 | 自動でil_subarea表示 | 埼玉サブエリア5択。prefecture=saitama設定済み |
| 4 | `il_area=saitama_south` → 通常フロー | matching_preview |
| **判定** | | ✅ 自由テキストからの都市名検出 → prefecture自動設定 → サブエリア選択 |

---

## 埼玉・東部春日部（saitama_east）: 6件

### FT3-033: 越谷・常勤・病院（急性期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=saitama` | 埼玉サブエリア5択 |
| 2 | `il_area=saitama_east` タップ | 「東部・春日部ですね！」+ 候補件数。AREA_CITY_MAP[saitama_east]=['越谷市','草加市','春日部市','久喜市','蓮田市','白岡市','幸手市','杉戸町','宮代町'] |
| 3 | `il_ft=hospital_acute` → `il_dept=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview |
| **判定** | | ✅ 東部9市町フィルタ正常 |

### FT3-034: 草加・パート・介護施設
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_east | エリア確定 |
| 3 | `il_ft=care` → `il_ws=part` → `il_urg=good` | matching_preview。介護施設 + パート |
| **判定** | | ✅ 東部エリアの介護施設パート検索 |

### FT3-035: 春日部・日勤・クリニック
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_east | エリア確定 |
| 3 | `il_ft=clinic` → `il_ws=day` → `il_urg=info` | matching_preview。クリニック + 日勤 |
| **判定** | | ✅ クリニック日勤検索正常 |

### FT3-036: saitama_east 隣接エリア（chiba_tokatsu連携）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_east → 厳しい条件 → 0件 | フォールバック |
| 4 | 隣接エリア | ADJACENT_AREAS[saitama_east]=['saitama_south','chiba_tokatsu']。県境を越えてchiba_tokatsuに拡大 |
| **判定** | | ✅ 県境越え隣接エリア定義正常: 埼玉東部→千葉東葛 |

### FT3-037: saitama_east 区名重複防止
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_east → 病院 → 常勤 → urgent | matching_preview |
| 4 | 結果確認 | 東京都の同名市区（該当なしだが念のため）や千葉県の求人が混入しないこと |
| **判定** | | ✅ work_location LIKE '%越谷市%' 等の都市名フィルタで他県排除 |

### FT3-038: saitama_east 候補件数段階確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=saitama` | 埼玉県全体件数X |
| 2 | `il_area=saitama_east` | 東部件数Y ≦ X |
| 3 | `il_ft=visiting` | 件数Z ≦ Y |
| 4 | `il_ws=day` | 件数W ≦ Z |
| **判定** | | ✅ 候補件数の段階減少確認 |

---

## 埼玉・西部川越所沢（saitama_west）: 6件

### FT3-039: 所沢・常勤・病院（慢性期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=saitama` | 埼玉サブエリア5択 |
| 2 | `il_area=saitama_west` タップ | 「西部・川越・所沢ですね！」+ 候補件数。AREA_CITY_MAP[saitama_west]=['所沢市','川越市','入間市','狭山市','飯能市','日高市','坂戸市','鶴ヶ島市','東松山市','ふじみ野市','富士見市'] |
| 3 | `il_ft=hospital_chronic` → `il_dept=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。慢性期病院 |
| **判定** | | ✅ 西部11市のフィルタ正常 / 慢性期サブタイプフィルタ |

### FT3-040: 川越・パート・訪問看護
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_west | エリア確定 |
| 3 | `il_ft=visiting` → `il_ws=part` → `il_urg=good` | matching_preview。訪問看護 + パート |
| **判定** | | ✅ 訪問看護パート検索正常 |

### FT3-041: 入間・夜勤専従・病院
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_west | エリア確定 |
| 3 | `il_ft=hospital_acute` → `il_dept=any` → `il_ws=night` → `il_urg=urgent` | matching_preview。夜勤専従フィルタ |
| **判定** | | ✅ 夜勤フィルタ正常 |

### FT3-042: saitama_west 隣接エリア確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_west → 厳しい条件 → 0件 | フォールバック |
| 4 | 隣接エリア | ADJACENT_AREAS[saitama_west]=['saitama_south','saitama_north','tokyo_tama']。東京多摩への県境越え拡大 |
| **判定** | | ✅ 3方向の隣接定義正常: 南部・北部・東京多摩 |

### FT3-043: saitama_west 条件変更→エリアリセット
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-5 | saitama_west → 結果表示 | matching_preview |
| 6 | `matching_preview=deep` タップ（条件を変えて探す） | 条件変更画面。condition_change=area で il_area にリセット |
| 7 | `condition_change=area` タップ | phase→il_area。entry.area/areaLabel/prefecture 削除。最初からやり直し |
| **判定** | | ✅ 条件変更→エリアリセットフロー正常 |

### FT3-044: saitama_west こだわりなし最大件数
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_west | エリア確定 |
| 3 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。フィルタ最小 = 最大件数 |
| **判定** | | ✅ 最大件数表示確認 / dedup後5件 |

---

## 埼玉・北部熊谷（saitama_north）— 施設少数エリア: 6件

### FT3-045: 熊谷・常勤・病院（回復期）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1 | `il_pref=saitama` | 埼玉サブエリア5択 |
| 2 | `il_area=saitama_north` タップ | 「北部・熊谷ですね！」+ 候補件数。AREA_CITY_MAP[saitama_north]=['熊谷市','深谷市','本庄市','行田市','加須市','羽生市','鴻巣市','秩父市'] |
| 3 | `il_ft=hospital_recovery` → `il_dept=any` → `il_ws=twoshift` → `il_urg=good` | matching_preview。回復期フィルタ |
| **判定** | | ✅ 北部8市のフィルタ正常 / 施設少数エリアでの検索 |

### FT3-046: 秩父・日勤・クリニック（極少エリア）
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-2 | 埼玉→saitama_north | エリア確定 |
| 3 | `il_ft=clinic` → `il_ws=day` → `il_urg=info` | matching_preview。秩父は含むがsaitama_north全体で検索 |
| 4 | 結果確認 | 0件の場合: D1 facilitiesフォールバック → 0件なら通知導線 |
| **判定** | | ✅ 極少エリアでの検索 + フォールバックチェーン（D1 jobs → EXTERNAL_JOBS → 隣接 → D1 facilities → 0件導線） |

### FT3-047: saitama_north 0件→通知購読→ナーチャリング
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_north → 訪問看護 + 夜勤 → 0件 | 0件表示 |
| 4 | `nurture=subscribe` タップ | phase→nurture_subscribed or area_notify_optin。新着通知登録 |
| 5 | 確認 | 「条件に合う求人が見つかったらLINEでお知らせします」等のメッセージ |
| **判定** | | ✅ 0件→ナーチャリング導線の完全フロー |

### FT3-048: saitama_north 隣接エリア確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_north → 厳しい条件 | フォールバック |
| 4 | 隣接エリア | ADJACENT_AREAS[saitama_north]=['saitama_west','saitama_east']。西部・東部に拡大 |
| **判定** | | ✅ 北部の隣接定義: 西部・東部（東京方面には直接隣接しない設計） |

### FT3-049: saitama_north suggestRelaxation確認
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-3 | saitama_north → 回復期 + 日勤 → 結果1-2件 | suggestRelaxation発火 |
| 4 | 緩和提案 | 「エリアを広げると、もっと多くの求人が見つかるかもしれません」or「日勤のみ→こだわらないにすると選択肢が増えます」 |
| **判定** | | ✅ 少数結果時の条件緩和提案が適切 |

### FT3-050: saitama_north 全条件リセット→再検索
| Step | 操作 | 期待結果 |
|------|------|----------|
| 1-5 | saitama_north → 結果表示（0件 or 少数） | matching_preview |
| 6 | `welcome=see_jobs` タップ | phase→il_area。全条件リセット（area/areaLabel/prefecture/facilityType/workStyle/urgency全削除） |
| 7 | 今度は `il_pref=saitama` → `il_area=saitama_all` | saitama_all選択 = 埼玉県全域検索（D1_AREA_PREF: 埼玉県でprefectureフィルタ） |
| 8 | `il_ft=any` → `il_ws=twoshift` → `il_urg=urgent` | matching_preview。全域検索で件数増加 |
| **判定** | | ✅ サブエリア→全域への切り替え正常 / saitama_allのprefecture='埼玉県'フィルタ正常 |

---

## 検証サマリ

| エリア | 件数 | 重点検証項目 |
|--------|------|-------------|
| chiba_tokatsu | 7件 | サブエリア5択表示 / 全施設タイプ網羅 / 重複制限 / 候補件数段階表示 |
| chiba_uchibo | 6件 | 6市フィルタ / 0件導線 / 隣接エリア拡大 / 条件変更リトライ |
| chiba_inba | 6件 | 7市町フィルタ / 隣接エリア / こだわりなし / 候補件数段階 |
| chiba_sotobo | 6件 | 13市町広域 / 0件ハンドリング / D1 facilitiesフォールバック / suggestRelaxation |
| saitama_south | 7件 | 16市町フィルタ / **上尾市移動確認** / 自由テキスト検出 / 10件上限 |
| saitama_east | 6件 | 9市町フィルタ / 県境越え隣接(chiba_tokatsu) / 区名重複防止 |
| saitama_west | 6件 | 11市フィルタ / 3方向隣接(南部+北部+東京多摩) / 条件リセット |
| saitama_north | 6件 | 8市フィルタ / 0件→ナーチャリング / suggestRelaxation / 全域切り替え |

### 検出すべきバグパターン
1. サブエリア選択肢が表示されない（il_subarea phase遷移失敗）
2. AREA_CITY_MAPの都市名不足（新規追加都市の漏れ）
3. D1 SQL: 都市名LIKE検索で他県同名市区が混入
4. 0件時の導線切れ（Quick Reply非表示 or 遷移先不正）
5. 上尾市がsaitama_south以外に残存
6. 隣接エリア定義の漏れ（県境越え含む）
7. 候補件数が0表示 or 負数表示
8. 条件リセット後に前回回答が残る（entry.area等の未削除）
