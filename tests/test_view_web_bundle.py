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
)
HTML_SINKS = (
    ("innerHTML", re.compile(r"\binnerHTML\b")),
    ("outerHTML", re.compile(r"\bouterHTML\b")),
    ("insertAdjacentHTML", re.compile(r"\binsertAdjacentHTML\b")),
    ("document.write", re.compile(r"\bdocument\s*\.\s*write(?:ln)?\s*\(")),
    ("srcdoc", re.compile(r"\bsrcdoc\b")),
    ("DOMParser", re.compile(r"\bDOMParser\b")),
    ("createContextualFragment", re.compile(r"\bcreateContextualFragment\b")),
)
# Loads a first-party file may start: import/export from, dynamic import, fetch, Worker, EventSource, XHR.
JS_REFERENCE = re.compile(
    r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\bfetch\s*\(\s*|\bnew\s+(?:Worker|SharedWorker|EventSource|URL)\s*\(\s*|
        \.open\s*\(\s*["'][A-Z]+["']\s*,\s*|\bimportScripts\s*\(\s*)(["'`])([^"'`]*)\1""", re.VERBOSE)
CSS_REFERENCE = re.compile(r"""(?:url\(\s*(["']?)([^)"']*)\1\s*\)|@import\s+(["'])([^"']*)\3)""", re.IGNORECASE)
REFERENCE_ATTRIBUTES = ("src", "href", "action", "formaction", "poster", "data", "srcset", "ping", "content")


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def is_local_reference(value: str) -> bool:
    """A reference stays in the page origin: a single-slash path, a fragment, a relative name or `data:`."""
    value = value.strip()
    if not value or value.startswith("#") or value.lower().startswith("data:"):
        return True
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
                self.references.append((tag, name, value))
            if name == "style":
                self.inline_styles.append(f"<{tag} style>")
        if tag == "meta" and attributes.get("http-equiv", "").lower() == "content-security-policy":
            self.meta_csp.append(attributes.get("content", ""))
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
    scan = PageScan(html)
    maps = [text for kind, text in scan.inline_scripts if kind == "importmap"]
    if len(maps) > 1:
        raise AssertionError("more than one import map")
    if not maps:
        return None
    return base64.b64encode(hashlib.sha256(maps[0].encode("utf-8")).digest()).decode("ascii")


def import_map_targets(html: str) -> list[str]:
    scan = PageScan(html)
    targets: list[str] = []
    for kind, text in scan.inline_scripts:
        if kind != "importmap":
            continue
        document = json.loads(text)
        for section in (document.get("imports", {}), *document.get("scopes", {}).values()):
            targets.extend(section.values())
    return targets


def violations_in_script(text: str) -> list[str]:
    found = [name for name, pattern in CODE_EVALUATION + HTML_SINKS if pattern.search(text)]
    found += [f"remote reference {match.group(2)!r}" for match in JS_REFERENCE.finditer(text)
              if not is_local_reference(match.group(2))]
    return found


def violations_in_style(text: str) -> list[str]:
    found = []
    for match in CSS_REFERENCE.finditer(text):
        target = match.group(2) if match.group(2) is not None else match.group(4)
        if not is_local_reference(target):
            found.append(f"remote reference {target!r}")
    return found


def violations_in_page(html: str) -> list[str]:
    scan = PageScan(html)
    found = [f"remote reference {tag} {name}={value!r}" for tag, name, value in scan.references
             if not is_local_reference(value)]
    found += [f"inline event handler {tag} {name}" for tag, name in scan.event_handlers]
    found += [f"inline style {item}" for item in scan.inline_styles]
    found += [f"inline script of type {kind or 'classic'}" for kind, _ in scan.inline_scripts if kind != "importmap"]
    if len([1 for kind, _ in scan.inline_scripts if kind == "importmap"]) > 1:
        found.append("more than one import map")
    found += [f"import map target {target!r}" for target in import_map_targets(html) if not is_local_reference(target)]
    return found


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
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertTrue(any(expected in item for item in violations_in_script(text)), text)

    def test_clean_script_passes(self):
        text = "import * as THREE from 'three';\nconst r = await fetch('/snapshot');\nel.textContent = 'x';"
        self.assertEqual(violations_in_script(text), [])

    def test_style_violations_are_found(self):
        self.assertTrue(violations_in_style("a { background: url(https://x.example/a.png) }"))
        self.assertTrue(violations_in_style("@import 'https://x.example/a.css';"))
        self.assertTrue(violations_in_style("a { background: url('//x.example/a.png') }"))
        self.assertEqual(violations_in_style("a { background: url(data:image/svg+xml;utf8,x) }"), [])

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
        }
        for html, expected in cases.items():
            with self.subTest(html=html):
                self.assertTrue(any(expected in item for item in violations_in_page(html)), html)

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
    def test_the_first_party_files_exist(self):
        for name in FIRST_PARTY:
            with self.subTest(name=name):
                self.assertTrue((WEB / name).is_file())

    def test_the_bundle_has_no_other_first_party_file(self):
        names = {path.name for path in WEB.iterdir()}
        self.assertEqual(names - {"vendor"}, set(FIRST_PARTY))

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

    def test_the_only_inline_script_allowed_is_the_import_map(self):
        kinds = [kind for kind, _ in PageScan(read("index.html")).inline_scripts]
        self.assertLessEqual(len(kinds), 1)
        self.assertTrue(all(kind == "importmap" for kind in kinds), kinds)

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
            if tag in ("script", "link") and name in ("src", "href") and not value.startswith("data:"):
                with self.subTest(tag=tag, value=value):
                    self.assertIn(value, files)

    def test_import_map_targets_are_vendored_files_listed_in_the_manifest(self):
        listed = {f"/web/vendor/{path}" for path in manifest()["files"]}
        for target in import_map_targets(read("index.html")):
            with self.subTest(target=target):
                self.assertIn(target, listed)


class ServedBundleTests(unittest.TestCase):
    """The real first-party files, served by ViewServer with the hash of the page's import map."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.bundle = {name: (WEB / name).read_bytes() for name in FIRST_PARTY}
        self.map_hash = import_map_hash(read("index.html"))
        self.server = ViewServer(LoomStore(), Path(tmp.name) / "run", bundle=self.bundle,
                                 import_map_sha256=self.map_hash)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join(5)))
        opened = self.fetch(f"/open?code={self.server.open_url.split('code=')[1]}")[1]
        self.cookie = opened.getheader("Set-Cookie").split(";")[0]

    def fetch(self, path, cookie=None):
        headers = {"Host": f"127.0.0.1:{self.server.port}"}
        if cookie:
            headers["Cookie"] = cookie
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            return response.status, response, response.read()
        finally:
            connection.close()

    def served_paths(self):
        return ["/"] + [f"/web/{name}" for name in FIRST_PARTY]

    def test_every_first_party_file_is_served_unchanged_to_a_session(self):
        for path in self.served_paths():
            with self.subTest(path=path):
                status, _, body = self.fetch(path, self.cookie)
                name = "index.html" if path == "/" else path[5:]
                self.assertEqual((status, body), (200, self.bundle[name]))

    def test_the_contract_policy_names_no_remote_origin_and_only_the_import_map_hash(self):
        script = "'self'" + (f" 'sha256-{self.map_hash}'" if self.map_hash else "")
        expected = (f"default-src 'self'; script-src {script}; style-src 'self'; img-src 'self' data:; "
                    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'; "
                    "require-trusted-types-for 'script'")
        for path in self.served_paths():
            with self.subTest(path=path):
                _, response, _ = self.fetch(path, self.cookie)
                policy = response.getheader("Content-Security-Policy")
                self.assertEqual(policy, expected)
                self.assertNotRegex(policy, r"(?i)https?:|wss?:|\*|unsafe-|blob:|//")
                self.assertIn("require-trusted-types-for 'script'", policy)

    def test_the_contract_headers_are_set_on_the_bundle_and_on_refusals(self):
        for path in self.served_paths():
            with self.subTest(path=path):
                _, response, _ = self.fetch(path, self.cookie)
                for name, value in CONTRACT_HEADERS.items():
                    self.assertEqual(response.getheader(name), value, name)
        status, response, _ = self.fetch("/")
        self.assertEqual(status, 404)  # no session
        self.assertEqual(response.getheader("Cache-Control"), "no-store")

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


def manifest() -> dict:
    return json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))


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
                self.assertTrue(file.is_file() and not file.is_symlink(), path)
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), digest)

    def test_nothing_unlisted_exists_under_vendor(self):
        listed = set(manifest()["files"]) | {"manifest.json"}
        present = {path.relative_to(VENDOR).as_posix() for path in VENDOR.rglob("*") if not path.is_dir()}
        self.assertEqual(present - listed, set(), "unlisted vendored files")
        self.assertEqual(listed - present, set(), "listed files missing")
        for path in VENDOR.rglob("*"):
            self.assertFalse(path.is_symlink(), path)

    def test_the_manifest_pins_package_version_and_integrity(self):
        document = manifest()
        for key in ("package", "version", "sourceUrl", "integrity"):
            with self.subTest(key=key):
                self.assertTrue(document.get(key))


if __name__ == "__main__":
    unittest.main()
