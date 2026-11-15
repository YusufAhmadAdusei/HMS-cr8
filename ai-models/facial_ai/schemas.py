
FACE_HEALTH_SCHEMA = {
    "type": "object",
    "properties": {
        "screening_status": {
            "type": "string",
            "enum": [
                "completed",
                "limited_image_quality",
                "unable_to_assess"
            ]
        },
        "face_detected": {
            "type": "boolean"
        },
        "overall_summary": {
            "type": "string"
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string"
                    },
                    "finding_type": {
                        "type": "string",
                        "enum": [
                            "redness",
                            "rash_like_appearance",
                            "lesion_or_spot",
                            "swelling_or_puffiness",
                            "dryness_or_scaling",
                            "discoloration",
                            "other_visible_change",
                            "none"
                        ]
                    },
                    "description": {
                        "type": "string"
                    },
                    "visual_confidence": {
                        "type": "string",
                        "enum": [
                            "low",
                            "moderate",
                            "high"
                        ]
                    },
                    "visual_severity": {
                        "type": "string",
                        "enum": [
                            "not_applicable",
                            "mild",
                            "moderate",
                            "marked",
                            "uncertain"
                        ]
                    }
                },
                "required": [
                    "region",
                    "finding_type",
                    "description",
                    "visual_confidence",
                    "visual_severity"
                ],
                "additionalProperties": False
            }
        },
        "baseline_comparison": {
            "type": "string",
            "enum": [
                "not_available",
                "no_clear_change",
                "possible_new_change",
                "possible_increased_change",
                "possible_decreased_change",
                "inconclusive"
            ]
        },
        "comparison_explanation": {
            "type": "string"
        },
        "image_quality": {
            "type": "string",
            "enum": [
                "good",
                "limited",
                "poor"
            ]
        },
        "human_review_required": {
            "type": "boolean"
        },
        "review_reason": {
            "type": "string"
        },
        "recommended_actions": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "limitations": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": [
        "screening_status",
        "face_detected",
        "overall_summary",
        "findings",
        "baseline_comparison",
        "comparison_explanation",
        "image_quality",
        "human_review_required",
        "review_reason",
        "recommended_actions",
        "limitations"
    ],
    "additionalProperties": False
}
