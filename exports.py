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

    @abstractmethod
    def serialize(self):
        """Returns a dictionary representing a serialized version of this
        export configuration."""
        return {"type": self.TYPE}

    @abstractmethod
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
        self.update_song_symlinks(library)
        self.update_playlists(library)

    def update_song_symlinks(self, library):
        mio.ensure_empty_dir(self.music_dir, only_delete_symlinks=True)

        for _, song in library.songs.items():
            src = os.path.join(library.get_music_path(), song.filename)
            dest = os.path.join(self.music_dir, song.filename)
            os.symlink(src, dest)

    def update_playlists(self, library):
        mio.ensure_empty_dir(self.playlist_dir, only_delete_symlinks=False)

        for name, playlist in library.playlists.items():
            path = os.path.join(self.playlist_dir, name + ".m3u")

            with open(path, "w") as f:
                for line in playlist.get_m3u(library):
                    print(line, file=f)

    def serialize(self):
        config = super().serialize()
        config["music_dir"] = self.music_dir
        config["playlist_dir"] = self.playlist_dir
        return config

    def unserialize(self, config):
        super().unserialize(config)
        self.music_dir = config["music_dir"]
        self.playlist_dir = config["playlist_dir"]

EXPORT_CLASSES = (FlatDirExport,)
EXPORT_MAPPING = {export.TYPE: export for export in EXPORT_CLASSES}
