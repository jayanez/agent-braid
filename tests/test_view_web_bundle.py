# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T026, T025: checks of the activity viewer web bundle (procedure_010, bundle and scene parts).

First-party files (`index.html`, `loom.js`, `braid-scene.js`, `style.css`) are scanned for remote
origins, code evaluation and HTML sinks; the real bundle is served by `ViewServer` to check the CSP,
headers and the manifest-listed vendor files of contracts/ui-security-privacy.md; vendored files are
checked by manifest hash only. The scene module is built under Node (when available) against the
real vendored Three.js and the model of the example stream, to check the visual grammar and the
bijection between drawn objects and source events without a browser.
"""
import base64
import functools
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path

from agent_braid.view_loom import parse_stream
from agent_braid.view_model import build_model
from agent_braid.view_serve import ViewServer
from agent_braid.view_store import LoomStore
from agent_braid.view_tail import MAX_ROOTS, root_label
from tests.view_http_helpers import http_request

WEB = Path(__file__).resolve().parents[1] / "integrations/agent-braid-view/web"
VENDOR = WEB / "vendor"
FIRST_PARTY = ("index.html", "loom.js", "braid-scene.js", "state.js", "strings.js", "timeline.js", "planmap.js", "style.css")
SCRIPTS = ("loom.js", "braid-scene.js", "state.js", "strings.js", "timeline.js", "planmap.js")
MODULES = tuple(name for name in SCRIPTS if name != "braid-scene.js")  # what loom.js imports (the scene is a dynamic import)
SERVED_PATHS = ("/", *(f"/web/{name}" for name in FIRST_PARTY))
EXAMPLE = Path(__file__).resolve().parents[1] / "specs/061-activity-viewer/contracts/loom-event.example.jsonl"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
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


@functools.lru_cache(maxsize=1)
def strings_table() -> dict:
    """The `en` and `es` string tables of strings.js, read by running the module under Node."""
    program = "import { STRINGS } from %s; console.log(JSON.stringify(STRINGS));" % json.dumps((WEB / "strings.js").as_uri())
    done = subprocess.run(["node", "--input-type=module", "-e", program], capture_output=True, text=True, timeout=60)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout)


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
                # The SVG namespace is an identifier the DOM API needs, never a request: it is not a remote reference.
                self.assertEqual(REMOTE_URL.findall(read(name).replace(SVG_NAMESPACE, "")), [])

    def test_the_scripts_have_no_evaluation_or_html_sink(self):
        for name in SCRIPTS:
            with self.subTest(name=name):
                self.assertEqual(violations_in_script(read(name)), [])

    def test_the_scene_module_sets_no_attribute_from_a_variable(self):
        text = read("braid-scene.js")
        self.assertEqual([m.group(0) for m in SET_ATTRIBUTE.finditer(text) if m.group(3) is not None], [])
        self.assertNotRegex(text, r"\.style\.cssText|\.setAttribute\(\s*[\"']style")

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

    def test_the_timeline_sets_only_allowlisted_svg_attributes(self):
        text = read("timeline.js")
        dynamic = [m.group(0) for m in SET_ATTRIBUTE.finditer(text) if m.group(3) is not None]
        self.assertEqual(len(dynamic), 1, dynamic)
        self.assertRegex(text, r"if \(!ALLOWED\.has\(name\)\) throw new Error")
        allowed = re.search(r"const ALLOWED = new Set\(\[(.*?)\]\);", text, re.S).group(1)
        for name in re.findall(r'"([^"]+)"', allowed):
            self.assertIsNone(UNSAFE_ATTRIBUTE.match(name) if name != "href" else None, name)  # href only carries "#symbol"
        self.assertRegex(text, r'href: "#" \+ id')
        self.assertNotRegex(text, r"\.innerHTML|insertAdjacent|\.style\.cssText")

    def test_every_symbol_and_pattern_the_scripts_and_styles_reference_is_defined_once_in_the_page(self):
        html = read("index.html")
        defined = re.findall(r'<(?:symbol|pattern) id="([^"]+)"', html)
        self.assertEqual(len(defined), len(set(defined)))
        used = set(re.findall(r'"(g-[a-z-]+)"', read("timeline.js") + read("loom.js")))
        used |= set(re.findall(r"url\(#([a-z-]+)\)", read("style.css") + read("timeline.js")))
        used.discard("tl-clip")  # the clip path is created by the timeline itself
        self.assertTrue(used)
        self.assertEqual(sorted(used - set(defined)), [])

    def test_a_meta_policy_copy_omits_frame_ancestors(self):
        for policy in PageScan(read("index.html")).meta_csp:
            with self.subTest(policy=policy):
                self.assertNotIn("frame-ancestors", policy)
                self.assertNotRegex(policy, r"(?i)https?:|unsafe-")

    def test_the_legend_states_a_class_is_not_a_guarantee(self):
        html = read("index.html")
        legend = html[html.index('aria-labelledby="legend-title"'):]
        self.assertIn(LEGEND_LITERAL, legend[:legend.index("</section>")])
        self.assertIn(LEGEND_LITERAL, read("strings.js"))  # the legend text lives in the string module

    def test_the_page_states_the_non_claim_and_read_only_markers(self):
        html = read("index.html")
        self.assertIn("not a safety ordering", html)
        self.assertIn("executionAuthorization: false", html)
        self.assertIn("Read-only", html)  # the boundary strip, visible on every screen
        self.assertIn("does not authorize execution", html)

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

    def test_the_page_declares_one_import_map_before_the_module_script(self):
        html = read("index.html")
        scan = PageScan(html)
        self.assertEqual([kind for kind, _ in scan.inline_scripts], ["importmap"])
        self.assertLess(html.index('type="importmap"'), html.index('type="module"'))
        imports = json.loads(scan.inline_scripts[0][1])["imports"]
        self.assertEqual(set(imports), {"three", "three/addons/controls/OrbitControls.js"})
        self.assertEqual(json.loads(scan.inline_scripts[0][1]).keys(), {"imports"})  # no scopes, no integrity table

    def test_every_bare_or_relative_import_of_the_scene_and_the_vendored_modules_resolves(self):
        mapped = set(json.loads(PageScan(read("index.html")).inline_scripts[0][1])["imports"])
        listed = set(manifest()["files"])
        statement = re.compile(r"""(?:^|[\s;}])(?:import|export)\s[^'";]*?\bfrom\s*["']([^"']+)["']|(?:^|\s)import\s*["']([^"']+)["']""", re.M)
        checked = 0
        for owner, text in [("braid-scene.js", read("braid-scene.js"))] + [
                (path, (VENDOR / path).read_text(encoding="utf-8")) for path in sorted(listed) if path.endswith(".js")]:
            for match in statement.finditer(text):
                specifier = match.group(1) or match.group(2)
                checked += 1
                with self.subTest(owner=owner, specifier=specifier):
                    if specifier.startswith("."):
                        self.assertNotEqual(owner, "braid-scene.js", "the scene module imports only through the import map")
                        self.assertIn((Path(owner).parent / specifier).as_posix(), listed)
                    else:
                        self.assertIn(specifier, mapped)
        self.assertGreaterEqual(checked, 3)

    def test_the_page_has_the_scene_elements_and_loom_has_no_static_scene_import(self):
        # Behaviour (playback binding, selection, every scene failure keeping the table) is in test_view_web_behaviour.
        text = read("loom.js")
        for statement in re.findall(r"(?m)^\s*import\b[^(].*?from\s*[\"']([^\"']+)[\"']", text, re.S):
            self.assertNotIn("braid-scene", statement, "loom.js must not import the scene statically")
        self.assertRegex(text, r"await import\(\"/web/braid-scene.js\"\)")
        html = read("index.html")
        for identifier in ("scene-section", "scene-box", "scene-hover", "scene-note", "scene-reset", "legend-scene"):
            self.assertIn(f'id="{identifier}', html)
        self.assertIn("hidden", html[html.index('id="scene-section"'):html.index('id="scene-title"')])

    def test_the_page_offers_source_checkboxes_that_filter_the_table_and_the_scene(self):
        html, script, scene = read("index.html"), read("loom.js"), read("braid-scene.js")
        for identifier in ("sources", "source-list", "source-status"):
            self.assertIn(f'id="{identifier}', html)
        self.assertIn("hidden", html[html.index('id="sources"'):html.index('id="source-list"')])
        self.assertLess(html.index('id="sources"'), html.index('id="scene-section"'), "the sources sit above both views")
        self.assertIn("never looks like an absent one", html)
        self.assertRegex(scene, r"setVisible\(seqs, position = seqs\)")
        self.assertRegex(scene, r"frontier = frontierX\(built, frontierSeqs\)")
        self.assertNotRegex(script, r"localStorage|sessionStorage|document\.cookie", "the page shell stores nothing itself")
        # Only two per-viewer preferences exist (language and view); the selection and the events are never stored.
        state = read("state.js")
        self.assertRegex(state, r'PREFERENCE_KEYS = new Set\(\["lang", "view"\]\)')
        self.assertNotRegex(state, r"sessionStorage|document\.cookie|indexedDB")
        self.assertEqual(re.findall(r"localStorage\.(\w+)", state), ["getItem", "removeItem", "setItem"])

    def test_the_scene_legend_and_page_say_a_class_is_not_a_guarantee_and_no_effort_is_drawn(self):
        legend = " ".join(value for key, value in strings_table()["en"].items() if key.startswith("sceneLegend."))
        self.assertIn(LEGEND_LITERAL, legend)
        self.assertIn("not a safety ordering", legend)
        self.assertIn("advisory plan, not a runtime measurement", legend + read("braid-scene.js"))
        self.assertIn("Effort and tokens are not drawn", legend)
        self.assertIn(LEGEND_LITERAL, read("index.html")[read("index.html").index('id="scene-section"'):])



SCENE_DRIVER = """
import { readFileSync } from "node:fs";
import { buildBraid, describeBraid, frontierX } from "./braid-scene.js";

const model = JSON.parse(readFileSync(process.argv[2], "utf8"));
const built = buildBraid(model, { labels: false });
const objects = [];
for (const [owner, list] of built.bySeq) {
  for (const object of list) {
    const material = object.material || {};
    objects.push({
      owner, part: object.userData.part, selectable: object.userData.seq === undefined ? null : object.userData.seq,
      color: material.color ? material.color.getHex() : null, opacity: material.opacity === undefined ? null : material.opacity,
      pulse: Boolean(material.userData && material.userData.pulse),
      sides: object.userData.sides !== undefined ? object.userData.sides
        : /-ring$/.test(object.userData.part) ? object.geometry.parameters.tubularSegments : null,
    });
  }
}
const seqs = model.elements.map((element) => element.seq);
const empty = buildBraid(null);
const labelled = buildBraid(model);
console.log(JSON.stringify({
  description: describeBraid(built), objects,
  frontier: { all: frontierX(built, seqs), none: String(frontierX(built, [])), first: frontierX(built, seqs.slice(0, 3)) },
  xs: Object.fromEntries(built.xOf), emptyParts: describeBraid(empty).parts,
  labels: labelled.labels.map((item) => ({ owner: item.owner, text: item.text, key: item.key, pin: item.pin, priority: item.priority })),
  unlabelled: built.labels.length,
  sprites: (() => { let count = 0; labelled.group.traverse((object) => { if (object.isSprite) count += 1; }); return count; })(),
}));
"""
TEAL, RED, AMBER = 0x2A9D8F, 0xD1495B, 0xE0A100


@unittest.skipIf(not shutil.which("node") and not os.environ.get("CI"), "node is needed to build the scene without a browser")
class SceneBuildTests(unittest.TestCase):
    """The scene module's objects, built under Node from the real vendored Three.js and the example model."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        package = root / "node_modules" / "three"
        for path in manifest()["files"]:
            if path.endswith(".js"):
                target = package / Path(path).relative_to("three")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(VENDOR / path, target)
        (package / "package.json").write_text(json.dumps(
            {"name": "three", "type": "module", "exports": {".": "./three.module.js", "./addons/*": "./addons/*"}}))
        (root / "package.json").write_text('{"type": "module"}')
        shutil.copyfile(WEB / "braid-scene.js", root / "braid-scene.js")
        (root / "driver.mjs").write_text(SCENE_DRIVER)
        cls.root = root
        cls.model = build_model(parse_stream(EXAMPLE.read_bytes()))
        cls.built = cls.build(cls.model)

    @classmethod
    def build(cls, model):
        path = cls.root / "model.json"
        path.write_text(json.dumps(model))
        done = subprocess.run(["node", "driver.mjs", str(path)], cwd=cls.root, capture_output=True, text=True, timeout=120)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        return json.loads(done.stdout)

    def elements(self, model=None):
        return {element["seq"]: element for element in (model or self.model)["elements"]}

    def parts(self, built=None):
        return {int(seq): set(parts) for seq, parts in (built or self.built)["description"]["parts"].items()}

    def objects_of(self, seq, built=None):
        return [item for item in (built or self.built)["objects"] if item["owner"] == seq]

    def expected_drawn(self, model=None):
        model = model or self.model
        lanes = {lane["strandId"] for lane in model["lanes"]}
        drawn = set()
        for element in model["elements"]:
            kind = element["element"]
            if kind == "crossing" and element["drawAs"] != "unplaced":
                drawn.add(element["seq"])
            elif kind == "strand" and element["strandId"] in lanes:
                drawn.add(element["seq"])
            elif kind in ("strand-state", "strand-end", "wave-plane", "wave-marker", "gate-ring") and (
                    element["lanes"] or kind in ("wave-plane", "gate-ring")):
                drawn.add(element["seq"])
            elif kind == "gap" and element["strandId"] in lanes:
                drawn.add(element["seq"])
            elif kind == "hazard-cone" and any(unit in lanes for unit in element["units"]):
                drawn.add(element["seq"])
        return drawn

    def test_labels_are_descriptors_for_html_not_sprites_and_each_agent_label_is_pinned_first(self):
        built = self.built
        self.assertEqual(built["sprites"], 0)
        self.assertEqual(built["unlabelled"], 0)
        pinned = [item for item in built["labels"] if item["pin"]]
        declared = [lane for lane in self.model["lanes"] if lane["declared"]]
        self.assertEqual(len(pinned), len(declared))
        self.assertTrue(all(item["priority"] == 0 for item in pinned))
        self.assertTrue(all(item["priority"] > 0 for item in built["labels"] if not item["pin"]))
        self.assertTrue({item["key"] for item in built["labels"]} - {None} <= {
            "scene.label.class", "scene.label.wavePlan", "scene.label.wave", "scene.label.grant", "scene.label.grantUnknown",
            "scene.label.gate", "scene.label.gateUnknown"})

    def test_every_declared_agent_has_an_invisible_hit_volume_that_selects_its_own_event(self):
        for lane in self.model["lanes"]:
            if not lane["declared"]:
                continue
            volumes = [item for item in self.objects_of(lane["seq"]) if item["part"] == "hit-volume"]
            self.assertEqual(len(volumes), 1)
            self.assertEqual(volumes[0]["selectable"], lane["seq"])

    def test_every_drawn_object_belongs_to_one_source_event_and_only_event_kinds_that_are_drawn_appear(self):
        elements = self.elements()
        parts = self.parts()
        self.assertTrue(set(parts) <= set(elements))
        self.assertEqual(set(parts), self.expected_drawn())
        drawn_kinds = {elements[seq]["element"] for seq in parts}
        self.assertEqual(drawn_kinds, {"strand", "strand-end", "crossing", "wave-plane", "wave-marker", "gate-ring",
                                        "hazard-cone", "gap"})
        for item in self.built["objects"]:
            self.assertIn(item["selectable"], (None, item["owner"]))  # a click selects the owner event, never another

    def test_events_that_are_not_drawn_say_why_and_none_is_both_drawn_and_left_out(self):
        notdrawn = {int(seq): reason for seq, reason in self.built["description"]["notDrawn"].items()}
        self.assertFalse(set(notdrawn) & set(self.parts()))
        every = set(self.elements())
        self.assertEqual(every - set(self.parts()) - set(notdrawn), set())  # nothing silently vanishes
        kinds = {self.elements()[seq]["element"] for seq in notdrawn}
        self.assertEqual(kinds, {"session", "report", "effort"})
        for reason in notdrawn.values():
            self.assertIn("table", reason)

    def test_effort_and_tokens_are_not_read_or_drawn(self):
        text = read("braid-scene.js")
        for field in ("knownTokens", "inputTokens", "outputTokens", "costUsd", "effortBasis", "cacheReadTokens"):
            self.assertNotIn(field, text)
        effort = [seq for seq, element in self.elements().items() if element["element"] == "effort"]
        self.assertTrue(effort)
        for seq in effort:
            self.assertNotIn(seq, self.parts())
            self.assertIn("effort and tokens are not drawn", self.built["description"]["notDrawn"][str(seq)])
        for item in self.built["objects"]:
            self.assertNotIn("effort", item["part"])

    def test_only_independent_candidate_pairs_become_swaps_and_non_adjacent_pairs_become_bridges(self):
        crossings = [e for e in self.elements().values() if e["element"] == "crossing"]
        self.assertGreaterEqual(len(crossings), 6)
        for element in crossings:
            seq, parts = element["seq"], self.parts()[element["seq"]]
            with self.subTest(seq=seq, classification=element["classification"], drawAs=element["drawAs"]):
                self.assertEqual("swap" in parts, element["classification"] == "independent-candidate" and element["drawAs"] == "swap")
                self.assertEqual(any(part.startswith("bridge") for part in parts), element["drawAs"] == "bridge")
                self.assertEqual("conflict-knot" in parts, element["classification"] == "conflicting" and element["drawAs"] != "bridge")
                self.assertEqual("unknown-link" in parts, element["drawAs"] == "unknown-link")
                self.assertEqual("ordered-link" in parts, element["drawAs"] == "ordered-link")
        self.assertTrue(any(e["drawAs"] == "swap" for e in crossings) and any(e["drawAs"] == "bridge" for e in crossings))

    def test_unknown_and_conflicting_pairs_are_never_coloured_as_independent_and_unknown_ones_pulse(self):
        for element in self.elements().values():
            if element["element"] != "crossing":
                continue
            drawn = [item for item in self.objects_of(element["seq"]) if item["part"] not in ("badge", "unverified-marker", "partial-halo")]
            colors = {item["color"] for item in drawn}
            with self.subTest(seq=element["seq"], classification=element["classification"]):
                if element["classification"] == "unknown":
                    self.assertNotIn(TEAL, colors)
                    self.assertTrue(drawn and all(item["pulse"] for item in drawn), "unknown pairs are dashed and pulsing")
                if element["classification"] == "conflicting":
                    self.assertEqual(colors, {RED})
                if element["classification"] == "independent-candidate":
                    self.assertEqual(colors, {TEAL})
                    self.assertFalse(any(item["pulse"] for item in drawn))

    def test_class_badges_are_categorical_with_one_colour_and_one_opacity(self):
        badges = [(seq, item) for seq in self.parts() for item in self.objects_of(seq) if item["part"] == "badge"]
        crossings = {seq: e for seq, e in self.elements().items() if e["element"] == "crossing" and seq in self.parts()}
        self.assertEqual({seq for seq, _ in badges}, set(crossings))
        self.assertEqual(len(badges), len(crossings))
        for seq, item in badges:
            self.assertEqual(item["sides"], 3 + crossings[seq]["compatibilityClass"])
        self.assertEqual(len({(item["color"], item["opacity"]) for _, item in badges}), 1, "no brightness or opacity per class")
        self.assertGreater(len({item["sides"] for _, item in badges}), 1)  # more than one class is shown, by shape

    def test_unverified_elements_carry_the_distinct_unverified_marker(self):
        unverified = [seq for seq in self.parts() if self.elements()[seq]["unverified"]]
        self.assertTrue(unverified)
        for seq in unverified:
            with self.subTest(seq=seq, kind=self.elements()[seq]["element"]):
                self.assertIn("unverified-marker", self.parts()[seq])
        crossings_and_gates = [seq for seq in self.parts() if self.elements()[seq]["element"] in ("crossing", "gate-ring")]
        self.assertTrue(crossings_and_gates)

    def test_a_verified_element_has_no_unverified_marker(self):
        model = json.loads(json.dumps(self.model))
        for element in model["elements"]:
            element["unverified"] = False
            element["verification"] = "rehashed"
        built = self.build(model)
        self.assertFalse(any(item["part"] == "unverified-marker" for item in built["objects"]))

    def test_an_unrecognised_verification_value_is_marked_unverified_like_the_table_does(self):
        model = json.loads(json.dumps(self.model))
        for element in model["elements"]:
            element["unverified"] = False
            element["verification"] = "something-new"
        built = self.build(model)
        marked = {item["owner"] for item in built["objects"] if item["part"] == "unverified-marker"}
        self.assertTrue(marked)
        self.assertTrue({e["seq"] for e in model["elements"] if e["element"] in ("crossing", "gate-ring")} & set(self.parts(built)) <= marked)

    def test_a_hazard_that_names_several_units_has_one_unverified_marker(self):
        for element in self.elements().values():
            if element["element"] == "hazard-cone" and element["unverified"] and self.parts().get(element["seq"]):
                markers = [i for i in self.objects_of(element["seq"]) if i["part"] == "unverified-marker"]
                self.assertEqual(len(markers), 1)

    def test_hazards_are_anchored_at_every_unit_they_name_and_not_observed_ones_are_dashed_and_pulsing(self):
        lanes = {lane["strandId"] for lane in self.model["lanes"]}
        hazards = [e for e in self.elements().values() if e["element"] == "hazard-cone"]
        self.assertTrue(hazards)
        for element in hazards:
            cones = [item for item in self.objects_of(element["seq"]) if item["part"].startswith("hazard-cone")]
            self.assertEqual(len(cones), len([unit for unit in element["units"] if unit in lanes]))
            if element["absence"]:
                self.assertTrue(all(item["part"] == "hazard-cone-unobserved" and item["pulse"] for item in cones))
                self.assertFalse(any(item["part"] == "hazard-spark" for item in self.objects_of(element["seq"])))
            else:
                self.assertTrue(all(item["part"] == "hazard-cone" and not item["pulse"] for item in cones))

    def test_gaps_break_the_strand_with_a_pulsing_stub_and_gates_have_rings(self):
        for element in self.elements().values():
            parts = self.parts().get(element["seq"], set())
            if element["element"] == "gap":
                self.assertTrue({"gap-stub", "gap-break"} <= parts)
                self.assertTrue(all(i["pulse"] for i in self.objects_of(element["seq"]) if i["part"] == "gap-stub"))
            if element["element"] == "gate-ring":
                self.assertTrue(parts & {"grant-ring", "gate-result-ring", "gate-phase-ring"})
            if element["element"] == "wave-plane":
                self.assertIn("wave-slab", parts)
            if element["element"] == "wave-marker":
                self.assertIn("wave-frame-edges", parts)

    def test_gate_results_and_grant_states_differ_in_colour_or_sides_and_an_unknown_value_is_grey(self):
        model = json.loads(json.dumps(self.model))
        gate = next(e for e in model["elements"] if e["element"] == "gate-ring" and e["ringKind"] == "workflow-result")
        grant = next(e for e in model["elements"] if e["element"] == "gate-ring" and e["ringKind"] == "grant")
        statuses = ["refused", "busy", "inconclusive", "hazards-found", "ok-analyzed", "ok-certified"]
        states = ["issued", "consumed", "expired", "refused"]
        clones = [dict(gate, seq=100 + i, gateStatus=name, status=name) for i, name in enumerate(statuses)]
        clones += [dict(grant, seq=200 + i, state=name, status=name) for i, name in enumerate(states)]
        clones += [dict(gate, seq=300, gateStatus="constructor"), dict(grant, seq=301, state="constructor")]
        model["elements"] += clones
        built = self.build(model)

        def shape(seq, part):
            return {(i["color"], i["sides"]) for i in self.objects_of(seq, built) if i["part"] == part}

        gates = [frozenset(shape(100 + i, "gate-result-ring")) for i in range(len(statuses))]
        grants = [frozenset(shape(200 + i, "grant-ring")) for i in range(len(states))]
        self.assertEqual(len(set(gates)), len(statuses), "each result has its own colour or sides")
        self.assertEqual(len(set(grants)), len(states), "each state has its own colour or sides")
        self.assertEqual(shape(300, "gate-result-ring"), {(0x8A8D96, 3)})
        self.assertEqual(shape(301, "grant-ring"), {(0x8A8D96, 3)})

    def test_the_playback_frontier_follows_the_last_visible_event(self):
        frontier = self.built["frontier"]
        xs = {int(seq): x for seq, x in self.built["xs"].items()}
        self.assertEqual(frontier["none"], "-Infinity")
        self.assertEqual(frontier["all"], max(xs.values()))
        self.assertEqual(frontier["first"], max(xs[1], xs[2], xs[3]))
        ordered = [xs[element["seq"]] for element in sorted(self.model["elements"], key=lambda e: e["order"])]
        self.assertEqual(ordered, sorted(ordered), "the scene axis never runs against the model order")

    def test_a_pair_without_a_placed_lane_is_left_to_the_table(self):
        model = json.loads(json.dumps(self.model))
        crossing = next(e for e in model["elements"] if e["element"] == "crossing")
        model["elements"].append(dict(crossing, seq=99, drawAs="unplaced", segments=[], isSwap=False))
        built = self.build(model)
        self.assertNotIn(99, self.parts(built))
        self.assertIn("table", built["description"]["notDrawn"]["99"])

    def test_the_draw_cap_leaves_the_rest_to_the_table(self):
        model = json.loads(json.dumps(self.model))
        arrow = next(e for e in model["elements"] if e["element"] == "crossing" and e["drawAs"] == "swap")
        arrow = dict(arrow, drawAs="ordered-link", classification="ordered", isSwap=False)
        model["elements"] += [dict(arrow, seq=1000 + index) for index in range(2105)]
        built = self.build(model)
        extra = [seq for seq in self.parts(built) if seq >= 1000]
        left_out = [int(seq) for seq in built["description"]["notDrawn"] if int(seq) >= 1000]
        self.assertEqual(len(extra) + len(left_out), 2105)
        self.assertGreater(len(left_out), 0)
        self.assertTrue(all("draw cap" in built["description"]["notDrawn"][str(seq)] for seq in left_out))

    def test_an_empty_model_builds_nothing(self):
        self.assertEqual(self.built["emptyParts"], {})


DOM_STUB = """
export class Node {}
class Text extends Node {
  constructor(data) { super(); this.data = data; }
  get textContent() { return this.data; }
}
class Element extends Node {
  constructor(tag) {
    super();
    Object.assign(this, { tag, tagName: tag, children: [], attrs: {}, listeners: {}, dataset: {}, hidden: false, className: "", own: null, tabIndex: 0 });
    this.style = {};
    this.clientWidth = 800;
    this.clientHeight = 400;
    const classes = new Set();
    this.classList = { add: (name) => classes.add(name), remove: (name) => classes.delete(name),
      toggle: (name, on) => { if (on === undefined ? !classes.has(name) : on) classes.add(name); else classes.delete(name); }, contains: (name) => classes.has(name) };
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = [...nodes]; this.own = null; }
  getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; }
  removeEventListener() {}
  contains() { return false; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 400 }; }
  setAttribute(name, value) {
    this.attrs[name] = value;
    if (name.startsWith("data-")) this.dataset[name.slice(5)] = value;
  }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  set textContent(value) { this.children = []; this.own = String(value); }
  get textContent() { return this.own !== null ? this.own : this.children.map((child) => child.textContent).join(""); }
  querySelector() { return null; }
  focus() {}
  descendants() { return this.children.flatMap((child) => (child instanceof Element ? [child, ...child.descendants()] : [])); }
}
const byId = new Map();
globalThis.document = {
  createElement: (tag) => new Element(tag),
  createTextNode: (data) => new Text(data),
  getElementById: (id) => { if (!byId.has(id)) byId.set(id, new Element("#" + id)); return byId.get(id); },
  activeElement: null,
  visibilityState: "visible",
  documentElement: { lang: "" },
  createElementNS: (ns, tag) => { const node = new Element(tag); node.namespace = ns; return node; },
  title: "",
  addEventListener() {},
  querySelectorAll: () => [],
};
Object.defineProperty(globalThis, "navigator", { value: { languages: JSON.parse(process.env.NAV_LANGUAGES || '["en"]') }, configurable: true });
globalThis.Node = Node;
globalThis.CSS = { escape: String };
globalThis.WebGL2RenderingContext = function WebGL2RenderingContext() {};
export const find = (id) => document.getElementById(id);
"""
SCENE_STUB = """
globalThis.sceneCalls = [];
export function createBraidScene(container, handlers) {
  let shown = [];
  return {
    setModel() {},
    setVisible(seqs, position) { shown = [...seqs]; sceneCalls.push({ seqs: [...seqs], position: position === undefined ? null : [...position] }); },
    setSelected() {},
    resetView() {},
    summary() { return { visible: shown.length, drawn: shown.length, seqs: shown, omitted: [] }; },
    dispose() {},
  };
}
"""
SCENE_HOOKS = """
export async function resolve(specifier, context, next) {
  if (specifier === "/web/braid-scene.js") return { url: new URL("./scene-stub.mjs", import.meta.url).href, shortCircuit: true };
  return next(specifier, context);
}
"""
PAGE_DRIVER = """
import { readFileSync } from "node:fs";
import { register } from "node:module";
import { find } from "./dom-stub.mjs";

const { model, steps } = JSON.parse(readFileSync(process.argv[2], "utf8"));
register("./scene-hooks.mjs", import.meta.url);
globalThis.location = { hash: "#v=map3d", pathname: "/", search: "" }; // these tests drive the 3D scene stub
globalThis.fetch = async (url) => {
  if (url === "/snapshot") return { ok: true, status: 200, json: async () => ({ model, droppedAttributeNames: [] }) };
  return new Promise(() => {}); // /events never answers: the model does not change
};
const settle = () => new Promise((resolve) => setTimeout(resolve, 30));
await import("./loom.js");
await settle();

const observe = () => {
  const checkboxes = find("source-list").descendants().filter((node) => node.attrs["data-source"]);
  const calls = sceneCalls[sceneCalls.length - 1] || null;
  return {
    checkboxes: Object.fromEntries(checkboxes.map((node) => [node.attrs["data-source"], node.checked])),
    labels: find("source-list").textContent,
    sourcesHidden: find("sources").hidden,
    status: find("source-status").textContent,
    rows: find("events-body").children.map((row) => Number(row.descendants().find((node) => node.attrs["data-seq"]).attrs["data-seq"])),
    emptyText: find("table-empty").textContent, emptyHidden: find("table-empty").hidden,
    scene: calls, sceneNote: find("scene-note").textContent,
    evidence: find("evidence").textContent, counters: find("counters").textContent,
    playback: find("pb-count").textContent,
  };
};
const results = [observe()];
for (const step of steps) {
  if (step.toggle) {
    const box = find("source-list").descendants().find((node) => node.attrs["data-source"] === step.toggle);
    box.checked = step.shown;
    box.listeners.change[0]({ target: box });
  } else if (step.select !== undefined) {
    const button = find("events-body").descendants().find((node) => node.attrs["data-seq"] === String(step.select));
    button.listeners.click[0]();
  } else if (step.cursor !== undefined) {
    find("pb-range").value = String(step.cursor);
    find("pb-range").listeners.input[0]({ target: find("pb-range") });
  }
  await settle();
  results.push(observe());
}
console.log(JSON.stringify(results));
process.exit(0);
"""
SOURCE_LABELS = {
    "watched": "Watched artifacts", "replay": "Replay file",
    "hook": "Hook and telemetry ingest", "viewer": "Derived by the viewer",
}


class NodePageCase(unittest.TestCase):
    """Runs the real loom.js under Node with a minimal DOM and a stub scene; `self.model` is what /snapshot returns."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        (cls.root / "package.json").write_text('{"type": "module"}')
        for name in MODULES:
            shutil.copyfile(WEB / name, cls.root / name)
        shutil.copyfile(WEB / "loom.js", cls.root / "loom.js")
        for name, text in (("dom-stub.mjs", DOM_STUB), ("scene-stub.mjs", SCENE_STUB),
                           ("scene-hooks.mjs", SCENE_HOOKS), ("driver.mjs", PAGE_DRIVER)):
            (cls.root / name).write_text(text)
        cls.model = cls.mixed_model()

    @classmethod
    def mixed_model(cls):
        """The example model with a replay file added: replayed events keep their reference and are unverified."""
        model = json.loads(json.dumps(build_model(parse_stream(EXAMPLE.read_bytes()))))
        watched = [e for e in model["elements"] if e["verification"] == "rehashed" and e["evidenceRef"]]
        for element in watched[:3]:
            element["verification"], element["unverified"] = "unverified", True
        return model

    def drive(self, steps=()):
        path = self.root / "input.json"
        path.write_text(json.dumps({"model": self.model, "steps": list(steps)}))
        done = subprocess.run(["node", "driver.mjs", str(path)], cwd=self.root, capture_output=True, text=True, timeout=60)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        return json.loads(done.stdout)

    def total(self):
        return len(self.model["elements"])


@unittest.skipIf(not shutil.which("node") and not os.environ.get("CI"), "node is needed to drive the page without a browser")
class SourceCheckboxTests(NodePageCase):
    """REQ-010 / SC-010 (amendment A1): per-source checkboxes drive loom.js under Node with a minimal DOM."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Written out, not recomputed: the example plus three watched events turned into replayed (unverified,
        # referenced) ones. seq 1 is a gap derived by the viewer; seq 18 to 21 are host reports with no artifact.
        cls.by_source = {"viewer": [1], "replay": [2, 3, 4], "hook": [18, 19, 20, 21],
                         "watched": [*range(5, 18), 22, 23, 24]}

    def test_the_example_covers_every_source_and_each_element_has_exactly_one(self):
        self.assertEqual(set(self.by_source), set(SOURCE_LABELS))
        self.assertEqual(sum(len(seqs) for seqs in self.by_source.values()), self.total())

    def test_one_checkbox_per_source_present_all_checked_and_nothing_hidden_by_default(self):
        first = self.drive()[0]
        self.assertFalse(first["sourcesHidden"])
        self.assertEqual(first["checkboxes"], dict.fromkeys(SOURCE_LABELS, True))
        for key, label in SOURCE_LABELS.items():
            count = len(self.by_source[key])
            self.assertIn(f"{label} ({count} event{'' if count == 1 else 's'})", first["labels"])
        self.assertIn("0 events hidden", first["status"])
        self.assertEqual(sorted(first["rows"]), sorted(e["seq"] for e in self.model["elements"]))
        self.assertEqual(sorted(first["scene"]["seqs"]), sorted(first["rows"]))
        self.assertNotIn("unchecked", first["sceneNote"])

    def test_unchecking_a_source_hides_its_elements_in_the_table_and_the_scene_and_shows_the_count(self):
        baseline = self.drive()[0]
        for key in SOURCE_LABELS:
            with self.subTest(source=key):
                after = self.drive([{"toggle": key, "shown": False}])[1]
                hidden = set(self.by_source[key])
                self.assertTrue(hidden)
                self.assertFalse(hidden & set(after["rows"]))
                self.assertEqual(set(after["rows"]), {e["seq"] for e in self.model["elements"]} - hidden)
                self.assertFalse(hidden & set(after["scene"]["seqs"]))
                self.assertEqual(set(after["scene"]["seqs"]), set(after["rows"]))
                self.assertFalse(after["checkboxes"][key])
                self.assertTrue(all(value for name, value in after["checkboxes"].items() if name != key))
                self.assertIn(f"{len(hidden)} of {self.total()} retained events are hidden", after["status"])
                self.assertIn("Hidden is not absent", after["status"])
                self.assertIn(f"{len(hidden)} events from unchecked sources are hidden here and in the table", after["sceneNote"])
                self.assertEqual(after["counters"], baseline["counters"], "counters keep covering hidden events")

    def test_the_scene_frontier_still_follows_the_playback_position_not_the_selection(self):
        after = self.drive([{"toggle": "hook", "shown": False}])[1]
        self.assertEqual(sorted(after["scene"]["position"]), sorted(e["seq"] for e in self.model["elements"]))
        self.assertTrue(set(after["scene"]["seqs"]) < set(after["scene"]["position"]))

    def test_rechecking_a_source_restores_its_elements_and_clears_the_count(self):
        first, hidden, back = self.drive([{"toggle": "viewer", "shown": False}, {"toggle": "viewer", "shown": True}])
        self.assertNotEqual(hidden["rows"], first["rows"])
        self.assertEqual(back["rows"], first["rows"])
        self.assertEqual(back["scene"]["seqs"], first["scene"]["seqs"])
        self.assertIn("0 events hidden", back["status"])
        self.assertNotIn("unchecked", back["sceneNote"])

    def test_several_unchecked_sources_add_up_and_hiding_everything_is_stated_not_silent(self):
        steps = [{"toggle": key, "shown": False} for key in SOURCE_LABELS]
        last = self.drive(steps)[-1]
        self.assertEqual(last["rows"], [])
        self.assertEqual(last["scene"]["seqs"], [])
        self.assertIn(f"{self.total()} of {self.total()} retained events are hidden", last["status"])
        self.assertFalse(last["emptyHidden"])
        self.assertIn("hidden", last["emptyText"])
        self.assertFalse(last["sourcesHidden"], "the checkboxes stay so a source can be shown again")

    def test_the_hidden_count_is_over_all_retained_events_while_the_table_follows_the_playback_position(self):
        hidden = self.by_source["hook"]
        late = self.drive([{"cursor": 3}, {"toggle": "hook", "shown": False}])[-1]
        self.assertIn(f"{len(hidden)} of {self.total()} retained events are hidden", late["status"])

    def test_the_playback_position_says_how_many_of_the_events_so_far_are_drawn(self):
        first, hidden = self.drive([{"toggle": "hook", "shown": False}])
        total = self.total()
        self.assertEqual(first["playback"], f"{total} of {total}")
        self.assertEqual(hidden["playback"], f"{total} of {total} ({total - len(self.by_source['hook'])} shown)")

    def test_hiding_the_source_of_the_selected_event_clears_the_evidence_panel(self):
        seq = self.by_source["hook"][0]
        selected, cleared = self.drive([{"select": seq}, {"toggle": "hook", "shown": False}])[1:]
        self.assertIn(f"Event {seq}", selected["evidence"])
        self.assertNotIn(f"Event {seq}", cleared["evidence"])
        self.assertIn("Select an event", cleared["evidence"])

    def test_hiding_another_source_keeps_the_selection(self):
        seq = self.by_source["watched"][0]
        kept = self.drive([{"select": seq}, {"toggle": "hook", "shown": False}])[-1]
        self.assertIn(f"Event {seq}", kept["evidence"])

    def test_a_model_with_one_source_offers_one_checkbox_and_an_empty_model_offers_none(self):
        original = self.model
        kept = set(self.by_source["watched"])
        self.model = dict(original, elements=[e for e in original["elements"] if e["seq"] in kept],
                          table=[row for row in original["table"] if row["seq"] in kept])
        try:
            self.assertEqual(list(self.drive()[0]["checkboxes"]), ["watched"])
            self.model = dict(original, elements=[], table=[], lanes=[])
            self.assertTrue(self.drive()[0]["sourcesHidden"])
        finally:
            self.model = original


@unittest.skipIf(not shutil.which("node") and not os.environ.get("CI"), "node is needed to drive the page without a browser")
class RootCheckboxTests(NodePageCase):
    """REQ-010 / SC-010 (amendment A1, T044): one checkbox per watched root label, driven under Node."""

    ROOT_1, ROOT_2, UNLABELLED = [*range(5, 11)], [*range(11, 18)], [22, 23, 24]
    OTHERS = {"replay": [2, 3, 4], "hook": [18, 19, 20, 21], "viewer": [1]}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for element in cls.model["elements"]:
            element["root"] = "root 1" if element["seq"] in cls.ROOT_1 else (
                "root 2" if element["seq"] in cls.ROOT_2 else None)
        for row in cls.model["table"]:
            row["root"] = next((e["root"] for e in cls.model["elements"] if e["seq"] == row["seq"]), None)

    def relabel(self, mapping):
        """Replace the model's roots for the duration of one test: `mapping` is seq -> label."""
        original = self.model
        self.model = json.loads(json.dumps(original))
        for element in self.model["elements"]:
            element["root"] = mapping.get(element["seq"])
        self.addCleanup(setattr, self, "model", original)

    def test_one_checkbox_per_root_then_the_unlabelled_watched_group_then_the_other_sources(self):
        first = self.drive()[0]
        self.assertEqual(list(first["checkboxes"]),
                         ["watched:root 1", "watched:root 2", "watched", "replay", "hook", "viewer"])
        self.assertEqual(set(first["checkboxes"].values()), {True})
        self.assertIn("root 1 (6 events)", first["labels"])
        self.assertIn("root 2 (7 events)", first["labels"])
        self.assertIn("Watched artifacts (3 events)", first["labels"])
        self.assertIn("0 events hidden", first["status"])

    def test_every_label_the_watcher_can_issue_gets_its_own_checkbox(self):
        self.relabel({5 + index: root_label(index) for index in range(MAX_ROOTS)})
        keys = list(self.drive()[0]["checkboxes"])
        self.assertEqual(keys[:MAX_ROOTS], [f"watched:{root_label(index)}" for index in range(MAX_ROOTS)])

    def test_roots_are_ordered_by_number_not_by_text(self):
        self.relabel({5: "root 10", 6: "root 2", 7: "root 1"})
        self.assertEqual(list(self.drive()[0]["checkboxes"])[:3], ["watched:root 1", "watched:root 2", "watched:root 10"])

    def test_unchecking_one_root_hides_only_its_events_in_the_table_and_the_scene(self):
        baseline = self.drive()[0]
        for key, hidden in (("watched:root 1", self.ROOT_1), ("watched:root 2", self.ROOT_2)):
            with self.subTest(root=key):
                after = self.drive([{"toggle": key, "shown": False}])[1]
                everything = {e["seq"] for e in self.model["elements"]}
                self.assertEqual(set(after["rows"]), everything - set(hidden))
                self.assertEqual(set(after["scene"]["seqs"]), set(after["rows"]))
                self.assertFalse(after["checkboxes"][key])
                self.assertEqual(sum(1 for shown in after["checkboxes"].values() if not shown), 1)
                self.assertIn(f"{len(hidden)} of {self.total()} retained events are hidden", after["status"])
                self.assertIn(f"{len(hidden)} events from unchecked sources are hidden here and in the table",
                              after["sceneNote"])
                self.assertEqual(after["counters"], baseline["counters"], "counters keep covering hidden events")

    def test_rechecking_a_root_restores_its_events(self):
        first, hidden, back = self.drive([{"toggle": "watched:root 2", "shown": False},
                                          {"toggle": "watched:root 2", "shown": True}])
        self.assertNotEqual(hidden["rows"], first["rows"])
        self.assertEqual(back["rows"], first["rows"])
        self.assertIn("0 events hidden", back["status"])

    def test_hiding_the_root_of_the_selected_event_clears_the_evidence_panel_and_another_root_keeps_it(self):
        seq = self.ROOT_1[0]
        selected, cleared = self.drive([{"select": seq}, {"toggle": "watched:root 1", "shown": False}])[1:]
        self.assertIn(f"Event {seq}", selected["evidence"])
        self.assertNotIn(f"Event {seq}", cleared["evidence"])
        kept = self.drive([{"select": seq}, {"toggle": "watched:root 2", "shown": False}])[-1]
        self.assertIn(f"Event {seq}", kept["evidence"])

    def test_a_replay_event_is_never_given_a_root_checkbox_even_if_it_carries_a_label(self):
        # Only rehashed or derived events with an evidence reference are watched artifacts.
        self.relabel({2: "root 1", 18: "root 1", 1: "root 1"})
        first = self.drive()[0]
        self.assertEqual(list(first["checkboxes"]), ["watched", "replay", "hook", "viewer"])

    def test_a_label_that_is_not_root_n_is_shown_nowhere_and_the_event_stays_in_the_watched_group(self):
        self.relabel({5: "/Users/someone/work", 6: "<b>root 1</b>", 7: "root 9" + "9" * 40, 8: 7})
        first = self.drive()[0]
        self.assertEqual(list(first["checkboxes"]), ["watched", "replay", "hook", "viewer"])
        self.assertIn(f"Watched artifacts ({len(self.ROOT_1) + len(self.ROOT_2) + len(self.UNLABELLED)} events)",
                      first["labels"])
        for private in ("/Users", "someone", "<b>"):
            self.assertNotIn(private, first["labels"])

    def test_a_model_without_roots_keeps_the_single_watched_checkbox(self):
        self.relabel({})
        first = self.drive()[0]
        self.assertEqual(list(first["checkboxes"]), ["watched", "replay", "hook", "viewer"])
        self.assertIn(f"Watched artifacts ({len(self.ROOT_1) + len(self.ROOT_2) + len(self.UNLABELLED)} events)",
                      first["labels"])

    def test_a_root_without_events_has_no_checkbox(self):
        original = self.model
        shrunk = json.loads(json.dumps(original))
        shrunk["elements"] = [e for e in shrunk["elements"] if e["seq"] not in self.ROOT_1]
        shrunk["table"] = [row for row in shrunk["table"] if row["seq"] not in self.ROOT_1]
        self.model = shrunk
        self.addCleanup(setattr, self, "model", original)
        self.assertNotIn("watched:root 1", self.drive()[0]["checkboxes"])


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
        return http_request(self.server.port, method, path, {"Cookie": cookie} if cookie else None, host=host)

    def test_every_first_party_file_is_served_unchanged_to_a_session(self):
        for path in SERVED_PATHS:
            with self.subTest(path=path):
                status, _, body = self.fetch(path, self.cookie)
                name = "index.html" if path == "/" else path[5:]
                self.assertEqual((status, body), (200, self.bundle[name]))

    def test_every_vendored_file_and_import_map_target_is_served_with_the_manifest_bytes(self):
        targets = import_map_targets(read("index.html"))
        self.assertTrue(targets)
        for path, digest in manifest()["files"].items():
            with self.subTest(path=path):
                status, response, body = self.fetch(f"/web/vendor/{path}", self.cookie)
                self.assertEqual(status, 200)
                self.assertEqual(hashlib.sha256(body).hexdigest(), digest)
                self.assertEqual(body, (VENDOR / path).read_bytes())
        for target in targets:
            with self.subTest(target=target):
                self.assertEqual(self.fetch(target, self.cookie)[0], 200)
                self.assertEqual(self.fetch(target)[0], 404)  # a session is still required

    def test_the_vendored_modules_are_served_as_javascript_under_the_page_policy(self):
        for target in import_map_targets(read("index.html")):
            with self.subTest(target=target):
                _, response, _ = self.fetch(target, self.cookie)
                self.assertTrue(response.getheader("Content-Type").startswith("text/javascript"))
                self.assert_contract_policy(response.getheader("Content-Security-Policy"), self.map_hash)

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
            ("GET", "/web/vendor/manifest.json", self.cookie, None, 404),  # the manifest does not list itself
            ("GET", "/web/vendor/three/unlisted.js", self.cookie, None, 404),
            ("GET", "/web/vendor/three/../../index.html", self.cookie, None, 404),
            ("GET", "/web/vendor/three/three.module.js", None, None, 404),  # no session
            ("GET", "/web/vendor/three/three.module.js", self.cookie, "evil.example", 403),
            ("POST", "/web/vendor/three/three.module.js", self.cookie, None, 405),
            ("GET", "/web/../index.html", self.cookie, None, 404),
            ("GET", "/web/manifest.json", self.cookie, None, 404),
            ("POST", "/", self.cookie, None, 405),
            ("GET", "/", self.cookie, "evil.example", 403),  # foreign Host
        )
        vendored = [("GET", f"/web/vendor/{path}", self.cookie, None, 200) for path in manifest()["files"]]
        cases = [("GET", path, self.cookie, None, 200) for path in SERVED_PATHS] + vendored + list(refusals)
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


class SequenceAxisStaticTests(unittest.TestCase):
    """Real-use bug 2026-11-04, read without running the scripts: the sequence-axis notice exists in every UI
    language, the timeline filters by position (not by stated time) and the scene is given the placed model."""

    def test_the_notice_and_the_axis_label_exist_in_every_language(self):
        table = strings_table()
        for language, entries in table.items():
            for key in ("tl.sequence.none", "tl.sequence.some", "tl.axisSequence"):
                with self.subTest(language=language, key=key):
                    self.assertTrue(entries.get(key))

    def test_the_timeline_never_hides_an_event_only_because_it_states_no_time(self):
        source = read("timeline.js")
        self.assertNotIn("timeKnown === false", source)
        self.assertIn("positioned(", source)

    def test_the_scene_and_the_timeline_draw_the_placed_model(self):
        source = read("loom.js")
        self.assertIn("scene.setModel(derived().placedModel)", source)
        self.assertIn("model: info.placedModel", source)
