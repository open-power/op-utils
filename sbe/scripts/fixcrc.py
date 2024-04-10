#!/usr/bin/env python3
# IBM_PROLOG_BEGIN_TAG
# This is an automatically generated prolog.
#
# $Source: public/src/build/utils/fixcrc.py $
#
# OpenPOWER sbe Project
#
# Contributors Listed Below - COPYRIGHT 2024
# [+] International Business Machines Corp.
#
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
#
# IBM_PROLOG_END_TAG
import os, sys, zlib
from typing import BinaryIO, List, Optional, Tuple
# ---- Main application ----
def main(args: List[str]) -> Optional[str]:
	# Handle arguments
	if len(args) != 3:
		return "Usage: python fixcrc.py FileName NewCrc32Value NewFileName"
	try:
		if len(args[1]) != 8 or args[1].startswith(("+", "-")):
			return "Error: Invalid new CRC-32 value"
		temp: int = int(args[1], 16)
		if temp & MASK != temp:
			return "Error: Invalid new CRC-32 value"
		new_crc: int = reverse32(temp)
	except ValueError:
		return "Error: Invalid new CRC-32 value"
	# Process the file
	try:
		modify_file_crc32(args[0], new_crc, args[2], True)
	except IOError as e:
		return "I/O error: " + str(e)
	except ValueError as e:
		return "Error: " + str(e)
	except AssertionError as e:
		return "Assertion error: " + str(e)
	return None
# ---- Main function ----
def modify_file_crc32(path: str, newcrc: int, new_path: str, printstatus: bool = False) -> None:
	data : bytearray = None
	with open(path, "r+b") as raf:
		data = bytearray(raf.read())
	# Read entire file and calculate original CRC-32 value
	crc: int = get_crc32(data)
	if printstatus:
		print(f"Original CRC-32: {reverse32(crc):08X}")
	# Compute the change to make
	delta: int = crc ^ newcrc
	delta = multiply_mod(reciprocal_mod(pow_mod(2, 4 * 8)), delta)
	# Patch 4 bytes in the file
	for i in range(4):
		data[-4 + i] ^= (reverse32(delta) >> (i * 8)) & 0xFF
	if printstatus:
		print("Computed and wrote patch")
	# Recheck entire file
	if get_crc32(data) != newcrc:
		raise AssertionError("Failed to update CRC-32 to desired value")
	elif printstatus:
		print("New CRC-32 successfully verified")
	with open(new_path, "w+b") as raf:
		raf.write(data)
# ---- Utilities ----
POLYNOMIAL: int = 0x104C11DB7  # Generator polynomial. Do not modify, because there are many dependencies
MASK: int = (1 << 32) - 1
def get_crc32(raf: bytearray) -> int:
	crc: int = 0
	offset = 0
	while True:
		try:
			buffer = raf[offset:(offset+ 128 * 1024)]
		except:
			buffer = raf[offset:]
		offset += len(buffer)
		if len(buffer) == 0:
			return reverse32(crc)
		crc = zlib.crc32(buffer, crc)
def reverse32(x: int) -> int:
	y: int = 0
	for _ in range(32):
		y = (y << 1) | (x & 1)
		x >>= 1
	return y
# ---- Polynomial arithmetic ----
# Returns polynomial x multiplied by polynomial y modulo the generator polynomial.
def multiply_mod(x: int, y: int) -> int:
	# Russian peasant multiplication algorithm
	z: int = 0
	while y != 0:
		z ^= x * (y & 1)
		y >>= 1
		x <<= 1
		if (x >> 32) & 1 != 0:
			x ^= POLYNOMIAL
	return z
# Returns polynomial x to the power of natural number y modulo the generator polynomial.
def pow_mod(x: int, y: int) -> int:
	# Exponentiation by squaring
	z: int = 1
	while y != 0:
		if y & 1 != 0:
			z = multiply_mod(z, x)
		x = multiply_mod(x, x)
		y >>= 1
	return z
# Computes polynomial x divided by polynomial y, returning the quotient and remainder.
def divide_and_remainder(x: int, y: int) -> Tuple[int,int]:
	if y == 0:
		raise ValueError("Division by zero")
	if x == 0:
		return (0, 0)
	ydeg: int = get_degree(y)
	z: int = 0
	for i in range(get_degree(x) - ydeg, -1, -1):
		if (x >> (i + ydeg)) & 1 != 0:
			x ^= y << i
			z |= 1 << i
	return (z, x)
# Returns the reciprocal of polynomial x with respect to the modulus polynomial m.
def reciprocal_mod(x: int) -> int:
	# Based on a simplification of the extended Euclidean algorithm
	y: int = x
	x = POLYNOMIAL
	a: int = 0
	b: int = 1
	while y != 0:
		q, r = divide_and_remainder(x, y)
		c = a ^ multiply_mod(q, b)
		x = y
		y = r
		a = b
		b = c
	if x == 1:
		return a
	else:
		raise ValueError("Reciprocal does not exist")
def get_degree(x: int) -> int:
	return x.bit_length() - 1
# ---- Miscellaneous ----
if __name__ == "__main__":
	errmsg = main(sys.argv[1:])
	if errmsg is not None:
		sys.exit(errmsg)
