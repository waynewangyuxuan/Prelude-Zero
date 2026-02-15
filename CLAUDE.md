# Memory

## Me
Wayne — 独立开发者/音乐爱好者，在做一个 LLM 驱动的音乐生成项目（个人项目，"玩票但认真玩"）。偏好创造性、创新性的产品。

## Project: Prelude Zero
**定位：** 用通用 LLM（Claude/GPT）作为音乐制作的大脑，通过 prompt engineering 而非模型训练，生成可控、有味道的音乐。
**核心理念：** LLM 提议 → 规则引擎把关 → 工具链渲染。
**阶段：** Phase 1 — 方法论探索（搞清楚什么 work、什么不 work）
**特色：** 探索古典 × 前卫摇滚的融合空间。不是 C-pop，是 Bach × Chopin × Pink Floyd。
**当前方向：** Tension-driven orchestration — 张力曲线驱动多声部编排。Pipeline: form → tension curve → orchestrator → melody_gen → MIDI

## Architecture (3 layers + LLM operator)
详见 `ARCHITECTURE.md`。核心：
| 层 | 职责 | 实现 |
|---|---|---|
| Compiler | 数学 → 音符，纯确定性 | core/scales.py, melody_gen.py, chords.py, midi_export.py, audio.py |
| Constraint Space | 规则即数学，LLM 在其中操作 | core/voice_leading.py, counterpoint.py, voicing.py |
| Metric Space | 量化"是什么"而非"好不好" | core/melody.py, tension.py, entropy.py |
| Orchestration | 张力曲线→多声部编排 | core/tension_curve.py, orchestrator.py |
| LLM (operator) | 翻译意图→指标范围，选择路径 | Claude prompt → metric targets |

**关键原则**: 指标是范围不是点, style 是 metric space 的子区域, 同样的范围不同路径 = 创造力

## Key Insights
- LLM 有音乐知识但缺乏多步推理能力（MusicTheoryBench ~25%）→ 外部规则引擎是必须的
- "味道"可以工程化：swing 偏移、velocity 曲线、timing 微调
- 现有项目要么是研究原型要么是 hackathon 实验，中间地带是空的
- Suno/Udio 是黑盒不可控，本项目追求每一步可见可调可迭代

### Experiment 001 发现 (2026-02-10)
- **Claude 选和弦的能力 OK**：Roman numeral 层面的巴洛克和声进行合理
- ~~**Voicing 是短板**~~ → **已解决**：`core/voicing.py` 向量引擎，穷举搜索 + 约束过滤，0 errors
- **关键分层**："选什么和弦"（LLM 擅长）vs "怎么排列声部"（需要规则引擎）
- Pipeline 端到端跑通：Roman numeral → music21 → pretty_midi → MIDI → WAV

### Voicing Engine (core/voicing.py) — 2026-02-10/11
- **核心思想**：Tymoczko's Geometry of Music — chord = Z^n 中的点, voice leading = displacement vector
- **v2 算法**：enumerate all voicings → hard constraints → filter parallels (full chord) → min L1 distance → 0 errors 但"平淡"
- **v3.1 算法**：multi-objective scoring = L1×5 + tendency×15 + contrary×3 + melodic×4
  - `_chromatic_pull`: 半音邻居检测 → tendency tone 方向
  - `_tendency_score`: 两级检查——target present in chord? + direct resolution bonus
  - `_contrary_score`: 外声部反向运动偏好
  - `_melodic_score`: 各声部旋律间隔质量（tritone/7th = 重罚）
- **v3.1 结果**：0 errors, tendency 71%, contrary 82%, voice independence 0.363
- **已知天花板**：sorted-position voice tracking 无法保证每个声部的 tendency 都在同一声部解决（需要 voice identity tracking）
- **架构**：SATB 固定 4 声部, 和弦不够用 doubling 补

### Experiment 002 发现 (2026-02-11, updated 02-13)
- **完整赋格 0 errors**：**350 notes** (v3), 26 bars, 78s, 8 sections, **0 counterpoint errors**, 97 warnings
- **Subject + Countersubject 配合 OK**：反向运动 + 节奏互补，0 errors
- **赋格 = 代数结构 + 手工打磨**：Subject transformations 可靠，但 free counterpoint 需迭代修复
- **Tonal answer 两区域设计 work**：head zone swap + tail zone real transposition，F#4 leading tone 保留
- **Stretto v3 (free counterpoint)**：
  - Layer 1: 2 subject entries as structural backbone (Alto: C maj, Soprano: +7 G maj)
  - Layer 2: 2 FREE voices replacing subject entries (Tenor: ascending chromatic w/ diminution 27 notes, Bass: chromatic pedal G/Ab/F# + staggered ascending chromatic 16 notes)
  - Layer 3: FREE tails after subject entries end (Alto: chromatic arch 15 notes, Soprano: ascending chromatic 8 notes)
  - 8 parallel errors → fixed with oblique motion, pitch holds, staggered timing → 0 errors
  - **结果 vs v2**: combined +32% (0.182→0.240), density +88%, registral +55%, pitch H 2.783→3.113 bits
- **Validate→fix→validate 循环有效**：从 9 errors 迭代到 0，oblique/contrary motion 是万能修复术
- **调性走向 C→G→Am→F→C**：Exposition→Episodes→Middle Entries 的调性规划合理

### Fugue Engine (core/fugue.py + core/counterpoint.py) — 2026-02-11
- **core/fugue.py**: Subject 定义 + 5 种变换 + tonal/real answer + exposition assembly + quality evaluation
- **core/counterpoint.py**: parallel 5ths/8ves, direct 5ths/8ves, consonance on strong beats, voice crossing, melodic intervals, gap-fill
- **完整赋格结果**: 4 voices, **350 notes** (v3), 0 errors, 97 warnings

## Open Questions
- ~~ABC vs musicpy vs pretty_midi 哪个做 LLM 输出格式最好？~~ → 决定用 Python 代码直接生成（music21 + pretty_midi）
- Claude vs GPT-4o 在音乐生成上的优劣？
- ~~Humanize 参数怎么调才像真人？~~ → ✓ 已解决：core/humanize.py 三层引擎，BAROQUE preset
- 华语 ballad 怎么 prompt 出好的 Royal Road 进行？
- Synthesizer V vs ACE Studio？
- GarageBand 够用还是需要 Logic？
- ~~Voicing 算法怎么改进？~~ → ✓ 已解决：core/voicing.py v3.1
- ~~Countersubject 设计~~ → ✓ 已完成：反向运动 + 节奏互补，0 errors
- ~~Episode generation~~ → ✓ 已完成：subject 片段 sequential motifs，3 episodes
- ~~Stretto~~ → ✓ 已完成：v3 free counterpoint (2 subject entries + 2 free voices + free tails), 0 errors, 350 notes
- ~~Humanize~~ → ✓ 已完成：core/humanize.py 三层引擎 (velocity/timing/articulation)
- ~~Pink Floyd 方向~~ → ✓ 已完成初步调研：7 首 MIDI 分析, Phrygian 主导, 三风格 metric profiling 完成
- ~~Melody Metrics~~ → ✓ 10 维指标体系 (Easy 6 + Medium 4), 三风格 benchmark 完成
- ~~融合方向~~ → 三风格 fusion zone 已识别, 暂 hold
- **NEW**: Compiler 升级路线完成 — Scale Engine + Melody Generator → 24/24 metrics pass

### Scale Engine (core/scales.py) — 2026-02-14/15
- **17 scale templates**: church modes (Ionian→Locrian) + pentatonics + blues + symmetric
- **Scale class**: snap(), step(), contains(), chromatic_neighbors(), triad(), seventh(), transpose()
- **from_name()** 构造器: `from_name('E', 'phrygian')` → Scale object
- 所有 melody generation 和 chord generation 共用同一个 pitch vocabulary

### Melody Generator (core/melody_gen.py) — 2026-02-14/15
- **核心思想**: 不是一个一个音写然后检查指标，而是从指标目标直接生成
- **StyleTarget dataclass**: 14 个参数 (density, duration_cv, step_ratio, direction_change_prob, chromaticism, repetition, ...)
- **4 步算法**: rhythm backbone → pitch random walk → phrase shaping → motif repetition
- **三个预设**: BACH_TARGET, CHOPIN_TARGET, FLOYD_TARGET (从 Experiment 005 校准)
- **关键校准发现**:
  - chromaticism metric 是非线性的 (unique chromatic PCs / total unique PCs)，per-note probability 需要 ×0.15
  - rhythm spread 用 `geomspace(shortest, longest, n_types)` 控制，`max_ratio = 2^(cv×3)`
  - repetition transposition 必须 snap 回 scale，否则引入意外半音化

### Experiment 006 发现 (2026-02-14/15) — Style Generation
- **v1 (hand-composed)**: Bach 6/8, Chopin 4/8, Floyd 4/8, cross-style diagonal broken
- **v2 (engine-generated)**: **Bach 8/8, Chopin 8/8, Floyd 8/8, all ★ on diagonal**
- **24/24 metrics within 2σ** of Experiment 005 reference distributions
- **核心洞察**: metric-guided generation >> hand-composition for style matching
- **Audio Route B 决定**: MIDI 是真正的 deliverable, additive synth 只用于 preview, 在 GarageBand 渲染听
- Bach BPM: 108→92 (per Wayne's feedback: "太快了有点")

### Tension Curve Engine (core/tension_curve.py) — 2026-02-15
- **核心思想**: 在作曲前定义张力曲线（prescriptive），不是事后分析（diagnostic）
- **PieceForm**: sections list → Section(name, beats, tension, transition)
- **TensionCurve**: per-beat array + .at() .section_at() .mean_tension() .section_range()
- **Smooth interpolation**: cosine (ease in/out), linear, sudden
- **三个 preset**: long_form_build (Floyd), arch_form (Chopin), ramp_form (Bach)

### Orchestrator Engine (core/orchestrator.py) — 2026-02-15
- **核心思想**: 张力曲线驱动多声部编排，一个引擎生成完整的多声部 MIDI
- **tension_to_target()**: [0,1] tension × base_style × role → StyleTarget
  - lead: density/range/chromaticism 随 tension 增长
  - counter: 与 lead 互补，密度较低，pitch offset 避免碰撞
  - bass: 稀疏，root-oriented，wider intervals
  - pad: 持续和弦，频率随 tension 变化
- **VoicePlan**: 滞回门控 (entry_tension ≠ exit_tension)，防止 threshold 附近频繁开关
- **arrange()**: plan_voices → per-section generate → assemble MIDI → humanize
- **Voice palette 可替换**: 不同风格换不同 GM program + entry/exit thresholds

### Experiment 007 发现 (2026-02-15) — Orchestrator Validation
- **3m16s Floyd long-form piece**: 4 voices, 454 notes, 6 sections
- **Lead melody 8/8 Floyd metrics within 2σ**
- **Density 正确跟随 tension curve**: Intro 0.47 → Build 0.62 → Dev 0.79 → Climax 0.92 → Descent 0.69 → Fade 0.47
- **Progressive layering**: solo → +bass → +pad → +counter → strip back
- **melody_gen.py density fix**: 将 n_notes = density × beats 前置，duration 按比例缩放填满 beats
- **Backward compatible**: Experiment 006 仍然 24/24 pass

## Phase 2 方向：从 "avoid errors" 到 "optimize beauty"

### 三个数学方向（2026-02-12 确定）
1. **Tension Curve（张力模型）** ← 当前方向，diagnostic 阶段完成
   - 核心洞察：音乐 = 张力和释放。我们缺的不是规则，是方向感
   - T(t) = w₁·harmonic + w₂·dissonance + w₃·melodic + w₄·registral + w₅·density
   - 权重: harmonic=0.30, dissonance=0.25, melodic=0.20, registral=0.10, density=0.15
   - Harmonic tension: DFT f₅ magnitude + phase distance from expected key
   - Dissonance: interval-class roughness (Hindemith/Huron: m2=1.0, tritone=0.8, M2=0.3, m3=0.2, M3=0.15, P4=0.05)
   - **Experiment 003 发现 (2026-02-12, updated 02-13)**:
     - **核心问题：张力峰值在错误的位置**
     - Prelude: 峰值在 beat 52 (Section C: Tonicize V) 而非 Section F (Dom pedal)
     - Fugue: 峰值在 beat 41.5 (Episode 1) 而非 Stretto
     - **Stretto v3 (free counterpoint) 进展**:
       - combined: 0.182 → **0.240** (+32%), now 3rd highest section (was 2nd lowest)
       - density: 0.215 → **0.404** (+88%) — diminution + 4-voice free writing
       - registral: 0.299 → **0.462** (+55%) — chromatic bass line widened spread
       - pitch entropy: 2.783 → **3.113** bits (+12%, in "adventurous" sweet spot)
       - Distance from ideal: 0.236 → **0.209** (-10%)
     - Prelude variance 只有 0.094 — 太平 → 缺乏对比
     - Prelude dissonance 太低 (mean 0.091) — 太"安全"
   - 下一步: 进一步 boost stretto (secondary dominants, augmented 6ths) 或 reduce episode tension

2. **Information-Theoretic Balance** ← ✓ 已完成基线测量 (2026-02-13)
   - 好音乐 entropy 在甜区：太低=无聊，太高=随机
   - Shannon entropy of pitch transitions、rhythm patterns
   - **Fugue overall pitch transition H = 1.79 bits** — below sweet spot (2.3-3.2)
   - **Stretto v3 pitch H = 3.113 bits** — "adventurous" zone, up from 2.783 (v2)
   - **Cross-voice MI = 0.719** — moderate voice independence
   - Free counterpoint pushed stretto into sweet spot, validating the approach

3. **Voice Leading Optimization on Orbifold**（待做）
   - Tymoczko: n-note chord = point in T^n/S_n
   - 从"最短距离"进化到"服务于 tension curve 的最优路径"
   - 把 tension curve 作为 cost function 的一部分

### Tension Engine (core/tension.py + core/tension_budget.py) — 2026-02-12
- **core/tension.py**: 5维张力函数 T(t) = Σ wᵢ·Tᵢ(t)
  - `compute_tension()`: MIDI → TensionCurve (per-beat 5维张力)
  - `target_curve()`: 理想曲线生成 (prelude/fugue/arch/custom)
  - `summarize()`: 人类可读报告
- **core/tension_budget.py**: 创作引擎集成
  - `TensionBudget`: 每 section → target per dimension
  - `tension_voicing_scorer()`: extra_scorer for voicing engine (偏好匹配 dissonance/registral 目标的 voicing)
  - `suggest_chords()`: 根据 harmonic tension 目标推荐和弦类型
  - `density_guidance()` / `melodic_guidance()`: 节奏密度和旋律跳进建议
  - `fugue_budget()` / `prelude_budget()`: 预设目标 (Stretto peak = 0.65, Dom pedal peak = 0.70)
- **核心发现**: 张力峰值在错误的位置 — 诊断有效，但修复需要 compositional changes (free counterpoint, chromatic passing tones, diminution)

### Entropy Engine (core/entropy.py) — 2026-02-13
- **核心思想**: Shannon entropy 量化音乐的 predictability vs surprise
- **测量维度**: pitch transition H, rhythm IOI H, interval-class H, cross-voice MI
- **windowed entropy**: per-beat entropy over sliding window (default 8 beats)
- **甜区**: 2.3-3.2 bits (Bach reference), <2.3 = too predictable, >3.2 = too random
- **关键发现**: Fugue overall H=1.79 (too predictable), but stretto v3 = 3.113 (adventurous)
- **EntropyProfile dataclass**: per-voice metrics + global summaries + windowed time series
- **集成**: `compute_entropy(pm, bpm)` → EntropyProfile, `summarize()` → human-readable report

### Melody Metrics Engine (core/melody.py) — 2026-02-13
- **核心思想**: 单声部旋律的 6 维度量化评估 (Easy tier)
- **6 个指标**: pitch range/tessitura, interval distribution, pitch entropy, rhythm entropy, rhythm density, tonal clarity
- **MelodyProfile dataclass**: 18 个字段, `genre_fit()` 检查是否在 genre 范围内
- **K-S Key Finding**: Krumhansl-Schmuckler profiles (major + minor) → tonal clarity score
- **三 Genre 校准**: baroque / romantic / pop, 从 15 首参考旋律 benchmark 校准
- **Benchmark 结果 (Experiment 004)**:
  - 15 首参考旋律 (5 baroque, 5 romantic, 5 pop), 手工编码 MIDI pitch/onset/duration
  - 校准后 9/9 melodies pass (8 at 10/10, 1 at 9/10)
  - **最强 genre 区分器**: rhythm_density (baroque 3.08, romantic 1.51, pop 1.28)
  - **其次**: direction_change_ratio (baroque 0.55, romantic/pop ~0.27)
  - **最弱**: pitch_entropy (all genres ~2.3-2.6, overlap too much)
  - transition_entropy 已移除 (short melodies 不可靠)
- **Architecture Layer**: Metric Space — measures WHAT melody is, not whether it's good

### Experiment 005 发现 (2026-02-14) — Three-Style Metric Profiling
- **10 维 metric engine** 完成: Easy 6 + Medium 4 (contour, mode, duration CV, repetition)
- **真实 Pink Floyd MIDI** 分析: 7 首, 12 tracks, 与 archetype 差异巨大
- **Style Signatures** (effect size > 1.5σ):
  - Bach: 零半音化(-3.3σ), motor rhythm(dur CV -2.2σ), 高密度(+2.1σ)
  - Chopin: 长弧线(dir change -2.3σ), 持续方向(run len +1.9σ), through-composed(rep -1.7σ)
  - Floyd: 极高时值对比(dur CV +2.8σ), 巨大音域(+2.8σ), 节奏多变(rH +2.7σ), 高重复(+1.6σ)
- **调式**: Floyd = **Phrygian 主导** (5/12), Bach = Aeolian, Chopin = Phrygian/Lydian mix
- **Fusion zone**: density [1.1, 2.0], step ratio [0.53, 0.93], tonal clarity [0.68, 0.82]
- **不重叠维度**: pitch range, duration CV, chromaticism, mean run length
- **核心洞察**: 融合不是取交集，是从每种风格取不同维度 (Bach motivic economy + Chopin phrase arc + Floyd temporal sparseness + Phrygian modality)

### Humanize Engine (core/humanize.py) — 2026-02-11
- **三层架构**: velocity shaping + timing micro-offsets + articulation
- **Velocity**: beat weights (1强3次2/4弱) + phrase arc (bell curve per section) + subject prominence + jitter
- **Timing**: Gaussian σ=8ms + voice bias (bass early -5ms, soprano late +3ms) + cadence rubato
- **Articulation**: non-legato 85% (baroque) / 90% (prelude arpeggios) + stepwise legato + phrase-end linger
- **Presets**: BAROQUE (detached, moderate) / ROMANTIC (legato, wider dynamics)
- **ProminenceWindow**: 标记 subject entry 时间段，该声部 +10 velocity
- **A/B 验证**: 赋格 velocity range 5→39, timing σ≈10ms, dur ×0.92; 前奏曲 velocity range 15→27

## Terms
| Term | Meaning |
|------|---------|
| Royal Road | IV△7–V7–iii7–vi，东亚流行最典型和声进行 |
| POP909 | 909 首华语流行数据集（NYU Shanghai/Music X Lab） |
| Humanize | 给 MIDI 加入人性化微偏移（timing、velocity） |
| voice leading | 声部进行——各声部从一个和弦到下一个和弦的连接方式 |
| ABC notation | 文本格式的乐谱表示，LLM 友好 |
| MusicTheoryBench | ChatMusician 提出的音乐理论推理基准测试 |
| tacit knowledge | LLM 内化的隐性知识，适合处理未形式化的音乐领域 |

## Preferences
- 中英文混用沟通
- 偏好创造性、创新性的方向
- 不搭框架、不写通用 API、不做 multi-agent、不优化性能
- 追求最短路径：脑中想法 → 能听的歌
- 实验导向：每次实验记录 Input / Output / Judgment
