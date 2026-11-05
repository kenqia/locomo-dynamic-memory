"""Check default wire/schema/fingerprints against the audited default-only tree."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

from locomo_memory.model import request_messages, DeepSeekModel
from locomo_memory.memory_schemas import ExtractionBatch
from locomo_memory.query_schemas import EffectiveResolution, EvidenceAnswer
from locomo_memory.relation_schemas import RelationBatch
from locomo_memory.retrieval_schemas import QueryAnalysis

ROOT = Path(__file__).resolve().parents[2]
CORE = 'c156a1d9cf344a06c9d4d0d7f9f97e39242277f7'
COMPLETE_POLICY = '3aabece1aac9bf5da0f35a43e3a281a43ee3de92'
source = subprocess.check_output(['git', 'show', CORE + ':src/locomo_memory/model.py'], cwd=ROOT, text=True)
module = ModuleType('locomo_memory._core_only_model')
module.__package__ = 'locomo_memory'
sys.modules[module.__name__] = module
exec(compile(source, module.__name__, 'exec'), module.__dict__)
payload = dict(operation='synthetic', question='What was planned?', status='insufficient',
               sources=[dict(source_id='s1', dataset_id='d1', sample_id='c1', text='I might move.', speaker='Alex',
                             session_time='2023-01-01', session_id='s1', position=0)],
               memories=[], relations=[], raw_sources=[])
from locomo_memory.raw_schemas import MixedResolution
operations = {'extract': ExtractionBatch, 'relate': RelationBatch, 'query_analysis': QueryAnalysis,
              'resolve': EffectiveResolution, 'answer': EvidenceAnswer,
              'resolve_raw': MixedResolution, 'answer_raw': EvidenceAnswer}
for operation, schema in operations.items():
    assert request_messages(operation, payload, schema) == module.request_messages(operation, payload, schema), operation
# Unchanged producers match the research core; the final evidence gate deliberately
# replaces ordinary packing and versions that policy in the query fingerprint.
for filename in ('builds.py', 'query_schemas.py', 'raw_schemas.py'):
    assert (ROOT / 'src/locomo_memory' / filename).read_bytes() == subprocess.check_output(
        ['git', 'show', CORE + ':src/locomo_memory/' + filename], cwd=ROOT), filename
for filename in ('queries.py', 'raw_queries.py', 'resolution_delivery.py'):
    assert (ROOT / 'src/locomo_memory' / filename).read_bytes() == subprocess.check_output(
        ['git', 'show', COMPLETE_POLICY + ':src/locomo_memory/' + filename], cwd=ROOT), filename
# Authorized rc2 default change: all other configuration bytes must stay identical.
old_config = subprocess.check_output(['git', 'show', CORE + ':src/locomo_memory/config.py'], cwd=ROOT)
assert (ROOT / 'src/locomo_memory/config.py').read_bytes() == old_config.replace(
    b'resolution_input_budget: int = Field(default=12000, gt=0)',
    b'resolution_input_budget: int = Field(default=24000, gt=0)')
assert not hasattr(DeepSeekModel, 'contract_identity')
print(json.dumps(dict(audited_core_commit=CORE, default_operations_identical=list(operations),
                     unchanged_fingerprint_producers_identical_except_authorized_default=True,
                     authorized_resolution_input_budget_default=24000,
                     complete_input_policy_commit=COMPLETE_POLICY, complete_policy_producers_identical=True, default_adapter_has_no_opt_in_contract=True,
                     live_calls=0), indent=2))
