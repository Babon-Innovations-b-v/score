"""Checks for the Scaleway backend's container path (registry, object_store and the runtime key), with every `scw`
call stubbed: nothing is made or read on the provider.

Run: .venv/bin/python tools/props/cloud/backends/scaleway_test.py   (make tests runs it)
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scaleway  # noqa: E402

OURS = "project-ours"
OTHER = "project-other"


class FakeScw:
    """Answers `scw` calls from a table of (first three arguments) -> answer, recording every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, *arguments):
        self.calls.append(arguments)
        if arguments[:3] == ("secret", "version", "create"):
            data = next(argument for argument in arguments if argument.startswith("data=@"))
            self.stored = pathlib.Path(data[len("data=@"):]).read_text()
        return self.answers.get(arguments[:3])

    def made(self, *head):
        return [call for call in self.calls if call[:len(head)] == head]


def with_fake(answers, check):
    """Run `check(fake)` with the backend's scw, account, secret and bucket calls stubbed."""
    kept = scaleway.scw, scaleway.account, scaleway.secret, scaleway.make_bucket
    fake = FakeScw(answers)
    scaleway.scw, scaleway.account = fake, lambda: OURS
    scaleway.secret = lambda name: json.dumps({"access_key": "AK", "secret_key": "SK"})
    scaleway.make_bucket = lambda store: fake.calls.append(("bucket", store["bucket"]))
    try:
        check(fake)
    finally:
        scaleway.scw, scaleway.account, scaleway.secret, scaleway.make_bucket = kept


def key_secret(project):
    return {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": project}]}


def test_an_existing_private_namespace_of_ours_is_used():
    answers = {**key_secret(OURS), ("registry", "namespace", "list"): [
        {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS, "is_public": False, "endpoint": "rg/ours"}]}

    def check(fake):
        assert scaleway.registry() == {"endpoint": "rg/ours", "username": "nologin", "password": "SK"}
        assert not fake.made("registry", "namespace", "create")
    with_fake(answers, check)


def test_a_namespace_of_another_project_is_never_taken():
    answers = {**key_secret(OURS),
               ("registry", "namespace", "list"): [
                   {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OTHER, "is_public": False, "endpoint": "rg/x"}],
               ("registry", "namespace", "create"): {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS,
                                                     "is_public": False, "endpoint": "rg/new"}}

    def check(fake):
        assert scaleway.registry()["endpoint"] == "rg/new"
        made = fake.made("registry", "namespace", "create")
        assert len(made) == 1 and f"project-id={OURS}" in made[0] and "is-public=false" in made[0]
    with_fake(answers, check)


def test_a_public_namespace_is_refused():
    answers = {**key_secret(OURS), ("registry", "namespace", "list"): [
        {"name": scaleway.REGISTRY_NAMESPACE, "project_id": OURS, "is_public": True, "endpoint": "rg/ours"}]}

    def check(fake):
        try:
            scaleway.registry()
        except SystemExit as refusal:
            assert "public" in str(refusal)
        else:
            raise AssertionError("a public namespace was taken")
    with_fake(answers, check)


def test_the_object_store_names_its_bucket_and_makes_it_once():
    def check(fake):
        store = scaleway.object_store()
        assert store == {"endpoint": "https://s3.fr-par.scw.cloud", "region": "fr-par", "bucket": scaleway.BUCKET,
                         "access_key": "AK", "secret_key": "SK"}
        assert ("bucket", scaleway.BUCKET) in fake.calls
    with_fake(key_secret(OURS), check)


def test_a_missing_key_is_made_scoped_to_the_project_and_kept_only_in_the_secret():
    answers = {("secret", "secret", "list"): [{"name": scaleway.RUNTIME_KEY_SECRET, "project_id": OTHER}],
               ("iam", "application", "list"): [],
               ("iam", "application", "create"): {"id": "app"},
               ("iam", "policy", "list"): [],
               ("iam", "api-key", "create"): {"access_key": "AK2", "secret_key": "SK2"},
               ("secret", "secret", "create"): {"id": "held"}}

    def check(fake):
        scaleway.runtime_key(OURS)
        policy = fake.made("iam", "policy", "create")[0]
        assert f"rules.0.project-ids.0={OURS}" in policy and "application-id=app" in policy
        assert {argument.split("=", 1)[1] for argument in policy if ".permission-set-names." in argument} == set(
            scaleway.RUNTIME_PERMISSIONS)
        assert f"default-project-id={OURS}" in fake.made("iam", "api-key", "create")[0]
        assert f"project-id={OURS}" in fake.made("secret", "secret", "create")[0]
        assert json.loads(fake.stored) == {"access_key": "AK2", "secret_key": "SK2"}
        assert not any("SK2" in argument for call in fake.calls for argument in call)
    with_fake(answers, check)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("scaleway_test: ok")
