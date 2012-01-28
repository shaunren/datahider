#!/usr/bin/env python2

############################################################################
#    Encodes / Decodes data into/from image (bmp & png & gif only)
#    Copyright (C) 2011,2012 Shaun Ren
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
############################################################################

import os, sys
import locale
import Image
import hashlib
import argparse

# Script parameters
VER_MAJOR, VER_MINOR = 0, 2
MAGIC = (b'\xa0', b'\xb1', b'\xc2', b'\xd3')

isvalidfile = lambda s: os.path.exists(s) and os.path.isfile(s)

# the 9th bit is an even parity bit i.e. B1 ^ ... ^ B8 ^ PB = 0 if correct
# decodes a byte (return an integer)
def decode_byte(pixels, index):
    assert index >= 0, 'Index underflow'
    assert (index+1) * 3 <= len(pixels), 'Index overflow'
    
    p = pixels[index*3:index*3 + 3]
    curbyte = 0
    paritybit = 0
    for i in range(3):
        for j in range(3):
            if i == 2 and j == 2:
                if (paritybit ^ (p[2][2] & 1)) != 0:
                    print 'Corrupted data - Parity bit check failed.'
                    exit(1)
                break

            bitset = p[i][j] & 1
            paritybit ^= bitset
            curbyte |= bitset << (i*3 + j)
    return curbyte

# decodes a series of bytes in [start, end)
def decode_bytes(pixels, start, end):
    assert start >= 0, 'Index underflow'
    assert end * 3 <= len(pixels), 'Index overflow'

    data = b''.join([chr(decode_byte(pixels, i)) for i in range(start,end)])

    return data

def decode_file(img, outfile=''):
    data = b''
    pixels = list(img.getdata())

    for i in range(len(MAGIC)):
        #print decode_byte(pixels, i)
        if decode_byte(pixels, i) != ord(MAGIC[i]):
            print 'Corrupted header - Invalid MAGIC.'
            exit(1)

    vermaj,vermin = decode_byte(pixels, 4), decode_byte(pixels, 5)
    if vermaj > VER_MAJOR:
        print 'Version not supported.'
        exit(1)
    elif vermaj == VER_MAJOR and vermin > VER_MINOR:
        cont = raw_input('The file is encoded using a newer version of this script. Continue decoding? [y/N]').strip().lower()
        if cont != 'y':
            print 'Decoding canceled.'
            return
    
    size = 0
    for i in range(4):
        size |= decode_byte(pixels, i+6) << (i*8)

    fn_start, usemd5 = 75, False
    if vermaj < 1 and vermin < 2: # uses md5
        usemd5 = True
        checksum = decode_bytes(pixels, 10, 26)
        fn_len, fn_start = decode_byte(pixels, 26), 27
    else:
        checksum = decode_bytes(pixels, 10, 74)
        fn_len = decode_byte(pixels, 74)

    if fn_len < 1:
        print 'Invalid filename length.'
        exit(1)

    filename = decode_bytes(pixels,fn_start,fn_start+fn_len)
    if (size*3 + fn_len + fn_start) > len(pixels):
        print 'Corrupted data - file too small.'
        exit(1)

    raw = decode_bytes(pixels, fn_start+fn_len, fn_start+fn_len+size)

    m = hashlib.md5() if usemd5 else hashlib.sha512()
    m.update(raw)
    if m.digest() != checksum:
        print 'Corrupted data - Invalid checksum.'
        exit(1)

    print 'Filename:', filename
    print 'Size:', locale.format('%d', size, grouping=True), 'bytes'
    print 'md5sum:' if usemd5 else 'sha512sum:', m.hexdigest()
    with open(filename if outfile == '' else outfile, 'wb') as f:
        f.write(raw)

    print 'Decoding successful.'

# header format (LSB for all numbers)
# magic (4 bytes)
# version (2 bytes) (major minor)
# size (4 bytes)
## md5 (16 bytes) (0.1)
# sha512 (64 bytes) (0.2+)
# fn_len (1 byte)
# filename (1~255 depending on fn_len)
def encode_file(img, filename):
    data = ''.join(MAGIC)

    data += chr(VER_MAJOR)
    data += chr(VER_MINOR)

    if not isvalidfile(filename):
        print 'Invalid input file.'
        exit(1)

    size = os.path.getsize(filename)
    fn = os.path.basename(filename)
    
    if (size*3 + len(fn) + 75) > (img.size[0] * img.size[1]):
        print 'Image is too small for the data.'
        exit(1)
    elif size <= 0:
        print 'Nothing to be encoded.'
        exit(1)

    raw = b''
    with open(filename, 'rb') as f:
        raw = f.read()
    
    m = hashlib.sha512()
    m.update(raw)
    checksum = m.digest()

    data += ''.join([chr((size >> (i*8)) & 0xFF) for i in range(4)])
    data += ''.join([checksum, chr(len(fn)), fn, raw])

    pixels = img.load()
    x, y = 0,0
    for i in xrange(len(data)):
        paritybit = 0
        for j in range(3):
            assert y < img.size[1]

            p = list(pixels[x,y])
            for k in range(3):
                if k == 2 and j == 2: # set parity bit
                    if paritybit == 1:
                        p[2] |= 1
                    else:
                        p[2] &= 0xFE
                    break

                bitset = ((ord(data[i]) >> (3*j + k)) & 0x1)
                paritybit ^= bitset

                if bitset == 1:
                    p[k] |= 1
                else:
                    p[k] &= 0xFE # 0b11111110

            pixels[x,y] = tuple(p)
            x += 1
            if x >= img.size[0]:
                x,y = 0, y+1
    
    return img


def main():
    locale.setlocale(locale.LC_ALL, '')

    # argparse
    parser = argparse.ArgumentParser(prog='datahider', 
                 description='Encode/decode data in an image.')
    parser.add_argument('--version', action='version', 
                        version='%(prog)s {}.{}'.format(VER_MAJOR,VER_MINOR))
    parser.add_argument('imagein', metavar='IMAGE', help='image file')
    parser.add_argument('-o', '--output', metavar='OUTFILE', dest='outfile',
                        help='output file', default='')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-d', '--decode', action='store_true',
                       help='decode infile')
    group.add_argument('-e', '--encode', metavar='INFILE', dest='infile',
                       help='encode infile with image')
    group.add_argument('-i', '--info', action='store_true',
                       help='show image info')
    args = parser.parse_args(sys.argv[1:])

    VALID_EXTS = {'.bmp', '.png', '.gif'}
    fn = os.path.splitext(args.imagein)
    if fn[1].lower() not in VALID_EXTS:
        parser.error('Invaild image file. A lossless image format is required.')
    elif not isvalidfile(args.imagein):
        parser.error('Image not found.')

    if not args.decode and len(args.outfile) > 0:
        extout = os.path.splitext(args.outfile)[1].lower()
        if extout not in VALID_EXTS:
            parser.error('Invalid output file. A lossless image format is required.')
            
    if args.decode:
        im = Image.open(args.imagein)
        if im.size[0] * im.size[1] < 228:
            parser.error('Image size too small.')
    
        decode_file(im, args.outfile)
    else: # encode
        im = Image.open(args.imagein)
        if im.size[0] * im.size[1] < 228:
            parser.error('Image size too small.')

        imout = encode_file(im, args.infile)
 
        if args.outfile == '':
            args.outfile = fn[0] + '.out' + fn[1]

        with open(args.outfile, 'wb') as f:
            imout.save(f)

        print 'Encoding successful.'


if __name__ == '__main__':
    main()
