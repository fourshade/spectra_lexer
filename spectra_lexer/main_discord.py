""" Main module for the Discord bot application. """

import sys

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.app_discord import build_app
from spectra_lexer.console import introspect
from spectra_lexer.discord.main import DiscordBot


def main() -> int:
    """ Run the application as a Discord bot. """
    opts = SpectraOptions("Run Spectra as a Discord bot.")
    opts.add("token", "", "Discord bot token (REQUIRED).")
    opts.add("command", "spectra", "!command string for Discord users.")
    spectra = Spectra(opts)
    log = spectra.logger.log
    log("Loading Discord bot...")
    app = build_app(spectra)
    if not opts.token:
        log("No token given. Opening test console...")
        return introspect(app)
    bot = DiscordBot(opts.token, log)
    bot.add_command(opts.command, app)
    log("Discord bot started.")
    return bot.run()


if __name__ == '__main__':
    sys.exit(main())
