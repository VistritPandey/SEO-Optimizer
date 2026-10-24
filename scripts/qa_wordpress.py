"""Opt-in QA against real disposable WordPress and WooCommerce Docker installations.

Requires Docker and network access to official images and the WordPress plugin registry.
Creates no external account. Secrets, certificates and runtime files stay under .data.
The private CA is trusted only by this process; TLS verification remains enabled.
"""

import json
import os
import secrets
import ssl
import subprocess
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from seo_optimizer.audit import PageParser
from seo_optimizer.connectors.models import Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.connectors.verification import verify_live
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import create_app
from seo_optimizer.worker import Worker

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".data/live-connectors/wordpress"
PLUGIN = """<?php
/** Isolated QA fixture. Not a production SEO plugin. */
add_action('init', function() {
    foreach (['yo_seo_title', 'yo_seo_description'] as $field) {
        register_post_meta('page', $field, [
            'type' => 'string', 'single' => true, 'show_in_rest' => true,
            'auth_callback' => function() { return current_user_can('edit_pages'); }
        ]);
    }
});
add_action('after_setup_theme', function() {
    remove_action('wp_head', '_wp_render_title_tag', 1);
}, 999);
add_action('wp_head', function() {
    remove_action('wp_head', '_wp_render_title_tag', 1);
    remove_action('wp_head', '_block_template_render_title_tag', 1);
}, 0);
add_action('wp_head', function() {
    if (!is_page()) return;
    $id = get_queried_object_id();
    $title = get_post_meta($id, 'yo_seo_title', true);
    if (!$title && get_post_meta($id, 'yo_title_fallback', true)) {
        $title = wp_get_document_title();
    }
    if ($title) echo '<title>' . esc_html($title) . '</title>' . "\\n";
    $description = get_post_meta($id, 'yo_seo_description', true);
    if ($description) echo '<meta name="description" content="' . esc_attr($description) . '">';
}, 1);
"""


def private_file(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    path.chmod(0o600)


def certificates() -> ssl.SSLContext:
    import ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Your Optimiser local QA")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    private_file(
        RUNTIME / "tls.key",
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
    )
    private_file(RUNTIME / "tls.pem", certificate.public_bytes(serialization.Encoding.PEM).decode())
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(RUNTIME / "tls.pem", RUNTIME / "tls.key")
    return context


def main() -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    RUNTIME.chmod(0o700)
    project = "optimiser-qa-" + secrets.token_hex(4)
    password, app_secret = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    private_file(RUNTIME / ".env", "QA_DB_PASSWORD=" + secrets.token_urlsafe(24) + "\n")
    plugin = RUNTIME / "qa-fields.php"
    private_file(plugin, PLUGIN)
    plugin.chmod(0o644)
    config = {
        "services": {
            "db": {
                "image": "mariadb:11.8",
                "environment": {
                    "MARIADB_DATABASE": "wordpress",
                    "MARIADB_USER": "wordpress",
                    "MARIADB_PASSWORD": "${QA_DB_PASSWORD}",
                    "MARIADB_RANDOM_ROOT_PASSWORD": "1",
                },
                "healthcheck": {
                    "test": ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"],
                    "interval": "2s",
                    "timeout": "5s",
                    "retries": 30,
                },
            },
            "wordpress": {
                "image": "wordpress:php8.3-apache",
                "ports": ["127.0.0.1::80"],
                "environment": {
                    "WORDPRESS_DB_HOST": "db",
                    "WORDPRESS_DB_USER": "wordpress",
                    "WORDPRESS_DB_PASSWORD": "${QA_DB_PASSWORD}",
                    "WORDPRESS_DB_NAME": "wordpress",
                    "WORDPRESS_CONFIG_EXTRA": "define('WP_ENVIRONMENT_TYPE', 'local');",
                },
                "volumes": [
                    "site:/var/www/html",
                    str(plugin) + ":/var/www/html/wp-content/mu-plugins/qa-fields.php:ro",
                ],
                "depends_on": {"db": {"condition": "service_healthy"}},
            },
            "cli": {
                "image": "wordpress:cli",
                "user": "33:33",
                "environment": {},
                "volumes": ["site:/var/www/html"],
                "profiles": ["tools"],
            },
        },
        "volumes": {"site": {}},
    }
    config["services"]["cli"]["environment"] = config["services"]["wordpress"]["environment"]
    private_file(RUNTIME / "compose.yaml", yaml.safe_dump(config))
    command = [
        "docker",
        "compose",
        "--project-name",
        project,
        "--env-file",
        str(RUNTIME / ".env"),
        "-f",
        str(RUNTIME / "compose.yaml"),
    ]

    def compose(*args: str, stdin: str | None = None) -> str:
        result = subprocess.run(
            [*command, *args], input=stdin, capture_output=True, text=True, timeout=600
        )
        if result.returncode:
            private_file(RUNTIME / "last-error.log", result.stderr)
            raise RuntimeError("Container command failed; inspect the private runtime log")
        return result.stdout.strip()

    def wp(*args: str, stdin: str | None = None) -> str:
        return compose("run", "--rm", "--no-deps", "cli", "wp", *args, stdin=stdin)

    report = {
        "verified_at": datetime.now(UTC).isoformat(),
        "scope": "Real local WordPress/WooCommerce, not a hosted account or plugin certification",
        "passed": [],
        "failed": [],
        "dependencies": [],
        "versions": {},
    }
    server = None
    old_ca = os.environ.get("SSL_CERT_FILE")
    try:
        print("Starting isolated WordPress and database", flush=True)
        compose("up", "-d", "--wait", "wordpress")
        endpoint = "http://" + compose("port", "wordpress", "80")

        class Proxy(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def forward(self):
                headers = dict(self.headers)
                headers["X-Forwarded-Proto"] = "https"
                size = int(self.headers.get("Content-Length", "0"))
                response = httpx.request(
                    self.command,
                    endpoint + self.path,
                    headers=headers,
                    content=self.rfile.read(size) if size else None,
                    follow_redirects=False,
                    timeout=90,
                )
                self.send_response(response.status_code)
                for key, value in response.headers.items():
                    if key.lower() not in {
                        "transfer-encoding",
                        "connection",
                        "content-length",
                        "content-encoding",
                    }:
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(response.content)))
                self.end_headers()
                self.wfile.write(response.content)

            do_GET = forward
            do_POST = forward
            do_PUT = forward
            do_DELETE = forward

        server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        server.socket = certificates().wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"https://127.0.0.1:{server.server_port}"
        os.environ["SSL_CERT_FILE"] = str(RUNTIME / "tls.pem")
        print("Installing the real CMS and sample content", flush=True)
        wp(
            "core",
            "install",
            "--url=" + base,
            "--title=Your Optimiser QA",
            "--admin_user=qa-operator",
            "--admin_email=operator@example.test",
            "--skip-email",
            "--prompt=admin_password",
            stdin=password + "\n",
        )
        wp("rewrite", "structure", "/%postname%/", "--hard")
        compose(
            "exec",
            "-T",
            "wordpress",
            "sh",
            "-c",
            "cat > /var/www/html/.htaccess",
            stdin=(
                "<IfModule mod_rewrite.c>\nRewriteEngine On\n"
                "RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]\n"
                "RewriteBase /\nRewriteRule ^index\\.php$ - [L]\n"
                "RewriteCond %{REQUEST_FILENAME} !-f\n"
                "RewriteCond %{REQUEST_FILENAME} !-d\n"
                "RewriteRule . /index.php [L]\n</IfModule>\n"
            ),
        )
        wp(
            "user",
            "create",
            "qa-editor",
            "editor@example.test",
            "--role=editor",
            "--prompt=user_pass",
            stdin=app_secret + "\n",
        )
        app_password = wp(
            "user", "application-password", "create", "qa-editor", "Connector QA", "--porcelain"
        )
        defect = wp(
            "post",
            "create",
            "--post_type=page",
            "--post_title=Desk lamps",
            "--post_name=desk-lamps",
            "--post_status=publish",
            "--post_content=Handmade desk lamps.",
            "--porcelain",
        )
        healthy = wp(
            "post",
            "create",
            "--post_type=page",
            "--post_title=Cedar workshop",
            "--post_name=healthy-page",
            "--post_status=publish",
            "--post_content=Workshop lighting guide.",
            "--porcelain",
        )
        for identity in [defect, healthy]:
            wp("post", "meta", "update", identity, "yo_seo_description", "Handmade desk lamps.")
        wp("post", "meta", "update", healthy, "yo_title_fallback", "1")
        report["versions"]["wordpress"] = wp("core", "version")
        private_file(
            RUNTIME / ".env.qa",
            f"QA_WORDPRESS_URL={base}\nQA_WORDPRESS_USERNAME=qa-editor\n"
            f"QA_WORDPRESS_APPLICATION_PASSWORD={app_password}\n",
        )
        with tempfile.TemporaryDirectory(prefix="optimizer-real-wp-") as folder:
            settings = Settings(
                data_dir=Path(folder),
                database_url="sqlite:///" + folder + "/control.db",
                secret_key=secrets.token_urlsafe(32),
                allow_private_network=True,
            )
            store = Store(settings)
            owner, token = store.create_user("owner@example.test", "qa-local-hash")
            with TestClient(create_app(settings, store)) as api, httpx.Client() as live:
                headers = {"Authorization": "Bearer " + token}
                project_data = api.post(
                    "/api/v1/projects",
                    headers=headers,
                    json={
                        "spec": {
                            "name": "Real CMS QA",
                            "website_url": base,
                            "publishing_platform": "wordpress",
                            "auto_fix": True,
                        }
                    },
                )
                assert project_data.status_code == 201
                pid = project_data.json()["id"]
                path = f"/api/v1/projects/{pid}/connectors/wordpress"
                saved = api.put(
                    path,
                    headers=headers,
                    json={
                        "platform": "wordpress",
                        "resource": base,
                        "options": {
                            "seo_title_field": "yo_seo_title",
                            "seo_description_field": "yo_seo_description",
                        },
                        "credentials": {
                            "username": "qa-editor",
                            "application_password": app_password,
                        },
                        "allow_writes": True,
                    },
                )
                assert saved.status_code == 200 and app_password not in saved.text
                worker = Worker(store, settings)
                # Initial read-only site audit may need unrelated sitemap/content work.
                assert worker.tick(owner.id)

                def queue(suffix, body=None):
                    response = api.post(path + suffix, headers=headers, json=body)
                    assert response.status_code == 202, response.status_code
                    job_id = response.json()["id"]
                    for _ in range(12):
                        job = store.job(owner.id, job_id)
                        if job.status not in {"queued", "running"}:
                            break
                        assert worker.tick(owner.id)
                    job = store.job(owner.id, job_id)
                    assert job.status == "complete", job.result.get("summary", job.status)
                    return job.result

                before = live.get(base + "/desk-lamps/")
                private_file(RUNTIME / "before.html", before.text)
                print("Fixture page HTTP status: " + str(before.status_code), flush=True)
                assert before.status_code == 200 and "<title>" not in before.text
                result = queue("/collect", {"resource_id": defect})
                assert len(result["proposals"]) == 1
                proposal = result["proposals"][0]
                result = queue(f"/proposals/{proposal['id']}/apply")
                assert result["proposal"]["verification"]["provider_readback"]
                result = queue(f"/proposals/{proposal['id']}/verify")
                assert result["proposal"]["status"] == "deployed_verified"
                after = live.get(base + "/desk-lamps/")
                assert "<title>Desk lamps</title>" in after.text
                report["passed"].append(
                    "Real REST authentication, durable worker collection, missing-title proposal, "
                    "field write, provider readback and live HTTPS verification"
                )
                queue(f"/proposals/{proposal['id']}/rollback")
                assert "<title>" not in live.get(base + "/desk-lamps/").text
                report["passed"].append(
                    "Restoration remains available after deployed verification "
                    "and restores the actual HTML"
                )
                healthy_html = live.get(base + "/healthy-page/").text
                parser = PageParser()
                parser.feed(healthy_html)
                assert "".join(parser.title).strip()
                result = queue("/collect", {"resource_id": healthy})
                if result["proposals"]:
                    report["failed"].append(
                        {
                            "id": "cms-fallback-title",
                            "severity": "high",
                            "expected": "No repair for an empty override when the live theme "
                            "provides a valid title",
                            "observed": "Agent proposed a title override despite an "
                            "existing live title",
                            "writes_performed": 0,
                        }
                    )
                else:
                    report["passed"].append(
                        "Healthy theme title fallback produces no unnecessary proposal"
                    )

                print("Installing WooCommerce from the official plugin registry", flush=True)
                wp("plugin", "install", "woocommerce", "--activate")
                report["versions"]["woocommerce"] = wp(
                    "plugin", "get", "woocommerce", "--field=version"
                )
                seed = """
$p = new WC_Product_Simple();
$p->set_name('Desk lamp'); $p->set_description('Handmade desk lamp.');
$p->set_status('publish'); $p->set_regular_price('29');
$p->set_manage_stock(true); $p->set_stock_quantity(3); $id = $p->save();
$ck = 'ck_' . bin2hex(random_bytes(20)); $cs = 'cs_' . bin2hex(random_bytes(20));
global $wpdb;
$wpdb->insert($wpdb->prefix . 'woocommerce_api_keys', [
    'user_id'=>1, 'description'=>'Local connector QA', 'permissions'=>'read_write',
    'consumer_key'=>wc_api_hash($ck), 'consumer_secret'=>$cs, 'truncated_key'=>substr($ck,-7)
]);
echo json_encode(['product_id'=>$id, 'consumer_key'=>$ck, 'consumer_secret'=>$cs]);
"""
                woo = json.loads(wp("eval", seed))
                private_file(
                    RUNTIME / ".env.qa",
                    (RUNTIME / ".env.qa").read_text()
                    + f"QA_WOOCOMMERCE_CONSUMER_KEY={woo['consumer_key']}\n"
                    + f"QA_WOOCOMMERCE_CONSUMER_SECRET={woo['consumer_secret']}\n",
                )
                path = f"/api/v1/projects/{pid}/connectors/woocommerce"
                saved = api.put(
                    path,
                    headers=headers,
                    json={
                        "platform": "woocommerce",
                        "resource": base,
                        "credentials": {
                            "consumer_key": woo["consumer_key"],
                            "consumer_secret": woo["consumer_secret"],
                        },
                        "allow_writes": True,
                    },
                )
                assert saved.status_code == 200
                product_id = str(woo["product_id"])
                result = queue("/collect", {"resource_id": product_id})
                record = result["collection"]["records"][0]
                proposal_response = api.post(
                    path + "/proposals",
                    headers=headers,
                    json={
                        "resource_id": product_id,
                        "changes": {"short_description": record["fields"]["content"]},
                        "reason": "Reuse the observed description for the empty product summary.",
                        "evidence_ids": [result["evidence_id"]],
                    },
                )
                assert proposal_response.status_code == 201, proposal_response.status_code
                proposal = proposal_response.json()
                queue(f"/proposals/{proposal['id']}/apply")
                native = live.get(
                    base + "/wp-json/wc/v3/products/" + product_id,
                    auth=(woo["consumer_key"], woo["consumer_secret"]),
                ).json()
                assert native["regular_price"] == "29" and native["stock_quantity"] == 3
                assert "Handmade desk lamp." in native["short_description"]
                report["passed"].append(
                    "Real WooCommerce authentication and product-summary write "
                    "preserve price and inventory"
                )
                service = ConnectorService(store, store.project(owner.id, pid))
                try:
                    verify_live(service, Platform.WOOCOMMERCE, proposal["id"])
                except ValueError:
                    report["dependencies"].append(
                        "WooCommerce summary edits have provider readback, but the agent "
                        "has no product-summary live verification criterion"
                    )
                queue(f"/proposals/{proposal['id']}/rollback")
                native = live.get(
                    base + "/wp-json/wc/v3/products/" + product_id,
                    auth=(woo["consumer_key"], woo["consumer_secret"]),
                ).json()
                assert not native["short_description"] and native["stock_quantity"] == 3
                report["passed"].append(
                    "Real WooCommerce rollback restores the summary and preserves inventory"
                )
            store.close()
    except Exception as error:
        report["failed"].append(
            {
                "id": "runtime",
                "type": type(error).__name__,
                "message": "Runtime stage did not complete; inspect private runtime logs",
            }
        )
        raise
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if old_ca is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = old_ca
        compose("down", "--volumes", "--remove-orphans")
        report["runtime_credentials"] = (
            "Private .data environment file; ephemeral target removed after QA"
        )
        report["customer_site_modified"] = False
        private_file(RUNTIME / "report.json", json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2), flush=True)
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
