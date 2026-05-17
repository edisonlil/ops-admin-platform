"""
Interactive selectors for ops-cli.
"""
from __future__ import annotations

import sys
from typing import List, Optional

# Try to use readline for better terminal experience
try:
    import readline

    def complete(text: str, state: int) -> Optional[str]:
        matches = [x for x in available_items if x.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None
except ImportError:
    readline = None

available_items: List[str] = []


class Selector:
    """Interactive selector with keyboard navigation."""

    def __init__(self, items: List[str], title: str = "Select an option:"):
        self.items = items
        self.title = title
        self.selected: List[int] = []
        self.current = 0

    def setup_readline(self) -> None:
        """Setup readline completion."""
        global available_items
        available_items = self.items
        if readline:
            readline.parse_and_bind("tab: complete")
            readline.set_completer(complete)

    def restore_readline(self) -> None:
        """Restore readline."""
        if readline:
            readline.set_completer(lambda text, state: None)

    def display(self) -> None:
        """Display the current state."""
        # Clear screen (simple approach)
        print("\033[2J\033[H", end="")  # Clear screen
        print("\n" + "=" * 50)
        print(self.title)
        print("=" * 50)

        for i, item in enumerate(self.items):
            prefix = "[ ]"
            if i in self.selected:
                prefix = "[x]"
            elif i == self.current:
                prefix = "[>]"

            marker = " " if i != self.current else ">"
            print(f"  {marker} {prefix} {item}")

        print("-" * 50)
        print("Navigation: ↑/↓ = move, SPACE = select, ENTER = confirm, Q = quit")

    def select_single(self) -> Optional[str]:
        """Select a single item (dropdown style)."""
        self.setup_readline()
        try:
            while True:
                self.display()
                key = self._get_key()

                if key == "up":
                    self.current = max(0, self.current - 1)
                elif key == "down":
                    self.current = min(len(self.items) - 1, self.current + 1)
                elif key == "enter":
                    self.restore_readline()
                    return self.items[self.current]
                elif key == "q":
                    self.restore_readline()
                    return None
        finally:
            self.restore_readline()

    def select_multiple(self) -> Optional[List[str]]:
        """Select multiple items (checkbox style)."""
        self.selected = []
        self.setup_readline()
        try:
            while True:
                self.display()
                key = self._get_key()

                if key == "up":
                    self.current = max(0, self.current - 1)
                elif key == "down":
                    self.current = min(len(self.items) - 1, self.current + 1)
                elif key == "space":
                    if self.current in self.selected:
                        self.selected.remove(self.current)
                    else:
                        self.selected.append(self.current)
                elif key == "enter":
                    self.restore_readline()
                    return [self.items[i] for i in sorted(self.selected)]
                elif key == "q":
                    self.restore_readline()
                    return None
        finally:
            self.restore_readline()

    def _get_key(self) -> str:
        """Get a key press."""
        try:
            import tty
            import termios

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)

                if ch == "\x1b":  # Escape sequence
                    sys.stdin.read(1)  # [
                    ch = sys.stdin.read(1)
                    if ch == "A":
                        return "up"
                    elif ch == "B":
                        return "down"
                    elif ch == "C":
                        return "right"
                    elif ch == "D":
                        return "left"
                elif ch == " ":
                    return "space"
                elif ch == "\r" or ch == "\n":
                    return "enter"
                elif ch.lower() == "q":
                    return "q"
                return "unknown"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except ImportError:
            # Fallback for Windows or when tty is not available
            return input("Choice: ").strip().lower()


def select_from_list(items: List[str], title: str = "Select:") -> Optional[str]:
    """Simple list selection."""
    if not items:
        print("No items available.")
        return None

    print(f"\n{title}")
    print("-" * 40)
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    print("-" * 40)

    while True:
        try:
            choice = input("Enter number (or 'q' to quit): ").strip()
            if choice.lower() == "q":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            print(f"Please enter a number between 1 and {len(items)}")
        except ValueError:
            print("Please enter a valid number")


def select_multiple_from_list(items: List[str], title: str = "Select (space-separated):") -> List[str]:
    """Select multiple items from a list."""
    if not items:
        print("No items available.")
        return []

    print(f"\n{title}")
    print("-" * 40)
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item}")
    print("-" * 40)
    print("Enter numbers separated by space (e.g., '1 3 5'), or 'a' for all, 'n' for none, 'q' to quit")

    while True:
        choice = input("Selection: ").strip().lower()
        if choice == "q":
            return []
        elif choice == "a":
            return items.copy()
        elif choice == "n":
            return []
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split()]
                selected = [items[i] for i in indices if 0 <= i < len(items)]
                return selected
            except ValueError:
                print("Invalid input. Try again.")