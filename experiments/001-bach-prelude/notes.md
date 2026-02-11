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

**第一次跑（naive voicing）**：8 errors（平行五度 2, 平行八度 6）
**第二次跑（smooth voice leading）**：3 errors + 14 spacing warnings

剩余 3 个错误：
- m.3→4: IV→V 平行五度（bass F→G 与 upper C→D）
- m.7→8: viio→iii 平行八度（F4→G4 与 F5→G5）
- m.31→32: I→IV 平行八度（E4→F4 与 E6→F6）

Spacing drift: 后半段（mm.21-34）上声部之间距离逐渐变大（最大 24 半音），
说明 smooth voice leading 算法在处理 diminished 和弦和 pedal 段落时声部会漂移。

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

### 什么不 WORK ✗
1. **Voicing 是短板**：LLM 能选对和弦，但不能保证 voicing 不产生平行运动。自动 voicing 需要更智能的算法。
2. **Spacing drift**：smooth voice leading 在 diminished 和弦处理上不稳定，声部间距会越来越大。
3. **音频预览太粗糙**：sine-based 合成器只能听和声，无法判断"味道"。需要 FluidSynth 或直接用 GarageBand。
4. **BWV 846 pattern 本身还可以更精确**：目前的 arpeggiation 是简化版，真实的 BWV 846 有 5 voice pattern。

### Key Insight
**LLM 在"选什么和弦"这个层面表现不错，但在"怎么排列声部"这个层面需要外部引擎。** 这完美验证了项目假设：LLM 有音乐知识但缺乏多步推理（voice leading 就是典型的多步推理问题）。

### 下一步
1. 改进 voicing 算法——可能需要一个 constraint-based solver（Diatony 风格）
2. 装 FluidSynth 或让 Wayne 用 GarageBand 听 MIDI
3. 尝试让 Claude 直接指定每个声部的具体音高（而不是只给 Roman numeral + bass）
4. 对比 BWV 846 原曲的 voicing 和我们生成的 voicing
