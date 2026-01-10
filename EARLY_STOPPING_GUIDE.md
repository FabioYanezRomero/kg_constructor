# Early Stopping in Iterative Extraction

## Overview

The iterative extraction process includes **multiple early stopping mechanisms** to prevent unnecessary API calls and optimize efficiency. The system automatically stops refining when:

1. **Connectivity goal achieved** - Components ≤ `max_disconnected`
2. **Maximum iterations reached** - Iterations ≥ `max_iterations`
3. **No new triples found** - LLM cannot find more connections (NEW ✨)
4. **No connectivity improvement** - Added triples didn't reduce components (NEW ✨)

---

## The Four Early Stopping Conditions

### 1. Connectivity Goal Achieved ✅

**Condition**: `num_components <= max_disconnected`

**When it triggers**:
- Graph reaches target connectivity level
- Example: If `max_disconnected=3`, stops when components ≤ 3

**Example**:
```
Initial extraction: 11 components

Iteration 1: +6 triples → 6 components
Iteration 2: +7 triples → 1 component

✅ STOP: connectivity_goal_achieved (1 ≤ 3)
```

**Configuration**:
```bash
MAX_DISCONNECTED=3  # Target: at most 3 components
```

**Metadata**:
```json
{
  "final_state": {
    "disconnected_components": 1,
    "stop_reason": "connectivity_goal_achieved",
    "iterations_used": 2
  }
}
```

---

### 2. Maximum Iterations Reached ⏱️

**Condition**: `iteration >= max_iterations`

**When it triggers**:
- Reached maximum allowed refinement iterations
- Prevents runaway API costs

**Example**:
```
Initial extraction: 15 components

Iteration 1: +5 triples → 12 components
Iteration 2: +4 triples → 9 components

⏱️ STOP: max_iterations_reached (2/2 used)
Final: 9 components (goal was 3, but budget exhausted)
```

**Configuration**:
```bash
MAX_ITERATIONS=2  # Allow at most 2 refinement iterations
```

**Metadata**:
```json
{
  "final_state": {
    "disconnected_components": 9,
    "stop_reason": "max_iterations_reached",
    "iterations_used": 2,
    "connectivity_improvement": 6
  }
}
```

---

### 3. No New Triples Found 🔍 (NEW)

**Condition**: `len(new_triples) == 0`

**When it triggers**:
- LLM returned triples, but all were duplicates
- OR LLM returned empty response
- Indicates LLM cannot find more connections

**Why important**:
- Prevents wasteful iterations
- Saves API calls when LLM "gives up"
- Indicates text may not support better connectivity

**Example**:
```
Initial extraction: 8 components

Iteration 1: +4 triples → 5 components
Iteration 2: +0 triples (all duplicates or empty)

🔍 STOP: no_new_triples_found
Final: 5 components (LLM exhausted connection possibilities)
```

**Metadata**:
```json
{
  "refinement_iterations": [
    {
      "iteration": 1,
      "new_triples": 4,
      "disconnected_components": 5
    },
    {
      "iteration": 2,
      "new_triples": 0,
      "disconnected_components": 5,
      "early_stop_reason": "no_new_triples_found"
    }
  ],
  "final_state": {
    "stop_reason": "no_new_triples_found",
    "iterations_used": 2
  }
}
```

**What this means**:
- ✅ Normal: Text may not contain connections between some components
- ✅ Normal: LLM correctly identifies no more valid connections exist
- ⚠️ Possible: Prompt might be too restrictive
- ⚠️ Possible: Temperature too low (0.0 might be too deterministic)

**Remediation**:
```bash
# Try increasing temperature slightly
TEMPERATURE=0.2

# Or modify bridging prompt to be less strict
nano /app/src/prompts/legal_background_prompt_step2_bridging.txt
```

---

### 4. No Connectivity Improvement 📊 (NEW)

**Condition**: `num_components >= prev_num_components`

**When it triggers**:
- Added new triples, but components didn't decrease
- Triples connected entities within same component (redundant)
- OR triples created new isolated components

**Why important**:
- Prevents iterations that add noise without benefit
- Detects when bridging strategy isn't working
- Saves API calls when triples don't help connectivity

**Example**:
```
Initial extraction: 10 components

Iteration 1: +5 triples → 7 components (✅ improved)
Iteration 2: +3 triples → 7 components (❌ no change)

📊 STOP: no_connectivity_improvement
Final: 7 components
```

**Metadata**:
```json
{
  "refinement_iterations": [
    {
      "iteration": 1,
      "new_triples": 5,
      "disconnected_components": 7
    },
    {
      "iteration": 2,
      "new_triples": 3,
      "disconnected_components": 7,
      "early_stop_reason": "no_connectivity_improvement"
    }
  ],
  "final_state": {
    "stop_reason": "no_connectivity_improvement",
    "iterations_used": 2,
    "connectivity_improvement": 3
  }
}
```

**What this means**:
- ⚠️ Triples are being added within existing components (not bridging)
- ⚠️ LLM might be misunderstanding component structure
- ⚠️ Bridging prompt might need refinement

**Remediation**:
```bash
# Review the bridging prompt
cat /app/src/prompts/legal_background_prompt_step2_bridging.txt

# Check if component formatting is clear
# Ensure prompt emphasizes "BETWEEN components"
nano /app/src/prompts/legal_background_prompt_step2_bridging.txt
```

---

## Early Stopping Decision Flow

```
Start Iteration
    ↓
Extract bridging triples
    ↓
Filter duplicates
    ↓
┌─ NEW TRIPLES = 0? ─→ YES ─→ STOP: no_new_triples_found
│
└─ NO
    ↓
Add triples & rebuild graph
    ↓
Count components
    ↓
┌─ COMPONENTS ≤ MAX_DISCONNECTED? ─→ YES ─→ STOP: connectivity_goal_achieved
│
└─ NO
    ↓
┌─ COMPONENTS ≥ PREV_COMPONENTS? ─→ YES ─→ STOP: no_connectivity_improvement
│
└─ NO
    ↓
┌─ ITERATION ≥ MAX_ITERATIONS? ─→ YES ─→ STOP: max_iterations_reached
│
└─ NO
    ↓
Next Iteration
```

---

## Configuration Guide

### Aggressive Connectivity (High API cost)

```bash
USE_ITERATIVE_EXTRACTION=true
MAX_DISCONNECTED=1   # Target: fully connected graph
MAX_ITERATIONS=5     # Allow many refinement attempts
```

**Use when**:
- Connectivity is critical
- Budget allows multiple API calls
- Text likely contains many implicit connections

**Expected behavior**:
- Will try hard to achieve full connectivity
- May use 4-6 API calls
- Early stopping from "no_new_triples" likely

---

### Balanced (DEFAULT)

```bash
USE_ITERATIVE_EXTRACTION=true
MAX_DISCONNECTED=3   # Target: at most 3 components
MAX_ITERATIONS=2     # Reasonable number of attempts
```

**Use when**:
- Want good connectivity without excessive cost
- Typical use case for most documents
- Balance between quality and efficiency

**Expected behavior**:
- Usually 2-3 API calls
- Early stopping from "connectivity_goal_achieved" common
- Good connectivity improvement

---

### Conservative (Low cost)

```bash
USE_ITERATIVE_EXTRACTION=true
MAX_DISCONNECTED=5   # Accept more disconnection
MAX_ITERATIONS=1     # Only one refinement attempt
```

**Use when**:
- Tight budget constraints
- Connectivity is nice-to-have, not critical
- Quick testing

**Expected behavior**:
- Exactly 2 API calls (initial + 1 refinement)
- Early stopping from "max_iterations_reached" common
- Modest connectivity improvement

---

### Simple One-Step (Minimal cost)

```bash
USE_ITERATIVE_EXTRACTION=false
```

**Use when**:
- Absolute minimum cost
- Connectivity not important
- Just need basic extraction

**Expected behavior**:
- Exactly 1 API call
- No early stopping (no iterations)
- May have many disconnected components

---

## Analyzing Stop Reasons

### Understanding Your Results

**Check the metadata**:
```bash
cat test_outputs/*/metadata/*_metadata.json | jq '.iterative_extraction.final_state'
```

**Example output**:
```json
{
  "total_triples": 47,
  "disconnected_components": 1,
  "is_connected": true,
  "iterations_used": 2,
  "stop_reason": "connectivity_goal_achieved",
  "connectivity_improvement": 10
}
```

### Interpreting Stop Reasons

| Stop Reason | What It Means | Action Needed |
|-------------|---------------|---------------|
| `connectivity_goal_achieved` | ✅ Success! Reached target connectivity | None - working as intended |
| `max_iterations_reached` | ⚠️ Budget exhausted before reaching goal | Increase `MAX_ITERATIONS` or accept result |
| `no_new_triples_found` | ⚠️ LLM can't find more connections | Review text; may be inherently disconnected |
| `no_connectivity_improvement` | ⚠️ Bridging isn't helping | Review/adjust bridging prompt |

---

## Troubleshooting

### Problem: Always stops with "no_new_triples_found"

**Possible causes**:
1. Bridging prompt too restrictive
2. Temperature too low (too deterministic)
3. Text genuinely lacks connections

**Solutions**:
```bash
# Increase temperature
TEMPERATURE=0.3

# Review bridging prompt
nano /app/src/prompts/legal_background_prompt_step2_bridging.txt

# Check initial extraction - might be comprehensive already
jq '.iterative_extraction.initial_extraction' metadata/*.json
```

---

### Problem: Always stops with "no_connectivity_improvement"

**Possible causes**:
1. Bridging triples connecting within components, not between
2. Component formatting in prompt unclear
3. LLM not understanding the task

**Solutions**:
```bash
# Check what triples are being added
jq '.iterative_extraction.refinement_iterations' metadata/*.json

# Enhance component formatting in prompt
# Make sure it clearly shows which entities are in which components
nano /app/src/prompts/legal_background_prompt_step2_bridging.txt

# Try different model (some are better at this task)
MODEL_NAME="gemini-1.5-pro"  # More powerful model
```

---

### Problem: Always hits "max_iterations_reached"

**Possible causes**:
1. Target connectivity too ambitious for the text
2. Iterations value too low
3. Text has inherently disconnected topics

**Solutions**:
```bash
# Increase iterations budget
MAX_ITERATIONS=4

# Relax connectivity goal
MAX_DISCONNECTED=5

# Accept that some texts are inherently disconnected
# Check connectivity improvement metric to see if progress is being made
jq '.iterative_extraction.final_state.connectivity_improvement' metadata/*.json
```

---

## Best Practices

### 1. Monitor Stop Reasons

Track why your extractions stop:
```bash
# Count stop reasons across multiple runs
grep -r "stop_reason" test_outputs/*/metadata/*.json | \
  jq -r '.iterative_extraction.final_state.stop_reason' | \
  sort | uniq -c
```

Example output:
```
15 connectivity_goal_achieved
 3 max_iterations_reached
 1 no_connectivity_improvement
 1 no_new_triples_found
```

### 2. Adjust Based on Patterns

- **Mostly "connectivity_goal_achieved"** → Configuration is good ✅
- **Mostly "max_iterations_reached"** → Increase `MAX_ITERATIONS` or relax `MAX_DISCONNECTED`
- **Mostly "no_new_triples_found"** → Review bridging prompt, increase temperature
- **Mostly "no_connectivity_improvement"** → Improve component formatting in prompt

### 3. Balance Cost vs Quality

```bash
# Calculate average API calls per document
jq -r '.iterative_extraction.final_state.iterations_used + 1' metadata/*.json | \
  awk '{sum+=$1; count++} END {print "Average API calls:", sum/count}'
```

### 4. Track Connectivity Improvement

```bash
# See how much connectivity improved
jq '.iterative_extraction.final_state.connectivity_improvement' metadata/*.json
```

If improvement is consistently low (0-2 components), consider:
- Is iterative extraction worth the cost for your use case?
- Should you adjust prompts or parameters?

---

## Example Metadata with Early Stopping

### Success Case (Goal Achieved)

```json
{
  "iterative_extraction": {
    "initial_extraction": {
      "triples": 34,
      "disconnected_components": 11
    },
    "refinement_iterations": [
      {
        "iteration": 1,
        "new_triples": 6,
        "total_triples": 40,
        "disconnected_components": 6
      },
      {
        "iteration": 2,
        "new_triples": 7,
        "total_triples": 47,
        "disconnected_components": 1
      }
    ],
    "final_state": {
      "total_triples": 47,
      "disconnected_components": 1,
      "is_connected": true,
      "iterations_used": 2,
      "stop_reason": "connectivity_goal_achieved",
      "connectivity_improvement": 10
    }
  }
}
```

### Early Stop Case (No New Triples)

```json
{
  "iterative_extraction": {
    "initial_extraction": {
      "triples": 28,
      "disconnected_components": 8
    },
    "refinement_iterations": [
      {
        "iteration": 1,
        "new_triples": 4,
        "total_triples": 32,
        "disconnected_components": 5
      },
      {
        "iteration": 2,
        "new_triples": 0,
        "total_triples": 32,
        "disconnected_components": 5,
        "early_stop_reason": "no_new_triples_found"
      }
    ],
    "final_state": {
      "total_triples": 32,
      "disconnected_components": 5,
      "is_connected": false,
      "iterations_used": 2,
      "stop_reason": "no_new_triples_found",
      "connectivity_improvement": 3
    }
  }
}
```

---

## Summary

The iterative extraction system includes **four intelligent early stopping mechanisms**:

1. ✅ **Connectivity Goal Achieved** - Reached target, mission accomplished
2. ⏱️ **Max Iterations Reached** - Budget limit, prevents runaway costs
3. 🔍 **No New Triples Found** (NEW) - LLM exhausted, saves wasteful calls
4. 📊 **No Connectivity Improvement** (NEW) - Triples not helping, stops noise

These mechanisms ensure:
- **Efficiency**: Stop when further iterations won't help
- **Cost control**: Respect budget limits
- **Quality**: Detect when goal is achieved or unachievable
- **Transparency**: Metadata explains why stopping occurred

**Configuration is flexible** - adjust `MAX_DISCONNECTED` and `MAX_ITERATIONS` to balance cost vs quality for your use case.
