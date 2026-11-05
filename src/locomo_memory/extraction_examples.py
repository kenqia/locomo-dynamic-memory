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

# Literal source wording and derived dates have separate roles. These examples
# are synthetic and do not select facts from any evaluation conversation.
_yesterday = claim("Alex painted yesterday.", "example/time", dimension="painting")
_yesterday["time"] = dict(original_expression="yesterday", anchor_source_id="example/time",
    event_start="2024-04-09", event_end="2024-04-09",
    basis="Yesterday relative to the cited April 10 source session.")
_next_month = claim("Alex plans to apply next month.", "example/next-month",
    dimension="application", statement="plan")
_next_month["time"] = dict(original_expression="next month", anchor_source_id="example/next-month",
    event_start="2024-05-01", event_end="2024-05-31",
    basis="Calendar month after the cited April 2024 session; exact day unknown.")
EXTRACTION_EXAMPLES.extend([
    {"sources": [{"source_id": "example/time", "speaker": "Alex",
                  "session_time": "2024-04-10T10:00:00", "text": "I painted yesterday."}],
     "output": {"memories": [_yesterday]},
     "avoid": "Do not put April 9, 2024 or the previous day in original_expression; neither appears in raw text. Keep yesterday and its supported derived date."},
    {"sources": [{"source_id": "example/no-time", "speaker": "Alex",
                  "session_time": "2024-04-10T10:00:00", "text": "I moved to Rome."}],
     "output": {"memories": [claim("Alex moved to Rome.", "example/no-time", value="Rome")]},
     "avoid": "The report timestamp alone does not date the move. Retain the move fact with unknown event time, rather than quoting metadata as source text."},
    {"sources": [{"source_id": "example/context", "speaker": "Sam",
                  "session_time": "2024-04-10T10:00:00", "text": "I applied yesterday."},
                 {"source_id": "example/next-month", "speaker": "Alex",
                  "session_time": "2024-04-10T10:01:00", "text": "I plan to apply next month."}],
     "output": {"memories": [
         {**_yesterday, "content": "Sam applied yesterday.", "entity_id": "Sam",
          "state_dimension": "application", "source_ids": ["example/context"],
          "time": {**_yesterday["time"], "anchor_source_id": "example/context"}}, _next_month]},
     "avoid": "Do not borrow Sam's yesterday for Alex's plan, paraphrase next month as the following month, or invent a particular day."},
])
