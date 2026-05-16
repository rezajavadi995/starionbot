from __future__ import annotations

import json
import re
import shlex
import socket
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from rich.console import Console

from admin_tools.env_manager import load_env_map, set_env_value

console = Console()

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)" r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)


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


def cloudflare_proxy_detected(domain: str) -> bool:
    ok, out = run(f"dig +short {shlex.quote(domain)}")
    if not ok:
        return False
    ips = [line.strip() for line in out.splitlines() if line.strip()]
    for ip in ips:
        if ip.startswith("104.") or ip.startswith("172.64.") or ip.startswith("188.114."):
            return True
    return False


def public_ip() -> str:
    ok, out = run("curl -fsSL https://api.ipify.org")
    return out.strip() if ok else ""


def _collect_full_domains(primary_domain: str, subdomains: list[str]) -> list[str]:
    full_domains = [primary_domain]
    for item in subdomains:
        clean = item.strip()
        if clean:
            full_domains.append(f"{clean}.{primary_domain}")
    return full_domains


def _validate_certificate_paths(cert_path: str, key_path: str) -> None:
    if not Path(cert_path).exists() or not Path(key_path).exists():
        raise RuntimeError("SSL certificate paths were not created by certbot")


def configure_domain_and_ssl(primary_domain: str, subdomains: list[str]) -> None:
    if not is_valid_domain(primary_domain):
        raise ValueError("Invalid primary domain format")

    full_domains = _collect_full_domains(primary_domain, subdomains)
    server_ip = public_ip()
    for domain in full_domains:
        ips = resolve_domain(domain)
        if not ips:
            raise ValueError(f"DNS not resolved for {domain}")
        if server_ip and server_ip not in ips:
            raise ValueError(f"{domain} DNS IP mismatch. expected={server_ip} got={ips}")
        if cloudflare_proxy_detected(domain):
            console.print(f"[yellow]Cloudflare proxy detected for {domain}[/yellow]")

    for port in (80, 443):
        ok, out = run(f"sudo ss -ltn '( sport = :{port} )' | tail -n +2")
        if not ok or not out.strip():
            console.print(f"[yellow]Port {port} is not currently listening.[/yellow]")

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
    _validate_certificate_paths(cert_path, key_path)

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
        proxy_set_header Connection "upgrade";
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


def generate_systemd_unit() -> str:
    unit = """[Unit]
Description=StarionBot API service
After=network.target

[Service]
Type=simple
WorkingDirectory={workdir}
EnvironmentFile={env_file}
ExecStart={venv_python} -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
    workdir = str(Path.cwd())
    env_file = str(Path.cwd() / ".env")
    venv_python = str(Path.cwd() / ".venv/bin/python")
    rendered = unit.format(workdir=workdir, env_file=env_file, venv_python=venv_python)
    Path("/tmp/starionbot.service").write_text(rendered)
    run("sudo mv /tmp/starionbot.service /etc/systemd/system/starionbot.service")
    run("sudo systemctl daemon-reload")
    run("sudo systemctl enable starionbot.service")
    return rendered


def backup_environment_artifacts(output_dir: str) -> list[str]:
    target = Path(output_dir).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    env_file = Path(".env")
    if env_file.exists():
        destination = target / ".env.backup"
        destination.write_text(env_file.read_text())
        created.append(str(destination))

    nginx_file = Path("/etc/nginx/sites-available/starionbot")
    if nginx_file.exists():
        destination = target / "starionbot.nginx.conf"
        destination.write_text(nginx_file.read_text())
        created.append(str(destination))

    unit_file = Path("/etc/systemd/system/starionbot.service")
    if unit_file.exists():
        destination = target / "starionbot.service"
        destination.write_text(unit_file.read_text())
        created.append(str(destination))

    return created


def restore_environment_artifacts(backup_dir: str) -> list[str]:
    source = Path(backup_dir).expanduser().resolve()
    if not source.exists():
        raise ValueError(f"Backup directory not found: {source}")

    restored: list[str] = []
    env_backup = source / ".env.backup"
    if env_backup.exists():
        Path(".env").write_text(env_backup.read_text())
        restored.append(".env")

    nginx_backup = source / "starionbot.nginx.conf"
    if nginx_backup.exists():
        run(f"sudo cp {shlex.quote(str(nginx_backup))} /etc/nginx/sites-available/starionbot")
        run("sudo nginx -t")
        run("sudo systemctl reload nginx")
        restored.append("/etc/nginx/sites-available/starionbot")

    unit_backup = source / "starionbot.service"
    if unit_backup.exists():
        run(f"sudo cp {shlex.quote(str(unit_backup))} /etc/systemd/system/starionbot.service")
        run("sudo systemctl daemon-reload")
        restored.append("/etc/systemd/system/starionbot.service")

    return restored


def _telegram_call(token: str, method: str, payload: dict[str, str]) -> dict[str, object]:
    base_url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(base_url, data=data)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw: Any = json.loads(response.read().decode("utf-8"))
            return cast(dict[str, object], raw)
    except urllib.error.URLError as exc:  # pragma: no cover - external network
        raise RuntimeError(f"Telegram API call failed for {method}: {exc}") from exc


def configure_telegram_webhook() -> None:
    env = load_env_map()
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    secret = env.get("WEBHOOK_SECRET", "")
    url = env.get("WEBHOOK_URL", "")
    if not token or not url:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or WEBHOOK_URL in .env")

    payload = {"url": url}
    if secret:
        payload["secret_token"] = secret
    set_result = _telegram_call(token, "setWebhook", payload)
    if not bool(set_result.get("ok")):
        raise RuntimeError("setWebhook did not return ok=true")

    info_result = _telegram_call(token, "getWebhookInfo", {})
    if not bool(info_result.get("ok")):
        raise RuntimeError("getWebhookInfo did not return ok=true")

    result_data = info_result.get("result")
    if not isinstance(result_data, dict):
        raise RuntimeError("getWebhookInfo returned unexpected payload")
    current = str(result_data.get("url", ""))
    if current != url:
        raise RuntimeError("Webhook URL mismatch after setWebhook")


def _ssl_expiry_days(domain: str) -> int | None:
    if not domain:
        return None
    try:
        cert = ssl.get_server_certificate((domain, 443))
        parsed = ssl.PEM_cert_to_DER_cert(cert)
        _ = parsed
    except OSError:
        return None
    ok, out = run(
        f"echo | openssl s_client -servername {shlex.quote(domain)} -connect "
        f"{shlex.quote(domain)}:443 2>/dev/null | openssl x509 -noout -enddate"
    )
    if not ok or "=" not in out:
        return None
    date_text = out.split("=", 1)[1].strip()
    expiry = datetime.strptime(date_text, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=UTC)
    remaining = expiry - datetime.now(UTC)
    return max(0, remaining.days)


def validate_https_infra() -> list[ValidationItem]:
    env = load_env_map()
    app_domain = env.get("APP_DOMAIN", "")
    api_domain = env.get("API_DOMAIN", "")
    webhook_url = env.get("WEBHOOK_URL", "")
    checks: list[ValidationItem] = []

    checks.append(
        ValidationItem("DNS app", bool(resolve_domain(app_domain)), app_domain or "not set")
    )
    checks.append(
        ValidationItem("DNS api", bool(resolve_domain(api_domain)), api_domain or "not set")
    )

    for port in (80, 443):
        ok, out = run(f"sudo ss -ltn '( sport = :{port} )' | tail -n +2")
        checks.append(
            ValidationItem(f"Port {port} open", bool(ok and out.strip()), "listener check")
        )

    ok, out = run("sudo systemctl is-active nginx")
    checks.append(ValidationItem("nginx status", ok and "active" in out, out or "unknown"))

    expiry_days = _ssl_expiry_days(app_domain)
    checks.append(
        ValidationItem(
            "SSL expiry",
            expiry_days is not None and expiry_days > 7,
            "unknown" if expiry_days is None else f"{expiry_days} days remaining",
        )
    )

    if app_domain:
        redirect_cmd = f"curl -k -I -s http://{app_domain} | head -n 1 | grep -q '301\\|308'"
        ok, _ = run(redirect_cmd)
    else:
        ok, _ = False, ""
    checks.append(ValidationItem("HTTP->HTTPS", ok, "redirect check"))

    ok, _ = run(f"curl -fsS https://{app_domain}/ >/dev/null") if app_domain else (False, "")
    checks.append(ValidationItem("Mini app reachability", ok, env.get("MINIAPP_URL", "not set")))

    ok, _ = run(f"curl -fsS {shlex.quote(webhook_url)} >/dev/null") if webhook_url else (False, "")
    checks.append(ValidationItem("Webhook reachability", ok, webhook_url or "not set"))

    ok, _ = run("curl -fsS http://127.0.0.1:8000/health >/dev/null")
    checks.append(ValidationItem("Backend availability", ok, "http://127.0.0.1:8000/health"))
    return checks
