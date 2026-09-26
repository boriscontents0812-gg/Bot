import sys
import io
import urllib.request
import urllib.parse
import json
import http.cookiejar

# Ensure stdout handles UTF-8 cleanly
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8000"

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def test_unauthenticated_root():
    req = urllib.request.Request(f"{BASE}/")
    with opener.open(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "Botyk" in html
        assert "landing-key-input" in html
        assert "Ultimate iMessage Toolkit" in html
        print("[PASS] 1. GET / (unauthenticated) -> Returns exact Landing Page")

def test_login_flow():
    data = json.dumps({"code": "6C6W-K6LD-JRVV-QGTM"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE}/login", data=data, headers={"Content-Type": "application/json"})
    with opener.open(req) as resp:
        assert resp.status == 200
        res_json = json.loads(resp.read().decode('utf-8'))
        assert res_json.get("ok") is True
        print("[PASS] 2. POST /login with 6C6W-K6LD-JRVV-QGTM -> Returns 200 OK & Sets session cookie")

def test_authenticated_root():
    req = urllib.request.Request(f"{BASE}/")
    with opener.open(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "const IS_DEMO = false;" in html
        assert "iMessage Video Generator" in html
        assert "script-input" in html
        print("[PASS] 3. GET / (authenticated) -> Returns full Studio App (IS_DEMO = false)")

def test_me_endpoint():
    req = urllib.request.Request(f"{BASE}/me")
    with opener.open(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        assert data.get("discord_name") == "mONSEY"
        assert data.get("credits_remaining") == 999999999
        assert data.get("credits_total") == 999999999
        assert data.get("is_unlimited") is True
        print(f"[PASS] 4. GET /me -> Returns profile (discord_name={data['discord_name']}, credits={data['credits_remaining']}/{data['credits_total']}, is_unlimited={data.get('is_unlimited')})")

def test_demo_flow():
    demo_cj = http.cookiejar.CookieJar()
    demo_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(demo_cj))
    
    req = urllib.request.Request(f"{BASE}/demo")
    with demo_opener.open(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "const IS_DEMO = true;" in html
        print("[PASS] 5. GET /demo -> Sets imsg_demo cookie and renders Studio in demo mode (IS_DEMO = true)")

    req2 = urllib.request.Request(f"{BASE}/demo/exit")
    with demo_opener.open(req2) as resp:
        assert resp.status == 200
        html2 = resp.read().decode('utf-8')
        assert "landing-key-input" in html2
        print("[PASS] 6. GET /demo/exit -> Clears demo cookie and returns to Landing Page")

def test_preview_generation():
    body_ios = {
        "script": "Alice 💕\n1: Alice > Hello there!\n2: Bob > Hey Alice! How are you?\n1: Alice > Doing great, check out this video!",
        "style": "ios",
        "theme": "dark",
        "page": 0
    }
    data = json.dumps(body_ios).encode('utf-8')
    req = urllib.request.Request(f"{BASE}/preview/0", data=data, headers={"Content-Type": "application/json"})
    with opener.open(req) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/jpeg"
        assert resp.headers.get("X-Total-Pages") == "1"
        img = resp.read()
        assert len(img) > 1000
        print(f"[PASS] 7. POST /preview/0 (iOS) -> Returns valid JPEG preview image ({len(img)} bytes), X-Total-Pages=1")

    body_wa = {
        "script": "Group\n1: Alice > Hey guys!\n2: Bob > Welcome!",
        "style": "whatsapp",
        "wa_theme": "dark",
        "page": 0
    }
    data_wa = json.dumps(body_wa).encode('utf-8')
    req_wa = urllib.request.Request(f"{BASE}/preview/0", data=data_wa, headers={"Content-Type": "application/json"})
    with opener.open(req_wa) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/jpeg"
        print("[PASS] 8. POST /preview/0 (WhatsApp) -> Returns valid JPEG preview image")

def test_projects_crud():
    req = urllib.request.Request(f"{BASE}/api/projects")
    with opener.open(req) as resp:
        assert resp.status == 200
        projects = json.loads(resp.read().decode('utf-8'))
        names = [p["name"] for p in projects]
        assert "Promo" in names
        print(f"[PASS] 9. GET /api/projects -> Returns {len(projects)} projects: {names}")

    req_load = urllib.request.Request(f"{BASE}/api/projects/Promo/load")
    with opener.open(req_load) as resp:
        assert resp.status == 200
        p_data = json.loads(resp.read().decode('utf-8'))
        assert p_data.get("name") == "Promo"
        assert len(p_data.get("script", "")) > 10
        print("[PASS] 10. GET /api/projects/Promo/load -> Successfully loaded Promo script & settings")

def test_static_assets():
    req = urllib.request.Request(f"{BASE}/assets/favicon.png")
    with opener.open(req) as resp:
        assert resp.status == 200
        print(f"[PASS] 11. GET /assets/favicon.png -> 200 OK ({len(resp.read())} bytes)")

    req_demo = urllib.request.Request(f"{BASE}/assets/demo/demo1.mp4")
    with opener.open(req_demo) as resp:
        assert resp.status == 200
        print("[PASS] 12. GET /assets/demo/demo1.mp4 -> 200 OK (video served)")

def test_admin_flow():
    req = urllib.request.Request(f"{BASE}/admin")
    with opener.open(req) as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "Admin Panel" in html
        print("[PASS] 13. GET /admin -> Returns Admin login interface")

    data = json.dumps({"password": "admin123"}).encode('utf-8')
    req_login = urllib.request.Request(f"{BASE}/admin/login", data=data, headers={"Content-Type": "application/json"})
    with opener.open(req_login) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode('utf-8'))
        assert res.get("ok") is True
        print("[PASS] 14. POST /admin/login -> Successfully authenticated admin session")

    req_dash = urllib.request.Request(f"{BASE}/admin/dashboard")
    with opener.open(req_dash) as resp:
        assert resp.status == 200
        dash = json.loads(resp.read().decode('utf-8'))
        assert "total_keys" in dash
        print(f"[PASS] 15. GET /admin/dashboard -> Total keys: {dash['total_keys']}, videos: {dash['total_videos']}")

if __name__ == "__main__":
    print("--- Running Verification Suite ---")
    test_unauthenticated_root()
    test_login_flow()
    test_authenticated_root()
    test_me_endpoint()
    test_demo_flow()
    test_preview_generation()
    test_projects_crud()
    test_static_assets()
    test_admin_flow()
    print("\nALL 15 VERIFICATION TESTS PASSED SUCCESSFULLY!")
