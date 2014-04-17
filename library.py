import datetime
import dateutil.parser
import errno
import json
import os
import os.path
import re
import shutil
import tempfile

import musicman.exports as mexports

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

# files which should never be added to libraries (lowercase)
FILE_BLACKLIST = (".ds_store", "thumbs.db", "itunes library.itl", "itunes music library.xml")

class Library:
	songs = []
	exports = []

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
			"exports": self._serialize_exports(),
			"songs": self._serialize_songs()
		}

		return config

	# serialization
	def _serialize_exports(self):
		return {export: self.exports[export].serialize() for export in self.exports}

	def _unserialize_exports(self, exports):
		def unserialize_export(config):
			export = mexports.EXPORT_MAPPING[config["type"]]()
			export.unserialize(config)
			return export

		return {export: unserialize_export(exports[export]) for export in exports}

	def _serialize_songs(self):
		def serialize_song(song):
			data = {
				"filename": song.filename,
				"date_added": song.date_added.isoformat()
			}

			return data

		return [serialize_song(song) for song in self.songs]

	def _unserialize_songs(self, songs):
		def unserialize_song(song):
			filename = song["filename"]
			date_added = dateutil.parser.parse(song["date_added"])
			return Song(filename, date_added)

		return [unserialize_song(song) for song in songs]

	def load_config(self, config):
		"""Loads a dictionary representing the library configuration."""
		self.extensions = config["extensions"]
		self.exports = self._unserialize_exports(config["exports"])
		self.songs = self._unserialize_songs(config["songs"])

	# music management
	def add_song(self, path, date_added=None, move=False):
		"""Adds the given path to the library, copying (or moving, if
		move=True) the music file to the appropriate directory."""

		if not date_added:
			date_added = datetime.datetime.now()

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

		song = Song(filename, date_added)
		self.songs.append(song)
		return song

	# file and directory paths
	def get_config_path(self):
		return os.path.join(self.path, FILENAME_CONFIG)

	def get_music_path(self):
		return os.path.join(self.path, FILENAME_MUSIC)

	def get_song_path(self, song):
		return os.path.join(self.get_music_path(), song)

class Song:
	def __init__(self, filename, date_added):
		self.filename = filename
		self.date_added = date_added

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
