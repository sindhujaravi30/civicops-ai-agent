from app.policy import retrieve_policy

def test_policy_retrieval_returns_relevant_chunks():
    """Ensure policy lookup returns relevant registration and insurance text."""
    results = retrieve_policy("vehicle registration insurance renewal")
    assert results
    assert any("insurance" in item["title"].lower() or "registration" in item["title"].lower()
               for item in results)
