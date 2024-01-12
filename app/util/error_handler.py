import sys
from colorama import Fore
from urllib.error import HTTPError

PROGRAM_EXIT = True
PROGRAM_CONTINUE = False

class ErrorHandler:
    @staticmethod
    def handle_error(e: Exception, message: str = "", exit_program: bool = False):
        # 特定のHTTPErrorをチェックして、404の場合はカスタムメッセージを表示
        if isinstance(e, HTTPError):
            if e.code == 404:
                sys.stderr.write(Fore.RED + f"Error: {e.code} - {e.reason}, Target article doesn't exist.\n")
            else:
                sys.stderr.write(Fore.RED + f"An HTTP error occurred: {e.code} - {e.reason}\n")
        else:
            sys.stderr.write(Fore.RED + f"An error occurred: {message}\n{e}\n")

        sys.stderr.write(Fore.RESET + "\n")
        sys.stderr.write("Please check the error message and try again.\n")

        if exit_program:
            sys.exit(1)
