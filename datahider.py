#!/usr/bin/env python2

############################################################################
#    Encodes / Decodes data into/from image (bmp & png & gif only)
#    Copyright (C) 2011 Shaun Ren
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

# Script parameters
VER_MAJOR, VER_MINOR = 0, 1
MAGIC = (b'\xa0', b'\xb1', b'\xc2', b'\xd3')

isvalidfile = lambda s: (os.path.exists(s) and os.path.isfile(s))

# the 9th bit is an even parity bit i.e. B1 ^ ... ^ B8 ^ PB = 0 if correct
# decodes a byte (return an integer)
def decode_byte(pixels, index):
    assert index >= 0, 'Index underflow'
    assert (index+1) * 3 < len(pixels), 'Index overflow'
    
    p = pixels[index*3:index*3 + 3]
    curbyte = 0
    paritybit = 0
    for i in range(3):
        for j in range(3):
            if i == 2 and j == 2:
                if (paritybit ^ (p[2][2] & 1)) != 0:
                    print 'Corrupted data - Parity bit check failed.'
                    exit(-1)
                break

            bitset = p[i][j] & 1
            paritybit ^= bitset
            curbyte |= bitset << (i*3 + j)
    return curbyte

# decodes a series of bytes in [start, end)
def decode_bytes(pixels, start, end):
    assert start >= 0, 'Index underflow'
    assert end * 3 <= len(pixels), 'Index overflow'

    data = b''
    
    for i in range(start, end):
        data += chr(decode_byte(pixels, i))

    return data

def decode_file(img):
    data = b''
    pixels = list(img.getdata())

    for i in range(len(MAGIC)):
        #print decode_byte(pixels, i)
        if decode_byte(pixels, i) != ord(MAGIC[i]):
            print 'Corrupted header - Invalid MAGIC.'
            exit(-1)

    vermaj,vermin = decode_byte(pixels, 4), decode_byte(pixels, 5)
    if vermaj > VER_MAJOR:
        print 'Version not supported.'
        exit(-1)
    elif vermaj == VER_MAJOR and vermin > VER_MINOR:
        cont = raw_input('The file is encoded using a newer version of this script. Continue decoding? [y/N]').strip().lower()
        if cont != 'y':
            print 'Decoding canceled.'
            return
    
    size = 0
    for i in range(4):
        size |= decode_byte(pixels, i+6) << (i*8)

    md5sum = decode_bytes(pixels, 10,26)
    fn_len = decode_byte(pixels, 26)

    if fn_len < 1:
        print 'Invalid filename length.'
        exit(-1)

    filename = decode_bytes(pixels,27,27+fn_len)
    if (size*3 + fn_len + 27) > len(pixels):
        print 'Corrupted data - length too short.'
        exit(-1)

    raw = decode_bytes(pixels, 27+fn_len, 27+fn_len+size)

    m = hashlib.md5()
    m.update(raw)
    if m.digest() != md5sum:
        print 'Corrupted data - Invalid md5sum.'
        exit(-1)

    print filename + '\t\t\tSize: ' + locale.format('%d', size, grouping=True) + ' bytes'
    print 'md5sum:', m.hexdigest()
    with open(filename, 'wb') as f:
        f.write(raw)

    print 'Decoding successful.'

# header format (LSB for all numbers)
# magic (4 bytes)
# version (2 bytes) (major minor)
# size (4 bytes)
# md5 (16 bytes)
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
    
    if (size*3 + len(fn) + 27) > (img.size[0] * img.size[1]):
        print 'Image is too small for the data.'
        exit(-1)
    elif size <= 0:
        print 'Nothing to be encoded.'
        exit(1)

    raw = b''
    with open(filename, 'rb') as f:
        raw = f.read()
    

    m = hashlib.md5()
    m.update(raw)
    md5sum = m.digest()

    for i in range(4):
        data += chr((size >> (i*8)) & 0xFF)

    data += md5sum
    data += chr(len(fn))
    data += fn

    data += raw

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
                y += 1
                x = 0
    
    return img


def main():
    locale.setlocale(locale.LC_ALL, '')

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print sys.argv[0] + ' ' + str(VER_MAJOR) + '.' + str(VER_MINOR) + \
            ' Encodes/decodes data into/from image.'
        print 'Copyright (C) 2011 Shaun Ren'
        print 'This program comes with ABSOLUTELY NO WARRANTY.'
        print 'This is free software, and you are welcome to redistribute it'
        print 'under certain conditions.'
        print
        print 'Usage: ' + sys.argv[0] + ' [imagein imageout inputfile | -d imagein] '
        exit(1)

    # We store 1 bit of data on every band of every pixel, and the B band of
    # every 3 pixels is parity bit
    decode = False
    imagein = sys.argv[1]
    imageout = ''
    infile = ''

    if imagein == '-d':
        if len(sys.argv) != 3:
            print 'Invalid arguments.'
            exit(1)

        decode = True
        imagein = sys.argv[2]
    else:
        if len(sys.argv) != 4:
            print 'Invalid arguments.'
            exit(1)

        imageout = sys.argv[2]
        infile = sys.argv[3]


    ext = os.path.splitext(imagein)[1].lower()
    if ext != '.bmp' and ext != '.png' and ext != '.gif':
        print 'Invaild picture file. A lossless image format is required.'
        exit(1)
    elif not isvalidfile(imagein):
        print 'Image not valid.'
        exit(1)

    if len(imageout) > 0:
        ext = os.path.splitext(imageout)[1].lower()
        if ext != '.bmp' and ext != '.png' and ext != '.gif':
            print 'Invalid output file. A lossless image format is required.'
            exit(1)

    if decode:
        im = Image.open(imagein)
        if im.size[0] < 100 or im.size[1] < 100:
            print 'Image size too small.'
            exit(-1)
    
        decode_file(im)
    else: # encode
        im = Image.open(imagein)
        if im.size[0] < 100 or im.size[1] < 100:
            print 'Image size too small.'
            exit(-1)

        imout = encode_file(im, infile)
    
        with open(imageout, 'wb') as f:
            imout.save(f)

        print 'Encoding successful.'


if __name__ == '__main__':
    main()
