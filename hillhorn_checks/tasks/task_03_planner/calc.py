# -*- coding: utf-8 -*- """CLI calc."""
import sys
if len(sys.argv) != 4:
    print("Usage: calc.py A op B"); sys.exit(1)
a, op, b = float(sys.argv[1]), sys.argv[2], float(sys.argv[3])
print({"+":a+b,"-":a-b,"*":a*b,"/":a/b}[op])
