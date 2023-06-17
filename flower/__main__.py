import sys
from celery.bin.celery import main as _main, celery
from flower.command import flower


def main():
    celery.add_command(flower)
    sys.exit(_main())


if __name__ == "__main__":
    main()
