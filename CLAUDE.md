# Memory

## Me
Wayne — 独立开发者/音乐爱好者，在做一个 LLM 驱动的音乐生成项目（个人项目，"玩票但认真玩"）。偏好创造性、创新性的产品。

## Project: Prelude Zero
**定位：** 用通用 LLM（Claude/GPT）作为音乐制作的大脑，通过 prompt engineering 而非模型训练，生成可控、有味道的音乐。
**核心理念：** LLM 提议 → 规则引擎把关 → 工具链渲染。
**阶段：** Phase 1 — 方法论探索（搞清楚什么 work、什么不 work）
**特色：** 关注华语流行（C-pop），Royal Road 进行，POP909 数据集，五声音阶体系。
**当前方向：** 巴赫 → Pink Floyd → 融合 → 回到华语流行。先用 BWV 846 (Well-Tempered Clavier) 验证 pipeline。

## Architecture (5 layers)
| 层 | 工具 | 用途 |
|---|---|---|
| LLM 层 | Claude / GPT | 曲式、和弦（Roman numeral）、旋律、风格、歌词 |
| 理论验证层 | music21 / tonal.js / musicpy | 和声检查、voice leading、格式转换 |
| 经验知识层 | Hooktheory API / POP909 / ChoCo | 和弦转移概率、华语流行 patterns |
| Humanize 层 | Swing / Velocity / Groove 模板 | 让音乐有"味道" |
| 渲染层 | Synthesizer V / ACE-Step / GarageBand | MIDI → 最终音频 |

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

### Voicing Engine (core/voicing.py) — 2026-02-10
- **核心思想**：Tymoczko's Geometry of Music — chord = Z^n 中的点, voice leading = displacement vector
- **算法**：enumerate all voicings → hard constraints (spacing, above bass) → filter parallels (full chord) → min L1 distance
- **结果**：34 bars, 33 transitions, 0 parallel errors. music21 交叉验证一致
- **架构**：SATB 固定 4 声部, 和弦不够用 doubling 补

## Open Questions
- ~~ABC vs musicpy vs pretty_midi 哪个做 LLM 输出格式最好？~~ → 决定用 Python 代码直接生成（music21 + pretty_midi）
- Claude vs GPT-4o 在音乐生成上的优劣？
- Humanize 参数怎么调才像真人？
- 华语 ballad 怎么 prompt 出好的 Royal Road 进行？
- Synthesizer V vs ACE Studio？
- GarageBand 够用还是需要 Logic？
- ~~Voicing 算法怎么改进？~~ → ✓ 已解决：core/voicing.py（穷举搜索 + numpy 向量约束）
- **NEW**: BWV 846 pattern 细节——5 voice 还是简化版？
- **NEW**: Geometry of Music 路线——Tonnetz 可视化 + 风格签名 + 交互式作曲（详见 notes/geometry-of-harmony.md）

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
