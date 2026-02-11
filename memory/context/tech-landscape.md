# Tech Landscape: LLM + Music Generation

## Core Finding
LLM 有音乐知识但缺乏多步推理能力 → 外部规则引擎必须。
"LLM proposes, theory engine disposes."

## Well-Formalised (可直接用)
Pitch/note, intervals, scales/modes, chord ID, key signatures, basic SATB rules, rhythm primitives, diatonic progressions, Euclidean rhythms, species counterpoint

## Partially Formalised (有 gap)
Voice leading (pop/jazz/gospel 风格不全), functional harmony (modal interchange 编码不一致), modulation planning, harmonic rhythm

## Not Formalised (LLM 发力点)
Musical form, orchestration, tension curves, melodic contour, groove/swing/feel, style-specific conventions, Schenkerian analysis, emotional mapping, cross-cultural systems, production rules

## Format Candidates for LLM Output
- ABC notation: 文本原生，可解析，但偏 Irish/folk
- musicpy: 数学化，AI 友好，但生态小
- pretty_midi: Python 标准，但 verbose
- music21 objects: 最强验证，但 token 开销大

## Key Stats
- Hooktheory: 71,000+ songs, I chord = 18.9%, IV = 17.2%
- After IV→I, V follows 43.6% of the time
- ComposerX "good case" rate: 18.4%, ~$0.80/piece
- CoComposer: GPT-4o 100% generation success rate
- 56.9% of independently released new songs in China Q1 2025 were AI-generated
