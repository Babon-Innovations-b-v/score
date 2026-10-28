"""The conductor's commands (score/conductor/__init__.py has the package's map).

    python -m score.conductor health [--write]   # the health as JSON, or written to $PROPS_HOME/health.json
    python -m score.conductor size               # one pass of the size timer: grow, shrink or nothing
    python -m score.conductor dry                # the free end-to-end check: one line, its detail in a file
    python -m score.conductor logs [--lines N]   # logs.tails: run logs, fault reports, unit journals, boot logs, as text
    python -m score.conductor disk               # disk.report: free room and the biggest folders, the rest in a file
    python -m score.conductor clean-frozen       # disk.clean: remove the frozen copies no run needs, what it freed
    python -m score.conductor clean-cache [--making-only]  # disk.clean_cache: checkouts relinked, the cache cleared
    python -m score.conductor relink-pixal       # disk.relink_pixal: work/pixal's stored files made links, one line
    python -m score.conductor score-lib status|pull  # library_checkout: score_lib's checkout against origin, one line
    python -m score.conductor offload-pixal      # disk.offload_pixal: takes into the library, freed once read back
"""
import argparse
import json
import sys

from score import conductor


def main(argv=None):
    parser = argparse.ArgumentParser(prog="score.conductor", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health").add_argument("--write", action="store_true", help=f"write {conductor.HEALTH}")
    commands.add_parser("size")
    commands.add_parser("dry")
    commands.add_parser("logs").add_argument("--lines", type=int, default=40, help="the last lines of each")
    commands.add_parser("disk")
    commands.add_parser("clean-frozen")
    commands.add_parser("clean-cache").add_argument("--making-only", action="store_true",
                                                    help="only the orphaned makes (the sync pass's sweep)")
    commands.add_parser("relink-pixal")
    commands.add_parser("score-lib").add_argument("action", choices=("status", "pull"))
    commands.add_parser("offload-pixal")
    options = parser.parse_args(argv)
    conductor.apply_free_only()
    if options.command == "health":
        from score.conductor import health
        found = health.read()
        print(f"health: written {health.write(found)}" if options.write else json.dumps(found, indent=1))
    elif options.command == "logs":
        from score.conductor import logs
        for name, lines in logs.tails(options.lines).items():
            print("\n".join([f"== {name}", *lines]))
    elif options.command == "disk":
        from score.conductor import disk
        summary, biggest = disk.report()
        print("\n".join([summary, *biggest]))
    elif options.command == "clean-frozen":
        clean_frozen()
    elif options.command == "clean-cache":
        clean_cache(options.making_only)
    elif options.command == "relink-pixal":
        relink_pixal()
    elif options.command == "score-lib":
        score_lib(options.action)
    elif options.command == "offload-pixal":
        offload_pixal()
    elif options.command == "size":
        from score.conductor import size
        size.tick()
    else:
        from score.conductor import dry
        with conductor.holding("dry"):
            line, code = dry.start()
        print(line, flush=True)
        sys.exit(code)


def clean_frozen():
    """disk.clean, its summary line last; exit 1 when it cannot tell which copies are dead or one failed."""
    from score.conductor import disk
    try:
        done = disk.clean()
    except disk.Unprovable as why:
        print(f"clean-frozen: refused, nothing removed: {why}", flush=True)
        sys.exit(1)
    print(f"clean-frozen: removed {len(done['removed'])}, kept {len(done['kept'])}, failed {len(done['failed'])}; "
          f"freed {done['freed_gb']} GB, {disk.free_gb():.1f} GB free", flush=True)
    sys.exit(1 if done["failed"] else 0)


def clean_cache(making_only):
    """disk.clean_cache (making/ alone with `making_only`), its summary line last; exit 1 when refused."""
    from score.conductor import disk
    try:
        done = disk.clean_cache(names=("making",) if making_only else tuple(disk.CLEARED))
    except disk.Unprovable as why:
        done = {"refused": str(why)}
    relinked = f"checkouts relinked, {done.get('relinked_gb', 0.0)} GB of copies freed"
    if done["refused"]:
        print(f"clean-cache: {relinked}; refused, nothing removed: {done['refused']}", flush=True)
        sys.exit(1)
    print(f"clean-cache: {relinked}; removed {', '.join(done['removed']) or 'nothing'}; freed {done['freed_gb']} GB, "
          f"{disk.free_gb():.1f} GB free", flush=True)


def relink_pixal():
    """disk.relink_pixal in one summary line: files relinked, GB freed, files kept and why."""
    from score.conductor import disk
    done = disk.relink_pixal()
    kept = ", ".join(f"{count} {why}" for why, count in sorted(done["kept"].items())) or "none"
    print(f"relink-pixal: relinked {done['relinked']} files, freed {done['freed_gb']} GB; kept: {kept}; "
          f"{disk.free_gb():.1f} GB free", flush=True)


def score_lib(action):
    """library_checkout's status or pull in one summary line, then what it lists (all of it in a file past LISTED);
    exit 1 when there is no checkout, the fetch failed or the pull refused."""
    from score.conductor import library_checkout
    from score.stages.library import backend
    root = backend.settings().get("SCORE_LIB_ROOT")
    if not root:
        print(f"score-lib {action}: no score_lib checkout here (SCORE_LIB_ROOT)", flush=True)
        sys.exit(1)
    if action == "pull":
        found, refusal = library_checkout.pull(root)
        moved = f"fast-forwarded {found['behind']} commits" if found["behind"] else "up to date"
        line = (f"score-lib pull: refused, nothing moved: {refusal}" if refusal else
                f"score-lib pull: {moved}, HEAD {library_checkout.head(root)}")
    else:
        found = library_checkout.status(root)
        refusal = found["fetch"]
        line = (f"score-lib status: HEAD {found['head']}; {found['upstream'] or 'no upstream'} ahead {found['ahead']} "
                f"behind {found['behind']}; {len(found['changes'])} local changes; last push "
                f"{found['last_push'] or 'none in the reflog'} (a failed push is not logged)"
                + (f"; the fetch failed, counts as of the last fetch: {found['fetch']}" if found["fetch"] else ""))
    listed = ([f"local change: {item}" for item in found["changes"]]
              + [f"local commit: {item}" for item in found["local_commits"]]
              + [f"incoming: {item}" for item in found["incoming"]])
    print("\n".join([line, *listed[:library_checkout.LISTED]]), flush=True)
    if len(listed) > library_checkout.LISTED:
        detail = conductor.HOME / "score-lib.txt"
        detail.parent.mkdir(parents=True, exist_ok=True)
        detail.write_text("\n".join([line, *listed]) + "\n")
        print(f"... {len(listed) - library_checkout.LISTED} more in {detail}", flush=True)
    sys.exit(1 if refusal else 0)
def offload_pixal():
    """disk.offload_pixal in one summary line: takes freed, GB freed, takes kept and why; exit 1 when refused."""
    from score.conductor import disk
    done = disk.offload_pixal()
    if done["refused"]:
        print(f"offload-pixal: refused, nothing freed: {done['refused']}", flush=True)
    kept = ", ".join(f"{len(takes)} {why}" for why, takes in sorted(done["kept"].items())) or "none"
    print(f"offload-pixal: freed {done['freed']} takes, {done['freed_gb']} GB; kept: {kept}; "
          f"{disk.free_gb():.1f} GB free", flush=True)


if __name__ == "__main__":
    main()
