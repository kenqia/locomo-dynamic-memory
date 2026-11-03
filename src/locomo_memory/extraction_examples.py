"""Synthetic examples, never derived from evaluation annotations or private turns."""


def claim(text, source, *, entity="Alex", value=None, dimension="relocation", kind="event", statement="fact", polarity="positive"):
    return {"content": text, "source_ids": [source], "entity_id": entity,
            "state_dimension": dimension, "state_value": value, "memory_type": kind,
            "statement_type": statement, "polarity": polarity, "time": {}}


EXTRACTION_EXAMPLES = [
    {"sources": [{"source_id": "example/plan", "speaker": "Alex", "text": "I plan to move to Rome."}],
     "output": {"memories": [claim("Alex plans to move to Rome.", "example/plan", value="Rome", statement="plan")]},
     "avoid": "Do not report an accomplished move or a current Rome residence."},
    {"sources": [{"source_id": "example/fact", "speaker": "Alex", "text": "I moved to Rome. I do not work for Acme."}],
     "output": {"memories": [claim("Alex moved to Rome.", "example/fact", value="Rome"),
                              claim("Alex does not work for Acme.", "example/fact", value="Acme", dimension="employment", kind="state", polarity="negative")]},
     "avoid": "Do not turn the negative employment claim positive, bundle it with residence, or invent a move date."},
    {"sources": [{"source_id": "example/quote", "speaker": "Alex", "text": "Sam told me, 'I plan to apply to nursing school.'"}],
     "output": {"memories": [claim("Sam plans to apply to nursing school.", "example/quote", entity="Sam", dimension="education_application", value="nursing school", statement="plan")]},
     "avoid": "The quoted I refers to Sam, not speaker Alex. Do not claim an application was submitted. Unresolved pronouns must not be assigned by guessing."},
    {"sources": [{"source_id": "example/research", "speaker": "Alex", "text": "I researched adoption agencies."},
                 {"source_id": "example/apply", "speaker": "Alex", "text": "I submitted my adoption application."},
                 {"source_id": "example/interview", "speaker": "Alex", "text": "I passed the adoption interview."}],
     "output": {"memories": [claim("Alex researched adoption agencies.", "example/research", dimension="adoption_status", value="research"),
                              claim("Alex submitted an adoption application.", "example/apply", dimension="adoption_status", value="application"),
                              claim("Alex passed the adoption interview.", "example/interview", dimension="adoption_status", value="interview")]},
     "avoid": "Keep each stage and its source. Passing an interview does not establish a completed adoption. Later details of an already completed event are not a new real-world stage."},
]
