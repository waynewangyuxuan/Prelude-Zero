# Prelude Zero — LLM-Orchestrated Music Generation

## Overview
个人项目，用通用 LLM 作为音乐制作大脑。不训练模型，纯 prompt engineering。
目标：脑中想法 → 能听的歌，每一步可见可调可迭代。

## Phase 1: 方法论探索（当前）
- 直接在 Claude/GPT 对话中尝试生成音乐
- 测试不同 prompt 策略
- 测试不同输出格式（ABC / musicpy / pretty_midi 脚本）
- 记录哪些风格/结构 LLM 做得好，哪些做不好
- 探索 humanize 的参数空间
- 找到自己喜欢的音色和渲染路径

## Architecture
5 层架构：LLM → 理论验证 → 经验知识 → Humanize → 渲染

## Key Reference Projects
- Microsoft MusicAgent（muzic/musicagent, ~4900⭐）— 最完整参考架构
- ComposerX（ISMIR 2024）— 多 agent ABC 作曲参考
- janvanwassenhove/MusicAgent — GPT/Claude → Sonic Pi，最接近完整 AI 音乐制作人
- GenAI_Agents notebook — LangGraph + music21，最好的教学实现
- mcp-midi — MCP 协议接 DAW，架构前瞻

## Key Tools
- music21（Python）— 核心理论引擎，和声验证、voice leading
- tonal.js（JS）— 浏览器端理论处理
- musicpy — AI 友好的数学化音乐表示
- Hooktheory API — 和弦转移概率查询
- POP909 — 909 首华语流行标注数据集
- ACE-Step / Synthesizer V — 渲染/人声合成

## C-Pop Specifics
- Royal Road: IV△7–V7–iii7–vi（王道進行）
- iii chord 在华语流行中比西方常用得多（作为 V/vi）
- 羽调式（Yu mode）最常见
- 普通话声调对旋律有软约束（~81% 匹配率）
- 偏好七和弦、IV 起始、欺骗终止（V–vi > V–I）

## Unformalised High-Value Targets (LLM tacit knowledge sweet spots)
- 曲式结构、编曲/配器、张力曲线
- 旋律写作、Groove/Feel、风格规则
- 情感映射
