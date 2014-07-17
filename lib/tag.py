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

	# use easy for getting key-value tags, hard for getting length of songs
	f_easy = mutagen.File(path, easy=True)
	f_hard = mutagen.File(path, easy=False)

	if not f_easy or not f_hard:
		sys.exit("unable to read file")

	tags = dict((k, v[0]) for (k, v) in f_easy.iteritems())

	if f_hard.info.length > 0:
		tags["length"] = f_hard.info.length

	print json.dumps(tags, indent=4)
