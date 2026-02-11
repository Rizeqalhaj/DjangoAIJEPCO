#!/usr/bin/env python
"""Interactive terminal chat with the KahrabaAI agent."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from agent.coach import EnergyDetective

PHONES = {
    "1": ("+962791000001", "Ahmed — residential family"),
    "2": ("+962791000002", "Sara — EV owner"),
    "3": ("+962791000003", "Abu Khalil — elderly couple"),
    "4": ("+962791000004", "Lina — home office"),
    "5": ("+962791000005", "Omar — wasteful teenager"),
}

print("\n=== KahrabaAI Terminal Chat ===\n")
print("Pick a subscriber:")
for k, (phone, desc) in PHONES.items():
    print(f"  {k}) {phone}  {desc}")
print()

choice = input("Enter number (1-5): ").strip()
if choice not in PHONES:
    print("Invalid choice.")
    sys.exit(1)

phone, desc = PHONES[choice]
print(f"\nChatting as {desc} ({phone})")
print("Type your messages. Press Ctrl+C or type 'quit' to exit.\n")

agent = EnergyDetective()

while True:
    try:
        msg = input("You: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
        break
    if not msg or msg.lower() == "quit":
        print("Bye!")
        break
    reply = agent.handle_message(phone, msg)
    print(f"Agent: {reply}\n")
