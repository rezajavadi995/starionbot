from __future__ import annotations

import json
import re
import shlex
import socket
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from admin_tools.env_manager import load_env_map, set_env_value

console = Console()

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)" r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)
PRODUCTION_PACKAGES = [
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


@dataclass(slots=True)
class ValidationItem:
    name: str
    ok: bool
    details: str


def run(cmd: str) -> tuple[bool, str]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + "\n" + proc.stderr).strip()


def ensure_packages() -> None:
    if not _command_exists("apt-get"):
        console.print("[yellow]apt-get not found; skipping package auto-install.[/yellow]")
        return

    missing: list[str] = []
    for package in PRODUCTION_PACKAGES:
        ok, _ = run(f"dpkg -s {shlex.quote(package)} >/dev/null 2>&1")
        if not ok:
            missing.append(package)

    if not missing:
        return

    console.print("[yellow]Installing production dependencies...[/yellow]")
    run("sudo apt-get update")
    packages = " ".join(shlex.quote(package) for package in missing)
    ok, out = run(f"sudo apt-get install -y {packages}")
    if not ok:
        raise RuntimeError(f"production package installation failed: {out[:400]}")


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_RE.match(domain))


def resolve_domain(domain: str) -> list[str]:
    if not domain:
        return []
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

    full_domains = _full_domain_list(primary_domain, subdomains)
    server_ip = public_ip()
    for domain in full_domains:
        _validate_domain_dns(domain, server_ip)
        if cloudflare_proxy_detected(domain):
            console.print(
                f"[yellow]Cloudflare proxy detected for {domain}; "
                "standalone certbot may require temporarily disabling proxy.[/yellow]"
            )

    for port in (80, 443):
        if not _port_listener_exists(port):
            console.print(f"[yellow]Port {port} listener not active yet; continuing.[/yellow]")

    ensure_packages()
    domains_flags = " ".join(f"-d {shlex.quote(domain)}" for domain in full_domains)
    cert_cmd = (
        "sudo certbot certonly --standalone --non-interactive --agree-tos "
        f"--register-unsafely-without-email {domains_flags}"
    )
    ok, out = run(cert_cmd)
    if not ok:
        raise RuntimeError(f"certbot failed: {out[:400]}")

    _enable_certbot_renewal()
    cert_path = f"/etc/letsencrypt/live/{primary_domain}/fullchain.pem"
    key_path = f"/etc/letsencrypt/live/{primary_domain}/privkey.pem"
    _validate_certificate(cert_path)

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

    config = _nginx_config(
        app_domain=app_domain,
        api_domain=api_domain,
        panel_domain=panel_domain,
        cert=cert,
        key=key,
    )
    Path("/tmp/starionbot-nginx.conf").write_text(config + "\n")
    commands = [
        "sudo mv /tmp/starionbot-nginx.conf /etc/nginx/sites-available/starionbot",
        "sudo ln -sfn /etc/nginx/sites-available/starionbot /etc/nginx/sites-enabled/starionbot",
        "sudo nginx -t",
        "sudo systemctl reload nginx",
    ]
    for command in commands:
        ok, out = run(command)
        if not ok:
            raise RuntimeError(f"nginx command failed: {out[:400]}")


def configure_telegram_webhook() -> None:
    env = load_env_map()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    secret = env.get("WEBHOOK_SECRET", "")
    url = env.get("WEBHOOK_URL", "")
    if not token or not url:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or WEBHOOK_URL in .env")

    set_webhook_result = _telegram_api_call(
        token,
        "setWebhook",
        {"url": url, "secret_token": secret} if secret else {"url": url},
    )
    if not bool(set_webhook_result.get("ok")):
        raise RuntimeError("Telegram setWebhook failed")

    info = _telegram_api_call(token, "getWebhookInfo", {})
    if not bool(info.get("ok")):
        raise RuntimeError("Webhook verification failed")

    result = info.get("result", {})
    current = result.get("url", "") if isinstance(result, dict) else ""
    if current != url:
        raise RuntimeError("Webhook URL mismatch after setWebhook")


def validate_https_infra() -> list[ValidationItem]:
    env = load_env_map()
    app_domain = env.get("APP_DOMAIN", "")
    api_domain = env.get("API_DOMAIN", "")
    webhook_url = env.get("WEBHOOK_URL", "")
    miniapp_url = env.get("MINIAPP_URL", "")
    cert = env.get("SSL_CERT_PATH", "")
    checks: list[ValidationItem] = []

    checks.append(_dns_validation_item("DNS app", app_domain))
    checks.append(_dns_validation_item("DNS api", api_domain))
    checks.append(_port_validation_item(80))
    checks.append(_port_validation_item(443))

    ok, out = run("sudo systemctl is-active nginx")
    checks.append(ValidationItem("nginx status", ok and "active" in out, out or "unknown"))

    checks.append(_certificate_validation_item(cert))
    checks.append(_https_redirect_item(app_domain))
    checks.append(_url_reachability_item("Mini app reachability", miniapp_url))
    checks.append(_url_reachability_item("Webhook reachability", webhook_url))

    ok, _ = run("curl -fsS http://127.0.0.1:8000/health >/dev/null")
    checks.append(ValidationItem("Backend availability", ok, "http://127.0.0.1:8000/health"))
    return checks


def cloudflare_proxy_detected(domain: str) -> bool:
    if not domain:
        return False
    ok, out = run(f"curl -I -s --max-time 5 https://{shlex.quote(domain)}")
    lowered = out.lower()
    return ok and ("cloudflare" in lowered or "cf-ray" in lowered)


def _command_exists(binary: str) -> bool:
    ok, _ = run(f"command -v {shlex.quote(binary)} >/dev/null 2>&1")
    return ok


def _full_domain_list(primary_domain: str, subdomains: list[str]) -> list[str]:
    full_domains = [primary_domain]
    full_domains.extend(f"{item.strip()}.{primary_domain}" for item in subdomains if item.strip())
    return full_domains


def _validate_domain_dns(domain: str, server_ip: str) -> None:
    ips = resolve_domain(domain)
    if not ips:
        raise ValueError(f"DNS not resolved for {domain}")
    if server_ip and server_ip not in ips:
        raise ValueError(f"{domain} DNS IP mismatch. expected={server_ip} got={ips}")


def _port_listener_exists(port: int) -> bool:
    ok, out = run(f"sudo ss -ltn '( sport = :{port} )' | tail -n +2")
    return ok and bool(out.strip())


def _enable_certbot_renewal() -> None:
    commands = [
        "sudo systemctl enable certbot.timer",
        "sudo systemctl start certbot.timer",
        "sudo certbot renew --dry-run",
    ]
    for command in commands:
        ok, out = run(command)
        if not ok:
            raise RuntimeError(f"certbot renewal command failed: {out[:400]}")


def _validate_certificate(cert_path: str) -> None:
    ok, out = run(f"sudo openssl x509 -checkend 2592000 -noout -in {shlex.quote(cert_path)}")
    if not ok:
        raise RuntimeError(f"certificate validation failed: {out[:400]}")


def _nginx_config(
    *,
    app_domain: str,
    api_domain: str,
    panel_domain: str,
    cert: str,
    key: str,
) -> str:
    return f"""
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
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    location / {{
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass http://127.0.0.1:3000;
    }}

    location /app {{
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass http://127.0.0.1:3000/app;
    }}
}}

server {{
    listen 443 ssl http2;
    server_name {api_domain} {panel_domain};

    ssl_certificate {cert};
    ssl_certificate_key {key};
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    location / {{
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass http://127.0.0.1:8000;
    }}
}}
""".strip()


def _telegram_api_call(token: str, method: str, data: dict[str, str]) -> dict[str, object]:
    body = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body if body else None,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read().decode()
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise RuntimeError("Unexpected Telegram API response")
    return parsed


def _dns_validation_item(name: str, domain: str) -> ValidationItem:
    ips = resolve_domain(domain)
    return ValidationItem(name, bool(ips), ", ".join(ips) if ips else domain or "not set")


def _port_validation_item(port: int) -> ValidationItem:
    ok = _port_listener_exists(port)
    return ValidationItem(f"Port {port}", ok, "listening" if ok else "not listening")


def _certificate_validation_item(cert_path: str) -> ValidationItem:
    if not cert_path:
        return ValidationItem("SSL certificate", False, "SSL_CERT_PATH not set")
    ok, out = run(f"sudo openssl x509 -enddate -noout -in {shlex.quote(cert_path)}")
    return ValidationItem("SSL certificate", ok, out or cert_path)


def _https_redirect_item(app_domain: str) -> ValidationItem:
    if not app_domain:
        return ValidationItem("HTTP->HTTPS", False, "APP_DOMAIN not set")
    command = f"curl -k -I -s http://{shlex.quote(app_domain)} | head -n 1"
    ok, out = run(command)
    redirected = ok and ("301" in out or "308" in out)
    return ValidationItem("HTTP->HTTPS", redirected, out or "redirect check failed")


def _url_reachability_item(name: str, url: str) -> ValidationItem:
    if not url:
        return ValidationItem(name, False, "not set")
    ok, _ = run(f"curl -fsS --max-time 10 {shlex.quote(url)} >/dev/null")
    return ValidationItem(name, ok, url)
