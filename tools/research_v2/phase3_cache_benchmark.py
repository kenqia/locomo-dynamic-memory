"""Real cached MiniLM replay, no network, no application factory or paid model."""
import argparse
from collections import defaultdict
from importlib.metadata import version
import json
from pathlib import Path
import resource
import sys
import time
import tracemalloc

import numpy as np
from rank_bm25 import BM25Okapi

from locomo_memory.config import Settings
from locomo_memory.embeddings import MiniLMEmbedder, normalize_vectors
from locomo_memory.retrieval import budget_tokens, indexing_text, tokenize
from .embedding_cache import ExactQueryEmbeddingCache
from .postbaseline import file_sha, readonly, sha, write


def rank(pool,vector,question,analysis,config):
    query=tokenize(question)+tokenize(' '.join((analysis.get('result') or {}).get('keywords',[])))
    scores=dict(dense=pool['vectors']@vector,bm25=pool['bm25'].get_scores(query))
    channels={};fused=defaultdict(float)
    for name,values in scores.items():
        indices=sorted(range(len(values)),key=lambda i:(-float(values[i]),pool['ids'][i]))[:config[name+'_k']]
        channels[name]=[(pool['ids'][i],float(values[i])) for i in indices]
        for r,i in enumerate(indices,1):fused[pool['ids'][i]]+=1/(config['rrf_constant']+r)
    order=sorted(fused,key=lambda mid:(-fused[mid],mid));selected=[];used=0
    for mid in order[:config['initial_k']]:
        cost=pool['tokens'][mid]
        if used+cost>config['candidate_token_budget']:break
        used+=cost;selected.append(mid)
    return dict(channels=channels,initial_candidates=selected,candidate_token_count=used)


def run(runtime,controlled,output):
    import torch
    torch.set_num_threads(1)
    runtime,controlled,output=map(Path,(runtime,controlled,output))
    groups=defaultdict(list)
    with (controlled/'initial-observations.jsonl').open() as stream:
        for line in stream:
            r=json.loads(line)
            if not r['initial']:raise ValueError('Missing initial observation')
            groups[r['build_id']].append(r)
    boot=time.perf_counter();bootcpu=time.process_time();pools={};encoders={};base=MiniLMEmbedder(Settings())
    with readonly(runtime/'memory.sqlite3') as db:
        for bid in groups:
            fp,metadata=db.execute('SELECT fingerprint,metadata_json FROM build_indexes WHERE build_id=?',(bid,)).fetchone()
            info=json.loads(metadata);encoder=base.for_identity(info['embedding']);encoders[bid]=encoder
            if encoder.identity()!=info['embedding']:raise ValueError('Encoder identity changed')
            entries=list(db.execute('SELECT e.memory_id,e.index_text,e.vector,m.memory_json FROM index_entries e JOIN memories m ON m.memory_id=e.memory_id WHERE e.build_id=? ORDER BY e.memory_id',(bid,)))
            ids=[r[0] for r in entries];texts=[r[1] for r in entries]
            vectors=normalize_vectors(np.vstack([np.frombuffer(r[2],dtype=np.float32) for r in entries]),len(entries),info['embedding']['dimensions'])
            pools[bid]=dict(ids=ids,vectors=vectors,bm25=BM25Okapi([tokenize(t) for t in texts]),
                tokens={r[0]:budget_tokens(indexing_text(json.loads(r[3]))) for r in entries},fingerprint=fp,**info)
    startup=dict(wall_seconds=time.perf_counter()-boot,cpu_seconds=time.process_time()-bootcpu,
        note='Model load, identity verification and four read-only index matrices/BM25 preparation. Shared by all measured phases.')
    cache=ExactQueryEmbeddingCache();metrics=[];reference={};ranks={};per_item=[]
    tracemalloc.start()
    for phase in ('disabled','cold','warm'):
        start=time.perf_counter();cpu=time.process_time();enc_cpu=enc_wall=rank_cpu=0;calls=0;mismatches=0
        for bid,observations in groups.items():
            pool=pools[bid];encoder=encoders[bid]
            for r in observations:
                qid=r['question_id'];q=r['question'];initial=r['initial']
                for repeat in range(3):
                    tick=time.perf_counter();ctick=time.process_time()
                    if phase=='disabled':vector=normalize_vectors(encoder.encode([q]),1,pool['embedding']['dimensions'])[0];calls+=1
                    else:
                        vector,meta=cache.vector(encoder,q,build_id=bid,index_fingerprint=pool['fingerprint'],text_schema_version=pool['text_schema_version']);calls+=meta['embedding_calls']
                    enc_cpu+=time.process_time()-ctick;enc_wall+=time.perf_counter()-tick
                    digest=sha(vector.tobytes())
                    if phase=='disabled' and repeat==0:reference[qid]=digest
                    if digest!=reference[qid]:mismatches+=1
                    tick=time.process_time();ranking=rank(pool,vector,q,initial['analysis'],initial['config']);rank_cpu+=time.process_time()-tick
                    rank_hash=sha(json.dumps(ranking,sort_keys=True).encode())
                    if phase=='disabled' and repeat==0:ranks[qid]=rank_hash
                    if rank_hash!=ranks[qid]:mismatches+=1
                if phase=='disabled':per_item.append(dict(question_id=qid,build_id=bid,index_fingerprint=pool['fingerprint'],vector_sha256=reference[qid],ranking_sha256=ranks[qid]))
            print(json.dumps(dict(phase=phase,conversation=observations[0]['conversation'],qa=len(observations))),flush=True)
        metrics.append(dict(phase=phase,logical_encodes=3*len(reference),embedding_calls=calls,
            wall_seconds=time.perf_counter()-start,cpu_seconds=time.process_time()-cpu,
            encoding_cpu_seconds=enc_cpu,encoding_wall_seconds=enc_wall,ranking_cpu_seconds=rank_cpu,
            vector_or_ranking_mismatches=mismatches,cache=cache.snapshot()))
    current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    if any(m['vector_or_ranking_mismatches'] for m in metrics):raise ValueError('Vector/ranking equivalence failed')
    disabled,cold,warm=metrics
    result=dict(version='phase3-e5-real-minilm-v1',qa=len(reference),strategy_repetitions=3,startup=startup,phases=metrics,
        cold_encoding_cpu_reduction=1-cold['encoding_cpu_seconds']/disabled['encoding_cpu_seconds'],
        cold_local_retrieval_cpu_reduction=1-cold['cpu_seconds']/disabled['cpu_seconds'],
        warm_encoding_cpu_reduction=1-warm['encoding_cpu_seconds']/disabled['encoding_cpu_seconds'],
        memory=dict(process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            python_tracemalloc_current_bytes=current,python_tracemalloc_peak_bytes=peak,
            cache_object_bytes_estimate=sys.getsizeof(cache.entries)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in cache.entries.items()),
            notice='One process shared model and four index pools. RSS is combined high-water mark, not cache-only memory or summed per-phase peaks.'),
        dependency_versions={name:version(name) for name in ('sentence-transformers','torch','numpy','rank-bm25')},
        embeddings={bid:p['embedding'] for bid,p in pools.items()},
        deepseek_physical_calls=0,provider_token_saving=0,provider_cny_saving=0,
        scope='Isolated query encoding + warm in-memory ranking replay of fixed index. Does not include production SQLite loading per query, paid analysis/resolution/answer, or new Build. Wall/CPU costs include benchmark tracing overhead; sequential phases share model warmup.',
        code_sha256={str(p):file_sha(p) for p in (Path(__file__),Path(__file__).with_name('embedding_cache.py'))})
    write(output/'cache-items.json',per_item);write(output/'cache-benchmark.json',result)
    print(json.dumps({k:result[k] for k in ('qa','cold_encoding_cpu_reduction','cold_local_retrieval_cpu_reduction','warm_encoding_cpu_reduction','memory')},indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','controlled','output'):p.add_argument('--'+name,required=True,type=Path)
    run(**vars(p.parse_args()))
