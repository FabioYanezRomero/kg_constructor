"""Legal domain examples for knowledge graph extraction.

Examples tailored for legal documents including:
- Court cases and proceedings
- Parties and their roles
- Legal entities and relationships
"""

from __future__ import annotations

import langextract as lx

from ...base import ExampleSet


class LegalExamples(ExampleSet):
    """Legal domain examples for knowledge graph extraction.
    
    These examples guide extraction from legal documents such as:
    - Court opinions and judgments
    - Case summaries
    - Legal proceedings
    """
    
    def get_examples(self) -> list[lx.data.ExampleData]:
        """Get legal domain examples for langextract extraction.
        
        Returns:
            List of ExampleData with Triple schema attributes.
        """
        # Example 1: Case parties and representation
        text1 = "Morrison & Foerster LLP represents the appellant, Smith Holdings Inc."
        extractions1 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Morrison & Foerster LLP represents the appellant",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=48),
                attributes={
                    "head": "Morrison & Foerster LLP",
                    "relation": "represents",
                    "tail": "appellant",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="appellant, Smith Holdings Inc.",
                char_interval=lx.data.CharInterval(start_pos=39, end_pos=69),
                attributes={
                    "head": "Smith Holdings Inc.",
                    "relation": "is_party_as",
                    "tail": "appellant",
                    "inference": "explicit",
                }
            )
        ]

        # Example 2: Court and jurisdiction
        text2 = "The UK Supreme Court affirmed the decision of the Court of Appeal."
        extractions2 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="UK Supreme Court affirmed the decision of the Court of Appeal",
                char_interval=lx.data.CharInterval(start_pos=4, end_pos=65),
                attributes={
                    "head": "UK Supreme Court",
                    "relation": "affirmed_decision_of",
                    "tail": "Court of Appeal",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="UK Supreme Court",
                char_interval=lx.data.CharInterval(start_pos=4, end_pos=20),
                attributes={
                    "head": "UK Supreme Court",
                    "relation": "is_type",
                    "tail": "court",
                    "inference": "explicit",
                }
            )
        ]

        # Example 3: Legal claims and rulings
        text3 = "The claimant alleged breach of contract. The court ruled in favor of the defendant."
        extractions3 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="claimant alleged breach of contract",
                char_interval=lx.data.CharInterval(start_pos=4, end_pos=39),
                attributes={
                    "head": "claimant",
                    "relation": "alleged",
                    "tail": "breach of contract",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="court ruled in favor of the defendant",
                char_interval=lx.data.CharInterval(start_pos=45, end_pos=82),
                attributes={
                    "head": "court",
                    "relation": "ruled_in_favor_of",
                    "tail": "defendant",
                    "inference": "explicit",
                }
            )
        ]

        # Example 4: Contextual relationship (bridging)
        text4 = "Lord Hope delivered the judgment. The case concerned tax liability."
        extractions4 = [
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Lord Hope delivered the judgment",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=32),
                attributes={
                    "head": "Lord Hope",
                    "relation": "delivered",
                    "tail": "judgment",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="case concerned tax liability",
                char_interval=lx.data.CharInterval(start_pos=38, end_pos=66),
                attributes={
                    "head": "case",
                    "relation": "concerns",
                    "tail": "tax liability",
                    "inference": "explicit",
                }
            ),
            lx.data.Extraction(
                extraction_class="Triple",
                extraction_text="Lord Hope delivered the judgment. The case concerned",
                char_interval=lx.data.CharInterval(start_pos=0, end_pos=52),
                attributes={
                    "head": "judgment",
                    "relation": "relates_to",
                    "tail": "case",
                    "inference": "contextual",
                    "justification": "The judgment delivered by Lord Hope pertains to the case being discussed.",
                }
            )
        ]

        return [
            lx.data.ExampleData(text=text1, extractions=extractions1),
            lx.data.ExampleData(text=text2, extractions=extractions2),
            lx.data.ExampleData(text=text3, extractions=extractions3),
            lx.data.ExampleData(text=text4, extractions=extractions4),
        ]


__all__ = ["LegalExamples"]
