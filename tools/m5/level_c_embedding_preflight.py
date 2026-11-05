"""Check all fixed question embeddings locally, without model generation or Gold."""
import argparse
import json
from pathlib import Path
import resource
import time

import numpy as np

from locomo_memory.embeddings import MiniLMEmbedder
from tools.m5.level_c import verify_plan
from tools.m5.offline import sha, write


def run(output):
    plan, settings, inputs = verify_plan(output)
    if not settings.embedding_local_files_only:
        raise ValueError('embedding_preflight_must_be_offline')
    start, cpu = time.perf_counter(), time.process_time()
    encoder = MiniLMEmbedder(settings)
    vectors = encoder.encode([r['question'] for r in inputs])
    if vectors.shape != (100,384) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors,axis=1),1,atol=1e-5):
        raise ValueError('fixed_question_embedding_preflight_failed')
    result = dict(status='passed', questions=len(inputs), dimensions=vectors.shape[1], embedding_identity=encoder.identity(),
        input_sha256=plan['inputs_sha256'], plan_sha256=sha(output/'plan.json'),
        wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu,
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        provider_calls=0, gold_read=False, gpu_used=False, generation_executed=False)
    write(output/'embedding-preflight.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.output)))
