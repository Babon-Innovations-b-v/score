"""The dashboard names no provider and imports none: no module under score/dashboard imports tools.*,
score.adapters or a cloud module, and no file names a provider; the list of names is built here from the
repository's own cloud backends and API kinds, so this test names none. The deploy templates hold only
<placeholders> for hosts and names."""
import ast
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
PACKAGE = REPO / "score/dashboard"
TEXT = (".py", ".html", ".css", ".js", ".yml", ".example", ".env", ".md", "")


def provider_words():
    """The stems of the cloud backends and cluster modules, and the words of the providers the models adapter's
    paid APIs name (score/adapters/models API)."""
    stems = {path.stem.split("_")[0] for folder in ("tools/props/cloud/backends", "tools/cloud/k8s/clusters")
             for path in (REPO / folder).glob("*.py") if not path.stem.startswith("_")}
    models = (REPO / "score/adapters/models/__init__.py").read_text()
    for provider in re.findall(r'"provider":\s*"([^"]+)"', models):
        stems |= {word for word in re.split(r"[^a-z]+", provider.lower()) if word not in ("api",)}
    return {stem for stem in stems if len(stem) > 3}


def cloud_modules():
    return {path.stem for folder in ("tools/props/cloud", "tools/cloud") for path in (REPO / folder).rglob("*.py")}


def files():
    return [path for path in PACKAGE.rglob("*") if path.is_file() and "__pycache__" not in path.parts
            and path.suffix in TEXT and path.name != "no_provider_test.py"]


def imported(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_no_module_imports_tools_the_adapters_or_a_cloud_module():
    cloud = cloud_modules()
    for path in PACKAGE.rglob("*.py"):
        for name in imported(path):
            assert not name.startswith(("tools", "score.adapters")), (path, name)
            assert name.split(".")[0] not in cloud, (path, name)


def test_no_file_names_a_provider():
    words = provider_words()
    assert words, "the provider list came out empty: the test would prove nothing"
    for path in files():
        text = path.read_text(errors="replace").lower()
        for word in words:
            assert not re.search(rf"\b{re.escape(word)}\b", text), (path, word)


def test_deploy_templates_hold_only_placeholders():
    for path in (PACKAGE / "deploy").iterdir():
        text = path.read_text()
        assert "TEMPLATE" in text, path
        for line in text.splitlines():
            if line.strip().startswith("#") or "=" not in line or not line.split("=", 1)[0].isupper():
                continue
            value = line.split("=", 1)[1].strip()
            assert value == "" or value.startswith("<") or re.fullmatch(r"[\w./:-]+", value) and not re.search(
                r"\.(org|com|net|nl|io)\b", value), (path, line)
