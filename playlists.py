from abc import ABCMeta, abstractmethod
import re

class Playlist(metaclass=ABCMeta):
	"""Playlist is an abstract class representing a single playlist. In
	general, SimplePlaylist and AutoPlaylist should be used."""
	TYPE = "unconfigured"

	@abstractmethod
	def get_songs(self):
		"""Returns a list of songs in order."""
		pass

	@abstractmethod
	def serialize(self):
		"""Returns a dictionary representing a serialized version of this
		playlist."""
		return {"type": self.TYPE}

	@abstractmethod
	def unserialize(self, config, library):
		"""Updates this (unconfigured) playlist to match the serialized config
		represented by the dictionary given."""
		pass

	def get_m3u(self, library):
		"""Returns a generator for an m3u-formatted playlist, with each
		returned string representing a line in the m3u file."""

		yield "#EXTM3U"

		for song in self.get_songs():
			yield ""

			seconds = song.metadata["length"]

			# TODO: allow custom title formats for playlists
			title = song.filename

			if "title" in song.metadata and "artist" in song.metadata:
				title = "{} - {}".format(
					song.metadata["title"], song.metadata["artist"])

			def sanitize(title):
				valid = r'[a-zA-Z0-9\-_ ()]'
				return "".join([c for c in title if re.match(valid, c)])

			yield "#EXTINF,{},{}".format(int(seconds), sanitize(title))
			yield library.get_song_path(song.filename)

class SimplePlaylist(Playlist):
	"""SimplePlaylist is an implementation of a static playlist. Songs can be
	added, removed, and reordered, but are not automatically managed."""

	TYPE = "simple"
	songs = []

	def get_songs(self):
		return self.songs

	def serialize(self):
		config = super().serialize()
		config["songs"] = [song.filename for song in self.songs]
		return config

	def unserialize(self, config, library):
		super().unserialize(config, library)
		self.songs = [library.get_song(fname) for fname in config["songs"]]

# TODO: complete this
class AutoPlaylist(Playlist):
	"""AutoPlaylist is an implementation of a dynamic playlist, with songs
	being added, removed, and ordered automatically based on a defined set of
	rules."""
	
	TYPE = "auto"

	def get_songs(self):
		return []

	def serialize(self):
		return super().serialize()

	def unserialize(self, config, library):
		super().unserialize(config, library)

PLAYLIST_CLASSES = (SimplePlaylist, AutoPlaylist)
PLAYLIST_MAPPING = {plist.TYPE: plist for plist in PLAYLIST_CLASSES}
