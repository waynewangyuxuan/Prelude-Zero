# Experiment 005: Three-Style Metric Profiling

## 目标
建立 Bach / Chopin / Pink Floyd 三种风格的 metric space profile，找到融合区域。

## 数据源
- **Bach**: 5 首手工编码短主题 (10-32 notes)
- **Chopin**: 5 首手工编码短主题 (16 notes)
- **Pink Floyd**: 12 tracks from 7 首真实 MIDI (37-375 notes)
  - Wish You Were Here (vocal + guitar solo)
  - Hey You (lead vocal)
  - Money (tenor sax + alto sax + guitar solo)
  - Time (lead guitar)
  - Shine On You Crazy Diamond (vocal + guitar lead)
  - Have a Cigar (guitar)
  - Another Brick in the Wall (keys lead + guitar solo)

## 指标体系 (10 dimensions)
Easy tier: pitch range, interval distribution, pitch entropy, rhythm entropy, rhythm density, tonal clarity
Medium tier: contour shape, mode/scale detection, duration variance, repetition index

## 核心发现

### Style Signatures (effect size > 1.5σ)

**Bach 的 DNA:**
- 零半音化 (chromaticism 0.000, effect -3.3σ) — 纯大小调
- 极低时值变化 (duration CV 0.168, effect -2.2σ) — motor rhythm
- 高密度 (3.08 n/beat, effect +2.1σ) — 持续跑动
- 低节奏信息量 (rhythm H 0.457, effect -2.0σ) — 均匀节奏

**Chopin 的 DNA:**
- 低方向变化 (0.289, effect -2.3σ) — 长弧线旋律
- 高平均 run length (3.05, effect +1.9σ) — 持续向一个方向
- 无大跳 (leap ratio 0.000, effect -1.7σ) — 纯步进
- 低 pitch 重复 (0.179, effect -1.7σ) — through-composed

**Pink Floyd 的 DNA:**
- 极高时值变化 (duration CV 0.967 / range ratio 4.98, effect +2.8~3.2σ) — 长 sustain + 短 ornament
- 巨大音域 (27.4 半音, effect +2.8σ) — 吉他 solo 跨 3-4 个八度
- 高节奏信息量 (rhythm H 2.22, effect +2.7σ) — 节奏极其多变
- 高半音化 (0.245, effect +2.0σ) — 色彩丰富
- 高重复 (pitch bigram rep 0.55, effect +1.6σ) — riff/lick 重复
- 高方向变化 (0.617, effect +1.5σ) — 不断改变方向

### 调式分布
- Bach: Aeolian (3), Lydian (1), Mixolydian (1) — 自然调式
- Chopin: Phrygian (2), Lydian (2), Mixolydian (1) — 混合
- **Floyd: Phrygian (5), Aeolian (3), Dorian (2)** — Phrygian 压倒性主导

### Fusion Zone (三风格重叠)

**强重叠 (>25%):**
- Rhythm bigram rep: [0.25, 1.00] (90%) — 三种风格都有节奏模式重复
- Step ratio: [0.53, 0.93] (48%) — 步进比例有大量重叠
- Dir bias: [-0.25, 0.07] (37%) — 方向偏好相似
- Tonal clarity: [0.68, 0.82] (27%) — 调性清晰度有交集
- Density: [1.11, 2.00] (24%) — 密度有窄重叠带

**无重叠 (关键区分维度):**
- Pitch range: Bach/Chopin [5-14] vs Floyd [16-47] — 音域完全分离
- Duration CV: Bach/Chopin [0-0.44] vs Floyd [0.38-1.58] — 时值变化几乎不重叠
- Dur range ratio: 完全不重叠
- Chromaticism: Bach [0] vs others [>0] — Bach 完全 diatonic
- Mean run length: Floyd [1.25-2.06] vs Chopin [2.25-3.75] — 旋律延续性完全分离

## 方法论注意
Bach/Chopin 是短主题 (10-32 notes), Floyd 是完整声部 (37-375 notes)。
长度差异会影响 pitch range (长片段自然更宽) 和 rhythm entropy (更多节奏类型)。
Duration CV 和 pitch range 的 Floyd 数据可能偏高。
但 step ratio, tonal clarity, direction changes 等比例指标受长度影响较小。

## 对融合的启示
1. **不可能简单取交集** — 太多维度没有重叠
2. **融合 = 从每种风格取不同维度**:
   - Bach 的 motivic economy + motor energy
   - Chopin 的 long phrase arc + chromatic color
   - Floyd 的 temporal sparseness + duration contrast + Phrygian modality
3. **Density 是关键选择点**: 1.1-2.0 n/beat 是三者唯一重叠带
4. **调式选择**: Phrygian 或 Dorian 最能代表融合方向（三者都出现）
