# LLM-Orchestrated Music Generation: Project Brief

> 日期：2025-02-10
> 状态：Exploration Phase（方法论探索）
> 定位：个人项目，玩票但认真玩，做自己想听的音乐

---

## 1. 我们想做什么

用 **通用 LLM（Claude / GPT）作为音乐制作的大脑**，通过 prompt engineering 而非模型训练，生成可控、有味道的音乐。

核心理念：**LLM 提议，规则引擎把关，工具链渲染。**

### 1.1 出发点

从"AI做歌"的好奇心出发，调研了 Suno/Udio 这类端到端工具后，发现一个关键问题：**它们是黑盒，每一步都不可控。**

于是提出了一个更好的思路：

```
自然语言描述 → LLM 生成结构化音乐表示（MIDI/ABC/MusicXML）
                → 导入 DAW（GarageBand/Logic）
                → 选音色、渲染、出成品
```

每一步可见、可调、可迭代。

### 1.2 关于"味道"的关键洞察

LLM 生成的音乐结构上合理但缺少"味道"（groove/feel）。但味道是可以工程化的：

- **Swing/Humanize**：音符时值加随机微偏移
- **Velocity 曲线**：力度动态变化，模拟真人演奏强弱
- **微妙 timing**：hi-hat 稍提前、snare 稍拖后 → groove 感
- **音色选择与叠加**：根据风格自动选 preset

这些都可以用代码精确控制，比 Suno 的黑盒更好。

---

## 2. 调研发现

### 2.1 现有工具——积木已经够用

| 层级 | 工具 | 用途 |
|------|------|------|
| 理论编码 | music21, tonal.js, musicpy | 和声验证、voice leading 检查、调式分析 |
| 经验数据 | Hooktheory API, POP909, ChoCo | 和弦转移概率、华语流行标注、语料库 |
| Humanize | Humanizer, Magenta Groove, Euclidean rhythm | 人性化处理、节奏算法 |
| 渲染 | MusicGen, ACE-Step, Synthesizer V, ACE Studio | MIDI → 最终音频 / 人声合成 |

**结论：每一块积木都有人做了，但没人用"LLM 作为大脑"的方式串起来。**

### 2.2 已有的 LLM + 音乐项目

调研了约 20 个开源项目，分三类：

**Tool-Orchestration Agents（LLM 调度外部模型）：**
- **Microsoft MusicAgent**（muzic/musicagent, ~4900⭐）—— 最完整的参考架构，GPT 作为 controller 调度 HuggingFace 模型
- **AudioGPT**（~10000⭐）—— 15+ 个模型，但太重
- **WavJourney / WavCraft** —— GPT-4 生成音频合成脚本

**Multi-Agent Composition（多 LLM 协作写曲）：**
- **ComposerX**（ISMIR 2024）—— 6 个 GPT-4 agent 协作，输出 ABC notation → MIDI
- **CoComposer** —— 5 agent，GPT-4o 效果最佳，100% 生成成功率
- **ByteComposer** —— 4 阶段 pipeline，专业作曲人评为"新手水平"

**Indie Projects（个人开发者接线）：**
- **janvanwassenhove/MusicAgent** —— GPT/Claude → Sonic Pi 脚本 → WAV，最接近"AI 音乐制作人"
- **GenAI_Agents 音乐 notebook** —— LangGraph 状态机，GPT-4o-mini + music21，最好的教学实现
- **mcp-midi** —— MCP 协议接 DAW，架构前瞻

### 2.3 关键研究发现

**LLM 有音乐知识，但没有音乐推理能力。**

ChatMusician 的 MusicTheoryBench 显示：所有 LLM（包括 GPT-4）在多步音乐推理上表现约 25%（接近随机）。

→ **外部规则引擎不是可选的，是必须的。**
→ **架构必须是：LLM 提议 → 规则引擎验证/纠正。**

### 2.4 华语流行特色资源

| 资源 | 内容 |
|------|------|
| POP909 | 909 首华语流行，含旋律/伴奏 MIDI、和弦标注 |
| Royal Road 进行 | IV△7–V7–iii7–vi，东亚流行最典型和声 |
| iii chord 强调 | 华语流行比西方多用 iii（作为 V/vi） |
| 羽调式为主 | 宫商角徵羽五声，羽调最常见 |
| 普通话声调 | 对旋律有软约束（约 81% 匹配率），不像粤语那么严格 |

---

## 3. 我们的方法论定位

### 3.1 与现有项目的区别

现有项目要么是**研究原型**（ComposerX 级别，做完发论文就完了），要么是**hackathon 实验**（个人开发者的 toy project）。中间地带是空的。

我们的定位不在这个谱系上：**我们不是做产品，也不是发论文，我们是给自己做音乐。**

这意味着：
- 不需要通用架构
- 不需要 multi-agent 复杂系统
- 不需要考虑 scalability
- **只需要最短路径：脑中想法 → 能听的歌**

### 3.2 核心方法

**Prompt Engineering 代替模型训练。**

不训练任何模型，不微调任何东西。用现有 LLM（Claude/GPT）的内在音乐知识，通过精心设计的 prompt，生成结构化音乐数据，再用现有工具链处理和渲染。

### 3.3 提出的架构

```
┌─────────────────────────────────────────────┐
│  LLM 层（Claude / GPT）                      │
│  · 曲式结构、和弦进行（Roman numeral）          │
│  · 旋律轮廓、风格参数、歌词                     │
│  · 利用 tacit knowledge 处理未形式化的领域       │
├─────────────────────────────────────────────┤
│  理论验证层（music21 / tonal.js / musicpy）    │
│  · 和声检查、voice leading 验证                │
│  · 格式转换（ABC → MIDI, etc.）               │
├─────────────────────────────────────────────┤
│  经验知识层                                   │
│  · Hooktheory API（和弦转移概率）              │
│  · POP909（华语流行 patterns）                │
│  · ChoCo（语料库支持的和声上下文）              │
├─────────────────────────────────────────────┤
│  Humanize 层                                 │
│  · Swing / timing 偏移                       │
│  · Velocity 曲线                             │
│  · Groove 模板                               │
├─────────────────────────────────────────────┤
│  渲染层                                      │
│  · Synthesizer V / ACE Studio（人声）          │
│  · MusicGen / ACE-Step（纯音乐音频）           │
│  · GarageBand / Logic（手动调整）              │
└─────────────────────────────────────────────┘
```

---

## 4. 当前阶段的定义

### Phase 1：方法论探索（当前）

**目标：搞清楚什么 work、什么不 work、为什么。**

- 代码可以很烂（throwaway scripts）
- 但文档记录要好——每次实验的 input / output / judgment
- 积累 insight，为后续工程化打基础

**不做的事：**
- 不搭框架
- 不写通用 API
- 不做 multi-agent
- 不优化性能

**要做的事：**
- 直接在 Claude/GPT 对话中尝试生成音乐
- 测试不同 prompt 策略
- 测试不同输出格式（ABC / musicpy / pretty_midi 脚本）
- 记录哪些风格/结构 LLM 做得好，哪些做不好
- 探索 humanize 的参数空间
- 找到自己喜欢的音色和渲染路径

### 实验记录模板

每次实验记三件事：

1. **Input**：给了什么 prompt / 指令 / 参数（调性、BPM、风格、和弦进行）
2. **Output**：生成了什么，转成 MIDI/音频后听感如何
3. **Judgment**：哪里好，哪里差，为什么，下次怎么改

---

## 5. 未回答的问题（待探索）

- ABC notation vs. musicpy vs. pretty_midi 脚本，哪个作为 LLM 输出格式效果最好？
- Claude vs. GPT-4o 在音乐生成上各有什么优劣？
- Humanize 参数怎么调才像真人？多少 swing 合适？
- 华语 ballad 具体要怎么 prompt 才能出好的 Royal Road 进行？
- Synthesizer V vs. ACE Studio，哪个更适合我们的 pipeline？
- GarageBand 够用还是需要 Logic？

---

## 6. 未形式化的"高价值靶区"

这些领域目前没有好的代码实现，正是 LLM tacit knowledge 可以发力的地方：

- **曲式结构**（verse-chorus-bridge 生成规则）
- **编曲/配器**（乐器选择、音色搭配）
- **张力曲线**（整首歌的张力释放弧线）
- **旋律写作**（好听的旋律轮廓、hook 构建）
- **Groove / Feel**（swing、pocket、shuffle）
- **风格特定规则**（华语流行结构公式、日式进行）
- **情感映射**（音乐元素 → 情绪效果）

**这些 gap = LLM agent 最有价值的应用点。**

---

## 附录：关键资源链接

### 工具 / 库
- music21: https://github.com/cuthbertLab/music21
- tonal.js: https://github.com/tonaljs/tonal
- musicpy: https://github.com/Rainbow-Dreamer/musicpy
- pretty_midi: https://github.com/craffel/pretty-midi
- Humanizer: https://github.com/xavriley/humanizer
- ACE-Step: https://github.com/ace-step/ACE-Step

### 数据集
- POP909: https://github.com/music-x-lab/POP909-Dataset
- Hooktheory API: https://www.hooktheory.com/api/trends/docs
- CCMusic: https://ccmusic-database.github.io/en/

### 参考项目
- Microsoft MusicAgent: https://github.com/microsoft/muzic/tree/main/musicagent
- ComposerX: https://github.com/lllindsey0615/ComposerX
- janvanwassenhove/MusicAgent: https://github.com/janvanwassenhove/MusicAgent
- GenAI_Agents 音乐 notebook: https://github.com/NirDiamant/GenAI_Agents

### 论文
- ChatMusician (ACL 2024): arXiv 2402.16153
- ComposerX (ISMIR 2024): arXiv 2404.18081
- CoComposer: arXiv 2509.00132
- ByteComposer: arXiv 2402.17785
- Rule-Guided Music Diffusion (ICML 2024 Oral)