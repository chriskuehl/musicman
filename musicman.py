#!/usr/bin/env python3
# Command-line interface to musicman
import argparse, sys, os, os.path

def get_library(path=os.getcwd()):
	"""Returns the root library directory that path is under, or None if path
	is not under a library."""

	# walk up until we hit either the root directory, or find a library
	while path != os.path.dirname(path):
		if is_library(path):
			return path

		path = os.path.dirname(path)

	return None

def is_library(path):
	"""Returns whether the path is a root library directory."""
	return os.path.exists(os.path.join(path, "musicman.json"))

def in_library(path):
	"""Returns whether the path is inside a library."""
	return get_library(path) is not None

def init():
	"""Initializes a new musicman library at the current directory."""
	path = os.getcwd()

	if in_library(path):
		print("Error: You're already inside a musicman library.")
		sys.exit(1)

	print(path)

def status():
	"""Prints information about the current musicman library."""
	path = get_library()

	if not path:
		print("Error: No musicman library exists here.")
		sys.exit(1)

	print("Library path: {}".format(path))

if __name__ == "__main__":
	commands = ["init", "status"]

	parser = argparse.ArgumentParser(description="Manage musicman libraries.")
	parser.add_argument("command", type=str, choices=commands)

	args = parser.parse_args()

	if args.command == "init":
		init()
	elif args.command == "status":
		status()
