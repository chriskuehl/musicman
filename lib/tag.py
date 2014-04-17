#!/usr/bin/env python2
"""Helper program whose only purpose is to print tags from a media file. Relies
on the mutagen library, which is currently only available for Python 2.

The rest of the musicman project invokes this as a binary (rather than, for
example, importing it) so that python3 compatibility can be maintained."""

import json
import sys

import mutagen

if __name__ == "__main__":
	if len(sys.argv) != 2:
		sys.exit("usage: tag.py [path to file]")

	path = sys.argv[1]
	f = mutagen.File(path, easy=True)

	if not f:
		sys.exit("unable to read file")

	print json.dumps(dict((k, v[0]) for (k, v) in f.iteritems()), indent=4)
