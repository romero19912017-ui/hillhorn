# -*- coding: utf-8 -*- """Bye utility."""
import sys
def bye(name):
    return f"Bye, {name}!"
if __name__ == "__main__":
    print(bye(sys.argv[1] if len(sys.argv) > 1 else "World"))
