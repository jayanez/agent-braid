# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T026: static checks of the activity viewer web bundle (procedure_010, bundle part).

First-party files (`index.html`, `loom.js`, `style.css`) are scanned for remote origins, code
evaluation and HTML sinks; the real bundle is served by `ViewServer` to check the CSP and headers
of contracts/ui-security-privacy.md; vendored files are checked by manifest hash only.
"""
import base64
import hashlib
import http.client
import json
import re
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path

from agent_braid.view_serve import ViewServer
from agent_braid.view_store import LoomStore

WEB = Path(__file__).resolve().parents[1] / "integrations/agent-braid-view/web"
VENDOR = WEB / "vendor"
FIRST_PARTY = ("index.html", "loom.js", "style.css")
SERVED_PATHS = ("/", *(f"/web/{name}" for name in FIRST_PARTY))
LEGEND_LITERAL = "not a guarantee"
CONTRACT_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
}

REMOTE_URL = re.compile(r"(?i)\b(?:https?|wss?|ftp):\s*//|(?<![:\w])//[\w.-]+\.[a-z]{2,}")
CODE_EVALUATION = (
    ("eval(", re.compile(r"\beval\s*\(")),
    ("new Function", re.compile(r"\bnew\s+Function\b")),
    ("Function(", re.compile(r"\bFunction\s*\(")),
    ("string timer", re.compile(r"""\b(?:setTimeout|setInterval)\s*\(\s*["'`]""")),
    (".constructor(", re.compile(r"\.\s*constructor\s*\(")),
    ("trustedTypes", re.compile(r"\btrustedTypes\b")),
)
# Network channels other than fetch/EventSource to the page origin (connect-src 'self' is the CSP side of this).
NETWORK_CHANNELS = (
    ("WebSocket", re.compile(r"\bWebSocket\b")),
    ("sendBeacon", re.compile(r"\bsendBeacon\b")),
    ("XMLHttpRequest", re.compile(r"\bXMLHttpRequest\b")),
)
# A `setAttribute` key must be a literal outside these, or the dynamic call must sit behind the ATTRS allowlist.
UNSAFE_ATTRIBUTE = re.compile(r"(?i)^(?:on.*|href|src|srcdoc|srcset|style|action|formaction|xlink:href|data|poster|ping)$")
SET_ATTRIBUTE = re.compile(r"""\bsetAttribute\s*\(\s*(?:(["'])([^"']*)\1|([^,)]*))""")
HTML_SINKS = (
    ("innerHTML", re.compile(r"\binnerHTML\b")),
    ("outerHTML", re.compile(r"\bouterHTML\b")),
    ("insertAdjacentHTML", re.compile(r"\binsertAdjacentHTML\b")),
    ("document.write", re.compile(r"\bdocument\s*\.\s*write(?:ln)?\s*\(")),
    ("srcdoc", re.compile(r"\bsrcdoc\b")),
    ("DOMParser", re.compile(r"\bDOMParser\b")),
    ("createContextualFragment", re.compile(r"\bcreateContextualFragment\b")),
    ("createElement script", re.compile(r"""\bcreateElement\s*\(\s*["'`]\s*script""", re.IGNORECASE)),
)
# Loads a first-party file may start: import/export from, dynamic import, fetch, Worker, EventSource, XHR.
JS_REFERENCE = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\bfetch\s*\(\s*|\bnew\s+(?:Worker|SharedWorker|EventSource|URL)\s*\(\s*|
        \.open\s*\(\s*["'][A-Z]+["']\s*,\s*|\bimportScripts\s*\(\s*)(["'`])([^"'`]*)\1""", re.VERBOSE)
CSS_REFERENCE = re.compile(r"""(?:url\(\s*(["']?)([^)"']*)\1\s*\)|@import\s+(["'])([^"']*)\3)""", re.IGNORECASE)
REFERENCE_ATTRIBUTES = ("src", "href", "xlink:href", "action", "formaction", "poster", "data", "srcset", "ping", "content")


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def is_local_reference(value: str, allow_data: bool = False) -> bool:
    """A reference stays in the page origin: a single-slash path, a fragment or a relative name.

    `data:` is local only where the CSP allows it (`img-src`), so callers opt in with `allow_data`.
    """
    value = value.strip()
    if not value or value.startswith("#"):
        return True
    if value.lower().startswith("data:"):
        return allow_data
    if value.startswith("//") or re.match(r"(?i)^[a-z][a-z0-9+.-]*:", value):
        return False
    return True


class PageScan(HTMLParser):
    """Collects what a CSP-hardened page may not contain, and the references it makes."""

    def __init__(self, html: str) -> None:
        super().__init__(convert_charrefs=False)
        self.inline_scripts: list[tuple[str, str]] = []  # (type, text)
        self.references: list[tuple[str, str, str]] = []  # (tag, attribute, value)
        self.event_handlers: list[tuple[str, str]] = []
        self.inline_styles: list[str] = []
        self.meta_csp: list[str] = []
        self.meta_refresh: list[str] = []
        self._script: list[str] | None = None
        self._script_type = ""
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        attributes = {name: value or "" for name, value in attrs}
        for name, value in attributes.items():
            if name.startswith("on"):
                self.event_handlers.append((tag, name))
            if name in REFERENCE_ATTRIBUTES and not (tag == "meta" and name == "content"):
                parts = [item.split()[0] for item in value.split(",") if item.split()] if name == "srcset" else [value]
                kind = "link[icon]" if tag == "link" and "icon" in attributes.get("rel", "").lower().split() else tag
                self.references.extend((kind, name, part) for part in parts)
            if name == "style":
                self.inline_styles.append(f"<{tag} style>")
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "content-security-policy":
            self.meta_csp.append(attributes.get("content", ""))
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "refresh":
            target = re.search(r"(?i)\burl\s*=\s*['\"]?([^'\";]*)", attributes.get("content", ""))
            self.meta_refresh.append(target.group(1) if target else "")
        if tag == "script" and "src" not in attributes:
            self._script, self._script_type = [], attributes.get("type", "").lower()
        if tag == "style":
            self.inline_styles.append("<style>")

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            self.inline_scripts.append((self._script_type, "".join(self._script)))
            self._script = None

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)


def import_map_hash(html: str) -> str | None:
    """The CSP `sha256-` value of the single inline import map, or None when the page has none."""
    maps = [text for kind, text in PageScan(html).inline_scripts if kind == "importmap"]
    if len(maps) > 1:
        raise AssertionError("more than one import map")
    if not maps:
        return None
    return base64.b64encode(hashlib.sha256(maps[0].encode("utf-8")).digest()).decode("ascii")


def import_map_targets(html: str) -> list[str]:
    targets: list[str] = []
    for kind, text in PageScan(html).inline_scripts:
        if kind != "importmap":
            continue
        document = json.loads(text)
        for section in (document.get("imports", {}), *document.get("scopes", {}).values()):
            targets.extend(section.values())
    return targets


def violations_in_script(text: str) -> list[str]:
    found = [name for name, pattern in CODE_EVALUATION + HTML_SINKS + NETWORK_CHANNELS if pattern.search(text)]
    found += [f"setAttribute {match.group(2) or match.group(3).strip()!r}" for match in SET_ATTRIBUTE.finditer(text)
              if (match.group(2) is not None and UNSAFE_ATTRIBUTE.match(match.group(2)))]
    found += [f"remote reference {match.group(2)!r}" for match in JS_REFERENCE.finditer(text)
              if not is_local_reference(match.group(2))]
    return found


def violations_in_style(text: str) -> list[str]:
    found = []
    for match in CSS_REFERENCE.finditer(text):
        target = match.group(2) if match.group(2) is not None else match.group(4)
        if not is_local_reference(target, allow_data=target.strip().lower().startswith("data:image/")):
            found.append(f"remote reference {target!r}")
    return found


def violations_in_page(html: str) -> list[str]:
    scan = PageScan(html)
    found = [f"remote reference {tag} {name}={value!r}" for tag, name, value in scan.references
             if not is_local_reference(value, allow_data=tag in ("img", "link[icon]"))]
    found += [f"meta refresh {target!r}" for target in scan.meta_refresh
              if not is_local_reference(target)]
    found += [f"inline event handler {tag} {name}" for tag, name in scan.event_handlers]
    found += [f"inline style {item}" for item in scan.inline_styles]
    found += [f"inline script of type {kind or 'classic'}" for kind, _ in scan.inline_scripts if kind != "importmap"]
    if len([1 for kind, _ in scan.inline_scripts if kind == "importmap"]) > 1:
        found.append("more than one import map")
    found += [f"import map target {target!r}" for target in import_map_targets(html) if not is_local_reference(target)]
    return found


def manifest() -> dict:
    return json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))


class ScannerTests(unittest.TestCase):
    """The scanners fail on the defects they exist for (a check that cannot fail checks nothing)."""

    def test_remote_urls_are_found(self):
        for text in ("https://cdn.example/x.js", "fetch('//cdn.example.com/x')", "wss://h/x", "HTTP://H/X"):
            with self.subTest(text=text):
                self.assertRegex(text, REMOTE_URL)
        for text in ("/web/loom.js", "a // comment", "data:,"):
            with self.subTest(text=text):
                self.assertNotRegex(text, REMOTE_URL)

    def test_script_violations_are_found(self):
        cases = {
            "eval(x)": "eval(", "const f = new Function('return 1')": "new Function",
            "Function('a')": "Function(", "el.innerHTML = x": "innerHTML",
            "el.outerHTML = x": "outerHTML", "el.insertAdjacentHTML('beforeend', x)": "insertAdjacentHTML",
            "document.write(x)": "document.write", "f.srcdoc = x": "srcdoc",
            "new DOMParser()": "DOMParser", "range.createContextualFragment(x)": "createContextualFragment",
            "import * as T from 'https://cdn.example/three.js'": "remote reference",
            "await import('//cdn.example/x.js')": "remote reference",
            "fetch('https://example.com/a')": "remote reference",
            "new EventSource('http://example.com/e')": "remote reference",
            "setTimeout('go()', 5)": "string timer", "setInterval(`go()`, 5)": "string timer",
            "x.constructor('return 1')()": ".constructor(", "document.createElement('script')": "createElement script",
            "trustedTypes.createPolicy('p', {})": "trustedTypes", "new WebSocket('/x')": "WebSocket",
            "navigator.sendBeacon('/x')": "sendBeacon", "new XMLHttpRequest()": "XMLHttpRequest",
            "el.setAttribute('onclick', x)": "setAttribute", "el.setAttribute('href', x)": "setAttribute",
            "el.setAttribute(\"srcdoc\", x)": "setAttribute", "el.setAttribute('src', x)": "setAttribute",
            "import x from 'data:text/javascript,1'": "remote reference",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertTrue(any(expected in item for item in violations_in_script(text)), text)

    def test_clean_script_passes(self):
        text = ("import * as THREE from 'three';\nconst r = await fetch('/snapshot');\nel.textContent = 'x';\n"
                "el.setAttribute('aria-pressed', 'true'); el.setAttribute(key, value); setTimeout(tick, 5);")
        self.assertEqual(violations_in_script(text), [])

    def test_style_violations_are_found(self):
        self.assertTrue(violations_in_style("a { background: url(https://x.example/a.png) }"))
        self.assertTrue(violations_in_style("@import 'https://x.example/a.css';"))
        self.assertTrue(violations_in_style("a { background: url('//x.example/a.png') }"))
        self.assertEqual(violations_in_style("a { background: url(data:image/svg+xml;utf8,x) }"), [])
        self.assertTrue(violations_in_style("a { background: url(data:text/css,x) }"))

    def test_page_violations_are_found(self):
        cases = {
            '<script src="https://cdn.example/x.js"></script>': "remote reference",
            '<link rel="stylesheet" href="//cdn.example/x.css">': "remote reference",
            "<script>alert(1)</script>": "inline script",
            '<script type="module">import "/web/a.js"</script>': "inline script",
            '<button onclick="x()">b</button>': "inline event handler",
            '<p style="color:red">x</p>': "inline style",
            "<style>p{color:red}</style>": "inline style",
            '<script type="importmap">{"imports":{"three":"https://cdn.example/three.js"}}</script>':
                "import map target",
            '<script type="importmap">{}</script><script type="importmap">{}</script>': "more than one import map",
            '<script src="data:text/javascript,1"></script>': "remote reference",
            '<link rel="stylesheet" href="data:text/css,p{}">': "remote reference",
            '<iframe src="data:text/html,x"></iframe>': "remote reference",
            '<img srcset="/a.png 1x, https://x.example/b.png 2x">': "remote reference",
            '<meta http-equiv="refresh" content="0; url=https://x.example/">': "meta refresh",
            '<svg><use xlink:href="https://x.example/s.svg#a"></use></svg>': "remote reference",
        }
        for html, expected in cases.items():
            with self.subTest(html=html):
                self.assertTrue(any(expected in item for item in violations_in_page(html)), html)

    def test_page_allows_data_only_for_images(self):
        self.assertEqual(violations_in_page('<img src="data:image/png;base64,AAAA"><link rel="icon" href="data:,">'), [])

    def test_page_with_only_a_local_import_map_passes(self):
        html = ('<script type="importmap">{"imports":{"three":"/web/vendor/three/three.module.js"}}</script>'
                '<script type="module" src="/web/loom.js"></script><link rel="stylesheet" href="/web/style.css">')
        self.assertEqual(violations_in_page(html), [])

    def test_import_map_hash_is_the_sha256_of_the_exact_text(self):
        text = '{"imports":{"three":"/web/vendor/three/three.module.js"}}'
        expected = base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
        self.assertEqual(import_map_hash(f'<script type="importmap">{text}</script>'), expected)
        self.assertNotEqual(import_map_hash(f'<script type="importmap"> {text}</script>'), expected)
        self.assertIsNone(import_map_hash("<script type=module src=/web/loom.js></script>"))


class FirstPartyBundleTests(unittest.TestCase):
    def test_the_bundle_is_exactly_the_first_party_files_plus_vendor(self):
        names = {path.name for path in WEB.iterdir() if not path.name.startswith(".")}
        self.assertEqual(names - {"vendor"}, set(FIRST_PARTY))
        for name in FIRST_PARTY:
            with self.subTest(name=name):
                self.assertTrue((WEB / name).is_file())

    def test_no_remote_url_in_any_first_party_file(self):
        for name in FIRST_PARTY:
            with self.subTest(name=name):
                self.assertEqual(REMOTE_URL.findall(read(name)), [])

    def test_the_script_has_no_evaluation_or_html_sink(self):
        self.assertEqual(violations_in_script(read("loom.js")), [])

    def test_the_stylesheet_loads_nothing_remote(self):
        self.assertEqual(violations_in_style(read("style.css")), [])

    def test_the_page_has_no_remote_reference_inline_code_handler_or_style(self):
        self.assertEqual(violations_in_page(read("index.html")), [])

    def test_set_attribute_is_limited_to_safe_keys_and_the_allowlisted_helper(self):
        text = read("loom.js")
        allowlist = re.search(r"const ATTRS = /(.*)/;", text)
        self.assertTrue(allowlist, "the attribute allowlist moved or was removed")
        pattern = re.compile(allowlist.group(1))
        for key in ("onclick", "onload", "href", "src", "srcdoc", "srcset", "style", "action", "formaction"):
            with self.subTest(key=key):
                self.assertIsNone(pattern.match(key))
        dynamic = [m.group(0) for m in SET_ATTRIBUTE.finditer(text) if m.group(3) is not None]
        self.assertEqual(len(dynamic), 1, dynamic)
        self.assertRegex(text, r"ATTRS\.test\(key\)\)\s*node\.setAttribute\(key,")

    def test_a_meta_policy_copy_omits_frame_ancestors(self):
        for policy in PageScan(read("index.html")).meta_csp:
            with self.subTest(policy=policy):
                self.assertNotIn("frame-ancestors", policy)
                self.assertNotRegex(policy, r"(?i)https?:|unsafe-")

    def test_the_legend_states_a_class_is_not_a_guarantee(self):
        html = read("index.html")
        legend = html[html.index('aria-labelledby="legend-title"'):]
        self.assertIn(LEGEND_LITERAL, legend[:legend.index("</section>")])
        self.assertIn(LEGEND_LITERAL, read("loom.js"))  # the legend rendered from script keeps the literal

    def test_the_page_states_the_non_claim_and_read_only_markers(self):
        html = read("index.html")
        self.assertIn("not a safety ordering", html)
        self.assertIn("executionAuthorization: false", html)
        self.assertIn("read-only", html)

    def test_every_page_script_and_style_comes_from_the_bundle(self):
        files = {f"/web/{name}" for name in FIRST_PARTY}
        for tag, name, value in PageScan(read("index.html")).references:
            if tag in ("script", "link") and name in ("src", "href"):
                with self.subTest(tag=tag, value=value):
                    self.assertIn(value, files)

    def test_import_map_targets_are_vendored_files_listed_in_the_manifest(self):
        listed = {f"/web/vendor/{path}" for path in manifest()["files"]}
        for target in import_map_targets(read("index.html")):
            with self.subTest(target=target):
                self.assertIn(target, listed)

    def test_import_map_targets_are_served_by_the_view_server(self):
        # ViewServer serves a flat {name: bytes} bundle at /web/<name>; a nested vendor path would answer 404.
        # Wiring Three.js into the page therefore needs server support first (T024/T025), and fails here until then.
        for target in import_map_targets(read("index.html")):
            with self.subTest(target=target):
                self.assertRegex(target, r"^/web/[^/]+$", "the ViewServer cannot serve nested bundle paths")


class ServedBundleTests(unittest.TestCase):
    """The real first-party files, served by ViewServer with the hash of the page's import map."""

    def setUp(self):
        self.bundle = {name: (WEB / name).read_bytes() for name in FIRST_PARTY}
        self.map_hash = import_map_hash(read("index.html"))
        self.start(self.bundle, self.map_hash)

    def start(self, bundle, map_hash):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.server = ViewServer(LoomStore(), Path(tmp.name) / "run", bundle=bundle, import_map_sha256=map_hash)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join(5)))
        opened = self.fetch(f"/open?code={self.server.open_url.split('code=')[1]}")[1]
        self.cookie = opened.getheader("Set-Cookie").split(";")[0]

    def fetch(self, path, cookie=None, method="GET", host=None):
        headers = {"Host": host or f"127.0.0.1:{self.server.port}"}
        if cookie:
            headers["Cookie"] = cookie
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request(method, path, headers=headers)
            response = connection.getresponse()
            return response.status, response, response.read()
        finally:
            connection.close()

    def test_every_first_party_file_is_served_unchanged_to_a_session(self):
        for path in SERVED_PATHS:
            with self.subTest(path=path):
                status, _, body = self.fetch(path, self.cookie)
                name = "index.html" if path == "/" else path[5:]
                self.assertEqual((status, body), (200, self.bundle[name]))

    def assert_contract_policy(self, policy, map_hash):
        directives = {}
        for item in policy.split(";"):
            name, *sources = item.split()
            directives[name] = sources
        self.assertEqual(directives["script-src"], ["'self'"] + ([f"'sha256-{map_hash}'"] if map_hash else []))
        for name in ("default-src", "style-src", "connect-src"):
            self.assertEqual(directives[name], ["'self'"], name)
        self.assertEqual(directives["img-src"], ["'self'", "data:"])
        for name in ("object-src", "base-uri"):
            self.assertEqual(directives[name], ["'none'"], name)
        self.assertEqual(directives["require-trusted-types-for"], ["'script'"])
        for name, sources in directives.items():
            for source in sources:
                with self.subTest(directive=name, source=source):
                    self.assertNotRegex(source, r"(?i)^(?:[a-z]+:)?//|^(?:https?|wss?|blob):|^\*$|unsafe-")

    def test_the_contract_policy_names_no_remote_origin_and_only_the_import_map_hash(self):
        for path in SERVED_PATHS:
            with self.subTest(path=path):
                _, response, _ = self.fetch(path, self.cookie)
                self.assert_contract_policy(response.getheader("Content-Security-Policy"), self.map_hash)

    def test_a_page_import_map_adds_exactly_its_hash_to_script_src(self):
        text = '{"imports":{"three":"/web/three.js"}}'
        page = f'<script type="importmap">{text}</script><script type="module" src="/web/loom.js"></script>'
        map_hash = import_map_hash(page)
        self.start({"index.html": page.encode(), "three.js": b"export default 1;"}, map_hash)
        for path in ("/", "/web/three.js"):
            with self.subTest(path=path):
                _, response, _ = self.fetch(path, self.cookie)
                self.assert_contract_policy(response.getheader("Content-Security-Policy"), map_hash)
                self.assertIn(f"'sha256-{map_hash}'", response.getheader("Content-Security-Policy"))

    def test_the_contract_headers_are_set_on_the_bundle_and_on_refusals(self):
        refusals = (
            ("GET", "/", None, None, 404),  # no session
            ("GET", "/web/loom.js", None, None, 404),
            ("GET", "/web/nope.js", self.cookie, None, 404),  # not in the bundle
            ("GET", "/web/vendor/three/three.module.js", self.cookie, None, 404),
            ("GET", "/web/../index.html", self.cookie, None, 404),
            ("GET", "/web/manifest.json", self.cookie, None, 404),
            ("POST", "/", self.cookie, None, 405),
            ("GET", "/", self.cookie, "evil.example", 403),  # foreign Host
        )
        cases = [("GET", path, self.cookie, None, 200) for path in SERVED_PATHS] + list(refusals)
        for method, path, cookie, host, expected in cases:
            with self.subTest(method=method, path=path, host=host, cookie=bool(cookie)):
                status, response, _ = self.fetch(path, cookie, method, host)
                self.assertEqual(status, expected)
                self.assertTrue(response.getheader("Content-Security-Policy"))
                for name, value in CONTRACT_HEADERS.items():
                    self.assertEqual(response.getheader(name), value, name)

    def test_script_hashes_in_the_policy_match_every_inline_script_of_the_served_page(self):
        _, response, body = self.fetch("/", self.cookie)
        policy = response.getheader("Content-Security-Policy")
        hashes = re.findall(r"'sha256-([^']+)'", policy)
        scan = PageScan(body.decode("utf-8"))
        inline = [text for _, text in scan.inline_scripts]
        self.assertEqual(len(inline), len(hashes))
        for text in inline:
            digest = base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")
            self.assertIn(digest, hashes)


class VendoredFilesTests(unittest.TestCase):
    """Vendored content is checked by hash only (ADR 0033); nothing unlisted may sit beside it."""

    def test_the_manifest_lists_files_with_sha256_digests(self):
        files = manifest()["files"]
        self.assertTrue(files)
        for path, digest in files.items():
            with self.subTest(path=path):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")
                self.assertFalse(path.startswith("/") or ".." in Path(path).parts)

    def test_every_listed_file_matches_its_sha256(self):
        for path, digest in manifest()["files"].items():
            with self.subTest(path=path):
                file = VENDOR / path
                self.assertTrue(file.is_file(), path)
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), digest)

    def test_nothing_unlisted_exists_under_vendor(self):
        listed = set(manifest()["files"]) | {"manifest.json"}
        entries = [path for path in VENDOR.rglob("*") if not any(part.startswith(".") for part in path.parts[len(VENDOR.parts):])]
        for path in entries:
            self.assertFalse(path.is_symlink(), path)
        present = {path.relative_to(VENDOR).as_posix() for path in entries if not path.is_dir()}
        self.assertEqual(present - listed, set(), "unlisted vendored files")
        self.assertEqual(listed - present, set(), "listed files missing")

    def test_the_manifest_pins_package_version_and_integrity(self):
        document = manifest()
        for key in ("package", "version", "sourceUrl", "integrity"):
            with self.subTest(key=key):
                self.assertTrue(document.get(key))


if __name__ == "__main__":
    unittest.main()
