#!/usr/bin/env python3
import main as cumiler
import sys, traceback

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: interpreter FILENAME")
    else:
        try:
            with open(sys.argv[1]) as f:
                prgm = f.read()
        except IOError as e:
            print("Can't open file:", e)
        else:
            glob = cumiler.new_globals({})

            cumiler.eval_lisp(
                cumiler.cumiler(
                    cumiler.parse_lisp(prgm),
                    glob
                )
            )