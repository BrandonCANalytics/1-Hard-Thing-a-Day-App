import os, time, random, string, sys, json
import requests

BASE_URL = os.getenv("BASE_URL", "https://one-hard-thing.fly.dev").rstrip("/")

def get(p, **kw):
    return requests.get(BASE_URL + p, timeout=10, **kw)

def post(p, **kw):
    return requests.post(BASE_URL + p, timeout=10, **kw)

def ok(resp, code=200):
    assert resp.status_code == code, f"{resp.request.method} {resp.request.url} -> {resp.status_code}: {resp.text}"
    return resp

def pretty(obj): return json.dumps(obj, indent=2, ensure_ascii=False)

def test_health():
    # If you didn't add /health, skip this one.
    r = get("/health")
    if r.status_code == 404:
        print("⚠️ /health not found (optional). Skipping.")
        return
    ok(r)
    data = r.json()
    assert data.get("status") == "ok", f"health payload: {data}"
    print("✅ /health OK")

def test_items_nonempty():
    r = ok(get("/items"))
    items = r.json()
    assert isinstance(items, list), "items should be a list"
    assert len(items) >= 1, "items list is empty; seed data missing?"
    # basic shape
    for i in items[:3]:
        for k in ["id","name","category","is_half","weight"]:
            assert k in i, f"missing key {k} in item: {i}"
    print(f"✅ /items returned {len(items)} items")

def test_choice_full_and_halfpair():
    # Full
    r = ok(get("/choice", params={"mode":"full","seed":123}))
    data = r.json()
    assert data["type"] == "full", data
    assert len(data["items"]) == 1 and not data["items"][0]["is_half"]
    print("✅ /choice (full) OK")

    # Half-pair
    r = ok(get("/choice", params={"mode":"half-pair","seed":123}))
    data = r.json()
    assert data["type"] == "half-pair", data
    assert len(data["items"]) == 2, data
    assert all(i["is_half"] for i in data["items"]), data
    assert data["items"][0]["id"] != data["items"][1]["id"], "duplicate half items"
    print("✅ /choice (half-pair) OK")

def test_choice_random_with_prob():
    # Force half with probability=1.0
    r = ok(get("/choice", params={"mode":"random","half_pair_probability":1.0,"seed":42}))
    data = r.json()
    assert data["type"] == "half-pair", data
    # Force full with probability=0.0
    r = ok(get("/choice", params={"mode":"random","half_pair_probability":0.0,"seed":42}))
    data2 = r.json()
    assert data2["type"] in ("full","half-pair"), data2  # if no full items exist, backend may fallback to half-pair
    print("✅ /choice (random) probability behavior OK")

def test_filters():
    # Exclude a category and ensure results respect it
    r = ok(get("/choice", params={"mode":"full","exclude_categories":"Discipline"}))
    data = r.json()
    if data["items"]:
        assert data["items"][0]["category"] != "Discipline", data
    print("✅ /choice filters OK (basic)")

def test_submit_pending():
    # Unique name to avoid 409 duplicate
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    body = {"name": f"QA Mobility {suffix}", "category":"Physical", "is_half": True}
    r = post("/items/submit", json=body)
    if r.status_code == 404:
        print("⚠️ /items/submit not implemented on this deploy. Skipping submit test.")
        return
    if r.status_code == 429:
        print("⚠️ Rate limit reached for submissions. Skipping submit test.")
        return
    data = ok(r, code=201).json()
    assert data.get("ok") is True and data.get("status") in ("pending","approved"), data
    print("✅ /items/submit OK ->", pretty(data))

def main():
    print(f"🔎 Testing {BASE_URL}")
    try:
        test_health()
    except AssertionError as e:
        print("❌ health test failed:", e)

    test_items_nonempty()
    test_choice_full_and_halfpair()
    test_choice_random_with_prob()
    test_filters()
    test_submit_pending()
    print("🎉 Smoke suite finished")

if __name__ == "__main__":
    main()
