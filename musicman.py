#!/usr/bin/env python3
# Command-line interface to musicman
import argparse, sys, os, os.path, errno, json, datetime, re

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

HELP_DESCRIPTION = "Manage musicman libraries"
HELP_EPILOG = "Try --help command to see required arguments."

def get_library(path=None):
	"""Returns a Library object representing the library the path exists under,
	or None if not under a library."""

	if not path:
		path = os.getcwd()

	# walk up until we hit either the root directory, or find a library
	while path != os.path.dirname(path):
		if is_library(path):
			return Library(path)

		path = os.path.dirname(path)

	return None

def is_library(path):
	"""Returns whether the path is a root library directory."""
	return os.path.exists(os.path.join(path, "musicman.json"))

def init():
	"""Initializes a new musicman library at the current directory."""
	path = os.getcwd()

	if get_library(path):
		print("Error: You're already inside a musicman library.")
		sys.exit(1)
	
	library = Library(path)
	library.init()
	library.save()

	print("New library initialized at {}".format(path))

def status():
	"""Prints information about the current musicman library."""
	library = get_library()

	if not library:
		print("Error: No musicman library exists above {}".format(os.getcwd()))
		sys.exit(1)

	print("Library information:")
	print("\tPath: {}".format(library.path))
	print("\t# of Songs: {}".format(len(library.music)))

class Library:
	music = []

	def __init__(self, path):
		self.path = path

	def init(self):
		"""Sets up a new library for the first time, creating necessary
		configuration files."""

		try:
			os.makedirs(self.get_music_path())
		except OSError as ex:
			if ex.errno != errno.EEXIST:
				raise
			print("Warning: `music` directory already existed, ignoring...")

	def load(self):
		"""Loads the library configuration from disk."""
		with open(self.get_config_path()) as file:
			self.load_config(json.load(file))

	def save(self):
		"""Saves the library configuration to disk."""
		with open(self.get_config_path(), "w") as file:
			json.dump(self.get_config(), file, indent=4)

	def get_config(self):
		"""Returns a dictionary representing the library configuration which
		can be serialized and persisted to disk."""

		config = {"music": self.music}
		return config

	def load_config(self, config):
		"""Loads a dictionary representing the library configuration."""
		print("loading config: {}".format(config))
	
	# music management
	def add_song(self, path, date_added=None, move=False):
		"""Adds the given path to the library, copying (or moving, if
		move=True) the music file to the appropriate directory."""

		if not date_added:
			date_added = datetime.now()

		filename = gen_filename(path)
		dest_path = get_song_path(filename)

		try:
			if move:
				shutil.move(path, dest_path)
			else:
				shutil.copyfile(path, dest_path)
		except IOError as error:
			print("Failed to {} file from `{}` to `{}`".format("move" if move else "copy", path, dest_path))
			sys.exit(1)

		song = {
				"filename": name,
				"date_added": date_added
		}

		songs.append(song)
		print(songs)

	# file and directory paths
	def get_config_path(self):
		return os.path.join(self.path, FILENAME_CONFIG)

	def get_music_path(self):
		return os.path.join(self.path, FILENAME_MUSIC)

	def get_song_path(self, song):
		return os.path.join(self.get_music_path(), song)

def gen_filename(path):
	"""Generates a file name a given song. Tries to be fairly conservative in
	what characters are allowed, but still readable.
	
	>>> gen_filename("~/Music/Televisor/01. Old Skool (Nitro Fun Remix).flac")
	'01-Old-Skool-Nitro-Fun-Remix.flac'
	"""

	basename = os.path.basename(path)
	parts = os.path.splitext(basename)

	name = parts[0]
	name = name.replace(" ", "-")
	name = "".join([c for c in name if re.match(r'[a-zA-Z0-9\-_]', c)])

	return  name + parts[1]

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=HELP_DESCRIPTION, epilog=HELP_EPILOG)
	subparsers = parser.add_subparsers(title="available commands", dest="command")

	parser_init = subparsers.add_parser("init", help="initialize new library")
	parser_status = subparsers.add_parser("status", help="print status about library")

	parser_add = subparsers.add_parser("add", help="add music file to library")
	parser_add.add_argument("path", type=str, help="path to file to add")

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
	elif args.command == "add":
		add(args.path)
