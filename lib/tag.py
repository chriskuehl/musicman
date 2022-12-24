#!/usr/bin/env python3
"""Helper program whose only purpose is to print tags from a media file. Relies
on the mutagen library, which used to be only available for Python 2.

Previously this was a separate binary so that it could be invoked with Python
2, but that is no longer necessary, and eventually we should just call mutagen
directly from musicman.
"""

import json
import sys

import mutagen

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: tag.py [path to file]")

    path = sys.argv[1]

    # use easy for getting key-value tags, hard for getting length of songs
    f_easy = mutagen.File(path, easy=True)
    f_hard = mutagen.File(path, easy=False)

    if not f_easy or not f_hard:
        sys.exit("unable to read file")

    tags = dict((k, v[0]) for (k, v) in f_easy.items())

    if f_hard.info.length > 0:
        tags["length"] = f_hard.info.length

    print(json.dumps(tags, indent=4))
