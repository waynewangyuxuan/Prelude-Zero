# Music theory as code: a comprehensive landscape of tools, research, and gaps

**Dozens of libraries, datasets, and constraint systems now encode Western music theory into computable rules — but critical gaps remain in form, groove, orchestration, and non-Western systems, making this an ideal frontier for LLM-based music agents.** The ecosystem spans from MIT's music21 (the gold standard for symbolic analysis) to crowd-sourced databases like Hooktheory's 71,000-song TheoryTab, from constraint solvers that guarantee no parallel fifths to neural models that compose full songs with vocals. For Chinese pop music specifically, the POP909 dataset, the "Royal Road" progression (IV△7–V7–iii7–vi), and a wave of Chinese AI music research (YuE, SongComposer, Tencent's LeVo) are transforming what's possible. This report maps the entire terrain — organized by category, with specific relevance to building an LLM-based music production pipeline.

---

## Dimension 1: Music theory libraries that encode theory as programmable APIs

### music21 is the undisputed foundation

MIT's **music21** (Python, BSD-3, v9.9+, actively maintained since 2008 by Michael Scott Cuthbert) is the most comprehensive music theory library in existence. It doesn't merely represent musical objects — it encodes *rules*. Its `voiceLeading` module detects **parallel fifths, parallel octaves, hidden fifths, contrary motion, and oblique motion** through a `VoiceLeadingQuartet` class. Its `figuredBass` module realizes figured bass lines into complete four-part textures using a `Rules` class with toggleable constraints like `forbidParallelFifths` and `forbidParallelOctaves`. The `roman` module provides full Roman numeral analysis with a `functionalityScore` (0–100) rating how "functional" a given chord is, supports secondary dominants (V7/vi), and handles minor-key scale-degree ambiguities. The `counterpoint.species` module implements `ModalCounterpoint` with legal harmonic and melodic interval sets. A built-in corpus of thousands of encoded scores (Bach chorales, Palestrina masses, leadsheets) enables corpus-wide statistical queries. The **RomanText format** (.rntxt), published at ISMIR 2019, standardizes computer-readable harmonic analyses, and the companion **When-in-Rome** corpus on GitHub provides hundreds of analyses in this format.

For an LLM pipeline, music21 serves as the **core theory engine and validation layer**: an LLM generates chord progressions as Roman numerals, music21 converts them to pitches in any key, checks voice leading, and exports to MIDI/MusicXML. Its primary limitation is a heavy dependency footprint and a focus on Western classical theory — pop-specific rules (groove, production conventions) are absent.

### The JavaScript ecosystem: tonal.js leads, with Tone.js for audio

**Tonal.js** (TypeScript, MIT, ~4,100 GitHub stars, actively maintained) is the browser-side counterpart to music21. Its purely functional, modular architecture (`@tonaljs/note`, `@tonaljs/chord`, `@tonaljs/scale`, `@tonaljs/key`, `@tonaljs/progression`) covers notes, intervals, chords, scales, modes, keys, voicings, and Roman-numeral-to-chord conversion. All functions are pure with no mutation, making it naturally composable with LLM-generated code. **Teoria.js** (~1,300 stars, MIT, low recent activity) adds particularly strong jazz chord parsing (handling symbols like "Ab#5b9" and "F(#11)"). **Tone.js** is often confused with these but is strictly a Web Audio synthesis/scheduling framework — not a theory library. The practical stack for browser-based production: tonal.js for theory validation + Tone.js for audio rendering.

### Musicpy: designed explicitly as an AI-music interface

**Musicpy** (Python, ~973 stars, by Rainbow Dreamer) aims to "completely transform the entire music theory system into pure mathematical models." Notes and chords are treated as mathematical objects (vectors, matrices). It encodes chord detection, scale/key analysis, chord progression analysis, tonality/modulation detection, melody-chord splitting, and counterpoint rules. Its creator explicitly designed it as "an interface to communicate music between people and AI" — making its concise syntax a natural intermediate representation between LLM text output and MIDI.

### Other notable libraries across languages

| Library | Language | Key strength | Stars/Status |
|---------|----------|-------------|-------------|
| **mingus** | Python (GPL) | Chord/scale construction + FluidSynth playback | Low activity |
| **JFugue** | Java (Apache-2) | `ChordProgression("I IV V").setRoot("C")` — Roman numeral API; LLM-friendly Staccato string notation | Stable/mature |
| **rust-music-theory** | Rust (MIT) | Notes/chords/scales + MIDI playback + WASM target | Active |
| **Kord** | Rust/WASM (MIT) | CLI with `describe`, `play`, `guess`, ML-based chord inference from audio | Active |
| **go-music-theory** | Go | Chord/scale "DNA" rule chains, CLI | Active |
| **pretty_midi** | Python (MIT) | MIDI data manipulation (not theory itself, but essential I/O) | Stable |
| **librosa** | Python (ISC) | Audio analysis: chromagrams, beat tracking, tempo, MFCCs | Active |
| **Essentia** | C++/Python (AGPL) | 250+ audio analysis algorithms, key/chord detection, pre-trained models | Active |
| **madmom** | Python | State-of-the-art neural beat/chord/onset detection | Active |
| **Magenta** | Python/JS (Apache-2) | ML generation: MusicVAE, Music Transformer, Groove (humanization) | Active (Google) |
| **MusicLang/maidi** | Python | AI composition co-pilot with mask-based MIDI regeneration, LLAMA2-based prediction | Active |
| **music21j** | JavaScript | Official JS port of music21 with RomanNumeral and VoiceLeadingQuartet classes | Active |

---

## Dimension 1 continued: Constraint-based and rule-based composition systems

### From CHORAL's 350 rules to modern constraint solvers

The history of formalizing music theory as constraints begins with **CHORAL** (Kemal Ebcioglu, 1988), which encoded **~350 rules for Bach chorale harmonization** — covering chord skeletons, voice leading, modulation, and cadences — using first-order predicate calculus. This remains one of the most ambitious rule-encoding efforts ever attempted.

The IRCAM ecosystem represents the most sustained institutional investment. **OpenMusic** (Common Lisp, LGPL, actively maintained) provides a visual patching environment with three constraint libraries: **PWConstraints** (pattern-matching), **Situation** (domain-specific musical knowledge), and **OMClouds** (heuristic solver). Its modernized successor **OM#** adds reactive programming and real-time capabilities. **PWGL** (Sibelius Academy, Helsinki) extended this with **PWMC** for combined pitch-rhythm constraints, spawning the crucial **Cluster Engine** (Örjan Sandred, University of Manitoba) — a standalone polyphonic constraint solver now ported to OpenMusic, OM#, Opusmodus, and Max/MSP. The companion **Cluster Rules** library provides predefined rules for melody, harmony, counterpoint, and rhythm that students can freely combine.

The most recent and directly implementable system is **Diatony** (Sprockeels & Van Roy, UCLouvain, IJCAI 2024), which formalizes **diatonic tonal harmonic rules** for four-voice composition using the Gecode constraint solver. It encodes SATB voice ranges, no voice crossing, no parallel fifths/octaves, proper doubling, tritone resolution, cadential patterns, and interval cost functions — producing MIDI output. Related IRCAM projects include **RhythmBox** (2020, constraint-based rhythm generation), **Melodizer 2.0** (2023, combined rhythm + pitch), and a **full formalization of Fux's species counterpoint** as constraints with cost functions (2023).

**Strasheela** (Torsten Anders, Oz/Mozart) offered perhaps the most elegant design philosophy — "composing music by composing rules" — where music theories are declared as constraint satisfaction problems and the system searches for compliant scores. Despite being effectively dormant (last release 2012, Oz platform has limited modern support), its concepts remain the ideal paradigm for LLM integration.

### Counterpoint: the most thoroughly formalized domain

Species counterpoint rules are the best-encoded subset of music theory. Implementations range from **Schottstaedt's seminal code** (CCRMA Stanford, 1984) to **Optimuse** (Herremans & Sörensen, 2012), which uses Variable Neighbourhood Search with 18 melodic + 15 harmonic rules from Fux as an objective function. **Contrapunctus v1.0** (Java) recognizes stylistic differences between treatises by Fux, Jeppesen, and Salzer. On GitHub, **ekzhang/harmony** uses dynamic programming to solve four-part SATB voice leading from Roman numeral input, implementing parallel-fifth avoidance, voice-crossing constraints, and stepwise-motion preferences — all built on top of music21.

### Euclidean rhythms: the single most implementable rhythm algorithm

Godfried Toussaint's 2005 paper demonstrated that distributing *k* onsets across *n* positions using Euclid's GCD algorithm generates nearly all important world music rhythms: **E(3,8) = Cuban tresillo**, E(5,8) = Cuban cinquillo, E(7,12) = West African Bembé bell pattern, E(5,16) = bossa nova. The algorithm is trivial to implement (~20 lines of code) and parameterized by just (k, n, offset) — making it ideal for LLM orchestration. An LLM selects appropriate parameters per instrument/style, layers multiple patterns for polyrhythmic grooves, and applies rotation for variation.

### David Cope's EMI: learning rules from data, not encoding them

**EMI (Experiments in Musical Intelligence)**, created by David Cope (who passed away May 4, 2025), took a fundamentally different approach: rather than programming music theory rules, it analyzed existing works to extract patterns and "signatures" of a composer's style, then recombined them to generate new compositions. Emily Howell (2003+) extended this with interactive feedback. The software is not openly available (Cope deleted the EMI database in 2004), but the conceptual approach — extracting style signatures as recombinable templates — is directly analogous to how an LLM encodes stylistic patterns.

---

## Dimension 2: Computational musicology and statistical analysis of pop music

### The foundational corpora for understanding pop harmony

Four datasets form the empirical backbone of computational pop musicology:

**The McGill Billboard Dataset** (Burgoyne, Wild, & Fujinaga, ISMIR 2011) provides **890 expert chord and structural annotations** covering 740 distinct Billboard Hot 100 songs (1958–1991), with section labels (verse, chorus, bridge), timing, metre, and tonic. It's available via the `mirdata` Python library and has become the standard ground truth for MIREX Audio Chord Estimation evaluations.

**The Rolling Stone Corpus** (de Clercq & Temperley, *Popular Music*, 2011) analyzed 200 songs from Rolling Stone's "500 Greatest Songs" list with both harmonic and melodic transcriptions. Their key finding: **IV is the most common chord after I in rock** — especially common preceding the tonic — contradicting common-practice classical music where V→I dominates. Flat-side harmonies (♭VII, ♭III, ♭VI) are characteristic of rock. The expanded **CoCoPops** corpus (Georgia Tech) adds melodic transcriptions in Humdrum format.

**Hooktheory's TheoryTab** is the largest crowd-sourced harmonic database: **71,000+ songs** with color-coded Roman numeral chord analyses, scale-degree-highlighted melodies, and section labels. Its **Trends API** enables programmatic queries: given a chord progression prefix, it returns probability distributions for what chord comes next. After IV→I, V follows **43.6%** of the time. The I chord constitutes 18.9% of all chords; IV is next at 17.2%. This API is directly usable as a Markov-chain-like backbone for chord generation.

**The Million Song Dataset** (Bertin-Mahieux et al., ISMIR 2011) contains derived audio features for **1 million tracks** in HDF5 format — tempo, key, mode, loudness, timbre vectors, and more — but no raw audio. The Echo Nest API that generated it is now defunct (acquired by Spotify in 2014), limiting extensibility. It remains useful for understanding statistical distributions of musical features across commercial music.

### What the data reveals about pop music evolution

Joan Serrà et al. (*Scientific Reports*, 2012) analyzed ~464,000 songs from 1955–2010, finding **restriction of pitch transitions** over time (fewer unique chord/melody paths used), **homogenization of the timbral palette**, and **growing loudness** (the "Loudness War"). Their provocative conclusion: "An old tune could perfectly sound novel and fashionable, provided that it consisted of common harmonic progressions, changed the instrumentation, and increased the average loudness."

Matthias Mauch et al. (*Royal Society Open Science*, 2015) analyzed ~17,000 Billboard Hot 100 recordings and identified three stylistic **"revolutions"**: **~1964** (British Invasion/soul), **~1983** (synths/drum machines), and **~1991** (hip-hop/rap — the greatest single revolution). They found 1986 was the least diverse year, attributed to the sudden popularization of drum machines. Notably, Serrà found decreasing diversity while Mauch found it increased after a 1980s dip — the discrepancy reflects methodological differences, with Mauch's less reductionistic approach including rhythmic features.

Elizabeth Margulis's *On Repeat* (Oxford, 2014) provides the cognitive science foundation: **repetition is a "design feature" of music** that triggers an attentional shift from local to global processing, enhances pleasure through implicit processing, and makes even atonal contemporary music sound more enjoyable, more interesting, and more likely to be human-composed.

### Hit song science: 75–88% accuracy, but social factors dominate

Predicting commercial success from audio features alone achieves **~75% accuracy** using Spotify features (danceability, energy, valence, loudness, tempo) with logistic regression, rising to **~88%** with Random Forest on larger datasets. The most striking result: Zak et al. (*Frontiers in AI*, 2023) used neurophysiologic responses (EEG-based "immersion") to achieve **97% accuracy** with ensemble ML on neural data, and found that **self-reported liking only predicts hits if the listener already knows the song**. The consensus: intrinsic musical features are necessary but insufficient — social and marketing factors remain at least as important.

---

## Chinese pop music: a rapidly maturing computational landscape

### POP909 is the essential C-pop dataset

The **POP909 Dataset** (Wang, Chen, Jiang et al., Music X Lab / NYU Shanghai, ISMIR 2020) is the single most important resource for Chinese pop computational analysis: **909 Chinese pop songs** with vocal melody MIDI, lead instrument melody MIDI, piano accompaniment MIDI, chord annotations, key annotations, beat/downbeat annotations, and tempo curves — all hand-labeled. Multiple arrangement versions per song make it invaluable for studying C-pop harmonic and melodic patterns.

The broader **CCMusic Database** (China Conservatory of Music, Fudan University, Zhejiang University; TISMIR 2025) is the most comprehensive open Chinese MIR database, covering pop, folk, traditional instrument sounds, pentatonic mode annotations, singing technique labels (breath, falsetto, vibrato, mute, slide), and song structure annotations. Additional datasets include **OpenCpop** (100 Mandarin songs, professional studio quality), **M4Singer** (multi-singer Mandarin corpus), **MPop600** (600 pop songs, 4 vocalists), **OpenGufeng** (chord-melody data for Chinese-style "古风" music), and **MIR-1K/MIR-ST500** (singing voice separation/transcription).

### The Royal Road progression and C-pop's harmonic fingerprint

The **"Royal Road" progression (王道進行)** — **IV△7–V7–iii7–vi** — is the most distinctive harmonic signature of East Asian pop music. Originating in 1970s Japanese city pop, it became foundational in 1990s J-pop and was adopted heavily in C-pop by artists like Jay Chou, Mayday, and JJ Lin. C-pop harmony differs from Western pop in several systematic ways: **heavier use of seventh chords** in primary progressions, **subdominant (IV) emphasis** as starting/focal point rather than I, **prominent iii chord** functioning as V/vi (far more common than in Western pop), **preference for deceptive cadences** (V–vi over V–I), and **pentatonic melodic lines layered over Western-derived harmonic progressions**. The "中国风" (Chinese style) sub-genre, exemplified by Jay Chou, specifically marries pentatonic melodies and traditional instrument timbres with Western chord structures.

Quantitative analysis (Journal of Mathematics and Music, 2024) found that in Chinese popular music, **Yu (羽) mode is most common**, followed by Gong (宫) and Shang (商), while Jue (角) mode is least used. The five pentatonic modes — Gong, Shang, Jue, Zhi (徵), Yu — with added tones Qingjue (清角) and Biangong (变宫) create the extended Chinese scale system. Fudan University's CNPM Database and CNN-based automatic mode recognition (ISMIR 2022) enable computational identification of these modes from audio.

### Mandarin tones and melody: a soft constraint

Research consistently shows that in Mandarin pop, **the melody dominates over lexical tones** — native speakers understand lyrics from context without tonal information (Chao 1956, Chan 1987). This contrasts sharply with **Cantonese pop, where 91.8% tone-melody correspondence** is preserved (Wong & Diehl 2002). Skilled Mandarin songwriters still avoid the most egregious tone-melody mismatches, and analysis of 10,427 phrases from the Mpop600 dataset shows non-random alignment (Segment Match Rate ~81%), but this is a soft rather than hard constraint. An agent-driven LLM system for Mandarin lyric generation (arXiv 2410.01450, 2024) demonstrated that multi-agent architecture can achieve 80% accuracy in generating Chinese lyrics with exact character counts and reasonable tone-melody alignment.

### Chinese AI music generation is exploding

The field is advancing at remarkable speed. **56.9% of independently released new songs in China during Q1 2025 were AI-generated**, per People's Daily. Key systems include:

- **YuE (乐)** (HKUST/M-A-P, 2025): Built on LLaMA2, generates lyrics-to-full-song up to 5 minutes with dual-track vocal + accompaniment output in Chinese/English/Japanese/Korean. Apache 2.0 license.
- **Tencent SongGeneration/LeVo** (2025): ~3B parameter model producing full songs with vocals, multi-track output, and style following. Open-source, Apache 2.0.
- **SongComposer** (Shanghai AI Lab/CUHK/Beihang, ACL 2025): LLM simultaneously composing lyrics AND melodies in symbolic format, trained on 280K lyrics + 20K melodies in Chinese and English.
- **ACE-Step** (ACE Studio + StepFun, 2025): Hybrid Qwen3 language model planner + Diffusion Transformer renderer, generating 4-minute songs in 2 seconds, supporting 50+ languages including Chinese.
- **Synthesizer V** (Dreamtonics): AI singing voice synthesis supporting Mandarin, Cantonese, and cross-lingual synthesis — a production-ready vocal rendering engine.

The leading research lab is **Music X Lab** (Gus Xia, NYU Shanghai/MBZUAI), responsible for POP909, AccoMontage, Beat Transformer, and Polyffusion. Tencent Music's Venus platform has reached **26+ million AI-generated tracks**, while NetEase's Tianyin has produced 40,000+ original AI pieces.

---

## GitHub projects and LLM integration for music theory

### Key open-source "theory as code" projects

Beyond the major libraries, several GitHub projects encode specific theory subsystems as standalone tools:

**ekzhang/harmony** solves four-part SATB voice leading from Roman numeral progressions using dynamic programming, implementing parallel-fifth avoidance and proper voice-leading constraints on top of music21. **HarmonySolver** (Swift) provides a clean constraint architecture with ChordEnumerator + SolverStrategy pattern. **The Harmonic Algorithm** (Haskell) implements Hindemith dissonance ranking, cyclic DP voice leading, and a Creative Systems Framework pipeline (Rules → Evaluation → Traversal). **musicntwrk** uses network/graph theory for harmonic analysis, including Tonnetz construction and the Chinese Postman algorithm for optimal harmonic paths. **total-serialism** (JavaScript) packages algorithmic composition building blocks: Euclidean rhythms, Lindenmayer strings, cellular automata, Fibonacci sequences, Markov chains, and twelve-tone techniques.

The most directly relevant recent work is **Rule-Guided Music Diffusion** (Yujia Huang et al., ICML 2024 Oral), which demonstrates how to combine symbolic music generation with **non-differentiable music theory rules** as classifier guidance for diffusion models. New rules can be added by writing short rule programs in Python — establishing a template for how an LLM-based system could inject theory constraints into neural generation.

### LLMs for music: promising but theory-limited

**ChatMusician** (ACL Findings 2024) showed that an LLM fine-tuned on ABC notation (LLaMA2-7B + 4B token MusicPile) can surpass GPT-4 in composition tasks. However, it also introduced **MusicTheoryBench** revealing that ALL tested LLMs — including GPT-4 — perform poorly on multi-step music *reasoning* (~25%, barely above random). **Music knowledge ≠ music reasoning.** This confirms the need for external rule engines alongside LLMs.

**ComposerX** (2024) and its successor **CoComposer** (2025) demonstrate multi-agent symbolic composition with GPT-4, using 5–6 specialized agents (Leader, Melody, Harmony, Instrument, Reviewer, Arrangement). In Turing tests, ~32.2% of ComposerX's good pieces were indistinguishable from human compositions. **ByteComposer** (2024) embeds the LLM as an expert module with a "library of music theory knowledge" within a four-stage pipeline: Conception Analysis → Draft Composition → Self-Evaluation → Aesthetic Selection.

**MusicLang** deserves special attention: it combines a Python music DSL with LLAMA2-based prediction, using enriched tokenization that describes chords and scales per bar and normalizes melodies relative to the current chord/scale. It supports counterpoint rules (`.get_counterpoint()`), chord progression specification, and inpainting — making it the **closest existing tool to an LLM-native music theory engine**.

### Ontologies and knowledge graphs for formal music theory

The **Polifonia Ontology Network** (EU H2020, ISWC 2023) is the most comprehensive formal representation, including a **Roman Chord Ontology** and the companion **ChoCo (Chord Corpus)** — a 20,000+ timed harmonic annotation knowledge graph with SPARQL endpoint, published in *Nature Scientific Data* (2023). A **Functional Harmony Ontology** (2022) uses OWL 2 RL to enable SPARQL-based reasoning about chord progressions. These could provide structured, queryable context for an LLM — answering questions like "what chords commonly follow a V7/vi in the key of C major?" with formal, corpus-backed responses.

---

## The gap map: what music theory is NOT yet well-formalized

The most significant finding of this research is how much of practical music theory remains **unformalized**. Here is a systematic assessment:

**Well-formalized (usable today):** Pitch/note representation, intervals, scales/modes, chord identification and construction, key signature mechanics, basic four-part harmony rules (parallel fifths/octaves, voice crossing, doubling), rhythm primitives, diatonic chord progressions, Euclidean rhythms, species counterpoint.

**Partially formalized (gaps remain):** Voice leading (basic rules exist, but style-specific voicing for jazz/pop/gospel is incomplete), functional harmony (Roman numerals work but modal interchange and chromatic harmony are inconsistently encoded), modulation (detection exists in music21, but modulation *planning* algorithms are rare), harmonic rhythm (chord-change timing relative to meter is rarely formalized).

**Poorly or not formalized at all:**

- **Musical form and structure** — No comprehensive code formalizes verse-chorus-bridge, AABA, sonata form, or other structures as executable, generative rules. Most systems treat form as user-specified templates rather than derived structures.
- **Orchestration and arrangement rules** — Instrument ranges exist, but idiomatic writing rules (brass voicing, string doublings, woodwind color, band arrangement conventions) are essentially absent from any library.
- **Tension/release curves** — No formalization of how dissonance/consonance should unfold over time across different styles and sections.
- **Melodic contour rules** — Rules for "good" melody writing (phrase shapes, climax placement, rhythmic variety, hook construction) are not encoded anywhere.
- **Groove, swing, and feel** — Timing deviations from the grid that create pocket, swing, shuffle, and humanization have no formal rule representation despite being central to pop/R&B/hip-hop production.
- **Style-specific conventions** — Jazz voicing rules, gospel harmony, EDM arrangement patterns, hip-hop beat construction, and K-pop/C-pop structural formulas are not formalized.
- **Schenkerian analysis** — Despite being one of the most important analytical frameworks in Western theory, no complete algorithmic implementation exists.
- **Emotional/affective mapping** — The relationship between musical elements and emotional responses is not systematically formalized as computable rules.
- **Cross-cultural theory systems** — Maqam, raga, gamelan, and Chinese pentatonic theory have minimal computational formalization (the CNPM database and xuangong transformation theory are early steps for Chinese music).
- **Production rules** — Mixing decisions, arrangement density, instrumentation choices as a function of genre/style/section are entirely unformalized.

These gaps represent the highest-value targets for an LLM-based music agent. An LLM's strength — encoding tacit, style-specific knowledge as natural language rules — directly complements the formalized constraint systems' strength at enforcing hard music-theoretic invariants.

---

## Conclusion: toward an LLM music production pipeline

The landscape reveals a clear architectural pattern for a viable LLM-based music production system. The **LLM layer** generates high-level structure (form templates, chord progressions as Roman numerals, melodic contour sketches, style parameters, lyrics) — leveraging its ability to encode the tacit, style-specific knowledge that remains unformalized. The **theory validation layer** (music21, tonal.js, musicpy) converts, checks, and transforms the symbolic output. A **constraint solver layer** (Cluster Engine, Diatony/Gecode) ensures hard music-theoretic invariants are satisfied. The **knowledge layer** (Hooktheory API for chord transition probabilities, ChoCo for corpus-backed harmonic context, POP909 for C-pop patterns) provides empirical grounding. Finally, the **rendering layer** (Synthesizer V or ACE Studio for vocals, YuE or LeVo for full audio) produces the final output.

For Chinese pop specifically, the pipeline would encode **Yu-mode pentatonic priors**, the **Royal Road progression family** (IV△7–V7–iii7–vi and its rotations), **iii-chord emphasis**, soft tone-melody alignment constraints for Mandarin, and train on POP909's 909 annotated songs. The biggest architectural insight from the research: LLMs exhibit poor multi-step music *reasoning* despite possessing music *knowledge* (ChatMusician's MusicTheoryBench shows ~25% accuracy on reasoning tasks). This means the external rule engine is not optional — it is essential. The LLM proposes; the theory engine disposes.