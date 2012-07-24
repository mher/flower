from celery.bin.base import Command

from .__main__ import main


class Admin(Command):

    def run_from_argv(self, prog_name, argv=None):
        argv = self.setup_app_from_commandline(argv)
        return main(argv)
