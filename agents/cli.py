#!/usr/bin/env python
"""
===============================================================================
  ULTIMATE BOT - AUTONOMOUS AGENT SYSTEM
===============================================================================

ONE COMMAND TO RULE THEM ALL:

    python -m agents.cli

That's it. The Ultimate Bot manages everything else.

===============================================================================
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===============================================================================
# COLORS
# ===============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    GOLD = '\033[38;5;220m'
    PURPLE = '\033[38;5;135m'
    ORANGE = '\033[38;5;208m'


def c(text, color):
    """Colorize text."""
    return f"{color}{text}{Colors.RESET}"


# ===============================================================================
# WELCOME SCREEN
# ===============================================================================

def print_welcome():
    """Print welcome screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

    # Use ASCII-safe characters for Windows console compatibility
    print("""
{c('+' + '=' * 70 + '+', Colors.CYAN)}
{c('|', Colors.CYAN)}                                                                      {c('|', Colors.CYAN)}
{c('|', Colors.CYAN)}   {c('ULTIMATE BOT', Colors.GOLD + Colors.BOLD)}                                                  {c('|', Colors.CYAN)}
{c('|', Colors.CYAN)}   {c('-----------------', Colors.GOLD)}                                                  {c('|', Colors.CYAN)}
{c('|', Colors.CYAN)}   {c('AUTONOMOUS AGENT SYSTEM', Colors.WHITE)}                                           {c('|', Colors.CYAN)}
{c('|', Colors.CYAN)}                                                                      {c('|', Colors.CYAN)}
{c('+' + '=' * 70 + '+', Colors.CYAN)}

{c('  Welcome, Creator!', Colors.WHITE)}

{c('  The Ultimate Bot is your substitute.', Colors.GRAY)}
{c('  It manages a team of expert bots that maintain your website 24/7.', Colors.GRAY)}

{c('  +--------------------------------------------------------+', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}                     {c('ULTIMATE BOT', Colors.GOLD + Colors.BOLD)}                        {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}                    {c('(Supreme Controller)', Colors.GRAY)}                       {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}                            {c('|', Colors.WHITE)}                               {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}          {c('+----------+------+-----+----------+', Colors.CYAN)}             {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}          {c('|', Colors.CYAN)}          {c('|', Colors.CYAN)}            {c('|', Colors.CYAN)}          {c('|', Colors.CYAN)}             {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}       {c('Fixer', Colors.GREEN)}    {c('Dev', Colors.BLUE)}      {c('Analyzer', Colors.YELLOW)}   {c('Security', Colors.RED)}    {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}       {c('Expert', Colors.GRAY)}     {c('Expert', Colors.GRAY)}       {c('Expert', Colors.GRAY)}       {c('Expert', Colors.GRAY)}       {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}          {c('|', Colors.CYAN)}          {c('|', Colors.CYAN)}            {c('|', Colors.CYAN)}          {c('|', Colors.CYAN)}             {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}       {c('Git', Colors.PURPLE)}     {c('Healer', Colors.ORANGE)}    {c('Tester', Colors.CYAN)}     {c('Deploy', Colors.GREEN)}     {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}       {c('Expert', Colors.GRAY)}     {c('Expert', Colors.GRAY)}       {c('Expert', Colors.GRAY)}       {c('Expert', Colors.GRAY)}       {c('|', Colors.PURPLE)}
{c('  |', Colors.PURPLE)}                                                              {c('|', Colors.PURPLE)}
{c('  +--------------------------------------------------------+', Colors.PURPLE)}

{c('  Each expert bot is specialized in their field.', Colors.WHITE)}
{c('  The Ultimate Bot evaluates their performance and coordinates them.', Colors.GRAY)}
""")


def print_starting():
    """Print starting message."""
    print("""
{c('  ------------------------------------------------------------------', Colors.GOLD)}

{c('  Starting Ultimate Bot...', Colors.GREEN + Colors.BOLD)}

{c('  The Ultimate Bot will now:', Colors.WHITE)}
{c('  - Scan your codebase for issues', Colors.GRAY)}
{c('  - Assign tasks to expert bots', Colors.GRAY)}
{c('  - Fix errors automatically', Colors.GRAY)}
{c('  - Commit and push to GitHub', Colors.GRAY)}
{c('  - Report any issues that need your attention', Colors.GRAY)}

{c('  Press Ctrl+C to stop.', Colors.YELLOW)}

{c('  ------------------------------------------------------------------', Colors.GOLD)}
""")


# ===============================================================================
# MAIN
# ===============================================================================

async def run_ultimate_bot():
    """Run the Ultimate Bot."""
    from agents.autonomous.ultimate_bot import get_ultimate_bot

    bot = get_ultimate_bot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()


def main():
    """
    Main entry point.

    Usage:
        python -m agents.cli           # Start Ultimate Bot
        python -m agents.cli --help    # Show help
    """
    # Check for help
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        print("""
{c('ULTIMATE BOT - Autonomous Agent System', Colors.GOLD + Colors.BOLD)}

{c('Usage:', Colors.WHITE)}
    python -m agents.cli              Start the Ultimate Bot
    python -m agents.cli --help       Show this help

{c('The Ultimate Bot:', Colors.WHITE)}
    - Manages all expert bots automatically
    - Scans, fixes, and improves your codebase
    - Commits and pushes to GitHub
    - Reports issues requiring your attention
    - Runs 24/7 as your substitute

{c('Expert Bots:', Colors.CYAN)}
    Fixer Expert      - Fixes code errors and bugs
    Developer Expert   - Writes new features and code
    Analyzer Expert    - Deep code analysis
    Security Expert    - Finds vulnerabilities
    Git Expert         - Version control management
    Healer Expert      - Auto-recovery from errors
    Tester Expert      - Runs tests
    Deployer Expert    - Handles deployments

{c('Just run:', Colors.GREEN)}
    python -m agents.cli

{c('And let the Ultimate Bot handle everything!', Colors.GRAY)}
""")
        return 0

    # Show welcome and start
    print_welcome()
    print_starting()

    # Run Ultimate Bot
    try:
        asyncio.run(run_ultimate_bot())
    except KeyboardInterrupt:
        print(f"\n{c('  Goodbye, Creator!', Colors.GOLD)}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
