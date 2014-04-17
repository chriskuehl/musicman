from abc import ABCMeta, abstractmethod
import os
import os.path

import musicman.io as mio

class Export(metaclass=ABCMeta):
	"""Export represents a single export configuration."""
	TYPE = "unconfigured"

	@abstractmethod
	def update(self, library):
		"""Updates the export."""
		pass

	def serialize(self):
		"""Returns a dictionary representing a serialized version of this
		export configuration."""
		return {"type": self.TYPE}

	def unserialize(self, config):
		"""Updates this (unconfigured) export to match the serialized config
		represented by the dictionary given."""
		pass

class FlatDirExport(Export):
	"""A 'flat dir' export creates a single 'flat' directory which contains a
	symlink to every music file. It then creates m3u playlists pointing to
	these symlinks.

	The flatdir export is very simple and can be used for testing, but is also
	useful (you can play or import the m3u's in basically any media player).
	"""
	TYPE = "flatdir"
	music_dir = None
	playlist_dir = None

	def update(self, library):
		# ensure directories exist and are empty
		mio.ensure_empty_dir(self.music_dir, only_delete_symlinks=True)
		mio.ensure_empty_dir(self.playlist_dir, only_delete_symlinks=False)

		# symlink all music files into music_dir
		for song in library.songs:
			src = os.path.join(library.get_music_path(), song["filename"])
			dest = os.path.join(self.music_dir, song["filename"])
			os.symlink(src, dest)

	def serialize(self):
		config = super().serialize()
		config["music_dir"] = self.music_dir
		config["playlist_dir"] = self.playlist_dir
		return config

	def unserialize(self, config):
		super().unserialize(config)
		self.music_dir = config["music_dir"]
		self.playlist_dir = config["playlist_dir"]

class BansheeExport(Export):
	TYPE = "banshee"
	music_dir = None
	config_dir = None

	def update(self, library):
		print("updating banshee...")

	def serialize(self):
		config = super().serialize()
		config["music_dir"] = self.music_dir
		config["config_dir"] = self.config_dir
		return config

	def unserialize(self, config):
		super().unserialize(config)
		self.music_dir = config["music_dir"]
		self.config_dir = config["config_dir"]

EXPORT_CLASSES = (FlatDirExport, BansheeExport)
EXPORT_MAPPING = {export.TYPE: export for export in EXPORT_CLASSES}