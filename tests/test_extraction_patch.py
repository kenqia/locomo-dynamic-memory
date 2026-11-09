"""Scoped address patches preserve original semantic fields and valid siblings."""
from copy import deepcopy
import pytest
from pydantic import ValidationError
from locomo_memory.evidence_catalog import EvidenceCatalog
from locomo_memory.layered_evidence import ContractViolation
from locomo_memory import extraction_patch

@pytest.fixture
def c():
    return extraction_patch

def source(text,pos=0,session='s1'):
    return {'source_id':f's{pos}','dataset_id':'test','sample_id':'test','session_id':session,'session_time':'2024-01-03','position':pos,'text':text,'speaker':'Ada','dia_id':f'D1:{pos}'}

def record(**kw):
    return {'content':'Ada left yesterday.','memory_type':'event','statement_type':'fact','polarity':'positive','entity_label':'Ada','state_dimension':'departure','state_value':None,'evidence_refs':['E0'],'time_refs':['T0'],**kw}

def test_atomic_scope_keeps_semantics_and_siblings(c):
    cat=EvidenceCatalog([source('I left yesterday. I like coffee.')]);records=[record(evidence_refs=['E0','T0']),record(content='Ada likes coffee.',evidence_refs=['E1'],time_refs=[])]
    before=deepcopy(records)
    revised=c.apply_patches(cat,records,{'status':'corrected','patches':[{'index':0,'evidence_refs':['E0'],'time_refs':['T0']}]})
    assert records==before and revised[1]==records[1]
    for k in records[0]:
        if k not in ('evidence_refs','time_refs'):assert revised[0][k]==records[0][k]
    with pytest.raises(ValidationError):c.apply_patches(cat,records,{'status':'corrected','patches':[{'index':0,'evidence_refs':['E0'],'time_refs':['T0'],'content':'Altered'}]})

def test_no_automatic_anchor_or_time_loss(c):
    cat=EvidenceCatalog([source('I left yesterday. I like coffee.')]);records=[record(evidence_refs=['E1'])]
    with pytest.raises(ContractViolation,match='repair_still_invalid'):c.apply_patches(cat,records,{'status':'corrected','patches':[{'index':0,'evidence_refs':['E1'],'time_refs':['T0']}]})
    with pytest.raises(ContractViolation,match='repair_time_meaning_changed|repair_time_dropped'):c.apply_patches(cat,records,{'status':'corrected','patches':[{'index':0,'evidence_refs':['E1'],'time_refs':[]}]})

def test_patch_scope_complete_unique_and_unsupported(c):
    cat=EvidenceCatalog([source('I left yesterday.')]);records=[record(evidence_refs=['T0'])]
    p={'index':0,'evidence_refs':['E0'],'time_refs':['T0']}
    for patches in ([],[p,p],[{**p,'index':1}]):
        with pytest.raises(ContractViolation,match='repair_scope_mismatch'):c.apply_patches(cat,records,{'status':'corrected','patches':patches})
    with pytest.raises(ContractViolation,match='atomic_repair_unsupported'):c.apply_patches(cat,records,{'status':'unsupported','patches':[]})
    good=[record()];assert c.apply_patches(cat,good,{'status':'corrected','patches':[]})==good
    with pytest.raises(ContractViolation,match='repair_of_valid_batch_forbidden'):c.apply_patches(cat,good,{'status':'corrected','patches':[p]})
