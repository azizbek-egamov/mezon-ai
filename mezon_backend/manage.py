#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # Windows konsoli (cp1251) o'zbekcha ʻ ʼ belgilarini chiqara olmaydi.
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding.lower() != "utf-8":
            stream.reconfigure(encoding="utf-8")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
