#!/usr/bin/env python3
# Command-line interface to musicman
import argparse, sys, os, os.path, errno, json, datetime, hashlib

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

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
	def add_song(self, path, add_date=None, move=False):
		"""Adds the given path to the library, copying (or moving, if
		move=True) the music file to the appropriate directory."""

		if not add_date:
			add_date = datetime.now()

		id = generate_id(path)

		try:
			if move:
				shutil.move(path, dest_path)
			else:
				shutil.copyfile(path, dest_path)
		except IOError as error:
			print("Failed to {} file from `{}` to `{}`".format("move" if move else "copy", path, dest_path))

	# file and directory paths
	def get_config_path(self):
		return os.path.join(self.path, FILENAME_CONFIG)

	def get_music_path(self):
		return os.path.join(self.path, FILENAME_MUSIC)

	def get_song_path(self, song):
		return os.path.join(self.get_music_path(), id)

def get_id(path):
	"""Generates an ID for a given song. The ID should be unique but
	deterministic (the same song always gets the same ID).

	This implementation simply hashes the file, so it's obviously quite slow.
	Possible improvements might be hashing file metadata, although there are
	other concerns here as well.
	"""

	md5 = hashlib.md5()

	with open(path, "rb") as file:
		for chunk in iter(lambda: file.read(8192), b""):
			md5.update(chunk)
	
	return md5.hexdigest()

if __name__ == "__main__":
	commands = ["init", "status"]

	parser = argparse.ArgumentParser(description="Manage musicman libraries.")
	parser.add_argument("command", type=str, choices=commands)

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
