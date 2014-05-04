#!/usr/bin/env python3
# Command-line interface to musicman
import argparse
import code
import datetime
import dateutil.parser
import json
import os
import os.path
import shutil
import subprocess
import sys
import tempfile

import musicman.imports as mimports
import musicman.io as mio
import musicman.library as mlib
import musicman.playlists as mplaylists

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

	# playlists
	print("\tPlaylists Configured ({}):".format(len(library.playlists)))

	for name, playlist in library.playlists.items():
		print("\t\t{}: {}".format(name, playlist))

	# exports
	print("\tExports Configured ({}):".format(len(library.exports)))

	for name, export in library.exports.items():
		print("\t\t{}: {}".format(name, export))

def add(paths, date_added, check_extension=True, recurse=False, no_bad_extensions=False):
	"""Adds the song at path to the current library."""
	library = get_library_or_die()
	add_files(library, paths, date_added, check_extension=check_extension,
		recurse=recurse, no_bad_extensions=no_bad_extensions)
	library.save()

def add_files(library, paths, date_added, check_extension=True, recurse=True, no_bad_extensions=False):
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

			if check_extension and ext.lower() not in library.extensions:
				print("Unexpected music extension `{}` found for file `{}`.".format(ext, path))

				if no_bad_extensions or input("Add song anyway? [yN] ") != "y":
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
			add_files(library, new_paths, date_added,
				check_extension=check_extension, recurse=recurse,
				no_bad_extensions=no_bad_extensions)
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

def update_metadata():
	"""Refreshes metadata for all songs in the library."""
	library = get_library_or_die()

	for _, song in library.songs.items():
		path = library.get_song_path(song.filename)

		try:
			song.update_metadata(path)
		except mio.UnableToReadTagsException:
			print("Warning: Unable to read tags from `{}`".format(path))

	library.save()

def playlist_new():
	"""Creates a new playlist."""
	library = get_library_or_die()
	
	# playlist name
	def cond_not_plist(s):
		return None if s not in library.playlists else "That playlist already exists."

	name = read("Playlist name:", lambda s: cond_not_blank(s) or cond_not_plist(s))

	# playlist type
	print("Choose a playlist type:")
	print("\t- simple (add and order songs manually)")
	print("\t- auto (define rules for inclusion and sorting)")
	
	def cond_plist_type(s):
		return None if s in ("", "auto", "simple") else "Enter either `simple` or `auto`"

	ptype = read("Playlist type [simple]:", cond_plist_type) or "simple"

	if ptype == "simple":
		plist = mplaylists.SimplePlaylist()
	elif ptype == "auto":
		plist = mplaylists.AutoPlaylist()

	library.playlists[name] = plist
	print("Playlist `{}` added.".format(name))

	library.save()

def vi():
	"""Opens the configuration file in the user's text editor, and validates it
	(printing any error messages) upon save."""
	library = get_library_or_die()

	editor = get_default_editor()
	dpath = tempfile.mkdtemp()
	fpath = os.path.join(dpath, mlib.FILENAME_CONFIG)

	shutil.copyfile(library.get_config_path(), fpath)

	while True:
		subprocess.check_call((editor, fpath))

		try:
			new_library = mlib.Library(dpath)
			new_library.load()
		except ValueError as e:
			print("Error loading new library:")
			print("\t{}".format(e))
			input("Press enter to continue.")
		else:
			break

	shutil.copyfile(fpath, library.get_config_path())
	shutil.rmtree(dpath)

def get_default_editor():
	return os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"

def import_banshee():
	"""Imports a banshee library."""
	library = get_library_or_die()

	# find banshee directory
	print("Where is the banshee library stored?")
	print("")
	print("Your banshee library directory contains a file called `banshee.db`, which we need to read.")
	print("By default, this directory lives at `~/.config/banshee-1`. Please enter the path to the directory.")

	banshee_db = lambda dir: os.path.join(os.path.expanduser(dir), "banshee.db")

	def cond_banshee_dir(dir):
		db = banshee_db(dir)

		if not os.path.isfile(db):
			return "Couldn't find `{}`, are you sure this is a banshee directory?".format(db)

		return None

	dir = read("Banshee library location:", cond_banshee_dir)
	db = banshee_db(dir)


def debug_dump():
	"""Prints the serialized version of the library. Only useful for
	debugging."""

	library = get_library_or_die()
	print(json.dumps(library.get_config(), indent=4))

def debug_save():
	"""Loads and saves the library without making changes. Useful for testing
	serialization."""
	library = get_library_or_die()
	library.save()

def debug_shell():
	"""Launches a Python shell after loading the current library."""
	library = get_library_or_die()

	print("Your library is available: library={}".format(library))
	print("To save changes, use library.save()")
	code.interact(banner="", local=locals())


# reading from command prompt helpers
def cond_any(s):
	"""Accepts any input."""
	return None

def cond_not_blank(s):
	"""Accepts any non-blank input"""
	return None if s else "Please enter a response."

def read(prompt, error):
	"""Reads from command-line with given prompt and validates with the given
	error function.

	If the error function returns a non-falsey value, it is printed and the
	user is prompted again."""

	while True:
		val = input(prompt + " ").strip()
		e = error(val)

		if not e:
			return val

		print(e)

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
	parser_add.add_argument("--no-bad-extensions", default=False, action="store_true",
		help="don't ask whether or not to add files with bad extensions (always assume no)")

	parser_playlist = subparsers.add_parser("playlist", help="manage playlists")
	playlist_subparsers = parser_playlist.add_subparsers(title="available subcommands", dest="subcommand")
	parser_playlist_add = playlist_subparsers.add_parser("new", help="create a new playlist")

	parser_export = subparsers.add_parser("export", help="export library into another format")
	parser_update_metadata = subparsers.add_parser("update-metadata", help="updates song metadata")

	parser_import = subparsers.add_parser("import",
			help="imports a library into musicman, without modifying the existing library")
	parser_import.add_argument("source", type=str, choices=("banshee",), help="type of library to import")

	parser_vi = subparsers.add_parser("vi", help="modify musicman config file")

	# debugging
	parser_debug = subparsers.add_parser("debug", help="debugging commands for testing musicman")
	debug_subparsers = parser_debug.add_subparsers(title="available subcommands", dest="subcommand")
	parser_dump = debug_subparsers.add_parser("dump", help="dumps library JSON")
	parser_save = debug_subparsers.add_parser("save", help="loads and saves library without making changes")
	parser_shell = debug_subparsers.add_parser("shell", help="loads library and starts a python interpreter")

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
	elif args.command == "add":
		add(args.path, dateutil.parser.parse(args.date),
			check_extension=not args.skip_check_extension,
			no_bad_extensions=args.no_bad_extensions,
			recurse=args.recurse)
	elif args.command == "export":
		export()
	elif args.command == "update-metadata":
		update_metadata()
	elif args.command == "playlist":
		if args.subcommand == "new":
			playlist_new()
	elif args.command == "vi":
		vi()
	elif args.command == "import":
		if args.source == "banshee":
			import_banshee()
	elif args.command == "debug":
		if args.subcommand == "dump":
			debug_dump()
		elif args.subcommand == "save":
			debug_save()
		elif args.subcommand == "shell":
			debug_shell()
