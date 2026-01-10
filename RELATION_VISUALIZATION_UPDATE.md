# Relation Information in Entity Visualization

## Question: Does langextract visualize relations between entities?

**Answer: YES!** The langextract visualization **DOES include relation information**, but it shows it differently than the graph visualization.

## How Relations Are Shown

### Entity Visualization (langextract)
- **Entities are highlighted** in the original text
- **Relations are shown in the entity's attributes** when you hover/inspect
- Each entity shows:
  - `relation`: Which relation it participates in
  - `role`: Whether it's the "head" or "tail" of the relation
  - `inference`: Whether it's "explicit" or "contextual"

### Example

**Text**: "John works at Google in California."

**Entity Visualization shows**:
```
[John] works at [Google] in [California]
 │              │           │
 └─ Attributes: └─ Attributes: └─ Attributes:
    relation: "works at"      relation: "works at"      relation: "located in"
    role: "head"              role: "tail"              role: "tail"
    inference: "explicit"     inference: "explicit"     inference: "explicit"
```

When you hover over or click an entity, you see its attributes including the relation it participates in!

## Two Types of Relation Display

| Feature | Entity Viz (langextract) | Graph Viz (Plotly) |
|---------|-------------------------|-------------------|
| **Shows entities** | ✅ Highlighted in text | ✅ As nodes |
| **Shows relations** | ✅ In entity attributes | ✅ As arrows/edges |
| **Relation visualization** | Text-based (attributes) | Visual (arrows) |
| **Relation structure** | Shown per entity | Shown as connections |
| **Interactive** | Click/hover for details | Zoom/pan network |
| **Original context** | ✅ Yes | ❌ No |

## What Each Visualization Answers

### Entity Visualization
- **"Where is this entity in the text?"** → Highlighted span
- **"What role does it play?"** → head/tail in attributes
- **"What relation?"** → Shown in attributes
- **"Is it explicit or inferred?"** → Shown in attributes

### Graph Visualization
- **"What's connected to what?"** → Visual network
- **"How are entities related?"** → Arrow labels
- **"What's the graph structure?"** → Complete network view

## Technical Implementation

### Updated Visualizer Code

The [visualizer.py](src/kg_constructor/visualizer.py) now includes relation information:

```python
def _create_extraction(
    self,
    entity_text: str,
    entity_type: str,
    text: str,
    extraction_index: int,
    relation: str | None = None,  # NEW!
    role: str | None = None,      # NEW!
    inference: str | None = None  # NEW!
) -> data.Extraction | None:
    # ... find entity in text ...

    # Build attributes dict with relation info
    attributes = {}
    if relation:
        attributes["relation"] = relation
    if role:
        attributes["role"] = role
    if inference:
        attributes["inference"] = inference

    # Build description
    description_parts = []
    if role and relation:
        description_parts.append(f"{role.capitalize()} of relation: '{relation}'")
    if inference:
        description_parts.append(f"Inference: {inference}")
    description = " | ".join(description_parts) if description_parts else None

    return data.Extraction(
        extraction_class=entity_type,
        extraction_text=entity_text,
        char_interval=char_interval,
        extraction_index=extraction_index,
        description=description,
        attributes=attributes  # Contains relation info!
    )
```

### How It Works

1. **Extract triples** from text:
   ```python
   triples = [
       {"head": "John", "relation": "works at", "tail": "Google", "inference": "explicit"}
   ]
   ```

2. **Find entities in text** and create Extraction objects with attributes:
   ```python
   Extraction(
       extraction_class="Head Entity",
       extraction_text="John",
       char_interval=CharInterval(start_pos=0, end_pos=4),
       attributes={"relation": "works at", "role": "head", "inference": "explicit"}
   )
   ```

3. **langextract.visualize()** creates HTML that includes these attributes:
   ```html
   <div class="entity-popup">
       <strong>class:</strong> Head Entity<br>
       <strong>attributes:</strong> {
           <span class="attr-key">relation</span>: <span class="attr-value">works at</span>,
           <span class="attr-key">role</span>: <span class="attr-value">head</span>,
           <span class="attr-key">inference</span>: <span class="attr-value">explicit</span>
       }
   </div>
   ```

## Viewing Relation Information

### In the HTML Visualization

1. Open the entity visualization HTML file
2. **Hover over** or **click** a highlighted entity
3. You'll see a popup/tooltip showing:
   - Entity class (e.g., "Head Entity")
   - **Attributes including the relation it participates in**
   - Role (head/tail)
   - Inference type

### Example Output

```html
Entity: John
├─ Class: Head Entity
└─ Attributes:
   ├─ relation: works at
   ├─ role: head
   └─ inference: explicit
```

## Complete Picture

For a complete understanding, use **BOTH** visualizations together:

### Workflow:
1. **Entity visualization**: See WHERE "John" and "Google" appear in text
2. **Hover/click entity**: See that "John" has relation "works at" (role: head)
3. **Graph visualization**: See HOW they're connected (John → works at → Google)

### Together they provide:
- ✅ Entity locations in text
- ✅ Relations each entity participates in
- ✅ Visual graph structure
- ✅ Complete knowledge graph insight

## Summary

**YES, the entity visualization DOES show relations!**

They appear in the **attributes** of each highlighted entity. When you hover or click on an entity, you can see:
- Which relation it participates in
- Its role in that relation (head/tail)
- The inference type (explicit/contextual)

This is different from the graph visualization, which shows relations as **visual arrows** connecting entities.

**Both types are complementary**:
- Entity viz: Relations shown as **attributes** (text-based)
- Graph viz: Relations shown as **edges** (visual network)

Together they provide a complete view of both the source text and the knowledge graph structure!
