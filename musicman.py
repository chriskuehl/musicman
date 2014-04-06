#!/usr/bin/env python3
# Command-line interface to musicman
import argparse, sys, os, os.path, errno, json

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

def get_library(path=os.getcwd()):
	"""Returns a Library object representing the library the path exists under,
	or None if not under a library."""

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

	# file and directory paths
	def get_config_path(self):
		return os.path.join(self.path, FILENAME_CONFIG)

	def get_music_path(self):
		return os.path.join(self.path, FILENAME_MUSIC)

if __name__ == "__main__":
	commands = ["init", "status"]

	parser = argparse.ArgumentParser(description="Manage musicman libraries.")
	parser.add_argument("command", type=str, choices=commands)

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
