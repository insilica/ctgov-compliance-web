from web import auth


def test_user_get_returns_user(monkeypatch):
    def fake_query(sql, params=None, fetchone=False):
        assert fetchone
        return {'id': 1, 'email': 'alice@example.com', 'password_hash': 'x'}
    monkeypatch.setattr(auth, 'query', fake_query)
    user = auth.User.get(1)
    assert isinstance(user, auth.User)
    assert user.id == 1
    assert user.email == 'alice@example.com'


def test_user_get_returns_none(monkeypatch):
    monkeypatch.setattr(auth, 'query', lambda *a, **k: None)
    assert auth.User.get(99) is None
