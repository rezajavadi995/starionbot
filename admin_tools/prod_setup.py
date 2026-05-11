from __future__ import annotations

import json
import re
import shlex
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from admin_tools.env_manager import load_env_map, set_env_value

console = Console()

DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$")


@dataclass
class ValidationItem:
    name: str
    ok: bool
    details: str


def run(cmd: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr).strip()


def ensure_packages() -> None:
    packages = [
        "nginx",
        "certbot",
        "python3-certbot-nginx",
        "docker.io",
        "docker-compose-plugin",
        "openssl",
        "curl",
        "ufw",
        "dnsutils",
        "net-tools",
    ]
    for package in packages:
        ok, _ = run(f"dpkg -s {shlex.quote(package)} >/dev/null 2>&1")
        if ok:
            continue
        console.print(f"[yellow]Installing {package}...[/yellow]")
        run("sudo apt-get update")
        run(f"sudo apt-get install -y {shlex.quote(package)}")


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain))


def resolve_domain(domain: str) -> list[str]:
    try:
        _, _, ips = socket.gethostbyname_ex(domain)
        return sorted(set(ips))
    except OSError:
        return []


def public_ip() -> str:
    ok, out = run("curl -fsSL https://api.ipify.org")
    return out.strip() if ok else ""


def configure_domain_and_ssl(primary_domain: str, subdomains: list[str]) -> None:
    if not is_valid_domain(primary_domain):
        raise ValueError("Invalid primary domain format")

    full_domains = [primary_domain] + [f"{item.strip()}.{primary_domain}" for item in subdomains if item.strip()]

    server_ip = public_ip()
    for domain in full_domains:
        ips = resolve_domain(domain)
        if not ips:
            raise ValueError(f"DNS not resolved for {domain}")
        if server_ip and server_ip not in ips:
            raise ValueError(f"{domain} DNS IP mismatch. expected={server_ip} got={ips}")

    for port in (80, 443):
        ok, _ = run(f"sudo ss -ltn '( sport = :{port} )' | tail -n +2")
        if not ok:
            console.print(f"[yellow]Port {port} listener not active yet; continuing.[/yellow]")

    ensure_packages()
    domains_flags = " ".join([f"-d {shlex.quote(domain)}" for domain in full_domains])
    cert_cmd = (
        "sudo certbot certonly --standalone --non-interactive --agree-tos "
        "--register-unsafely-without-email " + domains_flags
    )
    ok, out = run(cert_cmd)
    if not ok:
        raise RuntimeError(f"certbot failed: {out[:400]}")

    run("sudo systemctl enable certbot.timer")
    run("sudo systemctl start certbot.timer")
    run("sudo certbot renew --dry-run")

    cert_path = f"/etc/letsencrypt/live/{primary_domain}/fullchain.pem"
    key_path = f"/etc/letsencrypt/live/{primary_domain}/privkey.pem"
    set_env_value("APP_DOMAIN", primary_domain)
    set_env_value("API_DOMAIN", f"api.{primary_domain}")
    set_env_value("PANEL_DOMAIN", f"panel.{primary_domain}")
    set_env_value("MINIAPP_URL", f"https://{primary_domain}/app")
    set_env_value("WEBHOOK_URL", f"https://api.{primary_domain}/webhook")
    set_env_value("SSL_CERT_PATH", cert_path)
    set_env_value("SSL_KEY_PATH", key_path)


def configure_nginx() -> None:
    env = load_env_map()
    app_domain = env.get("APP_DOMAIN", "")
    api_domain = env.get("API_DOMAIN", "")
    panel_domain = env.get("PANEL_DOMAIN", "")
    cert = env.get("SSL_CERT_PATH", "")
    key = env.get("SSL_KEY_PATH", "")
    if not all([app_domain, api_domain, panel_domain, cert, key]):
        raise ValueError("Missing domain/SSL env values. Run domain setup first.")

    config = f"""
server {{
    listen 80;
    server_name {app_domain} {api_domain} {panel_domain};
    return 301 https://$host$request_uri;
}}
server {{
    listen 443 ssl http2;
    server_name {app_domain};
    ssl_certificate {cert};
    ssl_certificate_key {key};
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin-when-cross-origin;
    gzip on;
    location / {{ proxy_pass http://127.0.0.1:3000; }}
    location /app {{ proxy_pass http://127.0.0.1:3000/app; }}
}}
server {{
    listen 443 ssl http2;
    server_name {api_domain} {panel_domain};
    ssl_certificate {cert};
    ssl_certificate_key {key};
    location / {{
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection \"upgrade\";
        proxy_set_header Host $host;
        proxy_pass http://127.0.0.1:8000;
    }}
}}
""".strip()
    Path("/tmp/starionbot-nginx.conf").write_text(config + "\n")
    run("sudo mv /tmp/starionbot-nginx.conf /etc/nginx/sites-available/starionbot")
    run("sudo ln -sfn /etc/nginx/sites-available/starionbot /etc/nginx/sites-enabled/starionbot")
    run("sudo nginx -t")
    run("sudo systemctl reload nginx")


def configure_telegram_webhook() -> None:
    env = load_env_map()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    secret = env.get("WEBHOOK_SECRET", "")
    url = env.get("WEBHOOK_URL", "")
    if not token or not url:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or WEBHOOK_URL in .env")
    secret_flag = f"-d secret_token={shlex.quote(secret)}" if secret else ""
    run(f"curl -fsSL -X POST https://api.telegram.org/bot{token}/setWebhook -d url={shlex.quote(url)} {secret_flag}")
    ok, out = run(f"curl -fsSL https://api.telegram.org/bot{token}/getWebhookInfo")
    if not ok:
        raise RuntimeError("Webhook verification failed")
    data = json.loads(out)
    current = data.get("result", {}).get("url", "")
    if current != url:
        raise RuntimeError("Webhook URL mismatch after setWebhook")


def validate_https_infra() -> list[ValidationItem]:
    env = load_env_map()
    app_domain = env.get("APP_DOMAIN", "")
    api_domain = env.get("API_DOMAIN", "")
    checks: list[ValidationItem] = []

    checks.append(ValidationItem("DNS app", bool(resolve_domain(app_domain)), app_domain or "not set"))
    checks.append(ValidationItem("DNS api", bool(resolve_domain(api_domain)), api_domain or "not set"))

    ok, out = run("sudo systemctl is-active nginx")
    checks.append(ValidationItem("nginx status", ok and "active" in out, out or "unknown"))

    ok, _ = run(f"curl -k -I -s http://{app_domain} | head -n 1 | grep -q '301\\|308'") if app_domain else (False, "")
    checks.append(ValidationItem("HTTP->HTTPS", ok, "redirect check"))

    ok, _ = run(f"curl -fsS https://{app_domain}/ >/dev/null") if app_domain else (False, "")
    checks.append(ValidationItem("Mini app reachability", ok, env.get("MINIAPP_URL", "not set")))

    ok, _ = run("curl -fsS http://127.0.0.1:8000/health >/dev/null")
    checks.append(ValidationItem("Backend availability", ok, "http://127.0.0.1:8000/health"))
    return checks
