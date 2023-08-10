#!/usr/bin/env python3

# litetool.py - simple upload tool for litemenu
# Runs on Python 3.7 - requires the pyserial libaries to be installed

_authors_ = ["@danhans42", "@GoobyCorp"]
_description_ = "litetool.py - by @danhans42"

from pathlib import Path
from enum import IntEnum
from typing import TypeVar
from shutil import copyfileobj
from argparse import ArgumentParser
from struct import pack, unpack_from

# Windows: py -3 -m pip install pyserial
# Linux: python3 -m pip install pyserial
import serial

PathLike = TypeVar("PathLike", str, Path)

PSX_BAUD = 1036800
BUFFER_SIZE = 2048
PSX_HEADER_SIZE = 2048

def path_type(s: str) -> Path:
	return Path(s)

def hex_type(s: str) -> int:
	if s.startswith("0x"):
		return int(s, 16)
	return int(s)

class PSXCommand(IntEnum):
	CMD_UPLOAD_BIN = 0x62
	CMD_UPLOAD_EXE = 0x63
	CMD_DUMP       = 0x64
	CMD_GOTO       = 0x65
	CMD_REBOOT     = 0x72

class PSX:
	ser: serial.Serial = None

	def __init__(self, port: str):
		self.reset()
		self.ser = serial.Serial(port, PSX_BAUD, write_timeout=1)

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.ser.close()

	def reset(self) -> None:
		self.ser = None

	def upload_bin(self, file: PathLike, addr: int) -> None:
		size = file.stat().st_size
		with file.open("rb") as f:
			self.ser.write(pack("B", PSXCommand.CMD_UPLOAD_BIN))
			self.ser.write(pack("<I", addr))
			self.ser.write(pack("<I", size))

			copyfileobj(f, self.ser, BUFFER_SIZE)

	def upload_exe(self, file: PathLike) -> None:
		with file.open("rb") as f:
			hdr = f.read(PSX_HEADER_SIZE)
			(pc, addr, fsz) = unpack_from("4s 4x 4s 4s", hdr, 0x10)

			self.ser.write(pack("B", PSXCommand.CMD_UPLOAD_EXE))
			self.ser.write(pc)
			self.ser.write(addr)
			self.ser.write(fsz)

			copyfileobj(f, self.ser, BUFFER_SIZE)

	def dump(self, file: PathLike, addr: int, size: int) -> None:
		self.ser.write(pack("B", PSXCommand.CMD_DUMP))
		self.ser.write(pack("<I", addr))
		self.ser.write(pack("<I", size))

		with file.open("wb") as f:
			copyfileobj(self.ser, f, BUFFER_SIZE)

	def goto(self, addr: int) -> None:
		self.ser.write(pack("B", PSXCommand.CMD_GOTO))
		self.ser.write(pack("<I", addr))

	def reboot(self):
		self.ser.write(pack("B", PSXCommand.CMD_REBOOT))

def main() -> int:
	parser = ArgumentParser(description=_description_)

	subparsers = parser.add_subparsers(dest="mode", required=True)

	bin_parser = subparsers.add_parser("bin", help="upload file to address")
	bin_parser.add_argument("port", type=str, help="The serial port to use for PSX communication")
	bin_parser.add_argument("file", type=path_type, help="The file to upload")
	bin_parser.add_argument("addr", type=hex_type, help="The address to write the file to")

	exe_parser = subparsers.add_parser("exe", help="upload & execute PSX-EXE")
	exe_parser.add_argument("port", type=str, help="The serial port to use for PSX communication")
	exe_parser.add_argument("exe", type=path_type, help="The executable you want to run on the console")

	dump_parser = subparsers.add_parser("dump", help="download data from PSX")
	dump_parser.add_argument("port", type=str, help="The serial port to use for PSX communication")
	dump_parser.add_argument("file", type=path_type, help="The file to write the dump to")
	dump_parser.add_argument("addr", type=hex_type, help="The address of the chunk of memory")
	dump_parser.add_argument("size", type=hex_type, help="The size of the chunk of memory")

	goto_parser = subparsers.add_parser("goto", help="goto to address")
	goto_parser.add_argument("port", type=str, help="The serial port to use for PSX communication")
	goto_parser.add_argument("addr", type=hex_type, help="The address to go to")

	reboot_parser = subparsers.add_parser("reboot", help="reboot attached PSX")
	reboot_parser.add_argument("port", type=str, help="The serial port to use for PSX communication")

	args = parser.parse_args()

	with PSX(args.port) as psx:
		if args.mode == "bin":
			print(f"Uploading binary \"{args.file.name}\"...")
			psx.upload_file(args.file, args.addr)
		elif args.mode == "exe":
			print(f"Uploading PSX executable \"{args.file.name}\"...")
			psx.upload_exe(args.file)
		elif args.mode == "dump":
			print(f"Dumping 0x{args.size:X} bytes @ 0x{args.addr:08X} to \"{args.file.name}\"...")
			psx.dump(args.file, args.addr, args.size)
		elif args.mode == "goto":
			print(f"Going to address 0x{args.addr:08X}...")
			psx.goto(args.addr)
		elif args.mode == "reboot":
			print("Rebooting PSX...")
			psx.reboot()

	print("Done!")

	return 0

if __name__ == "__main__":
	exit(main())
	
	
