from __future__ import absolute_import
from __future__ import print_function

from flower.command import FlowerCommand


def main():
    try:
        flower = FlowerCommand()
        flower.execute_from_commandline()
    except:
        import sys
        import celery
        print(celery.bugreport(), file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
