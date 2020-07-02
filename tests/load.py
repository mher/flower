import time
import random

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