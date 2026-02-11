# Open-source projects using LLMs to orchestrate music generation

**The field of LLM-orchestrated music generation is real but young.** Across GitHub, arXiv, and HuggingFace, roughly 20 open-source projects wire a general-purpose LLM into a music production pipeline — ranging from Microsoft Research prototypes with thousands of stars to single-developer hackathon experiments. The dominant architectural pattern uses GPT-4 as a task planner that dispatches to specialized audio models, though a growing number of projects instead deploy multiple LLM agents that role-play as composer, arranger, and reviewer to collaboratively generate symbolic music in ABC notation. Most projects remain research prototypes; none has achieved production maturity for end-to-end music creation.

The projects fall into three distinct categories: **tool-orchestration agents** (LLM calls external music models/APIs), **multi-agent composition systems** (multiple LLM instances collaborate to write music directly), and **LLM + music library integrations** (LLM generates code or structured data for libraries like music21 or Sonic Pi). Below is every project found, organized by architecture and maturity.

---

## The big three: LLM hub agents that dispatch to specialized models

These projects follow the "HuggingGPT" pattern — a general-purpose LLM receives a user request, decomposes it into subtasks, selects appropriate specialized models, executes them, and aggregates results. The LLM does zero music generation itself.

**Microsoft MusicAgent** (`microsoft/muzic/musicagent`) is the canonical example and the most architecturally complete. Published at **EMNLP 2023**, it uses GPT-3.5/GPT-4 as a controller with three components: a Task Planner that decomposes user requests, a Tool Selector that picks from a registry of HuggingFace models, GitHub projects, and web APIs (Spotify, etc.), and a Response Generator. It handles text-to-music, singing voice synthesis, accompaniment generation, source separation, music classification, and transcription — producing both **MIDI and audio** output. The parent `muzic` repository has **~4,900 stars** and is actively maintained under MIT license. This is the project to study first for understanding the LLM-as-orchestrator pattern in music.

**AudioGPT** (`AIGC-Audio/AudioGPT`) extends this pattern beyond music to all audio domains. Published at **AAAI 2024** with an estimated **~10,000 stars**, it uses ChatGPT/GPT-4 with a LangChain tool framework to orchestrate **15+ specialized models** including AudioLDM, DiffSinger, MusicGen, Make-An-Audio, and Bark. For music specifically, it can generate, edit, and synthesize. The tradeoff is complexity — setup requires downloading many large models. It remains a research prototype with limited recent maintenance.

**WavJourney** (`Audio-AGI/WavJourney`, **540 stars**) takes a different approach: GPT-4 generates structured **audio composition scripts** — essentially programs that specify what audio to generate, when, and how to layer it. These scripts are then executed by a pipeline calling Bark for speech, AudioCraft/MusicGen for music, and mixing tools for assembly. The output is compositional audio scenes combining speech, music, and sound effects. Its successor **WavCraft** (`JinhuaLiang/WavCraft`, **524 stars**) refined this into an "LLM-as-programmer" pattern where GPT-4 writes executable Python programs that invoke expert models and DSP functions, supporting multi-round dialogue for iterative editing. WavCraft also added support for open-source LLMs (Mistral family).

A newer entrant, **AudioFab** (`SmileHnu/AudioFab`, **23 stars**, **138 commits**), uses the **Model Context Protocol (MCP)** to manage 36 audio tools spanning music creation, separation, mixing, speech editing, and multimodal workflows. Published at ACM Multimedia 2025, it addresses limitations of WavCraft/WavJourney with better tool management. It represents the emerging MCP-based approach to LLM-tool integration.

**Loop Copilot** (`ldzhangyx/loop-copilot`, **12 stars**) from ByteDance's Seed Music Team focuses on iterative music creation through multi-round dialogue. Its distinguishing feature is a **Global Attribute Table** that maintains musical coherence across editing rounds — solving a problem the other agents largely ignore.

## Multi-agent composition: LLMs writing music through collaboration

A second architectural family uses multiple instances of a general-purpose LLM role-playing as different music professionals — no specialized music models needed. The LLM's intrinsic knowledge of music theory, elicited through structured prompting, is the sole generation engine.

**ComposerX** (`lllindsey0615/ComposerX`, **~32 stars**) pioneered this approach and was published at **ISMIR 2024**. Six GPT-4-turbo agents — Group Leader, Melody Agent, Harmony Agent, Instrument Agent, Reviewer Agent, and Arrangement Agent — collaborate through Microsoft's AutoGen framework to produce multi-voice compositions in **ABC notation**, converted to MIDI via `abc2midi`. No fine-tuning is involved; it's pure prompt engineering on a stock GPT-4 API. The "good case" rate is **18.4%** at roughly **$0.80 per piece** (~$4.34 per musically interesting piece). The code is functional and reproducible.

**CoComposer** (paper: arXiv 2509.00132, GitHub at `PhotonCombiner/CoComposer` — accessibility unconfirmed) streamlined ComposerX's approach from 6 agents to 5, adding creation-orchestration synchronization. It tested **GPT-4o, DeepSeek-V3, and Gemini-2.5-Flash**, finding GPT-4o performed best with a **100% generation success rate**. It outperformed ComposerX on subjective aesthetic experience and production quality. The paper explicitly states "no additional large-scale music data pre-training" is needed.

**ByteComposer** (arXiv 2402.17785) from ByteDance represents a **hybrid approach**: GPT-4 acts as the expert/controller in a four-stage pipeline — Conception Analysis, Draft Composition (using external symbolic music generators), Self-Evaluation, and Aesthetic Selection. The LLM bridges user intent to musical attributes, invokes generators, evaluates output against music theory, and selects the best candidate. Professional composers rated it at "novice melody composer" level. **No public code is available**, limiting its practical value.

**FilmComposer** (arXiv 2503.08147, **CVPR 2025**) applies multi-agent LLMs specifically to film scoring. LLM agents analyze visual scenes, assess music theory dimensions (mode, melody, harmony, rhythm, emotional expression), and orchestrate arrangement in Reaper DAW. It combines waveform generation (rhythm-controllable MusicGen) with symbolic music for a cinematic-quality output pipeline.

| Project | Stars | LLM | Agent Count | Output | Venue |
|---------|-------|-----|-------------|--------|-------|
| ComposerX | ~32 | GPT-4-turbo | 6 | ABC → MIDI | ISMIR 2024 |
| CoComposer | new | GPT-4o / DeepSeek / Gemini | 5 | ABC → MIDI | arXiv 2025 |
| ByteComposer | — | GPT-4 | 4-stage | Symbolic | arXiv 2024 |
| FilmComposer | — | General LLMs | Multi-agent | Audio | CVPR 2025 |
| M⁶(GPT)³ | — | GPT models | 1 LLM + algorithms | Multi-track MIDI | arXiv 2024 |

## Indie projects wiring LLMs to music tools directly

The most practically interesting category for builders: individual developers connecting LLMs to music libraries through function calling, code generation, or structured output.

**janvanwassenhove/MusicAgent** (`janvanwassenhove/MusicAgent`, **31 stars**, **114 commits**) is the most complete independent project. It's a **multi-agent system** where GPT-3.5/GPT-4 or **Anthropic Claude** agents handle different song creation phases — structure, arrangement, lyrics, code generation — configured via JSON files (`ArtistConfig.json`, `MusicCreationChainConfig.json`). The agents generate **Sonic Pi Ruby scripts** as the final executable music output. It includes a web frontend, CLI, and Electron app, plus automatic WAV recording, album cover generation, and liner notes. This is the closest thing to a complete "AI music producer" in the list.

The **GenAI_Agents music compositor notebook** (`NirDiamant/GenAI_Agents`, parent repo **17,700 stars**) provides the best educational implementation. A **LangGraph state machine** chains GPT-4o-mini through five nodes — Melody Generator → Harmony Creator → Rhythm Analyzer → Style Adapter → MIDI Converter — using **music21** for theory-aware processing and MIDI output. It's a single Jupyter notebook but demonstrates the full pattern clearly with an architecture diagram.

**vdo/MusicAgent** (1 star) is a minimal but architecturally clean prototype using HuggingFace's **SmolAgents** with function-calling tools for chord analysis, scale/mode lookup, chord progression generation, and MIDI device control. It uses **Qwen2.5-Coder-32B** and outputs to actual MIDI hardware — making it the only project that sends LLM-generated music to physical instruments.

**mcp-midi** (`tezza1971/mcp-midi`, **3 stars**) bridges LLMs to DAWs via the **Model Context Protocol**, converting NoteSequence JSON from LLM/Magenta into MIDI data sent through virtual MIDI ports. It's an Electron/Next.js app with a 16-channel MIDI pipeline. Early stage but architecturally forward-looking.

**music21-chatgpt** (`sherwyn33/music21-chatgpt`, 4 stars) is a fork of MIT's music21 library adapted for token-efficient interaction with ChatGPT — wrapping music21 functions so GPT can create MIDI, MusicXML, and sheet music with minimal token overhead. It's a utility rather than a complete system, but fills a key integration gap.

**GPT-Musician** (`jiran214/GPT-Musician`, **15 stars**) is the most notable Chinese-language project — a CLI tool where ChatGPT generates MIDI data from Chinese prompts (e.g., "把月光曲改成现代流行音乐" / "convert Moonlight Sonata to modern pop"). Uses the `symusic` library. The author candidly notes results are "passable for simple music."

**soundTricker/composer-agent** (3 stars) uses **Google Gemini** through Google's Agent Development Kit with a Director Agent and Composer Sub-Agent that calls **Google Lyria** for actual generation — a clean two-agent architecture.

## What's not an orchestrator: specialized music LLMs to know about

Several high-profile projects appear in LLM-music searches but use fine-tuned or specialized models rather than general-purpose LLM orchestration. These are worth understanding as potential **tools that an orchestrator could call**.

**ChatMusician** (`hf-lin/ChatMusician`, **~295 stars**, ACL 2024) continually pre-trains LLaMA2-7B on MusicPile (4B tokens of music data) so the model treats ABC notation as a "second language." It generates music directly — no external tools — and surpasses GPT-4 on music benchmarks. However, it has a strong **Irish music bias** from training data and weak in-context learning. It's a specialized model, not an orchestrator, but could serve as a tool within one.

**MusicLang** (`MusicLang/musiclang`) is a pip-installable Python library with a custom GPT-2-based model for symbolic music prediction and inpainting. It does not integrate with general-purpose LLMs but provides a clean API that an LLM orchestrator could call. **MusicGPT** (`gabotechs/MusicGPT`, **~1,400 stars**) wraps Meta's MusicGen in a Rust application with a chat interface — misleading name but not an LLM orchestrator. **MIDI-LLM** (`slSeanWU/MIDI-LLM`, NeurIPS AI4Music 2025) extends Llama 3.2's vocabulary with 55,030 MIDI tokens for direct text-to-MIDI generation — a vocabulary extension approach rather than orchestration.

## Patterns, gaps, and what comes next

Across all projects, several patterns emerge. **GPT-4 dominates** as the orchestrator LLM, used in 12 of the ~20 projects. Only janvanwassenhove/MusicAgent supports Claude, one project uses Gemini, and one uses Qwen — LLM diversity is low. **ABC notation** has become the de facto symbolic music format for LLM interaction because it's text-native and parseable, though some projects use direct MIDI token representations or generate code for Sonic Pi / SuperCollider.

The field has a notable **maturity gap**. Academic multi-agent systems (ComposerX, CoComposer, FilmComposer) are architecturally sophisticated but exist only as research code. Individual developer projects (janvanwassenhove/MusicAgent, mcp-midi) are more practically usable but lack the compositional intelligence of the academic systems. No project yet combines a mature multi-agent LLM architecture with production-grade music tool integration and a polished user interface.

The most promising architectural directions for builders are:

- **MCP-based tool integration** (AudioFab, mcp-midi) — the Model Context Protocol provides a standardized way for LLMs to discover and invoke music tools, likely to become the dominant integration pattern
- **LangGraph state machines** (GenAI_Agents notebook) — explicit workflow graphs give more control than free-form agent chat
- **Multi-agent ABC composition** (ComposerX/CoComposer) — demonstrably works with stock LLM APIs and no training
- **Sonic Pi / SuperCollider code generation** (janvanwassenhove/MusicAgent) — using existing live-coding environments as the execution layer is pragmatic and produces real audio

## Conclusion

The landscape splits cleanly into **research prototypes** and **hackathon experiments**, with little in between. Microsoft's MusicAgent and AudioGPT proved the tool-orchestration pattern works at scale. ComposerX and CoComposer proved multi-agent LLMs can compose symbolic music without any specialized training. janvanwassenhove/MusicAgent proved a single developer can build a functional AI music producer with GPT/Claude and Sonic Pi. But the project that stitches together the best of all these approaches — multi-agent planning, music-theory-aware tools, DAW integration, iterative editing, and a usable interface — does not yet exist. For anyone building in this space, the GenAI_Agents LangGraph notebook is the fastest on-ramp, ComposerX is the reference architecture for multi-agent composition, and the MCP-based approach (AudioFab, mcp-midi) points toward the future of LLM-tool integration for music.