"""Interactive visualization of extracted entities using langextract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import langextract as lx
from langextract import data


class EntityVisualizer:
    """Creates interactive HTML visualizations of extracted entities.

    This class converts knowledge graph extraction results into langextract's
    AnnotatedDocument format and generates animated HTML visualizations that
    highlight entities in the original text.
    """

    def __init__(
        self,
        animation_speed: float = 1.0,
        show_legend: bool = True,
        gif_optimized: bool = False
    ) -> None:
        """Initialize the visualizer.

        Args:
            animation_speed: Animation speed in seconds between entity highlights
            show_legend: Whether to show color legend for entity types
            gif_optimized: Apply GIF-optimized styling (larger fonts, better contrast)
        """
        self.animation_speed = animation_speed
        self.show_legend = show_legend
        self.gif_optimized = gif_optimized

    def _create_extraction(
        self,
        entity_text: str,
        entity_type: str,
        text: str,
        extraction_index: int,
        relation: str | None = None,
        role: str | None = None,
        inference: str | None = None
    ) -> data.Extraction | None:
        """Create an Extraction object for an entity.

        Args:
            entity_text: The entity text to highlight
            entity_type: Type of entity (e.g., 'head', 'tail', 'person', 'organization')
            text: The full text to search in
            extraction_index: Index of this extraction
            relation: The relation this entity participates in
            role: Role of entity in relation ('head' or 'tail')
            inference: Inference type ('explicit' or 'contextual')

        Returns:
            Extraction object or None if entity not found in text
        """
        # Find the entity in the text (case-sensitive)
        start_pos = text.find(entity_text)

        if start_pos == -1:
            # Try case-insensitive search
            text_lower = text.lower()
            entity_lower = entity_text.lower()
            start_pos = text_lower.find(entity_lower)

            if start_pos == -1:
                return None

        end_pos = start_pos + len(entity_text)

        # Create CharInterval for the entity span (use start_pos, end_pos not start, end)
        char_interval = data.CharInterval(start_pos=start_pos, end_pos=end_pos)

        # Build attributes dict with relation info
        attributes = {}
        if relation:
            attributes["relation"] = relation
        if role:
            attributes["role"] = role
        if inference:
            attributes["inference"] = inference

        # Build description with relation info
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
            attributes=attributes if attributes else None
        )

    def visualize_triples(
        self,
        text: str,
        triples: list[dict[str, Any]],
        document_id: str | None = None,
        group_by: str = "entity_type"  # "entity_type" or "relation"
    ) -> str:
        """Create interactive HTML visualization from extracted triples.

        Args:
            text: The original text that was analyzed
            triples: List of extracted triples (dicts with head, relation, tail)
            document_id: Optional identifier for this document
            group_by: How to group entities - "entity_type" or "relation"

        Returns:
            HTML string with interactive visualization
        """
        if not text or not triples:
            return "<p>No text or triples to visualize</p>"

        extractions = []
        extraction_index = 0
        seen_entities = set()  # Track seen entities to avoid duplicates

        for triple in triples:
            head = triple.get("head", "")
            tail = triple.get("tail", "")
            relation = triple.get("relation", "")
            inference = triple.get("inference", "")

            # Determine entity types based on grouping strategy
            if group_by == "relation":
                head_type = f"{relation} (source)"
                tail_type = f"{relation} (target)"
            else:
                head_type = "Head Entity"
                tail_type = "Tail Entity"

            # Extract head entity (avoid duplicates)
            if head and head not in seen_entities:
                extraction = self._create_extraction(
                    entity_text=head,
                    entity_type=head_type,
                    text=text,
                    extraction_index=extraction_index,
                    relation=relation,
                    role="head",
                    inference=inference
                )
                if extraction:
                    extractions.append(extraction)
                    extraction_index += 1
                    seen_entities.add(head)

            # Extract tail entity (avoid duplicates)
            if tail and tail not in seen_entities:
                extraction = self._create_extraction(
                    entity_text=tail,
                    entity_type=tail_type,
                    text=text,
                    extraction_index=extraction_index,
                    relation=relation,
                    role="tail",
                    inference=inference
                )
                if extraction:
                    extractions.append(extraction)
                    extraction_index += 1
                    seen_entities.add(tail)

        if not extractions:
            return "<p>No entities found in the text</p>"

        # Create AnnotatedDocument
        annotated_doc = data.AnnotatedDocument(
            text=text,
            extractions=extractions,
            document_id=document_id
        )

        # Generate visualization using langextract
        html = lx.visualize(
            annotated_doc,
            animation_speed=self.animation_speed,
            show_legend=self.show_legend,
            gif_optimized=self.gif_optimized
        )

        # Convert to string if it's an IPython HTML object
        if hasattr(html, '_repr_html_'):
            html = html._repr_html_()
        elif not isinstance(html, str):
            html = str(html)

        return html

    def save_visualization(
        self,
        text: str,
        triples: list[dict[str, Any]],
        output_path: Path | str,
        document_id: str | None = None,
        group_by: str = "entity_type"
    ) -> Path:
        """Create and save HTML visualization to file.

        Args:
            text: The original text that was analyzed
            triples: List of extracted triples
            output_path: Path to save HTML file
            document_id: Optional identifier for this document
            group_by: How to group entities - "entity_type" or "relation"

        Returns:
            Path to saved HTML file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self.visualize_triples(
            text=text,
            triples=triples,
            document_id=document_id,
            group_by=group_by
        )

        # Wrap in a complete HTML document
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entity Visualization{f' - {document_id}' if document_id else ''}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .header .stats {{
            color: #666;
            font-size: 14px;
        }}
        .content {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Knowledge Graph Entity Visualization</h1>
        <div class="stats">
            <strong>Document:</strong> {document_id or 'Untitled'}<br>
            <strong>Entities:</strong> {len(set(t.get('head', '') for t in triples) | set(t.get('tail', '') for t in triples))}<br>
            <strong>Relations:</strong> {len(triples)}
        </div>
    </div>
    <div class="content">
        {html}
    </div>
</body>
</html>"""

        output_path.write_text(full_html, encoding="utf-8")
        return output_path

    def batch_visualize(
        self,
        records: dict[str, tuple[str, list[dict[str, Any]]]],
        output_dir: Path | str,
        group_by: str = "entity_type"
    ) -> list[Path]:
        """Create visualizations for multiple records.

        Args:
            records: Dict mapping record_id to (text, triples) tuples
            output_dir: Directory to save HTML files
            group_by: How to group entities - "entity_type" or "relation"

        Returns:
            List of paths to created HTML files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []
        for record_id, (text, triples) in records.items():
            output_path = output_dir / f"{record_id}.html"

            try:
                self.save_visualization(
                    text=text,
                    triples=triples,
                    output_path=output_path,
                    document_id=record_id,
                    group_by=group_by
                )
                created_files.append(output_path)
                print(f"Created visualization: {output_path}")
            except Exception as e:
                print(f"Error creating visualization for {record_id}: {e}")

        return created_files


__all__ = [
    "EntityVisualizer",
]
