# rust-ffmpeg Skill 最佳实践深度审查（Claude↔Codex Evidence Protocol）

**日期**: 2026-07-27　**快照**: git `0f46ec7`　**协议**: deep-review v8 Evidence Protocol（4 维并行 Codex round-1 + Claude 逐前提独立复核）
**Ledger**: `claudedocs/ledgers/ep-20260726T183134.ledger.jsonl`（9 事件，hash 链校验通过，`ledger-replay` 零错误）
**Exit 分布**: 23 个 finding CERTIFIED_SCOPE_ABSOLUTE / 2 个 PROVISIONAL_SCOPE_BOUNDED（TE-4、UX-1：依赖未文档化的语义触发器行为，无法机械验证）

## 一、裁决总表（Claude 原主张 × Codex 裁决）

| # | Claude 主张 | Codex 裁决 | 关键修正 |
|---|---|---|---|
| C1 | description 602 词超标，压到 ~150 词 | **partial** | 数字全复现；但"Layer 2 兜底"论证**无效**（规范：when-to-use 必须全在 description，body 触发后才加载，误漏不可恢复）。替代：分阶段，先 0 损失清理，终点 250-300 词 + 回归测试 |
| C1b | 根因是逐版本追加惯例 | **partial** | 初版已 208 词/15 组；(27)-(32) 仅占 20.8% 字符。停止追加成立，"根因"不成立 |
| C2 | 删 `artifacts/analysis-report.md` | **support** | 加固：git 已跟踪 + README `cp -r` 部署路径会装进用户机器；0.12 旧数据与现行表冲突 |
| C3 | 删 `_keywords_standard.md` | **support** | 死条目 11 → **12+1**（我误判 2 个、漏数 3 个）；文件第 3 行自认 maintainer 文档；listed sidecar 文件连初版树里都不存在；28/55 文件违反其自订规则 → 删除优于修复/搬迁 |
| C4a | Best Practices 全部压一行+链接 | **support**(事实) / **partial**(方案) | 三条 0.16 bullet 重复度 12/12、7/7、全簇确认；但 agent-ux 矩阵：**11 条 must-keep-inline / 6 条 safe-to-compress**（keyframe 事实在通用路由目标中 0 命中；错误策略/RAII 断言全库无处可寻） |
| C4b | 版本表 ×3、#246 考据重复 | **partial** | 实为 **2 表 + 1 散文**；#246/EXIF 只在 SKILL.md 一处（无重复）。同步负担实锤：每版 12-13 个文件带精确版本号 |
| C4c | 例子 6 砍后 3 个 | **partial** | 应砍 **1/3/5**；例 6 含表格没有的 runtime-gate 决策（缩短保留）；2/4 各有独特信号 |
| C4d | Layer-2 行内解释全部清除 | **partial** | 行 48/60/61 → link-first；行 66/68 缩短；行 43/53/64 的标签是真路由判别词，保留 |
| C5 | 30 文件缺 ToC；debugging.md 拆分；18 断锚 | **support** | 30 个精确清单一致（T3 后剩 29）；18 断锚清单与我逐文件一致（跨模型独立复现）；debugging.md 1,463 行/4,558 词，双路由，先拆 Detection & Measurement |
| C6 | transcoding.md 命名撞车，改名或合并 | **partial** | **合并被否**（0 相同代码块、Jaccard 0.29、合并 940 行超 800 上限）；改名 + 挪走越界的 "Basic Format Conversion" 段 + 原子迁移 3 处入链 |
| C7 | description 省 ~1k/会话；body 3.2k→2.2k 词省 ~1.3k | **partial** | description ~0.93-1.03k ✓；body 实为 **2,613** 词（3,226 是整文件），C4 编辑实测省 429 词 ≈ **0.57-0.88k** tokens |
| P2 | 两级引用结构可辩护 | **partial** | 23/24 两跳可达（操作上成立）；唯一真孤儿是 _keywords_standard.md；建议补紧凑直链清单 |

**我被修正的 7 处**：Layer-2 兜底论证、追加根因、死条目计数、版本表计数、body 词数、C4 节省额、砍例子的选择。**Codex 被我复核后全部前提成立**（每个决定性前提均以我方独立工具运行复现：force_key_frames 0 命中、RAII 断言 0 命中、body=2613、bullets=18、初版 208 词、docx 例 51 词、散文非表格等）。

## 二、Codex 独有新发现

1. **UX-7 路由死角**（medium）：description 含 `avformat_find_stream_info` 能触发，但 Layer-2 第 59 行不含它——触发后反而无字面路由；`AVSEEK_SIZE` 全 description 缺失（存量缺口）。Layer-2 关键词重叠（crop/watermark/metadata/capture 各出现在 2 行）且无优先级规则。→ 建议：补 C-API/FFI 行 + "load all applicable references, prefer the most specific row" 一句话规则。
2. **DD-7 逐字节重复**（low）：8 个 sidecar 文件的依赖块 sha256 相同；`ffmpeg_sidecar/core.md:29-40` ≡ `ffmpeg_sidecar.md:130-141`；`video_transcoding.md:23-34` ≡ `hardware_acceleration.md:24-35`；`ez_ffmpeg.md:10`（"New in 0.16" 段，0f46ec7 引入）与三个详细参考重复 → 压成链接式特性索引。
3. **TE-5 零损失清理**：266 字符（编号脚手架 151 + 引号 56 + 标签 21 + 重复短语 38）可立即移除，词表逐 token 验证无损；另 111 字符版本注记待触发测试。

## 三、修订后执行计划 v2（依赖顺序）

**Phase 0 — 纯删除（零风险）**
1. 删 `plugin/skills/rust-ffmpeg/artifacts/analysis-report.md`（连同空目录）
2. 删 `references/_keywords_standard.md`（先于 Phase 1，其中 2 处 transcoding.md 引用随之消失）
3. description 做 TE-5 的 266 字符词法清理（不动任何触发词）

**Phase 1 — 机械修复**
4. 修 18 个存量断锚（6 文件清单在 DD-5/P-DD5-4）
5. 为 29 个 >100 行无 ToC 文件补 ToC；cli_compat.md 的 ToC 上移
6. T6 原子改名：`scenarios/transcoding.md` → `pipelines_multi_output.md`，同一提交更新 SKILL.md:43、modern_codecs.md:21、subtitles.md:12，"Basic Format Conversion" 段挪去 video_transcoding.md，改后 grep 旧路径为零

**Phase 2 — 内容收敛（按矩阵，非一刀切）**
7. Best Practices：6 条 safe-to-compress 压一行+链接；11 条 must-keep 保留紧凑守卫句（守卫句保留"会静默出错的那个事实"，机制细节归 references）
8. 例子砍 1/3/5，保留 2/4/缩短的 6
9. Layer-2：行 48/60/61 link-first，66/68 缩短，43/53/64 标签保留；新增 UX-7 的 C-API/FFI 行 + 优先级一句话
10. SKILL.md:116 压缩：保一行兼容摘要 + `links="ffmpeg"` 冲突警告；bindgen 机制/legacy-pin/#246 考据沉入 installation.md；新增 version/build Layer-2 行
11. `ez_ffmpeg.md:10` 压成链接式特性索引
12. debugging.md 先拆出 Detection & Measurement 子文件，Layer-2 行 50 直指，7 处入链原子迁移

**Phase 3 — 有测试门槛（PROVISIONAL 项）**
13. description 601 → 250-300 词：先固化 UX-1 的 16-query 回归语料（可扩充），公布替换文本逐条对照，记录任何有意接受的 miss；保留 C-API/FFI、capture、loudness、frame/packet export、CLI translation、per-stream encoder、modern streaming、bitstream filter 八类 sentinel
14. 终止逐版本追加惯例：新触发词必须替换/合并现有文本，并在语料上证明增量价值

**预期收益（经修正的数字）**：description ~0.62-0.72k tokens/会话（250-300 词方案）或全量 ~0.93-1.03k（150 词方案，有 recall 风险）；body ~0.57-0.88k tokens/触发；包内消除 2 个多余文件与 3 处逐字节重复。

## 附：执行记录（2026-07-27，用户批准全量 0-3）

| Commit | 内容 |
|---|---|
| `5ba5523` | Phase 0：删 analysis-report.md + _keywords_standard.md |
| `325a312` | Phase 1：18 断锚修复；transcoding.md → pipelines_multi_output.md 原子迁移（3 入链 + Basic Format Conversion 段替换为指针） |
| `47ffa97` | Phase 2：Best Practices 按 12/6 矩阵收敛；例子砍 1/3/5；Layer-2 加 C-API 行 + version/build 行 + 优先级规则、行 48/60/61 link-first；#246/bindgen 考据沉入 installation.md；ez_ffmpeg.md New-in-0.16 压成链接索引；拆出 scenarios/detection_analysis.md（debugging.md 留 stub 保旧深链）；29 文件补生成式 ToC；cli_compat ToC 上移 |
| `b6c5ac9` | Phase 3：description 601→**239 词**（~490 tokens，省 ~745/会话），25/25 语料通过；claudedocs/skill-trigger-regression-corpus.md 固化门槛；YAML 注释钉死 ≤300 词预算并终止追加惯例 |

**与计划的偏差**（如实记录）：Phase 0 的 266 字符词法清理被 Phase 3 全量重写吸收（同分支落地，避免两次改写同一行）；description 终稿 239 词（低于 250-300 目标带下沿，语料 25/25 全过，更精简且无损）；ToC 修复中不存在的章节条目替换为文件内真实邻近章节而非发明内容。终检：57 文件 0 断链 0 断锚；SKILL.md 184→181 行 / 3,226→2,552 词。

## 四、开放假设（诚实边界）

- TE-4/UX-1：触发召回结论均为推理（skill-creator 只规定加载时机，不规定匹配算法）；Phase 3 的回归语料是把它转成可测的唯一途径。
- 协议注记：本次为 Phase-2 手工编排（stall_k 未触发，全部 finding 一轮收敛；无 arbitration）。Claude 侧 ledger 粒度为按维度合并事件，逐前提复核记录在 `independent_checks` 字段。
