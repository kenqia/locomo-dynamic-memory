import pytest

from tools.research_v2.phase3_paired import outcome, pair_state, score, oracle


@pytest.mark.parametrize('hs,ds,state', [
    ('succeeded','succeeded','both_succeeded'), ('succeeded','failed','hybrid_only_succeeded'),
    ('failed','succeeded','dynamic_only_succeeded'), ('failed','failed','both_failed'),
    ('unknown','succeeded','unknown'), ('succeeded','pending','unknown')])
def test_all_pair_states(hs,ds,state):
    assert pair_state(dict(status=hs),dict(status=ds))==state


def test_unknown_is_not_failed_or_zero():
    result=outcome([dict(status='succeeded',qa=.6),dict(status='failed',qa=None),dict(status='unknown',qa=None)])
    assert result['full_denominator_score'] is None
    assert result['full_denominator_bounds']==pytest.approx([.2,1.6/3])
    assert result['scorable']==1
    assert outcome([dict(status='failed',qa=None)])['full_denominator_score']==0


@pytest.mark.parametrize('value',[None,float('nan'),float('inf'),True,-.1,1.1,'1'])
def test_only_legal_successful_scores(value):
    assert score(dict(status='succeeded',result=dict(qa=dict(value=value)))) is None
    assert score(dict(status='failed',result=dict(qa=dict(value=1)))) is None


def test_oracle_cannot_choose_using_unknown_and_prefers_completion_to_failure():
    def arm(status,qa,cost):return dict(status=status,qa=qa,cost_by_stage={'all':{'known_peak_estimate_cny':cost}})
    rows=[dict(pair_state='both_succeeded',hybrid=arm('succeeded',.2,1),dynamic=arm('succeeded',.8,10)),
          dict(pair_state='hybrid_only_succeeded',hybrid=arm('succeeded',0,1),dynamic=arm('failed',None,2)),
          dict(pair_state='unknown',hybrid=arm('unknown',None,2),dynamic=arm('succeeded',1,10))]
    result=oracle(rows)
    assert result['choices']==dict(hybrid=1,dynamic=1,unknown=1)
    assert result['selected_historical_cost_cny']==11
    assert result['outcome']['full_denominator_score'] is None
