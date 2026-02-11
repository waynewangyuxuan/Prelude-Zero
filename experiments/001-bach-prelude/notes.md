# Experiment 001: Bach-Style C Major Prelude

**Date**: 2026-02-10
**Goal**: 验证 Claude 能否生成合理的巴洛克和声进行（以 BWV 846 为参照）

---

## Input

- **任务**：生成一首新的 C 大调 Prelude，使用 BWV 846 的分解和弦 pattern，但和声进行全新
- **约束**：巴洛克和声语言、smooth voice leading、无平行五度/八度
- **参数**：Key=C, BPM=66, 34 bars, BWV 846 arpeggiation pattern
- **LLM**：Claude (direct code generation, no prompt template)
- **工具链**：music21 (Roman numeral conversion) → pretty_midi (MIDI) → scipy (WAV preview)

## Output

### Claude 提议的和声进行
```
Section A (Statement):     I → vi7 → IV → V7
Section B (Expansion):     I → IVmaj7 → viio → iii → vi7 → ii7
Section C (Tonicize V):    V → V7/V → V → viio7/V
Section D (Return):        V7 → I6 → IVmaj7 → ii7 → V7 → I
Section E (Build tension): V7/IV → IV → viio7 → viio7/V → V7
Section F (Dom pedal):     I6/4 → V7 → vi → V7 → V9
Section G (Resolution):    I → IV → V7 → I
```

### Voice Leading Validation

**第一次跑（naive voicing, v1）**：8 errors（平行五度 2, 平行八度 6）
**第二次跑（smooth voice leading, v1）**：3 errors + 14 spacing warnings
**第三次跑（vector-based engine, v2）**：✓ **0 errors, 0 warnings**

v2 引擎改进：
- 穷举搜索所有 voicing → numpy 向量约束过滤 → L1 距离最优化
- SATB 固定 4 声部（bass + 3 upper），不再有 voice count 漂移
- 平行检查覆盖 full chord（bass + upper），不只是 upper-upper
- 交叉验证通过：numpy 引擎和 music21 VoiceLeadingQuartet 结果一致
- Stats: avg 8.1 semitones/transition, total 268 over 33 transitions

### 音频

- `output.mid` — 可导入 GarageBand
- `output.wav` — 简易合成预览（sine-based, 音质粗糙但能判断和声）

---

## Judgment

### 什么 WORK ✓
1. **Claude 的和声选择是合理的**：Roman numeral 层面的进行符合巴洛克习惯——circle of fifths、secondary dominants、diminished approaches、pedal points。没有明显的"非巴洛克"和弦。
2. **Dramatic arc 合理**：Statement → Expansion → Return → Tension → Pedal → Resolution 这个大结构是对的。
3. **规则引擎 catch 了 LLM 的问题**：voice leading validator 成功检测出平行五度/八度，证明"LLM 提议 → 规则引擎把关"这个架构是有效的。
4. **Pipeline 端到端跑通**：从 Roman numeral → MIDI → WAV 整个链条没有断。

### 什么不 WORK ✗（v1 问题，v2 已解决）
1. ~~**Voicing 是短板**~~：→ v2 向量引擎通过穷举搜索 + 约束过滤解决
2. ~~**Spacing drift**~~：→ v2 固定 SATB 4 声部 + spacing 约束
3. **音频预览太粗糙**：sine-based 合成器只能听和声，无法判断"味道"。需要 FluidSynth 或直接用 GarageBand。
4. **BWV 846 pattern 本身还可以更精确**：目前的 arpeggiation 是简化版，真实的 BWV 846 有 5 voice pattern。

### Key Insights
1. **LLM 在"选什么和弦"这个层面表现不错，但在"怎么排列声部"这个层面需要外部引擎。** 这完美验证了项目假设。
2. **Voice leading 是一个向量优化问题**：chord = Z^n 中的点，voice leading = 位移向量 d = v2 - v1，good voice leading = min ||d|| subject to constraints（Tymoczko's Geometry of Music）。
3. **穷举搜索 + 硬约束过滤在这个规模下完全可行**：34 bar progression，每个和弦几十到几百个候选 voicing，毫秒级完成。

### 下一步
1. ~~改进 voicing 算法~~ → ✓ DONE (core/voicing.py)
2. Wayne 用 GarageBand 听 output.mid，反馈"听感"
3. Tonnetz 可视化：把和声进行画在 Tonnetz 上，看 geometric 路径
4. 对比 BWV 846 原曲的 voicing 和我们生成的 voicing
5. 尝试更复杂的和声语言（更多 chromaticism、modal mixture）
