import sys
from colorama import Fore

PROGRAM_EXIT = True
PROGRAM_CONTINUE = False

class ErrorHandler:
    def __init__(self):
        pass

    @staticmethod
    def handle_error(e: Exception, message: str = "", exit_program: bool = False):
        sys.stderr.write(Fore.RED + f"An error occurred: {message}\n{e}\n")
        sys.stderr.write(Fore.RESET + "\n")
        sys.stderr.write("Please check the error message and try again.\n")

        if exit_program:
            sys.exit(1)
