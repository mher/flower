from __future__ import absolute_import
from __future__ import print_function
import sys
from celery.bin.celery import main as _main, celery
from flower.command import indexer


def main():
    celery.add_command(indexer)
    sys.exit(_main())


if __name__ == "__main__":
    main()
