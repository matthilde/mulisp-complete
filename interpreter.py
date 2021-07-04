#!/usr/bin/env python3
import main as cumiler
import sys, traceback

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: interpreter FILENAME")
    else:
        try:
            with open(sys.argv[1]) as f:
                prgm = f.read().split("\n")
        except IOError as e:
            print("Can't open file:", e)
        else:
            glob = cumiler.new_globals({})

            prgm = [x.strip() for x in prgm]
            prgmm = []
            tmp = ""
            for line in prgm:
                tmp += " " + line
                if tmp != "" and tmp.count('(') <= tmp.count(')'):
                    prgmm.append(tmp)
                    tmp = ""

            
            # Time to run this
            linenum = 0
            try:
                for ln, line in enumerate(prgmm):
                    linenum = ln
                    ps = cumiler.parse_lisp(line)
                    if ps == []: continue
                    cum = cumiler.cumiler(ps)
                    cumiler.eval_lisp(cum, glob)
            except Exception as e:
                print("!!! ERROR !!!")
                print(prgmm[linenum])
                print("-----------------------")
                print(traceback.format_exc())

