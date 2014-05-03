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
import musicman.playlists as mplaylists
import musicman.io as mio

FILENAME_CONFIG = "musicman.json"
FILENAME_MUSIC = "music"

# files which should never be added to libraries (lowercase)
FILE_BLACKLIST = {".ds_store", "thumbs.db", "itunes library.itl", "itunes music library.xml"}

class Library:
	songs = {}
	exports = {}
	playlists = {}

	# default list of permitted music extensions (can be adjusted per-library)
	extensions = ["mp3", "mp4", "wav", "m4a", "flac"]

	def __init__(self, path):
		self.path = path

	def init(self, skip_defaults=False):
		"""Sets up a new library for the first time, creating necessary
		configuration files and adding base config."""

		try:
			os.makedirs(self.get_music_path())
		except OSError as ex:
			if ex.errno != errno.EEXIST:
				raise
			print("Warning: `music` directory already existed, ignoring...")

		if not skip_defaults:
			self.set_defaults()

	def set_defaults(self):
		"""Add default config for new libraries. None of these are necessary to
		the functioning of the library, so could be skipped if desired."""

		if not "last-added" in self.playlists:
			# TODO: sorting options (once it's possible to sort by last added)
			self.playlists["last-added"] = mplaylists.AutoPlaylist()

	def load(self):
		"""Loads the library configuration from disk."""
		with open(self.get_config_path()) as file:
			self.load_config(json.load(file))

	def load_config(self, config):
		"""Loads a dictionary representing the library configuration."""

		# use default values if none provided
		for attr in ("exports", "playlists", "songs", "extensions"):
			if not attr in config:
				config[attr] = getattr(self, attr)

		self.extensions = config["extensions"]
		self.songs = self._unserialize_songs(config["songs"])
		self.exports = self._unserialize_exports(config["exports"])
		self.playlists = self._unserialize_playlists(config["playlists"])

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
			"playlists": self._serialize_playlists(),
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
				"date_added": song.date_added.isoformat(),
				"metadata": song.metadata
			}

			return data

		return {fname: serialize_song(song) for fname, song in self.songs.items()}

	def _unserialize_songs(self, songs):
		def unserialize_song(song):
			filename = song["filename"]
			date_added = dateutil.parser.parse(song["date_added"])
			metadata = song["metadata"] if "metadata" in song else {}
			return Song(filename, date_added, metadata)

		return {fname: unserialize_song(song) for fname, song in songs.items()}

	def _serialize_playlists(self):
		return {plist: self.playlists[plist].serialize() for plist in self.playlists}

	def _unserialize_playlists(self, plists):
		def unserialize_playlist(config):
			plist = mplaylists.PLAYLIST_MAPPING[config["type"]]()
			plist.unserialize(config, self)
			return plist

		return {plist: unserialize_playlist(plists[plist]) for plist in plists}

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

		song = Song(filename, date_added, {})

		try:
			song.update_metadata(dest_path)
		except mio.UnableToReadTagsException:
			print("Warning: Unable to read tags from `{}` (song still added to library)".format(path))

		self.songs[song.filename] = song
		return song
	
	def get_song(self, filename):
		return self.songs[filename]

	# file and directory paths
	def get_config_path(self):
		return os.path.join(self.path, FILENAME_CONFIG)

	def get_music_path(self):
		return os.path.join(self.path, FILENAME_MUSIC)

	def get_song_path(self, filename):
		return os.path.join(self.get_music_path(), filename)

class Song:
	ALLOWED_ATTRS = ("filename", "date_added")

	def __init__(self, filename, date_added, metadata):
		self.filename = filename
		self.date_added = date_added
		self.metadata = metadata

	def update_metadata(self, path):
		self.metadata = mio.get_tags(path)

	def get_attr(self, attr):
		"""Returns the requested attribute, where attr can be either some
		library-specific attribute (like date added), or song-specific metadata
		(like title or song length)."""

		if attr in Song.ALLOWED_ATTRS:
			return self.getattr(attr)

		if attr in self.metadata:
			return self.metadata[attr]

		return None

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
