#!/usr/bin/env python
"""
🤖👑 ULTIMATE BOT - Welcome Screen
Just run: python -m agents.cli
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    GOLD = '\033[38;5;220m'
    PURPLE = '\033[38;5;135m'
    ORANGE = '\033[38;5;208m'
    BLUE = '\033[94m'


def c(text, color):
    return f"{color}{text}{Colors.RESET}"


def main():
    """Show welcome screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

    now = datetime.now()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"

    print("""
{c('╔' + '═' * 70 + '╗', Colors.CYAN)}
{c('║', Colors.CYAN)}                                                                      {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}   {c('🤖👑 ULTIMATE BOT', Colors.GOLD + Colors.BOLD)}                                                  {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}   {c('━━━━━━━━━━━━━━━━━', Colors.GOLD)}                                                  {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}   {c('AUTONOMOUS AGENT SYSTEM', Colors.WHITE)}                                           {c('║', Colors.CYAN)}
{c('║', Colors.CYAN)}                                                                      {c('║', Colors.CYAN)}
{c('╚' + '═' * 70 + '╝', Colors.CYAN)}

  {c(greeting + ',', Colors.GRAY)} {c('Creator', Colors.GOLD + Colors.BOLD)}! {c('👋', Colors.RESET)}

  {c('The Ultimate Bot is ready to manage your website.', Colors.WHITE)}


{c('  ┌────────────────────────────────────────────────────────────────┐', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}                                                                  {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}                  {c('🤖👑 ULTIMATE BOT', Colors.GOLD + Colors.BOLD)}                           {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}                  {c('(Your Substitute)', Colors.GRAY)}                           {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}                         {c('│', Colors.WHITE)}                                    {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}       {c('┌─────────────────┼─────────────────┐', Colors.CYAN)}              {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}       {c('│', Colors.CYAN)}                 {c('│', Colors.CYAN)}                 {c('│', Colors.CYAN)}              {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}   {c('🛠️ Fixer', Colors.GREEN)}         {c('👨‍💻 Dev', Colors.BLUE)}          {c('🔬 Analyzer', Colors.YELLOW)}        {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}   {c('Expert', Colors.GRAY)}          {c('Expert', Colors.GRAY)}           {c('Expert', Colors.GRAY)}            {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}       {c('│', Colors.CYAN)}                 {c('│', Colors.CYAN)}                 {c('│', Colors.CYAN)}              {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}   {c('🔒 Security', Colors.RED)}      {c('🔄 Git', Colors.PURPLE)}           {c('⚡ Healer', Colors.ORANGE)}          {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}   {c('Expert', Colors.GRAY)}          {c('Expert', Colors.GRAY)}           {c('Expert', Colors.GRAY)}            {c('│', Colors.PURPLE)}
{c('  │', Colors.PURPLE)}                                                                  {c('│', Colors.PURPLE)}
{c('  └────────────────────────────────────────────────────────────────┘', Colors.PURPLE)}


{c('  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.GOLD)}

{c('  Just run this one command:', Colors.WHITE)}

{c('    python -m agents.cli', Colors.GREEN + Colors.BOLD)}

{c('  The Ultimate Bot will:', Colors.WHITE)}
{c('  • 🛠️  Scan and fix errors automatically', Colors.GRAY)}
{c('  • 🔄 Commit and push to GitHub', Colors.GRAY)}
{c('  • 📊 Evaluate and manage all expert bots', Colors.GRAY)}
{c('  • 💬 Coordinate experts through communication', Colors.GRAY)}
{c('  • 🧠 Learn from past fixes (gets smarter!)', Colors.GRAY)}
{c('  • 🏆 Run expert competition for better performance', Colors.GRAY)}
{c('  • 📋 Generate daily reports', Colors.GRAY)}
{c('  • ⏪ Auto-rollback on critical failures', Colors.GRAY)}
{c('  • 🚨 Alert you for urgent issues', Colors.GRAY)}

{c('  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', Colors.GOLD)}
""")


if __name__ == "__main__":
    main()
