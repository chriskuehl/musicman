from abc import ABCMeta, abstractmethod
import datetime
import re
import time

class Playlist(metaclass=ABCMeta):
	"""Playlist is an abstract class representing a single playlist. In
	general, SimplePlaylist and AutoPlaylist should be used."""
	TYPE = "unconfigured"

	@abstractmethod
	def get_songs(self, library):
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

		for song in self.get_songs(library):
			yield ""

			seconds = song.metadata["length"] if "length" in song.metadata else 0

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

	def get_songs(self, library):
		return self.songs

	def serialize(self):
		config = super().serialize()
		config["songs"] = [song.filename for song in self.songs]
		return config

	def unserialize(self, config, library):
		super().unserialize(config, library)
		self.songs = [library.get_song(fname) for fname in config["songs"]]


# constants are used only internally; when serializing, we use english mappings
# to maintain human readability and editability
CONDITION_IS = 1
CONDITION_IS_NOT = 2
CONDITION_CONTAINS = 3
CONDITION_DOES_NOT_CONTAIN = 4
CONDITION_IN = 5
CONDITION_NOT_IN = 6
CONDITION_CONTAINS_ALL = 7
CONDITION_CONTAINS_ANY = 8
CONDITION_CONTAINS_NONE = 9

# maps english phrase to internal constant
CONDITION_MAPPING = {
	"is": CONDITION_IS,
	"is not": CONDITION_IS_NOT,
	"contains": CONDITION_CONTAINS,
	"does not contain": CONDITION_DOES_NOT_CONTAIN,
	"in": CONDITION_IN,
	"not in": CONDITION_NOT_IN,
	"contains all": CONDITION_CONTAINS_ALL,
	"contains any": CONDITION_CONTAINS_ANY,
	"contains none": CONDITION_CONTAINS_NONE
}

# maps internal constant to english phrase
CONDITION_MAPPING_REVERSE = {v: k for k, v in CONDITION_MAPPING.items()}

# conditions on single values
CONDITIONS_SINGLE = {
	CONDITION_IS:
		lambda cur, rule: cur == rule,
	CONDITION_IS_NOT:
		lambda cur, rule: cur != rule,
	CONDITION_CONTAINS:
		lambda cur, rule: cur and rule in cur,
	CONDITION_DOES_NOT_CONTAIN:
		lambda cur, rule: cur or rule not in cur,
}

# conditions on multiple values
CONDITIONS_MULTIPLE = {
	CONDITION_IN:
		lambda cur, rule: cur in rule,
	CONDITION_NOT_IN:
		lambda cur, rule: cur not in rule,
	CONDITION_CONTAINS_ALL:
		lambda cur, rule: all(r in cur for r in rule if cur),
	CONDITION_CONTAINS_ANY:
		lambda cur, rule: any(r in cur for r in rule if cur),
	CONDITION_CONTAINS_NONE:
		lambda cur, rule: not any(r in cur for r in rule if cur)
}

class AutoPlaylist(Playlist):
	"""AutoPlaylist is an implementation of a dynamic playlist, with songs
	being added, removed, and ordered automatically based on a defined set of
	rules."""
	
	TYPE = "auto"
	sort = ["artist", "title"]
	conditions = []

	def get_conditions(self):
		return {"type": "and", "conditions": self.conditions}

	def get_songs(self, library):
		songs = [song for _, song in library.songs.items() if self.matches(song)]

		# sort on least-significant fields first since sort is stable
		for field in reversed(self.sort):
			reverse = field.startswith("!")
			if reverse:
				field = field[1:]
			songs.sort(key=lambda song: song.get_attr(field) or "", reverse=reverse)

		return songs
	
	def matches(self, song):
		def matches_condition(condition):
			if condition["type"] in ("and", "or"):
				match = any if condition["type"] == "or" else all
				return match(matches_condition(c) for c in condition["conditions"])
			else:
				clean = lambda s: s.lower().strip() if s else None

				val = song.get_attr(condition["attr"])
				match = condition["value"]

				if isinstance(match, list):
					match = [clean(s) for s in match]

				return condition["func"](clean(val), match)

		return matches_condition(self.get_conditions())

	def serialize(self):
		config = super().serialize()
		config["conditions"] = self._serialize_conditions()
		config["sort"] = self.sort
		return config

	def _serialize_conditions(self):
		def serialize_condition(condition):
			"""Turns a given condition into a list representing that condition,
			with particular emphasis on human readability of the serialized
			condition (represented in JSON)."""

			if condition["type"] in ("and", "or"):
				conditions = [serialize_condition(c) for c in condition["conditions"]]
				return [condition["type"], conditions]

			# not the most attractive format from our standpoint, but easy for
			# humans to read: ['artist', 'in', ['Gorillaz', 'Radiohead']]
			check = CONDITION_MAPPING_REVERSE[condition["type"]]
			return [condition["attr"], check, condition["value"]]

		# all conditions are implicitly wrapped in an "and" block, which we
		# don't serialize (so strip it before returning)
		return serialize_condition(self.get_conditions())[1]


	def unserialize(self, config, library):
		def unserialize_condition(condition):
			# TODO: better error messages on bad conditions

			if len(condition) == 2:
				if condition[0] in ("and", "or"):
					return {
						"type": condition[0],
						"conditions": [unserialize_condition(c) for c in condition[1]]
					}
				else:
					raise Exception()
			elif len(condition) == 3:
				# TODO: raises KeyError, make friendlier
				check = CONDITION_MAPPING[condition[1]]

				if isinstance(condition[2], list):
					func = CONDITIONS_MULTIPLE[check]
				else:
					func = CONDITIONS_SINGLE[check]

				return {
					"type": check,
					"attr": condition[0],
					"value": condition[2],
					"func": func
				}
			else:
				raise Exception()

		super().unserialize(config, library)

		self.sort = config["sort"] if "sort" in config else AutoPlaylist.sort

		# strip the and off since it's implicit on the first condition
		self.conditions = unserialize_condition(["and", config["conditions"]])["conditions"]

PLAYLIST_CLASSES = (SimplePlaylist, AutoPlaylist)
PLAYLIST_MAPPING = {plist.TYPE: plist for plist in PLAYLIST_CLASSES}
