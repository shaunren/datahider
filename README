datahider.py
------------
By Shaun Ren

## Introduction
datahider.py is a script used to encode/decode data into/from an image by 
manipulating the LSB of every band(R,G,B) of the pixels in the image. This
yields an image that has no noticable difference compared to the original (
both size and visual) yet effectively storing data into the image.

## Usage
 * Encoding data: ./datahider.py <original image> <output image> <data>
 * Decoding data: ./datahider.py -d <image with data>

## Limitations
datahider.py can only store a single file. However, this can be solved by
archiving all the files into a single tarball and possibly compressing it.
This script also does not provide any encryption algorithms, therefore
encrypting the file before encoding is recommended. 

The method used by this script, storing one bit of information on every band,
yields 1 byte of data per three pixels. The script also adds a header of length
76-330 bytes depending on the length of the file name. Therefore, you can store
at least # of pixels / 3 - 330 bytes of data and at most # of pixels / 3 - 76.

    e.g. a photo shot by a 3.1 MP camera (2048 * 1536) can store about
         (2048 * 1536) / 3 - 330 = 1048246 bytes of data, or around 1MB.

## Troubleshooting
This script only works on Python 2.6+ and DOES NOT work on Python 3+.
If you are using an UNIX-like operating system, try changing 'python2' in the
first line to 'python'.