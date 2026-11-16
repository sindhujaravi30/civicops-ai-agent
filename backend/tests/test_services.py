from app.services import seed_demo_profile, get_profile

def test_seed_profile_exists():
    """Verify the seeded demo profile exists with the expected vehicle identifier."""
    seed_demo_profile()
    profile = get_profile("demo-citizen")
    assert profile is not None
    assert profile["vehicle_id"] == "AUH-12345"
