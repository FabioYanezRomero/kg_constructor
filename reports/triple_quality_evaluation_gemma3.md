# Triple Quality Evaluation: Gemma3 (Ollama/LMStudio) & Gemini API Models

**Date:** 2026-03-24
**Record:** UKSC-2009-0143 (Sigma Finance Corporation)
**Domain:** Legal | **Mode:** Open | **Temperature:** 0.0

---

## Experiment Summary

| Model | Backend | Duration | Total Triples | Components | Output Directory |
|-------|---------|:--------:|:-------------:|:----------:|-----------------|
| gemini-2.0-flash | Gemini API | 12s | 11 | 1 | `single_extraction_20260324_092214` |
| gemini-2.5-flash | Gemini API | 110s | 43 | 1 | `single_extraction_20260324_092240` |
| gemini-3-flash-preview | Gemini API | 46s | 15 | 1 | `single_extraction_20260324_092443` |
| gemini-3-pro-preview | Gemini API | 58s | 10 | 1 | `single_extraction_20260324_092539` |
| gemini-3.1-pro-preview | Gemini API | 50s | 10 | 1 | `single_extraction_20260324_092649` |
| gemma3:1b | Ollama | 31s | 32 | 1 | `single_extraction_ollama_20260323_203922` |
| gemma3:4b | Ollama | 35s | 13 | 1 | `single_extraction_ollama_20260323_200118` |
| gemma3:12b | Ollama | 66s | 13 | 1 | `single_extraction_ollama_20260323_200204` |
| gemma3:27b | Ollama | 198s | 21 | 1 | `single_extraction_ollama_20260323_200319` |
| gemma-3-1b | LMStudio | 316s | 6 | 6 | `single_extraction_lmstudio_20260323_200806` |
| gemma-3-4b | LMStudio | 68s | 29 | 5 | `single_extraction_lmstudio_20260323_201333` |
| gemma-3-12b | LMStudio | 146s | 27 | 5 | `single_extraction_lmstudio_20260323_201450` |
| gemma-3-27b | LMStudio | 246s | 30 | 1 | `single_extraction_lmstudio_20260323_201726` |

---

## Source Text: Key Facts (Ground Truth)

From the UKSC-2009-0143 text, these are the factual assertions a complete extraction should capture:

1. Sigma Finance Corporation **is a** SIV
2. Sigma **established to invest in** asset-backed securities and financial instruments
3. Sigma **aimed to profit from** difference between funding cost and investment returns
4. Impact of **sub-prime mortgage market** caused assets to fall short
5. Assets **fall short of** amount needed to pay secured creditors
6. All assets **secured under** a security trust deed (STD)
7. STD **in favour of** Sigma's creditors
8. **Dispute between** various classes of creditors
9. Dispute **about correct application of** STD
10. Sigma **has insufficient funds** to satisfy all creditors
11. Sigma **failed to meet** a margin call
12. STD **provided for** 60-day realisation period
13. Trustees **should use** assets to create two pools (short/long term liabilities)
14. Clause 7.6: Security Trustee **shall discharge** Short Term Liabilities during realisation period
15. Court of Appeal **construed** clause 7.6 as preferential distribution
16. Distribution **made according to** dates when payment became due

---

## A. Extraction Quality (Explicit + Contextual Triples)

| Fact | G-2.0F | G-2.5F | G-3F | G-3P | G-3.1P | O-1b | O-4b | O-12b | O-27b | L-1b | L-4b | L-12b | L-27b |
|------|:------:|:------:|:----:|:----:|:------:|:----:|:----:|:-----:|:-----:|:----:|:----:|:-----:|:-----:|
| 1. Sigma is SIV | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| 2. Invested in securities | - | Y | Y | Y | Y | - | - | - | Y | - | Y | Y | Y |
| 3. Profit from difference | Y | Y | - | - | - | Y | Y | Y | Y | Y | Y | Y | Y |
| 4. Sub-prime impact | - | Y | - | - | - | - | - | - | - | Y* | - | Y | Y |
| 5. Assets fall short | Y | Y | - | - | - | Y* | Y | Y | Y | - | Y | Y | Y |
| 6. Secured under STD | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y |
| 7. STD in favour of creditors | - | Y | Y | Y | Y | - | - | - | Y | - | Y | - | Y |
| 8. Creditor dispute | Y | Y | - | - | - | Y* | Y | Y | Y | - | Y | Y | Y |
| 9. Dispute about STD application | - | Y | - | - | - | - | Y | - | Y | - | - | Y | Y |
| 10. Insufficient funds | - | Y | - | Y* | Y | - | - | - | - | - | - | Y | Y |
| 11. Failed margin call | - | Y | Y | Y | Y | - | - | - | Y | - | - | Y | Y |
| 12. 60-day realisation | Y | Y | Y | Y | Y | - | Y | Y | Y | - | - | Y | Y |
| 13. Two pools of funds | - | Y | - | - | - | - | - | - | Y | - | - | Y | Y |
| 14. Clause 7.6 provisions | - | Y | Y | - | - | - | Y | Y | Y | Y | Y | Y | Y |
| 15. Court of Appeal construed | Y | Y | Y | Y | Y | - | Y | Y | Y | Y | Y | Y | Y |
| 16. Distribution by dates | - | Y | Y* | - | - | - | - | - | Y | - | - | Y | Y |
| **Coverage** | **7/16** | **16/16** | **8/16** | **8/16** | **8/16** | **5/16** | **8/16** | **7/16** | **14/16** | **5/16** | **8/16** | **13/16** | **15/16** |

*\* = partially correct or with quality issues (see Factual Accuracy section)*

---

## B. Entity Normalization Issues

### Gemini API Models

| Model | Assessment |
|-------|-----------|
| **Gemini 2.0 Flash** | Clean normalization. Uses "Sigma Finance Corporation", "clause 7.6", "security trust deed" consistently. Augmentation introduces "The Legal Case" as a generic hub entity. |
| **Gemini 2.5 Flash** | Excellent. Uses "Sigma Finance Corporation", "security trust deed (STD)", "clause 7.6 of security trust deed (STD)" consistently. Differentiates "Sigma Finance Corporation's assets" from "Sigma Finance Corporation's available assets". Separate entities for "cash", "realisable assets", "maturing assets" -- all well-formed. |
| **Gemini 3 Flash Preview** | Very clean. Uses "Sigma Finance Corporation", "security trust deed", "clause 7.6 of security trust deed". Concise entity names. Augmentation introduces "The Legal Case" hub alongside direct bridges. |
| **Gemini 3 Pro Preview** | Very clean and minimal. Same entity names as 3 Flash. Augmentation creates no hub entities -- all bridges are direct (e.g., "owns", "part_of", "owes_money_to"). |
| **Gemini 3.1 Pro Preview** | Near-identical to 3 Pro. Clean entities with direct bridges. Slightly different relation naming (`"belongs_to"` vs `"owns"`, `"has_insufficient_funds_for"` vs `"owes_money_to"`). |

### Local Models (Ollama / LMStudio)

| Model | Issue |
|-------|-------|
| **Ollama 1b** | Uses "Sigma" instead of "Sigma Finance Corporation" inconsistently. `tail: "use Sigma's assets to create"` is a sentence fragment, not an entity. |
| **Ollama 4b** | Good normalization. Uses full name "Sigma Finance Corporation" consistently. Invents "Financial Framework" as a hub entity (not in text). |
| **Ollama 12b** | Good. Introduces "The Legal Case" as a synthetic hub entity. `tail: "profit from the difference"` is a truncated fragment. `tail: "assets"` is too vague. |
| **Ollama 27b** | Best Ollama normalization. Uses "Sigma Finance Corporation's assets" as a distinct entity (reasonable). Some hub entities ("The Legal Case", "financial instruments") are synthetic. |
| **LMS 1b** | Inconsistent ("Sigma" vs "Sigma Finance Corporation", "All of Sigma's assets", "The STD"). `tail: "during the Realisation Period"` is not a valid entity. |
| **LMS 4b** | Mixes naming conventions ("Sigma Finance Corporation" vs "(SIV)" as a standalone tail). `tail: "creditors"` is redundant with head "various classes of creditors". Creates "Financial Framework" and "Contractual Obligations" (not in text). |
| **LMS 12b** | Good normalization overall. Uses "Sigma Finance Corporation" consistently. Introduces hubs "The Legal Case", "Financial Framework", "Corporate Structure". |
| **LMS 27b** | Best local model. Clean entities: "dispute in UKSC-2009-0143", "Sigma's assets", "security trust deed". Introduces "The Legal Case" as hub but uses it meaningfully. |

---

## C. Relation Quality

### Gemini API Models

| Model | Relation Quality | Examples |
|-------|-----------------|---------|
| **Gemini 2.0 Flash** | Good | Clean extraction: `"is"`, `"aimed to profit from"`, `"fall short of amount needed to pay"`, `"secured under"`, `"provided for"`, `"construed"`. Augmentation uses generic `"subject_of"`, `"involved_in"`, `"part_of_context"`. |
| **Gemini 2.5 Flash** | Excellent | Rich, precise relations: `"is a type of"`, `"invests in"`, `"aimed to profit from"`, `"impacted"`, `"insufficient to pay"`, `"in favour of"`, `"between"`, `"concerns"`, `"failed to meet"`, `"shall discharge"`, `"distributed preferentially to"`, `"made according to"`. Augmentation: `"caused financial distress for"`, `"is part of"`, `"is a type of"`, `"mandates"`, `"involves creation of"`. |
| **Gemini 3 Flash Preview** | Good | Clean: `"is"`, `"invests in"`, `"has assets secured under"`, `"failed to meet"`, `"provided for"`, `"construed"`, `"held"`. Augmentation: `"is_part_of"`, `"subject_of_dispute_in"`, `"concerns_payment_to"`, `"adjudicated_by"`. |
| **Gemini 3 Pro Preview** | Very Good | Clean, precise: `"is"`, `"invests in"`, `"secured under"`, `"is in favour of"`, `"failed to meet"`, `"provided for"`, `"construed"`. Augmentation: `"owns"`, `"part_of"`, `"owes_money_to"` -- all semantically specific. |
| **Gemini 3.1 Pro Preview** | Very Good | Nearly identical to 3 Pro. Relations: `"belongs_to"`, `"part_of"`, `"has_insufficient_funds_for"` -- marginally more descriptive augmentation naming. |

### Local Models (Ollama / LMStudio)

| Model | Relation Quality | Examples of Problems |
|-------|-----------------|---------------------|
| **Ollama 1b** | Poor | `"has meant that"` (sentence fragment as relation), `"should have"` (vague), `"is between"` (ambiguous) |
| **Ollama 4b** | Good | Relations are descriptive: `"available assets fall short of"`, `"dispute is about"`. Some invented: `"involved_in"`, `"governed_by_context"` |
| **Ollama 12b** | Moderate | Clean extraction relations. Augmented relations use generic templates: `"involved_in"`, `"part_of_context"` |
| **Ollama 27b** | Good | Best Ollama relations: `"established to invest in"`, `"failed to meet"`, `"provided for discharge of"`. Augmented use `"connected_to"`, `"part_of_context"` |
| **LMS 1b** | Poor | `"is SIV"` (non-standard), `"provided that"` with bad tail `"during the Realisation Period"`, `"stemming from"` with wrong head |
| **LMS 4b** | Moderate | Some relations embed too much: `"is a structured investment vehicle"` (should be in tail), `"construed clause 7.6 as meaning..."` (entire clause in relation) |
| **LMS 12b** | Good | Clean: `"has assets that fall short of"`, `"has insufficient funds to satisfy"`, `"failed to meet"`. Augmented use templates appropriately. |
| **LMS 27b** | Best Local | Clear, normalized relations: `"is a"`, `"established to invest in"`, `"aimed to profit from"`, `"failed to meet"`. Augmented: `"connected_to"`, `"part_of_context"`, `"subject_of"` |

---

## D. Duplication Analysis

| Model | Total Triples | Unique Triples | Duplicates | Duplicate Rate |
|-------|:------------:|:--------------:|:----------:|:--------------:|
| Gemini 2.0 Flash | 11 | 11 | 0 | **0%** |
| Gemini 2.5 Flash | 43 | 43 | 0 | **0%** |
| Gemini 3 Flash Preview | 15 | 15 | 0 | **0%** |
| Gemini 3 Pro Preview | 10 | 10 | 0 | **0%** |
| Gemini 3.1 Pro Preview | 10 | 10 | 0 | **0%** |
| Ollama 1b | 32 | ~8 | ~24 | **75%** |
| Ollama 4b | 13 | 13 | 0 | **0%** |
| Ollama 12b | 13 | 13 | 0 | **0%** |
| Ollama 27b | 21 | 21 | 0 | **0%** |
| LMS 1b | 6 | 6 | 0 | **0%** |
| LMS 4b | 29 | ~14 | ~15 | **52%** |
| LMS 12b | 27 | ~16 | ~11 | **41%** |
| LMS 27b | 30 | 30 | 0 | **0%** |

**All Gemini API models produce zero duplicates.** This is consistent across all 5 models tested, regardless of generation or tier.

**Ollama 1b** has a severe duplication problem -- augmentation iterations repeated the same triples verbatim (e.g., `"Sigma Finance Corporation" -> "is a" -> "SIV"` appears 10+ times). The 1b model lacks the instruction-following ability to generate *new* bridging triples and instead regurgitates existing ones.

**LMS 4b and 12b** also have significant duplication in their augmentation phases, repeating the same 5-triple chain across iterations.

---

## E. Augmentation Quality

### Gemini API Models

| Model | Strategy | Quality Assessment |
|-------|----------|-------------------|
| **Gemini 2.0 Flash** | Hub-node ("The Legal Case") | **Good** -- creates a central hub connected via `subject_of`, `involved_in`, `part_of_context`. Achieves 1 component with 4 augmentation triples. Effective but produces a star topology. |
| **Gemini 2.5 Flash** | Component-aware semantic bridging | **Excellent** -- the best augmentation across all models. 18 contextual triples with explicit component references in justifications. Uses causal links (`"caused financial distress for"`), entity resolution (`"is part of"`, `"is a type of"`), hierarchical decomposition (`"cash"`, `"realisable assets"`, `"maturing assets"` as parts of total assets), and coreference bridges. No generic hubs. |
| **Gemini 3 Flash Preview** | Hybrid (semantic bridges + hub) | **Good** -- 6 contextual triples combining direct semantic bridges (`"is_part_of"`, `"subject_of_dispute_in"`, `"concerns_payment_to"`) with a "The Legal Case" hub for remaining gaps. Clean justifications. |
| **Gemini 3 Pro Preview** | Direct semantic bridges | **Very Good** -- only 3 contextual triples needed, all semantically precise: `"owns"` (Sigma → assets), `"part_of"` (clause → STD), `"owes_money_to"` (Sigma → creditors). No hub entities. Most efficient augmentation. |
| **Gemini 3.1 Pro Preview** | Direct semantic bridges | **Very Good** -- nearly identical strategy to 3 Pro. 3 contextual triples: `"belongs_to"` (assets → Sigma), `"part_of"` (clause → STD), `"has_insufficient_funds_for"` (Sigma → creditors). No hub entities. |

### Local Models (Ollama / LMStudio)

| Model | Strategy | Quality Assessment |
|-------|----------|-------------------|
| **Ollama 1b** | Regurgitates existing triples | **Useless** -- no real bridging, just copies extraction triples with `contextual` tag |
| **Ollama 4b** | Creates "Financial Framework" hub | **Moderate** -- connects components via synthetic concepts, but `"Financial Framework"` is vague and not in text |
| **Ollama 12b** | Creates "The Legal Case" hub | **Moderate** -- better hub concept, but generic. Successfully bridges 9->4 components in iteration 1 |
| **Ollama 27b** | Component-aware bridging | **Good** -- explicitly references "Component 1", "Component 2", creates targeted bridges between disconnected subgraphs |
| **LMS 1b** | Timed out | **Failed** -- 300s timeout exceeded, no augmentation produced |
| **LMS 4b** | Repeating pattern of 5 triples | **Poor** -- same 5-triple chain repeated 3x, creates "Financial Framework" -> "Contractual Obligations" (hallucinated concepts) |
| **LMS 12b** | Hub + specific bridges | **Moderate** -- "The Legal Case" as hub plus "Financial Framework" and "Corporate Structure". Some over-abstraction. |
| **LMS 27b** | Component-aware + hub | **Good** -- targeted component bridging plus "The Legal Case" hub that connects all subgraphs. Clean justifications. Achieved 1 component. |

---

## F. Factual Accuracy

### Gemini API Models

| Model | Factual Errors |
|-------|---------------|
| **Gemini 2.0 Flash** | No factual errors. All 7 extraction triples are accurate. Augmentation hub triples are structurally sound. |
| **Gemini 2.5 Flash** | No factual errors. All 25 extraction triples are well-supported by the source text. Augmentation triples maintain factual correctness with well-justified component bridges. The most precise model overall. |
| **Gemini 3 Flash Preview** | Minor: `"Court of Appeal" -> "held" -> "assets fall to be distributed preferentially to certain creditors"` is an accurate summary but uses a sentence-length entity as a tail rather than a concise concept. All other triples clean. |
| **Gemini 3 Pro Preview** | No factual errors. All extraction and augmentation triples are accurate and well-formed. |
| **Gemini 3.1 Pro Preview** | No factual errors. Identical accuracy profile to Gemini 3 Pro. |

### Local Models (Ollama / LMStudio)

| Model | Factual Errors |
|-------|---------------|
| **Ollama 1b** | `"should have" -> "use Sigma's assets to create"` (tail is a verb phrase, not an entity). Relations like `"has meant that"` are not meaningful predicates. |
| **Ollama 4b** | `"Financial Framework"` as an entity is hallucinated (not in the text). Otherwise factually sound. |
| **Ollama 12b** | `tail: "profit from the difference"` is truncated. `"Court of Appeal" -> "construed" -> "remaining assets"` is incorrect (the Court construed *clause 7.6*, not "remaining assets"). |
| **Ollama 27b** | Very few errors. `"financial instruments" -> "involved_in" -> "The Legal Case"` is loosely supported. All extraction triples are factually accurate. |
| **LMS 1b** | `"The impact on the financial markets" -> "stemming from" -> "Sigma's available assets"` reverses causality (impact stems from sub-prime market, not from assets). `"The STD" -> "provided that" -> "during the Realisation Period"` has an incomplete tail. |
| **LMS 4b** | `"various classes of creditors" -> "is dispute in this case between" -> "creditors"` is a circular, meaningless triple. `"Sigma's activities and the resulting legal dispute"` as a tail is a sentence, not an entity. |
| **LMS 12b** | `"Corporate Structure"` as a concept entity is hallucinated. Some augmented triples are over-abstracted but not factually wrong. |
| **LMS 27b** | Very clean. `"dispute in UKSC-2009-0143"` is a well-formed entity reference. The "The Legal Case" hub triples are structurally sound even if somewhat generic. |

---

## G. Summary Scorecard

| Metric | G-2.0F | G-2.5F | G-3F | G-3P | G-3.1P | O-1b | O-4b | O-12b | O-27b | L-1b | L-4b | L-12b | L-27b |
|--------|:------:|:------:|:----:|:----:|:------:|:----:|:----:|:-----:|:-----:|:----:|:----:|:-----:|:-----:|
| **Fact Coverage** (0-5) | 2 | 5 | 2.5 | 2.5 | 2.5 | 1.5 | 2.5 | 2 | 4.5 | 1.5 | 2.5 | 4 | 5 |
| **Entity Quality** (0-5) | 4 | 5 | 4.5 | 4.5 | 4.5 | 1 | 3.5 | 3 | 4 | 1.5 | 2 | 3.5 | 4.5 |
| **Relation Quality** (0-5) | 3.5 | 5 | 4 | 4.5 | 4.5 | 1 | 3.5 | 3 | 4 | 1 | 2.5 | 3.5 | 4.5 |
| **Duplication** (0-5) | 5 | 5 | 5 | 5 | 5 | 0.5 | 5 | 5 | 5 | 5 | 2 | 2.5 | 5 |
| **Augmentation** (0-5) | 3 | 5 | 4 | 4.5 | 4.5 | 0 | 3 | 3 | 4 | 0 | 1.5 | 3 | 4.5 |
| **Factual Accuracy** (0-5) | 5 | 5 | 4.5 | 5 | 5 | 2 | 4 | 3.5 | 4.5 | 1.5 | 2.5 | 3.5 | 4.5 |
| **Connectivity** (1 = best) | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 6 | 5 | 5 | 1 |
| **Duration** | 12s | 110s | 46s | 58s | 50s | 31s | 35s | 66s | 198s | 316s | 68s | 146s | 246s |
| **TOTAL** (/30) | **22.5** | **30** | **24.5** | **26** | **26** | **6** | **21.5** | **19.5** | **26** | **11** | **15** | **20** | **28** |

---

## H. Key Findings

### Gemini API Models

1. **Gemini 2.5 Flash achieves a perfect score (30/30)** -- the only model to capture all 16 ground truth facts with excellent entity normalization, zero duplication, and the best augmentation strategy (component-aware semantic bridging with entity resolution). It is the clear winner across all 13 models tested.

2. **Gemini 3 Pro and 3.1 Pro produce nearly identical output** -- both extract the same 7 explicit triples with the same entity names. They differ only in augmentation relation naming (`"owns"` vs `"belongs_to"`, `"owes_money_to"` vs `"has_insufficient_funds_for"`). This suggests they share the same underlying extraction capability with minor prompting differences.

3. **Gemini 2.0 Flash is the fastest model (12s)** but extracts the fewest facts (7/16) among Gemini models. It trades coverage for speed and remains a viable option for rapid prototyping where coverage is not critical.

4. **All Gemini models achieve 1 connected component and zero duplication** -- a stark contrast to local models where only 3 out of 8 achieved full connectivity and 3 had significant duplication. API-level instruction following is categorically superior.

5. **Gemini 3 Flash Preview vs 3 Pro Preview** -- Flash extracts one more fact (8 vs 7 with explicit only, though Pro captures fact 10 via contextual bridge) and is faster (46s vs 58s). Pro has slightly cleaner augmentation (no hub entity). The two are nearly equivalent in quality.

### Local Models (unchanged from previous evaluation)

6. **LMStudio 27b is the best local model (28/30)**, with the highest local fact coverage (15/16), clean entity normalization, no duplication, and successful augmentation achieving 1 connected component.

7. **Ollama 27b ties with Gemini 3 Pro and 3.1 Pro at 26/30**, despite being a 27B local model. Its strength is fact coverage (14/16) -- better than all Gemini models except 2.5 Flash. Its weakness is generic augmentation relations.

8. **The 1b models are not viable** for this task on any backend. Ollama 1b produces massive duplication (75% rate), and LMStudio 1b times out during augmentation.

9. **Duplication is exclusively a local model problem** -- no Gemini API model produced any duplicate triples, while 3 of 8 local models had significant duplication (Ollama 1b: 75%, LMS 4b: 52%, LMS 12b: 41%).

### Cross-Provider Insights

10. **Coverage vs Quality tradeoff**: Gemini 2.5 Flash maximizes both, but among other models, local 27b variants (Ollama, LMStudio) extract more facts than most Gemini models while having lower entity/relation quality. Gemini models prioritize precision over recall.

11. **Augmentation strategies evolved across Gemini generations**: 2.0 Flash uses generic hubs, 2.5 Flash uses semantic entity resolution, 3.x models use minimal direct bridges. The trend is toward fewer, more precise augmentation triples.

12. **Speed vs Quality**: Gemini 2.0 Flash (12s) is 4-26x faster than local 27b models (198-246s) while matching their entity quality. Gemini 2.5 Flash (110s) takes comparable time to local 12b models but produces categorically better output.

---

## I. Recommendations

- **For production use (quality-first):** Gemini 2.5 Flash is the clear choice -- perfect fact coverage, best augmentation, excellent entity normalization, zero duplication. 110s per document is acceptable for batch processing.
- **For production use (speed-first):** Gemini 2.0 Flash (12s) or Gemini 3 Flash Preview (46s) for rapid processing at the cost of coverage (7-8/16 facts).
- **For local inference:** gemma3:27b on LMStudio (28/30, 246s) or Ollama (26/30, 198s). Best balance of quality and data sovereignty.
- **For rapid local prototyping:** gemma3:4b on Ollama (35s, decent quality, zero duplication)
- **Pipeline improvement:** Add a deduplication step in the augmentation phase to filter exact and near-duplicate triples before saving (primarily benefits local models)
- **Entity normalization:** Consider a post-processing step to normalize entity names (e.g., "Sigma" -> "Sigma Finance Corporation") -- primarily benefits local models; Gemini models rarely need this
- **Minimum model size:** gemma3:4b should be the minimum recommended model size for local knowledge graph extraction tasks
- **Gemini model selection:** Unless budget-constrained, Gemini 2.5 Flash is the recommended API model. The 3.x models do not improve on 2.5 Flash for this extraction task despite being newer.
