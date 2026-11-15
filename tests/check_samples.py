"""Run the analyzer over every log in samples/ and check the verdicts.

    python tests/check_samples.py          # summary
    python tests/check_samples.py -v       # plus every stage
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import deck_uart_analyzer as a  # noqa: E402

# expected final verdict for each sample (all logs come from a working board)
EXPECTED = {
    "01_no_battery_no_controllers.txt": a.WARN,
    "02_no_display_with_ssd_cut.txt": a.WARN,
    "03_bare_board_no_ssd.txt": a.WARN,
    "04_battery_ssd_display.txt": a.WARN,  # no controller board
    "05_full_assembly_cut.txt": a.OK,
    "06_full_assembly_battery_then_charger.txt": a.OK,
}


def run(path, verbose=False):
    an = a.Analyzer("en")
    with open(path, encoding="latin-1") as f:
        for line in f.read().splitlines():
            if line.strip():
                an.feed(line)
    an.check_hang(0, final=True)
    if verbose:
        for key, *_ in a.STAGES:
            lvl, info = an.stages[key][:2]
            print(f"    {key:10} {lvl or '-':5} {info or ''}")
    return an.verdict()


def main():
    verbose = "-v" in sys.argv
    sdir = os.path.join(ROOT, "samples")
    failed = 0
    for name in sorted(os.listdir(sdir)):
        if not name.endswith(".txt") or name.upper().startswith("LICENSE"):
            continue
        got = run(os.path.join(sdir, name), verbose)
        exp = EXPECTED.get(name)
        ok = exp is None or got == exp
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:45} verdict={got} expected={exp}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
