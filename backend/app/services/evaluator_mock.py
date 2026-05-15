import asyncio
from typing import Dict, Any

class MockEvaluatorService:
    @staticmethod
    async def evaluate_grammar(input_text: str, target_language: str) -> Dict[str, Any]:
        """
        Mock evaluation service matching the logic we need for international language certifications.
        Returns the structure expected by the AgentOutput.
        """
        # Simulate network delay
        await asyncio.sleep(1.5)
        
        return {
            "task_type": "evaluate",
            "success": True,
            "data": {
                "task_type": "evaluate",
                "version": "1.0",
                "generated_at": "2024-05-15T12:00:00Z",
                "source_language": "English",
                "target_language": target_language,
                "content": {
                    "corrections": [
                        f"Found some minor structural issues in '{input_text[:20]}...'",
                        "Ensure verb tense consistency."
                    ],
                    "score": 85,
                    "explanation": f"The sentence has a good flow but contains a few grammatical inconsistencies common for {target_language} learners.",
                    "tips": [
                        "Review subject-verb agreement.",
                        "Practice with irregular verbs."
                    ]
                }
            }
        }
