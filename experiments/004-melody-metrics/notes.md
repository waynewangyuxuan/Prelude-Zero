# Experiment 004: Melody Metric Dimensions — Literature Survey

**Date:** 2026-02-13
**Goal:** 确定用哪些数学维度来衡量单声部旋律的质量，从学术文献中提取已有的、可计算的指标，为 Metric Space 打地基。

## 核心问题

给定一条 16 小节的单声部旋律，我用哪些数学维度来判断它"能不能听"？每个维度的定义是什么？range 是什么？这些维度合在一起能不能区分"好听"和"不好听"？

---

## 一、已有的计算框架

### 1.1 FANTASTIC Toolbox (Müllensiefen, 2009)

最全面的旋律特征提取工具，实现了约 32 个 summary features + m-type repetition features + corpus density features，共约 82 个特征。

**分类：**
- Pitch features: range, mean, std, entropy of pitch class distribution
- Interval features: mean interval size, direction changes, step/leap ratio
- Contour features: Huron's 9 contour classes, global direction
- Duration features: mean IOI, IOI entropy, duration ratio patterns
- Tonality features: key clarity (Krumhansl-Schmuckler), tonal center
- Repetition features: m-type frequencies (短旋律-节奏片段的重复率)

**关键发现：** 仅用 pitch range + entropy 两个特征就能以接近 100% 准确率区分"成功"和"不成功"的歌。

### 1.2 IDyOM — Information Dynamics of Music (Pearce, 2005)

基于 variable-order Markov model 的旋律预测模型。逐音符计算 Information Content (surprise) 和 Entropy (uncertainty)。

**核心概念：**
- **Information Content (IC)**: IC(x) = -log₂ P(x | context)。一个音符在上下文中越出乎意料，IC 越高。
- **Entropy**: H = -Σ P(x) log₂ P(x)。当前位置的总体不确定性。高 entropy = 所有续音都差不多可能。
- **Long-term model (LTM)**: 从大语料库学到的统计规律（如"旋律多以级进为主"）
- **Short-term model (STM)**: 从当前曲子里动态学到的局部规律
- **Combined**: geometric mean, weighted by entropy

**验证：** 解释了听者 pitch expectation 83% 的方差。还成功预测了 EEG electrophysiological 反应。

**对我们的意义：** 这就是"这个音符好不好"的逐音符评分。IC 过高 = 太 random，IC 过低 = 太无聊。

### 1.3 Narmour's Implication-Realization Model (1990)

基于 Gestalt 原则的旋律期望模型：
- **A + A → A**: 两个相似的间隔 → 期望继续（inertia）
- **A + B → C**: 两个不同的间隔 → 期望改变（reversal）

**底层原则（Schellenberg 1997 简化版，5 个变量）：**
1. **Registral direction**: 小间隔后期望同方向，大间隔后期望反方向
2. **Intervallic difference**: 期望下一个间隔与当前相似
3. **Registral return**: 期望回到前一个音高附近
4. **Proximity**: 期望小间隔（步进）
5. **Consonance**: 期望协和音程

**对我们的意义：** 可以逐音符计算"期望满足度"。太满足 = 无聊，太违反 = 不自然。

### 1.4 Lerdahl's Tonal Tension Model (2001)

四个组件计算调性张力：
1. **Hierarchical structure**: prolongational tree (哪些音是结构音，哪些是装饰)
2. **Tonal pitch space distance**: 音高、和弦、调性之间的距离
3. **Surface dissonance**: 声学粗糙度
4. **Voice-leading attraction**: 旋律吸引力（tendency tones）

**对我们的意义：** 虽然主要面向和声，但 component 2 和 4 可以用于单声部——旋律音对 tonal center 的距离。

### 1.5 Simonton's Melodic Originality (1984)

对 15,618 个古典音乐主题的统计分析：
- 计算 two-note transition probability（从语料库统计）
- **Originality = 1 - mean(transition_probability)**
- 用的间隔越 rare，originality 越高

**关键发现：** melodic fame 是 originality 的正线性函数。不是倒 U。更原创的旋律更 famous。

**Berlyne 的修正：** 但 listener preference 对 complexity 是倒 U 的——太简单无聊，太复杂混乱。Sweet spot 在中间。

**对我们的意义：** originality 可以直接算。但 originality ≠ quality。Quality ≈ originality within the sweet spot。

### 1.6 Huron's Statistical Learning Model (Sweet Anticipation, 2006)

**关键统计规律：**
- **Pitch proximity**: 旋律多以小间隔（级进）为主
- **Step inertia**: 级进后期望继续同方向
- **Step declination**: 旋律整体有下降趋势
- **Melodic regression**: 大跳后回归到平均音高（regression to mean）
- **Post-skip reversal**: 大跳后期望反方向（其实是 regression to mean 的副效果）
- **Melodic arch**: 乐句呈拱形（先升后降）

**对我们的意义：** 这些是可以直接计算的统计特征。违反这些规律太多 = 不自然。

---

## 二、单声部旋律指标维度

从文献中提炼出以下可计算的维度，按照我们架构的 Metric Space 组织：

### Dimension 1: Pitch Range & Tessitura（音域）
- **定义**: max_pitch - min_pitch (semitones)
- **扩展**: mean_pitch (整体偏高还是偏低), std_pitch (分散程度)
- **数学**: range = max(P) - min(P); tessitura_center = median(P)
- **Genre ranges**:
  - Baroque: 通常 12-19 semitones (一到一个半八度)
  - Romantic: 常超过 24 semitones (两个八度)
  - Pop: 通常 10-15 semitones (vocal range 限制)

### Dimension 2: Interval Distribution（音程分布）
- **定义**: 连续音符之间的间隔大小和方向的分布
- **数学**: intervals = [P(n+1) - P(n) for n in melody]; step_ratio = count(|i| ≤ 2) / total
- **子指标**:
  - step_ratio: 级进占比（步进 vs 跳进）
  - mean_abs_interval: 平均间隔大小
  - leap_ratio: 大于 P5 的跳进占比
  - direction_change_ratio: 方向改变的频率
- **Genre ranges**:
  - Baroque: step_ratio ≈ 0.65-0.80 (级进为主，但有装饰音造成的小跳)
  - Romantic: step_ratio ≈ 0.45-0.65 (更多大跳，表达 yearning)
  - Pop: step_ratio ≈ 0.60-0.75 (vocal friendly)

### Dimension 3: Contour Shape（旋律轮廓）
- **定义**: 旋律的整体起伏形态
- **数学**: Huron's 9 contour classes, 或简化为 ascending/descending/arch/inverted-arch
- **子指标**:
  - global_direction: (last_pitch - first_pitch) / range
  - arch_score: correlation with idealized arch shape
  - phrase_final_descent: 乐句末尾是否下降（跨文化的统计规律）
- **文献支持**: Huron 发现拱形（先升后降）在各文化中最普遍

### Dimension 4: Pitch Entropy（音高熵）
- **定义**: 音高使用的不确定性
- **数学**: H(pitch) = -Σ P(pc) log₂ P(pc)，pc = pitch class (0-11)
- **扩展**:
  - zeroth-order H: 音高本身的分布
  - first-order H: bigram transition 的条件熵（Simonton/IDyOM）
  - windowed H: per-beat entropy over sliding window
- **Sweet spot**: 2.3-3.2 bits (我们从 Bach 实验中得到的)
- **注意**: 单声部的 sweet spot 可能跟多声部不同，需要重新标定

### Dimension 5: Rhythmic Entropy（节奏熵）
- **定义**: 节奏模式的不确定性
- **数学**: H(IOI) = -Σ P(ioi) log₂ P(ioi)，IOI = inter-onset interval (量化到 16th note grid)
- **子指标**:
  - rhythmic_density: notes per beat
  - syncopation: off-beat onsets ratio
  - duration_variety: how many different note values used
- **Genre ranges**:
  - Baroque: moderate H, regular beat patterns, 多 8th/16th
  - Romantic: higher H, rubato, 节奏更自由
  - Pop: lower H, repetitive patterns, hook 需要 rhythmic consistency

### Dimension 6: Melodic Originality（旋律独创性）
- **定义**: 旋律使用 rare interval transitions 的程度
- **数学**: originality = 1 - mean(P(interval_n | interval_{n-1})) (from reference corpus)
- **Berlyne sweet spot**: inverted-U between originality and preference
- **依赖 reference corpus**: 不同 genre 需要不同的 baseline

### Dimension 7: Expectation Profile（期望曲线）
- **定义**: 逐音符的"意外程度"曲线
- **数学**: IC(n) = -log₂ P(pitch_n | context)，via IDyOM or Markov model
- **子指标**:
  - mean_IC: 整首旋律的平均意外程度
  - IC_variance: 意外程度的波动（好音乐有对比——predictable passages + surprise moments）
  - IC_climax_position: 最大 surprise 出现在哪里（应该在高潮段）
- **与 tension curve 的关系**: IC 高的位置通常也是 tension 高的位置

### Dimension 8: Tonal Clarity（调性清晰度）
- **定义**: 旋律暗示的调性有多明确
- **数学**: Krumhansl-Schmuckler key-finding algorithm → correlation with best-fit key profile
- **子指标**:
  - key_clarity: max correlation (0-1)
  - key_ambiguity: 1st vs 2nd best key correlation 的差距
  - chromaticism: non-diatonic pitch class ratio
- **Genre ranges**:
  - Baroque: key_clarity 高 (0.8+)，调性明确
  - Romantic: key_clarity 中等 (0.5-0.8)，更多 chromaticism
  - Pop: key_clarity 高 (0.8+)，调性简单直接
  - Atonal: key_clarity 低 (<0.3)

### Dimension 9: Phrase Structure（乐句结构）
- **定义**: 旋律的分句和呼吸感
- **数学**: 基于 IOI gap detection + melodic boundary detection
- **子指标**:
  - phrase_length_mean: 平均乐句长度 (beats)
  - phrase_length_regularity: 乐句长度的一致性 (std/mean)
  - phrase_count: 旋律中的乐句数
  - antecedent_consequent: 是否有问答式结构
- **Genre ranges**:
  - Baroque: 规整的 2+2 或 4+4 乐句
  - Romantic: 不规则乐句长度，延长和缩短制造戏剧性
  - Pop: 非常规整的 4+4 或 8+8 bars

### Dimension 10: Repetition & Motivic Economy（重复与动机经济）
- **定义**: 旋律材料的重复使用程度
- **数学**: FANTASTIC m-type analysis — 短旋律-节奏片段的出现频率
- **子指标**:
  - m_type_diversity: 独立 m-type 数量 / 总 m-type 数量 (type-token ratio)
  - exact_repetition_ratio: 完全重复占比
  - varied_repetition_ratio: 变化重复占比（transposition, augmentation）
  - compression_ratio: 旋律的可压缩程度（Kolmogorov complexity 近似）
- **Genre ranges**:
  - Baroque: 高 motivic economy (少量 motif 的大量变换)
  - Romantic: 中等 (旋律更 through-composed)
  - Pop: 高重复率 (hook repetition 是核心)

---

## 三、Genre-Specific Metric Profiles

### 3.1 Baroque (Bach, Handel, Vivaldi)

| Dimension | Typical Range | 特征 |
|-----------|--------------|------|
| Pitch range | 12-19 st | 一到一个半八度 |
| Step ratio | 0.65-0.80 | 级进为主 |
| Contour | Arch dominant | 乐句拱形 |
| Pitch entropy | 2.5-3.0 bits | 中等复杂度 |
| Rhythmic entropy | Low-medium | 规则节奏，motor rhythm |
| Originality | Medium | 遵循惯例但有装饰性变化 |
| Tonal clarity | 0.80+ | 调性非常明确 |
| Phrase structure | Regular (4+4) | 方整乐句 |
| Motivic economy | Very high | 少量 motif 大量变换 |

**额外特征**: 装饰音密度高 (trills, mordents, appoggiaturas)，voice leading 偏好 conjunct motion

### 3.2 Romantic (Chopin, Schumann, Liszt)

| Dimension | Typical Range | 特征 |
|-----------|--------------|------|
| Pitch range | 20-30+ st | 两个八度以上 |
| Step ratio | 0.45-0.65 | 更多大跳 (6ths, octaves) |
| Contour | More varied | arch + dramatic gestures |
| Pitch entropy | 3.0-3.5 bits | 更高复杂度 |
| Rhythmic entropy | High | rubato, 自由节奏 |
| Originality | Higher | 更多 chromaticism |
| Tonal clarity | 0.50-0.80 | Chromaticism 模糊调性 |
| Phrase structure | Irregular | 不规则延长和缩短 |
| Motivic economy | Medium | More through-composed |

**额外特征**: chromaticism 是核心表达手段，Chopin 的 lyrical flow vs Schumann 的 disjunct fragments

### 3.3 Pop (C-pop, Western pop)

| Dimension | Typical Range | 特征 |
|-----------|--------------|------|
| Pitch range | 10-15 st | Vocal range 限制 |
| Step ratio | 0.60-0.75 | Singable intervals |
| Contour | Verse ascending → Chorus peak | Energy build |
| Pitch entropy | 1.8-2.5 bits | 较低复杂度 |
| Rhythmic entropy | Low | Repetitive, danceable |
| Originality | Low-medium | 惯例为主 + 小 surprises |
| Tonal clarity | 0.80+ | 调性简单直接 |
| Phrase structure | Very regular (4+4+8) | Verse-Chorus format |
| Motivic economy | High repetition | Hook is king |

**额外特征**: catchiness = simplicity × repetition × incongruity (小惊喜)。副歌 hook 用 ≥3 个不同音高。

---

## 四、从单声部到多声部的 Transform

当加入第二条旋律时，空间被 transform：

**新增的交互指标（不替代单声部指标）：**
- Voice independence: MI(voice_1, voice_2) — 越低越独立
- Consonance profile: 纵向音程的协和度分布
- Parallel motion ratio: 同向运动的比例
- Registral overlap: 两个声部音域重叠程度
- Rhythmic complementarity: 两个声部的节奏互补程度

**每加一个声部：**
- 对所有已有声部对，计算交互指标
- 新声部的可行域 = 原始空间 ∩ (constraint from voice_1) ∩ (constraint from voice_2) ∩ ...
- 空间缩小，但交互指标增加

---

## 五、可以直接实现的指标 (Phase 1)

按实现难度排序：

### Easy (可以用 pretty_midi + numpy 直接算)
1. **Pitch range & tessitura** — max/min/mean/std of MIDI pitches
2. **Interval distribution** — diff of consecutive pitches → histogram
3. **Pitch entropy** — pitch class histogram → Shannon entropy
4. **Rhythmic entropy** — IOI histogram → Shannon entropy
5. **Rhythmic density** — notes per beat
6. **Tonal clarity** — Krumhansl-Schmuckler (music21 已有)

### Medium (需要一些算法但有现成参考)
7. **Contour shape** — correlation with arch template
8. **Melodic originality** — bigram transition probabilities from corpus
9. **Phrase structure** — IOI gap detection + boundary detection
10. **Direction change ratio** — sign changes in interval sequence

### Hard (需要较复杂的模型)
11. **Expectation profile (IC curve)** — 需要 Markov model or simplified IDyOM
12. **Repetition analysis** — m-type extraction (FANTASTIC-style)
13. **Compression ratio** — Kolmogorov complexity approximation (gzip trick)

---

## 六、Key Insight: 好的旋律活在一个 Sweet Spot

所有研究都指向同一个结论：

**好的旋律 ≈ optimal balance of predictability and surprise。**

- Berlyne: 复杂度和偏好是 inverted-U 关系
- IDyOM: IC 既不能太高也不能太低
- Huron: 遵循统计规律但偶尔违反
- Simonton: originality 高的旋律更 famous (但不是无限高)
- 我们的 entropy 实验: sweet spot 在 2.3-3.2 bits

这不是一个 coincidence，这是同一个现象的不同数学表达。而且这个 sweet spot 是 **genre-dependent** 的：baroque 偏 predictable，romantic 偏 surprising，pop 偏 repetitive。

所以指标的 range 不是绝对的，是相对于目标风格的。这正是我们架构里"Style 是 Metric Space 中的一个 region"的数学基础。

---

## 七、Benchmark 策略

没有现成的"旋律好不好听"benchmark。我们自己建 reference baseline。

### 方法
1. 收集真实旋律（MIDI 单声部）跨三个 genre
2. 对每条旋律跑 6 个 Easy-tier 指标
3. 建立每个 genre 的分布（mean ± std）
4. 生成的旋律落在分布内 = "统计上像真的"

### Reference Corpus

**Baroque (目标 ~10 条)**
- Bach: WTC Book I fugue subjects (C major, C minor, D major, D minor...)
- Bach: Inventions 主题 (2-part inventions, 单声部提取)
- Bach: Cello Suite No.1 Prelude (单声部典范)

**Romantic (目标 ~10 条)**
- Chopin: Nocturne Op.9 No.2 右手旋律
- Chopin: Ballade No.1 主题
- Schumann: Träumerei 主旋律
- Liszt: Liebestraum No.3 主题

**Pop (目标 ~10 条)**
- POP909 dataset vocal melody 抽样
- 经典 C-pop: 周杰伦/林俊杰 vocal line (手动 MIDI)
- Western pop: 从 Hooktheory 抽取 melody

### 验证标准
- 6 个指标能不能区分三个 genre？（如果 baroque 和 pop 的分布完全重叠，说明指标没用）
- 每个指标的 measured range 和文献预估 range 是否一致？
- 指标之间的相关性如何？（过高相关 = 冗余维度）

---

## References

- Müllensiefen, D. (2009). FANTASTIC: Feature ANalysis Technology Accessing STatistics (In a Corpus). Technical Report.
- Pearce, M. T. (2005). The Construction and Evaluation of Statistical Models of Melodic Structure. PhD Thesis, City University London.
- Narmour, E. (1990). The Analysis and Cognition of Basic Melodic Structures. University of Chicago Press.
- Schellenberg, E. G. (1997). Simplifying the Implication-Realization Model. Music Perception, 14(3), 295-318.
- Lerdahl, F. (2001). Tonal Pitch Space. Oxford University Press.
- Lerdahl, F. & Krumhansl, C. L. (2007). Modeling Tonal Tension. Music Perception, 24(4), 329-366.
- Simonton, D. K. (1984). Melodic Structure and Note Transition Probabilities. Psychology of Music, 12, 3-16.
- Huron, D. (2006). Sweet Anticipation: Music and the Psychology of Expectation. MIT Press.
- Berlyne, D. E. (1974). Studies in the New Experimental Aesthetics. Hemisphere.
- Tymoczko, D. (2011). A Geometry of Music. Oxford University Press.
- Kader, F. B. et al. (2025). A Survey on Evaluation Metrics for Music Generation. arXiv:2509.00051.
- Lerch, A. et al. (2025). Survey on the Evaluation of Generative Models in Music. ACM Computing Surveys.
