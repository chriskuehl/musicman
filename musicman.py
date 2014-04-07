#!/usr/bin/env python3
# Command-line interface to musicman
import argparse, sys, os, os.path, errno, json, re, shutil, dateutil.parser, tempfile
from datetime import datetime

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

HELP_DESCRIPTION = "Manage musicman libraries"
HELP_EPILOG = "Try command --help to see required arguments."

# files which should never be added to libraries (lowercase)
FILE_BLACKLIST = (".ds_store", "thumbs.db", "itunes library.itl", "itunes music library.xml")

def get_library(path=None):
	"""Returns a Library object representing the library the path exists under,
	or None if not under a library."""

	if not path:
		path = os.getcwd()

	# walk up until we hit either the root directory, or find a library
	while path != os.path.dirname(path):
		if is_library(path):
			library = Library(path)
			library.load()
			return library

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
	"""Prints information about the current library."""
	library = get_library_or_die()

	print("Library information:")
	print("\tPath: {}".format(library.path))
	print("\t# of Songs: {}".format(len(library.songs)))

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
		if basename.lower() in FILE_BLACKLIST:
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

def get_library_or_die():
	"""Returns the library at the current working directory, or prints an error
	message and exits. Intended for usage on the CLI."""

	library = get_library()

	if not library:
		print("Error: No musicman library exists above {}".format(os.getcwd()))
		sys.exit(1)

	return library

class Library:
	songs = []

	# default list of permitted music extensions (can be adjusted per-library)
	extensions = ["mp3", "mp4", "wav", "m4a", "flac"]

	def __init__(self, path):
		self.path = path

	def init(self):
		"""Sets up a new library for the first time, creating necessary
		configuration files and adding base config."""

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
		"""Saves the library configuration to disk.
		
		First saves to a temporary file and then moves to the proper location
		to avoid destroying the library if an exception occurs while dumping
		the config."""
		handle, path = tempfile.mkstemp()

		with open(handle, "w") as file:
			json.dump(self.get_config(), file, indent=4)

		shutil.move(path, self.get_config_path())

	def get_config(self):
		"""Returns a dictionary representing the library configuration which
		can be serialized and persisted to disk."""

		config = {
			"extensions": self.extensions,
			"songs": self._serialize_songs()
		}

		return config

	def _serialize_songs(self):
		def serialize_song(song):
			data = {
				"filename": song["filename"],
				"date_added": song["date_added"].isoformat()
			}

			return data

		return [serialize_song(song) for song in self.songs]

	def _unserialize_songs(self, songs):
		def unserialize_song(song):
			data = {
				"filename": song["filename"],
				"date_added": dateutil.parser.parse(song["date_added"])
			}

			return data

		return [unserialize_song(song) for song in songs]

	def load_config(self, config):
		"""Loads a dictionary representing the library configuration."""
		self.extensions = config["extensions"]
		self.songs = self._unserialize_songs(config["songs"])
	
	# music management
	def add_song(self, path, date_added=None, move=False):
		"""Adds the given path to the library, copying (or moving, if
		move=True) the music file to the appropriate directory."""

		if not date_added:
			date_added = datetime.now()

		filename = gen_filename(path)
		dest_path = self.get_song_path(filename)

		try:
			if move:
				shutil.move(path, dest_path)
			else:
				shutil.copyfile(path, dest_path)
		except IOError as error:
			print("Failed to {} file from `{}` to `{}`".format("move" if move else "copy", path, dest_path))
			sys.exit(1)

		song = {
			"filename": filename,
			"date_added": date_added
		}

		self.songs.append(song)

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

	# add parser
	parser_add = subparsers.add_parser("add", help="add music file to library")
	parser_add.add_argument("path", type=str, nargs="+", help="path to file(s) to add")

	parser_add.add_argument("-r", default=False, action="store_true", dest="recurse",
		help="recurse into directories without prompting when finding files")
	parser_add.add_argument("--date", type=str, default=datetime.now().isoformat(),
		help="when the song was added (iso8601 format)")
	parser_add.add_argument("--skip-check-extension", default=False, action="store_true",
		help="skip checking file extension against preferred extension types")

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
	elif args.command == "add":
		add(args.path, dateutil.parser.parse(args.date),
			check_extension=not args.skip_check_extension,
			recurse=args.recurse)
