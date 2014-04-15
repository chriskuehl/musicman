import os
import os.path
import shutil
import sys

def ensure_dir(path):
	"""Ensures that the given path is a directory, creating it if necessary.

	If the parent directory of the given path does not exist, an error message
	is printed and the program exits. In other words, this will refuse to
	recursively create directories.

	Also fails if the path exists but is not a directory."""

	parent_dir = os.path.dirname(path)

	if not os.path.isdir(parent_dir):
		print("Error: Parent directory doesn't exist `{}`".format(parent_dir))
		print("\tFailed when creating directory `{}`".format(path))
		sys.exit(1)

	if os.path.exists(path) and not os.path.isdir(path):
		print("Error: Path exists but isn't a directory `{}`".format(parent_dir))
		print("\tFailed when creating directory `{}`".format(path))
		sys.exit(1)
	
	if not os.path.exists(path):
		os.mkdir(path)

def ensure_empty_dir(path, allow_delete_dirs=False, only_delete_symlinks=False):
	"""Ensures that the given path is an empty directory, subject to the
	conditions in ensure_dir (fails if parent directory doesn't exist, or the
	path exists and is a file).
	
	The optional parameters allow_delete_dirs and only_delete_symlinks provide
	safety (e.g. to avoid accidentally deleting the entire home directory if
	you mistype some path)."""

	ensure_dir(path)

	for fname in os.listdir(path):
		fpath = os.path.join(path, fname)

		if not os.path.islink(fpath) and only_delete_symlinks:
			print("Error: Refusing to delete non-link file `{}`".format(fpath))
			print("\tFailed when emptying directory `{}`".format(path))
			sys.exit(1)

		if os.path.isdir(fpath):
			if not allow_delete_dirs:
				print("Error: Refusing to delete directory `{}`".format(fpath))
				print("\tFailed when emptying directory `{}`".format(path))
				sys.exit(1)

			shutil.rmtree(fpath)
		else:
			os.remove(fpath)
