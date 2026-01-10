# Dual-Prompt System for Iterative Extraction

## Overview

The knowledge graph extraction system now uses **separate, customizable prompts** for each step of the iterative extraction process:

1. **Step 1 Prompt**: Initial comprehensive extraction
2. **Step 2 Prompt**: Connectivity-focused bridging/refinement

This separation allows you to fine-tune each stage independently for better results.

---

## Why Separate Prompts?

### Single Prompt Limitations

The original single-prompt approach asked the LLM to:
1. Extract all explicit relationships
2. Check connectivity
3. Add bridging triples if needed

This combined approach had issues:
- **Conflicting goals**: Extraction breadth vs connectivity focus
- **Unclear prioritization**: Should the LLM focus on completeness or connectivity?
- **No iteration feedback**: Cannot show component structure to guide bridging

### Dual-Prompt Advantages

✅ **Clear separation of concerns**:
- Step 1: Focus purely on comprehensive extraction
- Step 2: Focus purely on connectivity improvement

✅ **Better context for bridging**:
- Shows exact component structure
- Guides LLM to specific connection points

✅ **Independent customization**:
- Tune initial extraction for your domain
- Tune bridging strategy for your connectivity needs

✅ **Iterative feedback**:
- Step 2 sees results of Step 1
- Can adapt bridging based on component structure

---

## The Three Prompt Files

### 1. `legal_background_prompt.txt` (Original)

**Use case**: Simple one-step extraction (`USE_ITERATIVE_EXTRACTION=false`)

**Characteristics**:
- All-in-one: extraction + connectivity in single pass
- Asks for bridging triples within the same prompt
- 1 API call
- Faster but may produce more disconnected components

**When to use**:
- Quick testing
- Low cost priority
- Text with naturally well-connected content

### 2. `legal_background_prompt_step1_initial.txt` (New)

**Use case**: Step 1 of iterative extraction

**Focus**: Comprehensive initial extraction
- Extract ALL explicit relationships
- Don't worry about connectivity yet
- Be thorough and complete
- Label everything as "explicit"

**Key differences from original**:
- No connectivity instructions
- Emphasis on comprehensiveness
- Explicitly states "subsequent refinement step will analyze connectivity"
- More detailed entity and relation type guidance

**Example instructions**:
```
Focus on extracting ALL explicit relationships, events, and entities.
Be comprehensive: extract every relationship you can identify in the text.
At this stage, focus on explicit information only.
Do not worry about graph connectivity - just extract all explicit relationships.
```

### 3. `legal_background_prompt_step2_bridging.txt` (New)

**Use case**: Step 2 of iterative extraction (refinement)

**Focus**: Connectivity improvement
- Connect disconnected components
- Add minimal bridging triples
- Prefer explicit over contextual
- No re-extraction

**Key features**:
- Shows disconnected components
- Provides bridging strategies (in priority order)
- Emphasizes minimal additions
- Requires justification for contextual triples

**Example instructions**:
```
Extract ONLY bridging triples that connect the disconnected components.

Bridging Strategies (in order of preference):
1. Shared Entities
2. Implicit Relationships
3. Temporal Connections
4. Causal Connections
5. Hierarchical Relationships
6. Contextual Entities (minimal, only if necessary)
```

---

## Configuration

### Default Configuration (Iterative with Dual Prompts)

```bash
# In test_single_extraction.sh

# Enable iterative extraction
USE_ITERATIVE_EXTRACTION=true

# Step 1: Initial extraction
PROMPT_FILE_STEP1="/app/src/prompts/legal_background_prompt_step1_initial.txt"

# Step 2: Bridging/refinement
PROMPT_FILE_STEP2="/app/src/prompts/legal_background_prompt_step2_bridging.txt"
```

### Simple One-Step (Original Behavior)

```bash
# Disable iterative extraction
USE_ITERATIVE_EXTRACTION=false

# Use original single prompt
PROMPT_FILE="/app/src/prompts/legal_background_prompt.txt"
```

---

## Prompt Customization

### Customizing Step 1 (Initial Extraction)

**Example**: Add domain-specific entity types

```bash
# Create custom Step 1 prompt
cat > /app/prompts/medical_initial.txt << 'EOF'
You are an expert at extracting knowledge graphs from medical case notes.

Extract all explicit relationships focusing on:
- Medical conditions and symptoms
- Medications and treatments
- Diagnostic procedures
- Patient outcomes
- Temporal sequences

[Rest of prompt...]
EOF

# Use it
PROMPT_FILE_STEP1="/app/prompts/medical_initial.txt"
```

### Customizing Step 2 (Bridging)

**Example**: Emphasize temporal connections

```bash
# Create custom Step 2 prompt
cat > /app/prompts/temporal_bridging.txt << 'EOF'
The knowledge graph has {num_components} disconnected components:
{component_info}

Original text:
{text}

Focus on TEMPORAL connections:
1. Events that occurred simultaneously
2. Causal sequences (A led to B)
3. Timeline relationships

Extract minimal bridging triples to connect components.
EOF

# Use it
PROMPT_FILE_STEP2="/app/prompts/temporal_bridging.txt"
```

### Template Variables for Step 2

The bridging prompt supports these variables:
- `{num_components}` - Number of disconnected components (e.g., "11")
- `{component_info}` - Formatted component list (e.g., "Component 1: EntityA, EntityB...")
- `{text}` - Original full text

**Example usage in custom prompt**:
```
The graph has {num_components} components that need connecting.

Components:
{component_info}

Use this text:
{text}
```

---

## Comparison: Single vs Dual Prompts

### Example: Legal Case Extraction

**Text**: "Sigma Finance Corporation, a structured investment vehicle, faced difficulties during the 2008 financial crisis..."

#### With Single Prompt (`legal_background_prompt.txt`)

**One API call**:
```
You are an expert system for extracting knowledge graphs.

Extract all explicit triples.
If the graph is disconnected, add bridging triples.

Text: [full text]
```

**Result**:
- 34 triples extracted
- 11 disconnected components
- LLM tried to add bridging but within same extraction pass
- Connectivity: ❌ Poor

#### With Dual Prompts (Step 1 + Step 2)

**Step 1 API call** (`legal_background_prompt_step1_initial.txt`):
```
Focus on extracting ALL explicit relationships.
Do not worry about connectivity - just be comprehensive.

Text: [full text]
```

**Step 1 Result**:
- 34 triples extracted
- 11 components

**Step 2 API call** (`legal_background_prompt_step2_bridging.txt`):
```
The graph has 11 disconnected components:
Component 1: Sigma Finance Corporation, Security Trustee, STD
Component 2: creditor, payment, discharge
[...]

Original text: [full text]

Extract ONLY bridging triples to connect these components.
Focus on shared entities and implicit relationships.
```

**Step 2 Result**:
- +6 triples (iteration 1) → 6 components
- +7 triples (iteration 2) → 1 component
- Connectivity: ✅ Excellent

**Total**: 47 triples, fully connected graph, 3 API calls

---

## Prompt Engineering Tips

### For Step 1 (Initial Extraction)

✅ **DO**:
- Emphasize comprehensiveness
- List specific entity types for your domain
- List specific relation types for your domain
- Encourage splitting complex phrases
- Focus on explicit information

❌ **DON'T**:
- Mention connectivity
- Mention bridging
- Ask for minimal extraction
- Mix explicit and contextual in first pass

### For Step 2 (Bridging)

✅ **DO**:
- Show component structure clearly
- Provide bridging strategies
- Prioritize explicit over contextual
- Require justification for contextual
- Emphasize minimal additions
- Explicitly forbid re-extraction

❌ **DON'T**:
- Ask for comprehensive extraction
- Focus on entity types
- Allow hallucination
- Encourage many contextual triples

---

## Advanced Usage

### Domain-Specific Dual Prompts

Create tailored prompts for your domain:

**Medical domain**:
```bash
PROMPT_FILE_STEP1="/app/prompts/medical/initial_diagnosis.txt"
PROMPT_FILE_STEP2="/app/prompts/medical/treatment_connections.txt"
```

**Financial domain**:
```bash
PROMPT_FILE_STEP1="/app/prompts/finance/transaction_extraction.txt"
PROMPT_FILE_STEP2="/app/prompts/finance/entity_resolution.txt"
```

### A/B Testing Prompts

Compare different prompt strategies:

```bash
# Test 1: Conservative bridging
PROMPT_FILE_STEP2="/app/prompts/bridging_conservative.txt"
OUTPUT_DIR="/app/test_outputs/test1_conservative"
./test_single_extraction.sh

# Test 2: Aggressive bridging
PROMPT_FILE_STEP2="/app/prompts/bridging_aggressive.txt"
OUTPUT_DIR="/app/test_outputs/test2_aggressive"
./test_single_extraction.sh

# Compare results
jq '.graph_structure' /app/test_outputs/test1_conservative/metadata/*.json
jq '.graph_structure' /app/test_outputs/test2_aggressive/metadata/*.json
```

### Iterative Prompt Refinement

1. **Run extraction with default prompts**
2. **Analyze results** - Check metadata for disconnected components
3. **Identify issues** - Too many components? Too many contextual triples?
4. **Adjust prompts** - Modify Step 1 or Step 2
5. **Re-run and compare**

---

## Migration Guide

### From Single Prompt to Dual Prompts

**Before** (old configuration):
```bash
USE_ITERATIVE_EXTRACTION=false
PROMPT_FILE="/app/src/prompts/legal_background_prompt.txt"
```

**After** (new configuration):
```bash
USE_ITERATIVE_EXTRACTION=true
PROMPT_FILE_STEP1="/app/src/prompts/legal_background_prompt_step1_initial.txt"
PROMPT_FILE_STEP2="/app/src/prompts/legal_background_prompt_step2_bridging.txt"
```

**No other changes needed** - the script automatically uses the appropriate prompts.

### Backwards Compatibility

The original single-prompt approach still works:
```bash
USE_ITERATIVE_EXTRACTION=false
PROMPT_FILE="/app/src/prompts/legal_background_prompt.txt"
```

---

## Files Created

| File | Purpose | Type |
|------|---------|------|
| `legal_background_prompt.txt` | Original all-in-one | Single prompt |
| `legal_background_prompt_step1_initial.txt` | Initial extraction | Step 1 |
| `legal_background_prompt_step2_bridging.txt` | Bridging refinement | Step 2 |

All located in: `/app/src/prompts/`

---

## See Also

- [ITERATIVE_EXTRACTION_PROMPTS.md](ITERATIVE_EXTRACTION_PROMPTS.md) - Detailed prompt documentation
- [ITERATIVE_EXTRACTION_DEFAULT.md](ITERATIVE_EXTRACTION_DEFAULT.md) - Iterative extraction overview
- [TEST_SCRIPT_GUIDE.md](TEST_SCRIPT_GUIDE.md) - Test script usage guide
