#!/usr/bin/env python3
"""
new_post.py — create a new blog post from posts/post-template.html

Usage:
    python3 new_post.py

Run this from inside the blog/ folder (same level as index.html).
It will ask for the name of the new post's HTML file, copy the
template, and tell you what to do next.
"""

import os
import re
import shutil
import sys

BLOG_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(BLOG_DIR, "posts")
TEMPLATE_PATH = os.path.join(POSTS_DIR, "post-template.html")


def ask_filename():
    while True:
        raw = input("Name for the new post's HTML file (e.g. gameweek-2): ").strip()

        if not raw:
            print("  Please enter a name.\n")
            continue

        # Allow the user to type with or without .html
        if not raw.lower().endswith(".html"):
            raw += ".html"

        # Basic sanity check: letters, numbers, dashes, underscores, dot
        name_no_ext = raw[:-5]
        if not re.match(r"^[a-zA-Z0-9_-]+$", name_no_ext):
            print("  Use only letters, numbers, dashes, and underscores (no spaces or slashes).\n")
            continue

        dest_path = os.path.join(POSTS_DIR, raw)
        if os.path.exists(dest_path):
            overwrite = input(f"  '{raw}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite != "y":
                print()
                continue

        return raw, dest_path


def main():
    if not os.path.isfile(TEMPLATE_PATH):
        print(f"Couldn't find the template at {TEMPLATE_PATH}")
        print("Make sure this script sits in the blog/ folder, next to the posts/ directory.")
        sys.exit(1)

    print("New FPL Tracker blog post")
    print("-" * 30)
    filename, dest_path = ask_filename()

    shutil.copyfile(TEMPLATE_PATH, dest_path)

    print(f"\nCreated posts/{filename}")
    print("\nNext steps:")
    print(f"  1. Open posts/{filename} and fill in the numbered comments")
    print("     (gameweek number, date, headline, stat pills, team sections).")
    print(f"  2. Add a matching card in index.html's postList, linking to")
    print(f"     posts/{filename}")
    print("  3. Commit and push:")
    print(f"       git add posts/{filename} index.html")
    print(f'       git commit -m "Add post: {filename}"')
    print("       git push")


if __name__ == "__main__":
    main()
