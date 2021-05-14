#!/usr/bin/env python2
# encoding: utf-8
#
# Copyright (c) 2020 Dean Jackson <deanishe@deanishe.net>
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2020-05-03
#

"""Generate appropriately-coloured icons."""

from __future__ import print_function, absolute_import

import logging
import os

log = logging.getLogger(__name__)


class Icons(object):
    """Create coloured icons based on a mask image."""

    def __init__(self, dirpath, default='icon.png', template='icon.png'):
        """Create new icon loader/generator."""
        self.dirpath = dirpath
        self.default = default
        self.template = template

    def get_icon(self, colour, default=None):
        """Return icon for ``colour`` or ``default`` if it doesn't exist."""
        default = default or self.default
        path = self._icon_path(colour)
        return path if os.path.exists(path) else default

    def create_icon(self, colour, template=None):
        """Create a new icon for ``colour`` based on ``template``."""
        template = template or self.template
        if not template:
            raise ValueError('no template specified')

        path = self._icon_path(colour)
        if os.path.exists(path):
            return path

        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        log.debug('[icons] generating icon %s ...', path)
        _write_image(template, path, colour)
        return path

    def _icon_path(self, colour):
        """Return path for image based on colour."""
        elems = [str(hash(n)) for n in colour]
        filename = '-'.join(elems) + '.png'
        dirname = os.path.join(*elems)
        return os.path.join(self.dirpath, dirname, filename)


def _write_image(template, outfile, colour):
    """Make a copy of template image with given colour.

    A new image is created at ``outfile`` with the opaque parts of
    ``template`` replaced with ``colour``.

    Args:
        template (unicode): Path to template image.
        outfile (unicode): Path to image to create.
        colour (list): (r, g, b, a) values for NSColor of new image.

    """
    from Cocoa import (
        NSBitmapImageRep,
        NSColor,
        NSCompositeSourceIn,
        NSImage,
        NSPNGFileType,
        NSRectFillUsingOperation,
    )

    tint = NSColor.colorWithDeviceRed_green_blue_alpha_(*colour)
    mask = NSImage.alloc().initWithContentsOfFile_(template)
    dest = mask.copy()
    dest.lockFocus()
    tint.set()

    rect = (0, 0), dest.size()
    NSRectFillUsingOperation(rect, NSCompositeSourceIn)
    dest.unlockFocus()
    rep = NSBitmapImageRep.imageRepWithData_(dest.TIFFRepresentation())
    data = rep.representationUsingType_properties_(NSPNGFileType, {})
    data.writeToFile_atomically_(outfile, False)


def cache_path(colour):
    """Return *relative* cache path for image based on colour."""
    elems = [str(hash(n)) for n in colour]
    filename = '-'.join(elems) + '.png'
    dirname = os.path.join(*elems)
    return os.path.join(dirname, filename)


def main():
    """Run script."""
    logging.basicConfig(
        format='%(filename)s:%(lineno)s %(levelname)-8s %(message)s'
    )
    logging.getLogger().setLevel(logging.DEBUG)
    mask = 'icon.png'
    temp = 'temp.png'
    # iCloud default
    colour = (0.10526836663484573, 0.6784334182739258, 0.9730395674705505, 1)
    # Sonarr
    colour = (0.6203451156616211, 0.8828734755516052, 0.9091058373451233, 1)
    # Work
    colour = (0.2067018747329712, 0.8234491944313049, 0.5591840147972107, 1)
    log.info('colour=%r', colour)
    log.info('hash=%r', [hash(f) for f in colour])
    log.info('path=%r', cache_path(colour))
    _write_image(mask, temp, colour)
    log.info('wrote %s', temp)


if __name__ == '__main__':
    main()
