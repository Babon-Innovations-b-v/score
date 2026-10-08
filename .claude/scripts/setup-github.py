#!/usr/bin/env python3
"""Create the GitHub-side state the loop reads: labels, and optionally the board.

    python3 .claude/scripts/setup-github.py [--board] [--dry-run]

"Use this template" copies files and nothing else, so a fresh repo starts with GitHub's
default labels and no project. The skills read both: `triage` moves an issue between the
state labels, `to-prd` stamps a category on every issue it creates, and `close` sets a
board column. This script puts them there, and writes what it discovered into
`.claude/project.json`, which is the one place repo, board and people are named.

Safe to re-run. A label that already exists is updated in place, and an existing board
(one whose number is already in project.json) is reused rather than duplicated.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / ".claude" / "project.json"

# The triage state machine and the two categories, exactly as the skills spell them.
LABELS = [
    ("PRD", "5319e7", "Epic: one module or workstream, with a definition of done"),
    ("vision", "c5def5", "Long-term vision PRD, separate from operational work"),
    ("bug", "d73a4a", "Something is broken"),
    ("enhancement", "a2eeef", "New feature or improvement"),
    ("needs-triage", "fbca04", "Waiting for the maintainer to evaluate"),
    ("needs-info", "d4c5f9", "Waiting on the reporter"),
    ("ready-for-agent", "0e8a16", "Fully specified, carries an agent brief"),
    ("ready-for-human", "1d76db", "Needs a human: judgment, access or design"),
    ("wontfix", "ffffff", "Will not be actioned"),
]

# Board columns. Order matters: it is the order they appear on the board.
STATUS_OPTIONS = [
    ("LowPriority", "GRAY", "Real, not now. The standing backlog PRDs live here permanently."),
    ("Not started", "GRAY", "Accepted, nobody has begun."),
    ("In Progress", "YELLOW", "Someone is working on it right now."),
    ("Review", "ORANGE", "Done by its author, waiting on a second pair of eyes."),
    ("Done", "GREEN", "Acceptance list genuinely met."),
]

DATE_FIELDS = ["Roadmap start", "Roadmap end"]


def run(args: list[str], *, check: bool = True) -> str:
    """Run a command and return stdout, exiting with the tool's own message on failure."""
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"{' '.join(args[:3])} failed:\n{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def graphql(query: str, **variables) -> dict:
    """Run a GraphQL query through gh and return its data block.

    The whole request goes in as one JSON body rather than as -f/-F pairs, because a
    variable that is a list of objects (the single-select options) cannot be expressed
    as a flag value: gh rejects it as "not a key-value object".
    """
    body = json.dumps({"query": query, "variables": variables})
    result = subprocess.run(
        ["gh", "api", "graphql", "--input", "-"], input=body, capture_output=True, text=True
    )
    payload = json.loads(result.stdout or "{}")
    if result.returncode != 0 and not payload:
        sys.exit(f"gh api graphql failed:\n{result.stderr.strip()}")
    if "errors" in payload:
        sys.exit(f"GraphQL failed: {json.dumps(payload['errors'])}")
    return payload["data"]


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")


def current_repo() -> tuple[str, str]:
    """The repo this checkout points at, as (owner/name, owner)."""
    raw = run(["gh", "repo", "view", "--json", "nameWithOwner,owner"])
    data = json.loads(raw)
    return data["nameWithOwner"], data["owner"]["login"]


def sync_labels(repo: str, dry_run: bool) -> None:
    existing = {
        label["name"]
        for label in json.loads(run(["gh", "label", "list", "--repo", repo, "--limit", "200", "--json", "name"]) or "[]")
    }
    for name, color, description in LABELS:
        verb = "update" if name in existing else "create"
        if dry_run:
            print(f"would {verb} label {name}")
            continue
        # `create --force` both creates and updates, so one call covers either case.
        run(["gh", "label", "create", name, "--repo", repo, "--color", color,
             "--description", description, "--force"])
        print(f"label {verb}d: {name}")


def project_fields(number: int, owner: str) -> list[dict]:
    raw = run(["gh", "project", "field-list", str(number), "--owner", owner, "--format", "json"])
    return json.loads(raw or "{}").get("fields", [])


def ensure_project(config: dict, repo: str, owner: str, dry_run: bool) -> None:
    number = config.get("project", {}).get("number") or 0
    project_owner = config.get("project", {}).get("owner") or owner

    if dry_run:
        print(f"would create a project on {project_owner} and link it to {repo}")
        return

    title = repo.split("/")[-1]
    if number:
        print(f"project #{number} already in project.json, reusing it")
    else:
        existing = json.loads(
            run(["gh", "project", "list", "--owner", project_owner, "--format", "json"]) or "{}"
        ).get("projects", [])
        match = next((p for p in existing if p["title"] == title and not p["closed"]), None)
        if match:
            number = match["number"]
            print(f"project #{number} already exists ({match['url']}), reusing it")
        else:
            created = json.loads(
                run(["gh", "project", "create", "--owner", project_owner, "--title", title, "--format", "json"])
            )
            number = created["number"]
            print(f"project created: #{number} {created['url']}")

    project_id = json.loads(
        run(["gh", "project", "view", str(number), "--owner", project_owner, "--format", "json"])
    )["id"]

    fields = {field["name"]: field for field in project_fields(number, project_owner)}

    status = fields.get("Status")
    wanted = [name for name, _, _ in STATUS_OPTIONS]
    if status is None:
        print("no Status field on this project; add one in the UI, then re-run")
    elif [option["name"] for option in status.get("options", [])] == wanted:
        print("Status columns already correct")
    else:
        options = [
            {"name": name, "color": color, "description": description}
            for name, color, description in STATUS_OPTIONS
        ]
        graphql(
            """mutation($f:ID!,$o:[ProjectV2SingleSelectFieldOptionInput!]!){
                 updateProjectV2Field(input:{fieldId:$f, singleSelectOptions:$o}){
                   projectV2Field{ ... on ProjectV2SingleSelectField { id } }
                 }
               }""",
            f=status["id"],
            o=options,
        )
        print("Status columns set: " + ", ".join(wanted))

    for name in DATE_FIELDS:
        if name in fields:
            print(f"date field already there: {name}")
            continue
        graphql(
            """mutation($p:ID!,$n:String!){
                 createProjectV2Field(input:{projectId:$p, dataType:DATE, name:$n}){
                   projectV2Field{ ... on ProjectV2Field { id } }
                 }
               }""",
            p=project_id,
            n=name,
        )
        print(f"date field created: {name}")

    areas = config.get("areas") or []
    if areas and "Area" not in fields:
        options = [{"name": area, "color": "BLUE", "description": area} for area in areas]
        graphql(
            """mutation($p:ID!,$o:[ProjectV2SingleSelectFieldOptionInput!]!){
                 createProjectV2Field(input:{projectId:$p, dataType:SINGLE_SELECT, name:"Area", singleSelectOptions:$o}){
                   projectV2Field{ ... on ProjectV2SingleSelectField { id } }
                 }
               }""",
            p=project_id,
            o=options,
        )
        print("Area field created: " + ", ".join(areas))

    run(["gh", "project", "link", str(number), "--owner", project_owner, "--repo", repo], check=False)
    config["project"] = {"number": number, "owner": project_owner}
    print(
        "\nOne thing this script cannot do: turn on the board's auto-add workflow "
        "(GitHub has no API for it). Open the project, Workflows, enable "
        '"Item added to repository". Until then to-prd and close add each issue '
        "themselves, which works but is one API call slower."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", action="store_true", help="also create the project board")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen, change nothing")
    args = parser.parse_args()

    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        sys.exit("gh is not logged in. Run: gh auth login")

    repo, owner = current_repo()
    config = load_config()
    if config.get("repo") and config["repo"] != repo:
        # "Use this template" copies project.json verbatim, so a fresh repo arrives
        # carrying the template's board number, backlog issue and people. Reusing any of
        # those would point this repo's skills at another repo's board, so drop them.
        print(f"config came from {config['repo']}; resetting board, backlog and people\n")
        config["project"] = {"number": 0, "owner": ""}
        config["backlog_prd"] = None
        config["people"] = {}
    config["repo"] = repo
    config["owner"] = owner
    if not config.get("people"):
        config["people"] = {owner: owner}

    print(f"repo: {repo}\n")
    sync_labels(repo, args.dry_run)

    if args.board:
        print()
        ensure_project(config, repo, owner, args.dry_run)

    if not args.dry_run:
        save_config(config)
        print(f"\nwrote {CONFIG_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
