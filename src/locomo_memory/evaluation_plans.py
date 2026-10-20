"""Deterministic, generation-free development plans from imported annotations."""
import hashlib
import json
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .builds import BuildError
from .evaluation import EvaluationInput
from .imports import canonical_json
from .model import utc_now

COURSE_SPLIT = {'dev': ['conv-26', 'conv-30', 'conv-41', 'conv-42'], 'test': ['conv-43', 'conv-44']}
STRATEGIES = ['full_text', 'vector', 'hybrid_no_resolution', 'dynamic']
PLAN_VERSION = 'fixed-development-v1'


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    scope: Literal['development', 'smoke'] = 'development'
    include_raw_fallback: bool = False

    @model_validator(mode='after')
    def limited_raw_comparison(self):
        if self.include_raw_fallback and self.scope != 'smoke':
            raise ValueError('Raw fallback is limited to smoke plans')
        return self


class EvaluationPlanService:
    def __init__(self, evaluation):
        self.evaluation = evaluation
        self.database = evaluation.database
        with self.database.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS evaluation_plans(plan_id TEXT PRIMARY KEY, result_json TEXT NOT NULL)')

    def get(self, plan_id):
        with self.database.connect() as db:
            row = db.execute('SELECT result_json FROM evaluation_plans WHERE plan_id=?', (plan_id,)).fetchone()
        if row is None:
            raise BuildError('not_found', 404)
        return json.loads(row[0])

    def create(self, request):
        with self.database.connect() as db:
            dataset = db.execute('SELECT * FROM datasets WHERE dataset_id=?', (request.dataset_id,)).fetchone()
            artifact = db.execute('SELECT * FROM import_artifacts WHERE dataset_id=? AND artifact_sha256=?', (request.dataset_id, request.artifact_sha256)).fetchone()
        if dataset is None or artifact is None:
            raise BuildError('evaluation_artifact_not_found', 404)
        # The explicit artifact identity avoids selecting arbitrary annotations when
        # identical source conversations were imported with different QA metadata.
        annotations = {a['sample_id']: a for a in json.loads(artifact['annotations_json'])}
        selected = COURSE_SPLIT['dev'] if request.scope == 'development' else ['conv-26']
        samples, questions = [], []
        for sample_id in selected:
            qa = annotations.get(sample_id, {}).get('qa')
            if not isinstance(qa, list) or not qa:
                raise BuildError('development_questions_missing', 422)
            seen_categories = set()
            for index, item in enumerate(qa):
                if not isinstance(item, dict):
                    raise BuildError('invalid_evaluation_annotations', 422)
                if request.scope == 'smoke':
                    category = item.get('category')
                    if category not in (1, 2, 3, 4, 5) or category in seen_categories:
                        continue
                    seen_categories.add(category)
                samples.append({key: item[key] for key in ('question', 'answer', 'category', 'evidence') if key in item} | {'sample_id': sample_id})
                questions.append({'sample_id': sample_id, 'qa_index': index, 'question_id': f'{sample_id}:qa:{index}', 'question': item.get('question'), 'category': item.get('category')})
            if request.scope == 'smoke' and seen_categories != {1, 2, 3, 4, 5}:
                raise BuildError('smoke_categories_missing', 422)
        try:
            inputs = EvaluationInput(dataset_id=request.dataset_id, kind='course', course_split=COURSE_SPLIT, samples=samples)
        except ValidationError:
            raise BuildError('invalid_evaluation_annotations', 422) from None
        strategies = STRATEGIES + (['dynamic_raw_fallback'] if request.include_raw_fallback else [])
        plan = {
            'plan_version': PLAN_VERSION, 'scope': request.scope, 'status': 'preview',
            'dataset_id': request.dataset_id, 'source_sha256': dataset['source_sha256'],
            'version': dataset['version'], 'license': dataset['license'],
            'artifact_sha256': request.artifact_sha256, 'checksum_basis': artifact['checksum_basis'],
            'provenance': json.loads(artifact['provenance_json']),
            'course_split': COURSE_SPLIT, 'partition': 'dev', 'grading_set': 'hidden_not_available',
            'strategies': strategies, 'questions': questions,
            'question_count': len(questions), 'combination_count': len(questions) * len(strategies),
        }
        plan_id = hashlib.sha256(canonical_json(plan).encode()).hexdigest()
        with self.database.connect() as db:
            previous = db.execute('SELECT result_json FROM evaluation_plans WHERE plan_id=?', (plan_id,)).fetchone()
        if previous is not None:
            return json.loads(previous[0])
        saved = self.evaluation.add_input(inputs)
        saved['question_identities'] = [{key: q[key] for key in ('sample_id', 'qa_index', 'question_id')} for q in questions]
        saved['plan_id'] = plan_id
        saved['source_identity'] = {key: plan[key] for key in ('dataset_id', 'source_sha256', 'version', 'license', 'artifact_sha256', 'checksum_basis', 'provenance')}
        plan.update(plan_id=plan_id, input_id=saved['input_id'], created_at=utc_now())
        with self.database.connect() as db:
            db.execute('UPDATE evaluation_inputs SET result_json=? WHERE input_id=?', (canonical_json(saved), saved['input_id']))
            db.execute('INSERT INTO evaluation_plans VALUES (?,?)', (plan_id, canonical_json(plan)))
        return plan


def register_evaluation_plan_routes(app, evaluation):
    service = EvaluationPlanService(evaluation)
    app.state.evaluation_plans = service

    def execute(fn, *args):
        try:
            return fn(*args)
        except BuildError as error:
            raise HTTPException(error.status, detail={'code': error.code, 'message': 'Evaluation plan operation failed'}) from None

    @app.post('/evaluation-plans', status_code=201)
    def create_plan(request: PlanRequest):
        return execute(service.create, request)

    @app.get('/evaluation-plans/{plan_id}')
    def get_plan(plan_id: str):
        return execute(service.get, plan_id)
