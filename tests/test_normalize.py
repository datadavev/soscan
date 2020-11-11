"""
Test normalization of json-ld by way of framing
"""

import pytest
import jsonschema
import soscan.pipelines


jsonld_test_cases = [
    {
        "@context": "http://schema.org/",
        "@type": "Dataset",
        "name": "test 1",
    },
    {
        "@context": {"SO": "http://schema.org/"},
        "@type": "SO:Dataset",
        "SO:name": "http with namespace prefix = SO",
    },
    {
        "@graph": [
            {
                "@context": {"SO": "http://schema.org/"},
                "@type": "SO:Dataset",
                "SO:name": "Single dataset graph with dataset local @context http with namespace prefix = SO",
            }
        ]
    },
    [  # An array of two graphs
        {"@context": "https://schema.org/", "@type": "Dataset", "name": "d7 a"},
        {
            "@context": "http://schema.org/",
            "@type": ["Dataset", "Person"],
            "name": "d7 b",
        },
    ],
]

schema = {
    "description": "Generic JSON-LD schema.org structure",
    "type": "object",
    "properties": {
        "@context": {
            "description": "The context will always have a vocabulary of 'https://schema.org/'",
            "type": "object",
            "properties": {"@vocab": {"$ref": "#/$defs/soVocab"}},
        },
        "@graph": {
            "description": "One or more graphs will always be present",
            "type": "array",
            "items": {"$ref": "#/$defs/someGraph"},
        },
    },
    "$defs": {
        "soVocab": {"type": "string", "pattern": "^https://schema\.org/$"},
        "someGraph": {
            "description": "Properties within a graph will vary",
            "type": "object",
            "properties": {"@type": {"type": ["string", "array"]}},
        },
    },
}


@pytest.mark.parametrize("original", jsonld_test_cases)
def test_normalize(original):
    processor = soscan.pipelines.SoscanNormalizePipeline()
    normalized = processor.normalizeSchemaOrg(original)
    jsonschema.validate(instance=normalized, schema=schema)
