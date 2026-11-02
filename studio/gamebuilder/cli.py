"""Run one game build from the command line, on the same code the page uses: python -m studio.gamebuilder.cli --prompt "..." --prompt "..." [--kit kart] [--seed 7] [--size small] [--id NAME]. Prints the final board as JSON."""
import argparse
import json
import sys


def main(argv=None):
    import faulthandler, signal
    faulthandler.register(signal.SIGUSR1, all_threads=True)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prompt", action="append", required=True)
    ap.add_argument("--kit")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--size", default="medium")
    ap.add_argument("--difficulty", default="normal")
    ap.add_argument("--id")
    ap.add_argument("--image-want")
    a = ap.parse_args(argv)
    from studio import server  # noqa: F401  so World Kit's job bridge finds the studio's ComfyUI client
    from studio.gamebuilder import pipeline as P
    gid = a.id or P.new_id()
    state = P.Game(gid, a.prompt, {"kit": a.kit, "seed": a.seed, "size": a.size, "difficulty": a.difficulty}).run()
    print(json.dumps({k: state.get(k) for k in ("id", "title", "kit", "state", "error", "fallbacks", "sizes", "playtest")}, indent=1))
    return 0 if state.get("state") == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
