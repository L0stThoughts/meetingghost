def test_search_stub():
    from backend.search.search_engine import search
    res = search('budget')
    assert isinstance(res, list)
