from web import dashboard


def test_get_user_trials(monkeypatch):
    calls = {}
    def fake_query(sql, params=None):
        calls['sql'] = sql
        calls['params'] = params
        return [{'nct_id': 'NCT1'}]
    monkeypatch.setattr(dashboard, 'query', fake_query)
    result = dashboard.get_user_trials(2)
    assert result == [{'nct_id': 'NCT1'}]
    assert 'uo.user_id = %s' in calls['sql']
    assert calls['params'] == [2]


def test_get_org_compliance(monkeypatch):
    calls = {}
    def fake_query(sql, params=None):
        calls['sql'] = sql
        calls['params'] = params
        return [{'name': 'Org', 'rate': 100}]
    monkeypatch.setattr(dashboard, 'query', fake_query)
    result = dashboard.get_org_compliance()
    assert result == [{'name': 'Org', 'rate': 100}]
    assert 'organization' in calls['sql'].lower()
    assert calls['params'] is None
