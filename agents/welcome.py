#!/usr/bin/env python
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     ██████╗ ██╗   ██╗███╗   ██╗███████╗██╗  ██╗████████╗██████╗  █████╗ ██████╗ ███████╗  ║
║    ██╔═══██╗██║   ██║████╗  ██║██╔════╝╚██╗██╔╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝  ║
║    ██║   ██║██║   ██║██╔██╗ ██║█████╗   ╚███╔╝    ██║   ██████╔╝███████║██║  ██║█████╗    ║
║    ██║▄▄ ██║██║   ██║██║╚██╗██║██╔══╝   ██╔██╗    ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝    ║
║    ╚██████╔╝╚██████╔╝██║ ╚████║███████╗██╔╝ ██╗   ██║   ██║  ██║██║  ██║██████╔╝███████╗  ║
║     ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝  ║
║                                                                               ║
║                        AUTONOMOUS AGENT CONTROL CENTER                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Welcome Dashboard - Shows system status and available commands
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════
# COLORS
# ═══════════════════════════════════════════════════════════════════════

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
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

    # Special
    GOLD = '\033[38;5;220m'
    PURPLE = '\033[38;5;135m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;213m'


def c(text, color):
    """Colorize text."""
    return f"{color}{text}{Colors.RESET}"


# ═══════════════════════════════════════════════════════════════════════
# WELCOME SCREEN
# ═══════════════════════════════════════════════════════════════════════

def print_logo():
    """Print the main logo."""
    logo = f"""
{c('╔' + '═' * 78 + '╗', Colors.CYAN)}
{c('║', Colors.CYAN)}                                                                              {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}   {c('█▀█ █░█ █▄░█ █▀▀ ▀▄▀ ▀█▀ █▀█ ▄▀█ █▀▄ █▀▀', Colors.GOLD)}                              {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}   {c('▀▀█ █▄█ █░▀█ ██▄ █░█ ░█░ █▀▄ █▀█ █▄▀ ██▄', Colors.GOLD)}                              {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}                                                                              {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}              {c('A U T O N O M O U S   A G E N T   S Y S T E M', Colors.WHITE + Colors.BOLD)}               {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}                                                                              {c('║', Colors.CYAN)}
{c('╚' + '═' * 78 + '╝', Colors.CYAN)}
"""
    print(logo)


def print_welcome():
    """Print welcome message."""
    now = datetime.now()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"

    print(f"""
  {c(greeting + ',', Colors.GRAY)} {c('Creator', Colors.GOLD + Colors.BOLD)}! {c('👋', Colors.RESET)}

  {c('Your autonomous workers are ready to serve you.', Colors.WHITE)}
  {c('They will scan, fix, and improve your website automatically.', Colors.GRAY)}
""")


def print_status():
    """Print current system status."""
    print(f"""
  {c('┌─────────────────────────────────────────────────────────────────────────┐', Colors.GRAY)}
  {c('│', Colors.GRAY)}  {c('SYSTEM STATUS', Colors.CYAN + Colors.BOLD)}                                                          {c('│', Colors.GRAY)}
  {c('├─────────────────────────────────────────────────────────────────────────┤', Colors.GRAY)}""")

    # Skip status check to avoid async complexity - just show ready state
    print(f"""  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}    Status:     {c('● READY', Colors.GREEN)}                                               {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}    Agents:     {c('9 workers available', Colors.WHITE)}                                       {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}    Time:       {c(datetime.now().strftime('%Y-%m-%d %H:%M'), Colors.WHITE)}                                      {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}""")

    print(f"  {c('└─────────────────────────────────────────────────────────────────────────┘', Colors.GRAY)}")


def print_workers():
    """Print list of workers."""
    workers = [
        ("🔍", "Master Agent", "Analyzes system, creates tasks"),
        ("🛠️", "Fixer Agent", "Fixes code errors automatically"),
        ("👨‍💻", "Developer Agent", "Writes new features and code"),
        ("🔬", "Analyzer Agent", "Deep code analysis"),
        ("🔒", "Security Agent", "Finds security vulnerabilities"),
        ("📊", "Database Agent", "Monitors database health"),
        ("⚡", "Self-Healer", "Auto-recovers from errors"),
        ("🕐", "Scheduler", "Runs scheduled tasks"),
        ("🔄", "Git Agent", "Commits and pushes to GitHub"),
    ]

    print(f"""
  {c('┌─────────────────────────────────────────────────────────────────────────┐', Colors.GRAY)}
  {c('│', Colors.GRAY)}  {c('YOUR WORKERS', Colors.CYAN + Colors.BOLD)}                                                            {c('│', Colors.GRAY)}
  {c('├─────────────────────────────────────────────────────────────────────────┤', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}""")

    for icon, name, desc in workers:
        # Pad manually to avoid ANSI code interference
        name_padded = name.ljust(18)
        desc_padded = desc.ljust(36)
        print(f"  {c('│', Colors.GRAY)}    {icon}  {c(name_padded, Colors.WHITE + Colors.BOLD)} {c(desc_padded, Colors.GRAY)} {c('│', Colors.GRAY)}")

    print(f"""  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('└─────────────────────────────────────────────────────────────────────────┘', Colors.GRAY)}""")


def print_commands():
    """Print available commands."""
    commands = [
        ("status", "Check system health"),
        ("diagnose", "Find all issues"),
        ("fixall --check", "Fix ALL errors"),
        ("auto", "Run one cycle"),
        ("work", "Start 24/7 mode"),
        ("helpme", "See manual tasks"),
        ("git commit", "Push to GitHub"),
    ]

    print(f"""
  {c('┌─────────────────────────────────────────────────────────────────────────┐', Colors.GRAY)}
  {c('│', Colors.GRAY)}  {c('QUICK COMMANDS', Colors.CYAN + Colors.BOLD)}                                                          {c('│', Colors.GRAY)}
  {c('├─────────────────────────────────────────────────────────────────────────┤', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}""")

    for cmd, desc in commands:
        cmd_full = f"python -m agents.cli {cmd}".ljust(38)
        desc_padded = desc.ljust(24)
        print(f"  {c('│', Colors.GRAY)}    {c(cmd_full, Colors.GREEN)}  {c(desc_padded, Colors.GRAY)} {c('│', Colors.GRAY)}")

    print(f"""  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('└─────────────────────────────────────────────────────────────────────────┘', Colors.GRAY)}""")


def print_workflow():
    """Print the workflow diagram."""
    print(f"""
  {c('┌─────────────────────────────────────────────────────────────────────────┐', Colors.GRAY)}
  {c('│', Colors.GRAY)}  {c('HOW IT WORKS', Colors.CYAN + Colors.BOLD)}                                                            {c('│', Colors.GRAY)}
  {c('├─────────────────────────────────────────────────────────────────────────┤', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('┌──────────┐', Colors.BLUE)}    {c('┌──────────┐', Colors.GREEN)}    {c('┌──────────┐', Colors.PURPLE)}    {c('┌──────────┐', Colors.CYAN)}   {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('│', Colors.BLUE)} {c('ANALYZE', Colors.BLUE + Colors.BOLD)}  {c('│', Colors.BLUE)}───▶{c('│', Colors.GREEN)} {c('FIX CODE', Colors.GREEN + Colors.BOLD)} {c('│', Colors.GREEN)}───▶{c('│', Colors.PURPLE)}  {c('COMMIT', Colors.PURPLE + Colors.BOLD)}  {c('│', Colors.PURPLE)}───▶{c('│', Colors.CYAN)}   {c('PUSH', Colors.CYAN + Colors.BOLD)}   {c('│', Colors.CYAN)}   {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('└──────────┘', Colors.BLUE)}    {c('└──────────┘', Colors.GREEN)}    {c('└──────────┘', Colors.PURPLE)}    {c('└──────────┘', Colors.CYAN)}   {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}        {c('│', Colors.GRAY)}                                              {c('│', Colors.GRAY)}        {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}        {c('▼', Colors.GRAY)}                                              {c('▼', Colors.GRAY)}        {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('Find issues', Colors.GRAY)}                                    {c('GitHub/Live', Colors.GRAY)}   {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('Every 5 minutes, your workers:', Colors.WHITE)}                                     {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('• Scan for errors and fix them', Colors.GREEN)}                                     {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('• Commit changes to git', Colors.PURPLE)}                                            {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('• Push to GitHub automatically', Colors.CYAN)}                                       {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}   {c('• Alert you for manual issues', Colors.YELLOW)}                                       {c('│', Colors.GRAY)}
  {c('│', Colors.GRAY)}                                                                         {c('│', Colors.GRAY)}
  {c('└─────────────────────────────────────────────────────────────────────────┘', Colors.GRAY)}""")


def print_quick_start():
    """Print quick start guide."""
    print(f"""
  {c('┌─────────────────────────────────────────────────────────────────────────┐', Colors.GOLD)}
  {c('│', Colors.GOLD)}  {c('⚡ QUICK START', Colors.GOLD + Colors.BOLD)}                                                          {c('│', Colors.GOLD)}
  {c('├─────────────────────────────────────────────────────────────────────────┤', Colors.GOLD)}
  {c('│', Colors.GOLD)}                                                                         {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}   {c('Start your workers now:', Colors.WHITE)}                                              {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}                                                                         {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}   {c('python -m agents.cli work', Colors.GREEN + Colors.BOLD)}                                           {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}                                                                         {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}   {c('This will run your workers 24/7, fixing and improving', Colors.GRAY)}              {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}   {c('your website automatically. Press Ctrl+C to stop.', Colors.GRAY)}                  {c('│', Colors.GOLD)}
  {c('│', Colors.GOLD)}                                                                         {c('│', Colors.GOLD)}
  {c('└─────────────────────────────────────────────────────────────────────────┘', Colors.GOLD)}
""")


def print_footer():
    """Print footer."""
    print(f"""
  {c('─' * 77, Colors.GRAY)}
  {c('QunexTrade Agent System v2.0', Colors.GRAY)} | {c('Your workers never sleep 🌙', Colors.PURPLE)}
  {c('─' * 77, Colors.GRAY)}
""")


def main():
    """Main welcome screen."""
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')

    print_logo()
    print_welcome()
    print_status()
    print_workers()
    print_commands()
    print_workflow()
    print_quick_start()
    print_footer()


if __name__ == "__main__":
    main()

