# Prelude Zero — Architecture

> LLM 提议 → 规则引擎把关 → 工具链渲染
>
> 核心信仰：音乐的"好听"可以被数学描述，但不能被数学穷尽。
> 数学定义 destination，LLM 选择 journey。

---

## 三层架构

```
┌─────────────────────────────────────────────────────┐
│                    LLM (Operator)                    │
│                                                     │
│  "有点忧伤的情歌" ──→ metric ranges                  │
│   metric ranges ──→ constraint space 内的 path 选择   │
│                                                     │
│  不是一层，是使用者。做两件事：翻译意图、创作选择。       │
└───────────┬──────────────────────────┬───────────────┘
            │ 设定目标                  │ 在可行域内选择
            ▼                          ▼
┌───────────────────────────────────────────────────────┐
│               Layer 2: Metric Space                   │
│                                                       │
│  所有"好不好听"和"像不像 X"都在这里。                    │
│  每个指标是一个 range，不是一个 point。                   │
│                                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │
│  │  Tension    │ │  Entropy    │ │  Groove     │     │
│  │  Curve      │ │  Profile    │ │  Feel       │     │
│  │             │ │             │ │             │     │
│  │ T(t) = Σwᵢ │ │ H(pitch),  │ │ swing,      │     │
│  │ ·Tᵢ(t)     │ │ H(rhythm), │ │ velocity    │     │
│  │             │ │ MI(voices) │ │ contour     │     │
│  └─────────────┘ └─────────────┘ └─────────────┘     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │
│  │  Harmonic   │ │  Melodic    │ │  Style      │     │
│  │  Color      │ │  Contour    │ │  Affinity   │     │
│  │             │ │             │ │             │     │
│  │ brightness, │ │ range,      │ │ "baroque":  │     │
│  │ chromaticism│ │ arch shape, │ │ 0.0 — 1.0   │     │
│  │ modal mix   │ │ interval    │ │ "jazz": ... │     │
│  └─────────────┘ └─────────────┘ └─────────────┘     │
│                                                       │
│  验证：创作完成后测量，是否落在目标 range 内？             │
└───────────────────────┬───────────────────────────────┘
                        │ 目标 range 约束
                        ▼
┌───────────────────────────────────────────────────────┐
│             Layer 1: Constraint Space                  │
│                                                       │
│  数学形式的规则，定义"合法"的可行域。                      │
│  LLM 在可行域内自由活动，不会犯"编译错误"。               │
│                                                       │
│  • Voice leading: displacement vector ∈ Z^n            │
│  • Parallel motion: forbidden perfect interval pairs   │
│  • Range: each voice ∈ [low, high] MIDI range          │
│  • Crossing: voice_i < voice_{i+1} at all times        │
│  • Consonance: strong beats require consonant intervals │
│  • Tension budget: section → target range per dimension │
│                                                       │
│  这一层说"什么不能做"和"大概做到什么程度"。               │
│  不说"具体做什么"——那是 LLM 的事。                       │
└───────────────────────┬───────────────────────────────┘
                        │ 合法的音乐指令
                        ▼
┌───────────────────────────────────────────────────────┐
│               Layer 0: Compiler                        │
│                                                       │
│  纯数学 → 音符。没有品味，只有正确性。                    │
│  输入抽象指令，输出保证合法的 MIDI。                      │
│                                                       │
│  • Voicing engine: chord + prev → SATB (Tymoczko)      │
│  • Counterpoint checker: parallel/direct/crossing       │
│  • Subject transforms: T_n, I, R, RI, augmentation     │
│  • Humanize: velocity/timing/articulation shaping       │
│  • Render: MIDI → WAV (pretty_midi + FluidSynth)       │
│                                                       │
│  类比：这是 gcc。你写 C 代码，它生成 binary。             │
│  它不关心你写的程序好不好，只关心语法对不对。              │
└───────────────────────────────────────────────────────┘
```

---

## 关键设计原则

### 1. 指标是 range，不是 point

"欢快的开头"不是一个精确的向量，是一个区域：

```
happy_intro = {
    tension_mean:       [0.10, 0.25],
    entropy_pitch:      [2.0, 2.8],
    harmonic_brightness: [0.5, 0.8],
    rhythmic_density:    [0.4, 0.7],
    style_affinity: {
        "cpop_ballad":  [0.3, 0.8],
        "baroque":      [0.0, 0.2],
    }
}
```

两首歌可以落在同一个 range 内，但听起来完全不同。
**1 + 2 = 3，1.5 + 1.5 = 3。destination 相同，journey 不同。**
Journey 的选择是 LLM tacit knowledge 发挥的地方——它"知道"什么好听，但这个知识无法被形式化。

### 2. 风格是指标，不是约束

"巴洛克风格"不是一个开关，是一组指标：

```
baroque_affinity = {
    voice_independence:  [0.6, 1.0],    # 高 → 声部各自有旋律线
    motivic_coherence:   [0.7, 1.0],    # 高 → 材料经济，变换严密
    contrapuntal_rigor:  [0.8, 1.0],    # 高 → 对位法严格
    harmonic_vocabulary: [0.0, 0.4],    # 低 → 和声词汇保守
    rhythmic_regularity: [0.5, 0.9],    # 中高 → 节奏稳定但不死板
}
```

一首无调性作品可以在 `voice_independence` 和 `motivic_coherence` 上得高分，
表面不像巴赫，但数学骨架比一首浪漫主义改编更巴赫。
**Style binding 的强度本身就是一个可调的参数。**

### 3. LLM 做翻译和选择，不做计算

LLM 的两个角色：

**翻译者**：自然语言 → metric ranges
```
"写一首有点忧伤的华语情歌，副歌要炸"
    ↓ LLM 翻译
{
    verse:  { tension: [0.15, 0.30], entropy: [1.8, 2.4], brightness: [0.2, 0.4] },
    chorus: { tension: [0.55, 0.80], entropy: [2.5, 3.2], brightness: [0.5, 0.7] },
    style:  { cpop_ballad: [0.7, 1.0], royal_road: [0.5, 0.9] }
}
```

**创作者**：在 constraint space 内选择 path
```
"副歌第一拍用 IV△7 还是 IVadd9？"
    → 两个都在可行域内
    → LLM 根据 tacit knowledge 选择
    → Compiler 保证选择合法
    → Metric Space 验证结果在目标 range 内
```

LLM 永远不直接输出音符。它输出意图（和弦选择、旋律方向、结构决策），
Compiler 把意图变成正确的音符。

---

## 创作流程

```
用户意图（自然语言）
    │
    ▼
┌─────────────┐
│ LLM 翻译     │  "忧伤情歌" → metric ranges
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ LLM 规划     │  曲式、段落、调性走向、每段 target ranges
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│ 逐段创作循环                         │
│                                     │
│  LLM 提议 (和弦/旋律/节奏)            │
│       │                             │
│       ▼                             │
│  Constraint Space 检查合法性          │
│       │ ✗ → 反馈给 LLM，重新提议      │
│       │ ✓                           │
│       ▼                             │
│  Compiler 生成 MIDI                  │
│       │                             │
│       ▼                             │
│  Metric Space 测量                   │
│       │ 不在 range 内 → 反馈，调整     │
│       │ 在 range 内 ✓                │
│       ▼                             │
│  下一段                              │
└─────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│ Humanize    │  velocity, timing, articulation
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Render      │  MIDI → WAV / Synthesizer V
└──────┬──────┘
       │
       ▼
    最终音频
```

---

## 当前实现状态

| 组件 | 状态 | 文件 |
|------|------|------|
| **Compiler** | | |
| Voicing engine | ✓ v3.1 | `core/voicing.py` |
| Counterpoint checker | ✓ | `core/counterpoint.py` |
| Fugue transforms | ✓ | `core/fugue.py` |
| Humanize | ✓ | `core/humanize.py` |
| MIDI render | ✓ | `pretty_midi + FluidSynth` |
| **Constraint Space** | | |
| Tension budget | ✓ 雏形 | `core/tension_budget.py` |
| 通用 constraint solver | ✗ | — |
| **Metric Space** | | |
| Tension curve (5D) | ✓ | `core/tension.py` |
| Entropy profile | ✓ | `core/entropy.py` |
| Harmonic color | ✗ | — |
| Melodic contour quality | ✗ | — |
| Rhythmic groove | ✗ | — |
| Style affinity | ✗ | — |
| Composite metrics | ✗ | — |
| **LLM Integration** | | |
| Intent → metric ranges | ✗ | — |
| Propose → validate loop | ✗ | — |

---

## 下一步

**指标研究是核心。** 指标的质量决定系统的天花板。

需要回答的问题：
- 哪些指标维度足以描述"好听"？（tension + entropy 是前两个，远远不够）
- 每个指标的数学定义是什么？（必须可计算，不能模糊）
- 指标之间的相关性？（避免冗余维度）
- 不同风格的指标 range 是什么？（需要从真实音乐中统计）
- 复合指标怎么组合？（加权？还是非线性？）

当指标系统足够丰富时，LLM 的翻译任务就变成了一个有据可依的映射，
而不是现在这样的 ad hoc prompt engineering。
