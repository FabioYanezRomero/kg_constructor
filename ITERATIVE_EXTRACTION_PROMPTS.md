# Iterative Extraction Prompts

This document describes the prompts used in the two-step iterative connectivity-aware extraction approach.

## Overview

The iterative extraction approach uses **two different prompts**:

1. **Step 1: Initial Extraction Prompt** - Configured via `prompt_path` parameter
2. **Step 2: Bridging/Refinement Prompt** - Hardcoded in `extract_connected_graph()` method

---

## Step 1: Initial Extraction Prompt

**Location**: Specified via `prompt_path` parameter (e.g., `/app/src/prompts/legal_background_prompt.txt`)

**Purpose**: Extract explicit and contextual triples from the text

**How it's used**:
```python
# In extract_connected_graph() method
triples = self.extract_from_text(text, record_id, temperature, max_tokens)
```

This uses the standard prompt template loaded when initializing the `KnowledgeGraphExtractor`:
```python
extractor = KnowledgeGraphExtractor(
    client_config=config,
    prompt_path="/app/src/prompts/legal_background_prompt.txt"  # Custom prompt
)
```

**Example prompt structure** (from `legal_background_prompt.txt`):
```
You are an expert at extracting knowledge graphs from legal documents.

Extract all entities (people, organizations, legal concepts, dates, amounts)
and their relationships from the following text.

For each relationship, specify:
- head: source entity
- relation: relationship type
- tail: target entity
- inference: "explicit" if directly stated, "contextual" if inferred
- justification: explanation (required for contextual triples)

Text to analyze:
{{record_json}}

Return a JSON array of triples.
```

---

## Step 2: Bridging/Refinement Prompt

**Location**: Hardcoded in `/app/src/kg_constructor/extractor.py` at lines 296-314

**Purpose**: Extract additional triples to connect disconnected graph components

**How it's used**:
```python
# In extract_connected_graph() method, inside the iterative refinement loop
while num_components > max_disconnected and iteration < max_iterations:
    component_info = self._format_components(components, G)

    # Create bridging prompt
    bridging_prompt = f"""
The previously extracted knowledge graph has {num_components} disconnected components.

Disconnected Components:
{component_info}

Original Text:
{text}

Task: Find EXPLICIT relationships in the text that connect these components,
or infer MINIMAL contextual triples necessary for connectivity. Focus on:
1. Shared entities between components
2. Implicit relationships stated in the text
3. Temporal or causal connections
4. Hierarchical relationships (part-of, type-of)

Extract ONLY the bridging triples needed to connect components.
Do not re-extract existing triples.
"""

    # Extract bridging triples
    bridging_triples = self.client.extract(
        text=bridging_prompt,
        prompt_description="Extract bridging triples to connect graph components",
        examples=self._create_examples(),
        format_type=Triple,
        temperature=temperature,
        max_tokens=max_tokens
    )
```

**Full prompt template**:
```
The previously extracted knowledge graph has {num_components} disconnected components.

Disconnected Components:
{component_info}

Original Text:
{text}

Task: Find EXPLICIT relationships in the text that connect these components,
or infer MINIMAL contextual triples necessary for connectivity. Focus on:
1. Shared entities between components
2. Implicit relationships stated in the text
3. Temporal or causal connections
4. Hierarchical relationships (part-of, type-of)

Extract ONLY the bridging triples needed to connect components.
Do not re-extract existing triples.
```

**Key features of the bridging prompt**:

1. **Component Awareness**: Shows the LLM which components are disconnected
2. **Original Text**: Provides full context for finding connections
3. **Explicit Priority**: Prioritizes finding explicit relationships first
4. **Minimal Contextual**: Only infer when necessary for connectivity
5. **Focus Areas**: Guides the LLM to look for specific connection types
6. **No Duplication**: Explicitly instructs to avoid re-extracting existing triples

---

## Prompt Customization

### Customizing Initial Extraction Prompt

Easy - just create a new prompt file and specify it:

```bash
# Create custom prompt
cat > /app/prompts/my_custom_prompt.txt << 'EOF'
You are an expert at extracting knowledge graphs.
[Your custom instructions here]
EOF

# Use it in the script
PROMPT_FILE="/app/prompts/my_custom_prompt.txt"
./test_single_extraction.sh
```

### Customizing Bridging Prompt

✅ **Now fully supported!** You can customize the bridging prompt in two ways:

**Option 1: Use the provided template** (recommended):

```bash
# Edit the test script configuration
PROMPT_FILE_STEP1="/app/src/prompts/legal_background_prompt_step1_initial.txt"
PROMPT_FILE_STEP2="/app/src/prompts/legal_background_prompt_step2_bridging.txt"

# Modify the step2 bridging prompt as needed
nano /app/src/prompts/legal_background_prompt_step2_bridging.txt
```

**Option 2: Create your own custom bridging prompt**:

```bash
# Create custom bridging prompt
cat > /app/prompts/my_custom_bridging.txt << 'EOF'
You are an expert at connecting graph components.

The knowledge graph has {num_components} disconnected components:
{component_info}

Original text:
{text}

Your task: [Your custom instructions here]
EOF

# Use it in the script
PROMPT_FILE_STEP2="/app/prompts/my_custom_bridging.txt"
./test_single_extraction.sh
```

**Template Variables**:
- `{num_components}`: Number of disconnected components
- `{component_info}`: Formatted list of components with entities
- `{text}`: Original input text

**Fallback**: If `PROMPT_FILE_STEP2` is empty or not specified, the system uses a hardcoded default prompt.

---

## Examples of Bridging Prompt in Action

### Example: Legal Case (UKSC-2009-0143)

**Disconnected components found**:
```
Component 1: Sigma Finance Corporation, Security Trustee, STD, Security Trust Deed
Component 2: creditor, payment, discharge
Component 3: financial crisis, market, cost of funding
Component 4: profit, difference, assets
...
```

**Bridging triples extracted**:
```json
[
  {
    "head": "Sigma Finance Corporation",
    "relation": "has",
    "tail": "activities",
    "inference": "contextual",
    "justification": "Text mentions 'cost of funding its activities'"
  },
  {
    "head": "cost of funding",
    "relation": "affects",
    "tail": "Sigma's available assets",
    "inference": "contextual",
    "justification": "Higher funding costs reduce available assets"
  },
  {
    "head": "Security Trustee",
    "relation": "is a type of",
    "tail": "trustees",
    "inference": "contextual",
    "justification": "Security Trustee is a specific type of trustee role"
  }
]
```

**Result**: Components reduced from 11 → 1 (fully connected) with 2 iterations

---

## Design Rationale

### Why Two Separate Prompts?

1. **Different Goals**:
   - Initial: Extract all relevant information
   - Bridging: Focus specifically on connectivity gaps

2. **Context Efficiency**:
   - Initial: Processes full text once
   - Bridging: Shows component structure to guide targeted extraction

3. **Quality Control**:
   - Initial: Broad extraction with high recall
   - Bridging: Precise extraction with high precision (only what's needed)

4. **Semantic Validity**:
   - Bridging prompt explicitly instructs "EXPLICIT relationships... or infer MINIMAL"
   - Prevents hallucination by grounding in original text

### Why Hardcode Bridging Prompt?

Current design prioritizes:
- **Consistency**: Same bridging strategy across all extractions
- **Simplicity**: Users don't need to manage two prompt files
- **Proven effectiveness**: The hardcoded prompt has been validated

Future enhancement could externalize for advanced users who want to customize the bridging strategy.

---

## Summary

| Aspect | Step 1: Initial Extraction | Step 2: Bridging Refinement |
|--------|---------------------------|----------------------------|
| **Prompt location** | External file (configurable) | External file (configurable) ✅ |
| **Purpose** | Extract all triples | Connect components |
| **Customizable** | ✅ Easy (specify file path) | ✅ Easy (specify file path) |
| **Context provided** | Original text | Text + component structure |
| **API calls** | 1 | 0-2 (iterative) |
| **Default prompt** | `legal_background_prompt_step1_initial.txt` | `legal_background_prompt_step2_bridging.txt` |
| **Fallback** | Generic default prompt | Hardcoded prompt (if not specified) |

**Total API calls for iterative approach**: 1 (initial) + 0-2 (refinement) = 1-3 calls
