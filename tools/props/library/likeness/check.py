"""The look-alike check over a list of surfaces (#155): each surface's maps fitted to a recipe (fit.py), the map
material and the recipe rendered side by side on this PC's card (inside/likeness.py, one Blender for every surface,
through the card queue), measured (measure.py) and the failing ones refined and rendered again, at most ROUNDS
renders a surface. Each surface's result is its fitted recipe and its likeness block.

    python3 tools/props/library/likeness/check.py <surface address> ... --out <folder>
        [--algorithm algorithm/surface_recipes@N] [--size 256] [--samples 64] [--rounds 6]

A surface's maps are the files its surface.json `maps` lists (else every texture file of its entry), each by its
role (fit.roles), fetched through the library (tools/library/library_files.py); its tile size is surface.json's
`tile_metres`, else TILE_METRES (said in its result as assumed). The recipe algorithm a likeness names is --algorithm,
else the library index's newest algorithm/surface_recipes. Writes <out>/<surface id>@<version>/likeness.json
({"address", "recipe": {"recipe", "settings", "wear_levels"}, "likeness": {"measures", "pass", "algorithm"},
"rounds", "family_from", "tile_metres_from"}) and <out>/summary.json, and prints one summary line. The pictures stay
in <out>: a map's render is an adaptation of the set's own material and is never stored in the library.

A run over many surfaces takes minutes to hours: start it detached (tools/cloud/detached.py), never in the
foreground.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(REPO), str(REPO / "tools/library")]
import fit  # noqa: E402
import library_files  # noqa: E402
import measure  # noqa: E402

from score import library  # noqa: E402

SCRIPT = HERE.parent / "inside/likeness.py"
RECIPE_ALGORITHM = "algorithm/surface_recipes"
TILE_METRES = 1.0
ROUNDS = 6
SIZE = 256
SAMPLES = 64
SEED = 0
VIEWS = ("overview", "close")
# The Blender run's limit, its wait for the card not counted: a surface's pair takes seconds.
SECONDS_A_SURFACE = 60


class CheckFailed(RuntimeError):
    """A surface the check could not fit or render (its maps missing, the Blender run failed)."""


def address_parts(address):
    """(kind, id, version) of `<kind>/<id>@<version>`."""
    kind, rest = address.split("/", 1)
    entry_id, version = rest.rsplit("@", 1)
    return kind, entry_id, int(version)


def fetched(address, name):
    """One of the entry's files on disk, through the library; CheckFailed when the library does not hold it."""
    found = library_files.resolve(library_files.reference(address, name))
    if found is None:
        raise CheckFailed(f"{address}: the library holds no {name}")
    return str(found)


def surface_maps(root, address):
    """The surface's maps {role: path} and (tile metres, where they came from)."""
    record = library.entry(root, *address_parts(address))
    described = {}
    if "surface.json" in record["files"]:
        described = json.loads(pathlib.Path(fetched(address, "surface.json")).read_text())
    names = described.get("maps") or [name for name, about in record["files"].items() if about.get("role") == "texture"]
    found = fit.roles(names)
    if "albedo" not in found:
        raise CheckFailed(f"{address}: no albedo map among {names}")
    tile = (described["tile_metres"], "surface.json") if "tile_metres" in described else (TILE_METRES, "assumed")
    return {role: fetched(address, name) for role, name in found.items()}, tile


def newest_recipe_algorithm(root):
    """The library index's newest version of the recipe algorithm."""
    versions = [address_parts(row["address"])[2] for row in library.index(root, "algorithm")["entries"]
                if row["address"].startswith(RECIPE_ALGORITHM + "@")]
    if not versions:
        raise CheckFailed(f"the library's index holds no {RECIPE_ALGORITHM}: name one with --algorithm")
    return f"{RECIPE_ALGORITHM}@{max(versions)}"


def folder_name(address):
    """The surface's folder under the run's: `<id>@<version>`."""
    return address.split("/", 1)[1]


def render_round(out, pairs, size, samples):
    """One Blender over every pair through the card queue; CheckFailed with the log's tail when it fails."""
    from score.stages.place_build import render
    job = out / "job.json"
    job.write_text(json.dumps({"out": str(out), "size": size, "samples": samples, "seed": SEED, "pairs": pairs},
                              indent=1))
    log = out / "blender.log"
    command = render.queued("likeness", SCRIPT, [str(job)], seconds=SECONDS_A_SURFACE * len(pairs))
    with log.open("a") as written:
        done = subprocess.run(command, stdout=written, stderr=subprocess.STDOUT, cwd=REPO)
    if done.returncode:
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise CheckFailed(f"the likeness Blender exited {done.returncode}, log {log}: {tail}")


def views_of(out, name):
    """A pair's measures, view by view, from its pictures."""
    folder = out / name
    return {view: measure.view_measures(folder / f"map-{view}.png", folder / f"recipe-{view}.png") for view in VIEWS}


def checked(addresses, out, algorithm, size, samples, rounds, method=fit.METHOD):
    """Every surface fitted, rendered and refined for at most `rounds` renders: {address: result}; a surface whose
    maps the library does not hold is a result naming the error, never rendered."""
    root = library_files.settings()["SCORE_LIB_ROOT"]
    algorithm = algorithm or newest_recipe_algorithm(root)
    wear_levels = json.loads(pathlib.Path(method).read_text())["wear_levels"]
    open_pairs, results = {}, {}
    for address in addresses:
        try:
            maps, (tile, tile_from) = surface_maps(root, address)
        except CheckFailed as missing:
            results[address] = {"address": address, "error": str(missing), "rounds": 0}
            continue
        made = fit.fitted(address_parts(address)[1], maps, tile, method)
        open_pairs[address] = {"name": folder_name(address), "maps": maps, "tile_metres": tile,
                               "recipe": made["recipe"], "map": True}
        results[address] = {"address": address, "family_from": made["family_from"], "tile_metres_from": tile_from,
                            "statistics": made["statistics"], "rounds": 0}
    for _ in range(rounds):
        if not open_pairs:
            break
        render_round(out, list(open_pairs.values()), size, samples)
        for address, pair in list(open_pairs.items()):
            views = views_of(out, pair["name"])
            verdict = measure.likeness(views, algorithm)
            results[address].update(rounds=results[address]["rounds"] + 1, likeness=verdict,
                                    recipe=recipe_block(pair["recipe"], wear_levels))
            if verdict["pass"]:
                del open_pairs[address]
            else:
                pair.update(recipe=measure.refined(pair["recipe"], views), map=False)
    return results


def recipe_block(spec, wear_levels):
    """The fitted recipe as a surface's record holds it: its family, its settings and the wear levels it is drawn
    at."""
    return {"recipe": spec["recipe"], "settings": {key: value for key, value in spec.items() if key != "recipe"},
            "wear_levels": wear_levels}


def written(results, out):
    """Each surface's likeness.json and the run's summary.json; the summary line."""
    for address, result in results.items():
        folder = out / folder_name(address)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "likeness.json").write_text(json.dumps(result, indent=1))
    passed = sorted(address for address, result in results.items() if result.get("likeness", {}).get("pass"))
    failed = sorted(set(results) - set(passed))
    unread = sorted(address for address, result in results.items() if "error" in result)
    (out / "summary.json").write_text(json.dumps({"passed": passed, "failed": failed, "unread": unread}, indent=1))
    renders = sum(result["rounds"] for result in results.values())
    return (f"likeness: {len(results)} surfaces, {len(passed)} pass, {len(failed)} fail (their recipe a written gap), "
            f"{len(unread)} of them unread, {renders} renders; {out / 'summary.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("addresses", nargs="+")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--algorithm")
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--samples", type=int, default=SAMPLES)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    arguments = parser.parse_args()
    arguments.out.mkdir(parents=True, exist_ok=True)
    results = checked(arguments.addresses, arguments.out.resolve(), arguments.algorithm, arguments.size,
                      arguments.samples, arguments.rounds)
    print(written(results, arguments.out.resolve()))


if __name__ == "__main__":
    main()
