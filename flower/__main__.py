from __future__ import absolute_import

from flower.command import FlowerCommand


def main():
    flower = FlowerCommand()
    flower.execute_from_commandline()


if __name__ == "__main__":
    main()
