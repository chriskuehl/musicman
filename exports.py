from abc import ABCMeta, abstractmethod

class Export(metaclass=ABCMeta):
	"""Export represents a single export configuration."""
	TYPE = "unconfigured"

	@abstractmethod
	def update(self):
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

class BansheeExport(Export):
	TYPE = "banshee"
	music_dir = None
	config_dir = None

	def update(self):
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

EXPORT_CLASSES = (BansheeExport,)
EXPORT_MAPPING = {export.TYPE: export for export in EXPORT_CLASSES}
