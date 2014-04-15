#!/usr/bin/env python3
# Command-line interface to musicman
import argparse
import datetime
import dateutil.parser
import json
import os
import os.path
import sys

import musicman.library as mlib

HELP_DESCRIPTION = "Manage musicman libraries"
HELP_EPILOG = "Try command --help to see required arguments."

def init():
	"""Initializes a new musicman library at the current directory."""
	path = os.getcwd()

	if mlib.get_library(path):
		print("Error: You're already inside a musicman library.")
		sys.exit(1)
	
	library = mlib.Library(path)
	library.init()
	library.save()

	print("New library initialized at {}".format(path))

def status():
	"""Prints information about the current library."""
	library = get_library_or_die()

	print("Library information:")
	print("\tPath: {}".format(library.path))
	print("\t# of Songs: {}".format(len(library.songs)))
	print("\tExports Configured ({}):".format(len(library.exports)))

	for name, export in library.exports.items():
		print("\t\t{}: {}".format(name, export))

def add(paths, date_added, check_extension=True, recurse=False):
	"""Adds the song at path to the current library."""
	library = get_library_or_die()
	add_files(library, paths, date_added, check_extension=check_extension, recurse=recurse)
	library.save()

def add_files(library, paths, date_added, check_extension=True, recurse=True):
	"""Adds a list of paths to the given library, optionally recursing into
	directories."""

	for path in paths:
		basename = os.path.basename(path)

		# skip garbage files
		if basename.lower() in mlib.FILE_BLACKLIST:
			print("Skipping file in blacklist: `{}`.".format(path))
			continue

		if basename.startswith("."):
			print("Skipping hidden file/directory: `{}`.".format(path))
			continue
		
		# add files, recurse into directories
		if os.path.isfile(path):
			ext = os.path.splitext(path)[1][1:]

			if check_extension and ext not in library.extensions:
				print("Unexpected music extension `{}` found for file `{}`.".format(ext, path))

				if input("Add song anyway? [yN] ") != "y":
					print("Skipping song.")
					continue

			library.add_song(path, date_added=date_added)
			print("Added song `{}`".format(path))
		elif os.path.isdir(path):
			if not recurse:
				print("Encountered directory `{}`.".format(path))

				if input("Recurse into directory? [yN] ") != "y":
					print("Skipping directory.")
					continue

			print("Recursing into directory: {}".format(path))
			new_paths = [os.path.join(path, p) for p in os.listdir(path)]
			add_files(library, new_paths, date_added, check_extension=check_extension, recurse=recurse)
		else:
			print("Song doesn't exist: `{}`".format(path))
			print("Skipping song.")

def export():
	"""Updates all exports for the given library."""
	library = get_library_or_die()

	if len(library.exports) <= 0:
		print("You haven't configured any exports.")
		sys.exit(1)

	for name, export in library.exports.items():
		print("Updating export `{}`..".format(name))
		export.update(library)

def dump():
	"""Prints the serialized version of the library. Only useful for
	debugging."""
	library = get_library_or_die()
	print(json.dumps(library.get_config(), indent=4))

def get_library_or_die():
	"""Returns the library at the current working directory, or prints an error
	message and exits."""

	library = mlib.get_library()

	if not library:
		print("Error: No musicman library exists above {}".format(os.getcwd()))
		sys.exit(1)

	return library

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=HELP_DESCRIPTION, epilog=HELP_EPILOG)
	subparsers = parser.add_subparsers(title="available commands", dest="command")

	parser_init = subparsers.add_parser("init", help="initialize new library")
	parser_status = subparsers.add_parser("status", help="print status about library")

	parser_add = subparsers.add_parser("add", help="add music file to library")
	parser_add.add_argument("path", type=str, nargs="+", help="path to file(s) to add")
	parser_add.add_argument("-r", default=False, action="store_true", dest="recurse",
		help="recurse into directories without prompting when finding files")
	parser_add.add_argument("--date", type=str, default=datetime.datetime.now().isoformat(),
		help="when the song was added (iso8601 format)")
	parser_add.add_argument("--skip-check-extension", default=False, action="store_true",
		help="skip checking file extension against preferred extension types")

	parser_export = subparsers.add_parser("export", help="export library into another format")
	parser_dump = subparsers.add_parser("dump", help="dumps library JSON (for debugging serialization)")

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
	elif args.command == "add":
		add(args.path, dateutil.parser.parse(args.date),
			check_extension=not args.skip_check_extension,
			recurse=args.recurse)
	elif args.command == "export":
		export()
	elif args.command == "dump":
		dump()
