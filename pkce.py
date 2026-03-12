"""Генерация code_verifier и code_challenge для VK OAuth PKCE"""
import base64
import hashlib
import secrets

# Генерируем code_verifier (43-128 символов, URL-safe)
code_verifier = secrets.token_urlsafe(48)
digest = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")

device_id = "9b8b1f2d-4e0b-4e5b-9e8d-4a37b7b3f2c1"
client_id = "54478990"
redirect_uri = "https://oauth.vk.com/blank.html"

auth_url = (
    f"https://id.vk.com/authorize"
    f"?response_type=code"
    f"&client_id={client_id}"
    f"&redirect_uri={redirect_uri}"
    f"&scope=messages,offline"
    f"&code_challenge={code_challenge}"
    f"&code_challenge_method=S256"
    f"&state=mybot123"
    f"&device_id={device_id}"
)

print("=" * 60)
print("VK OAuth PKCE — сохрани эти значения для обмена code на токен")
print("=" * 60)
print("code_verifier:", code_verifier)
print("code_challenge:", code_challenge)
print("device_id:", device_id)
print()
print("Ссылка для авторизации:")
print(auth_url)
print()
print("После авторизации скопируй code из redirect URL и выполни:")
print(
    f'curl -X POST "https://id.vk.com/oauth2/auth" '
    f'-H "Content-Type: application/x-www-form-urlencoded" '
    f'-d "grant_type=authorization_code" '
    f'-d "client_id={client_id}" '
    f'-d "code=ТВОЙ_CODE" '
    f'-d "redirect_uri={redirect_uri}" '
    f'-d "code_verifier={code_verifier}" '
    f'-d "device_id={device_id}"'
)
