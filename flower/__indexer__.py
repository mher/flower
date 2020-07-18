from __future__ import absolute_import
from __future__ import print_function

from flower.command import IndexerCommand
from flower.utils import bugreport


def main():
    try:
        flower = IndexerCommand()
        flower.execute_from_commandline()
    except:
        import sys
        print(bugreport(app=flower.app), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
