import time
import random

import os
import sys
tests_dir = os.path.dirname(__file__)
examples_dir = os.path.join(tests_dir, '../examples')
examples_dir = os.path.realpath(examples_dir)
sys.path.insert(0, examples_dir)

from tasks import add, sleep, error


def main():
    while True:
        for i in range(10):
            add.delay(i, i)
        sleep.delay(random.randint(1, i))
        error.delay("Something went wrong")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass