# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Copyright (c) 2011 Andoni Morales Alstruey <ylatuya@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import stat
import errno
import logging
import tempfile
import shutil
import os

import fuse

from musclofs.errors import PathNotFound


class MuscloStat(fuse.Stat):

  def __init__(self):
      self.st_mode = 0 
      self.st_ino = 0
      self.st_dev = 0
      self.st_nlink = 0
      self.st_uid = 0
      self.st_gid = 0
      self.st_size = 0
      self.st_atime = 0
      self.st_mtime = 0
      self.st_ctime = 0


class MuscloNode(MuscloStat):

    stat = None

    def __init__(self, name):
        self.stat = MuscloStat()
        self.name = name


class MuscloFile(MuscloNode):

    backend = None

    def __init__(self, name, backend):
        MuscloNode.__init__(self, name)
        self.stat.st_mode = stat.S_IFREG | 0755
        self.backend = backend


class MuscloDirectory(MuscloNode):

    _files = None

    def __init__(self, name):
        MuscloNode.__init__(self, name)
        self.stat.st_mode = stat.S_IFDIR | 0755
        self.stat.st_nlink = 2
        self.stat.st_size = 4096
        self._files = {}

    def add_file(self, m_file):
        self._files[m_file.name] = m_file

    def get_file(self, path):
        try:
            return self._files[path]
        except KeyError:
            raise PathNotFound()

    def remove_file(self, path):
        try:
            del self._files[path]
        except KeyError:
            pass

    def get_dirents(self):
        dirents = ['.', '..'] + self._files.keys()
        logging.debug("Getting dirs: %s", dirents)
        return dirents


class MuscloRoot(MuscloDirectory):

    _backends_list = None

    def __init__(self):
        MuscloDirectory.__init__(self, 'ROOT')
        self._backends_list = []

    def add_backend(self, backend):
        self._backends_list.append(backend)

    def get_dirents(self):
        dirents = MuscloDirectory.get_dirents(self) + self._backends_list
        logging.debug("Getting root dirs: %s", dirents)
        return dirents


class Store(object):

    _backends = None
    _root = None

    def __init__(self):
        self._backends = dict()
        self._root = MuscloRoot()

    def add_backend(self, backend):
        if backend.name in self._backends:
            log.Error("Backend %s already exists", backend)
        self._backends[backend.name] = backend
        self._root.add_backend(backend.name)

    def find_backend(self, path):
        is_root, backend, path = self._parse_path(path)
        try:
            return self._backends[backend]
        except Exception, e:
            return None

    def get_path(self, path):
        is_root, backend, path = self._parse_path(path)
        logging.debug("Store::get_path is_root:%s, backend:%s, path:%s" %
                      (is_root, backend, path))
        if is_root:
            return self._root
        if backend not in self._backends:
            raise PathNotFound()
        return self._backends[backend].get_file(path)

    def remove_path(self, path):
        is_root, backend, path = self._parse_path(path)

        if is_root:
            raise PathNotRemovable()
        if backend not in self._backends:
            raise PathNotFound()
        try:
            self._backends[backend].remove_file(path)
        except Exception, e:
            logging.error("Error removing path %s", path)

    def _parse_path(self, path):
        elements = path.split('/')[1:]
        logging.debug(str(elements))
        if elements[0] == '':
            return (True, None, None)
        backend = elements[0]
        try:
            path = '/'.join(elements[1:])
        except:
            path = None
        return False, backend, path


class MusCloFS(fuse.Fuse):
    """
    """

    def __init__(self, backends, *args, **kwargs):
        fuse.Fuse.__init__(self, *args, **kwargs)
        self.store = Store()
        for backend in backends:
            backend.start()
            self.store.add_backend(backend)

    def getattr(self, path):
        """
        """
        logging.info('getattr: %s' % path)
        try:
            node = self.store.get_path(path)
        except PathNotFound, e:
            logging.error('Path not found %s' % path)
            return -errno.ENOENT
        return node.stat

    def readdir(self, path, offset):
        logging.info('readdir %s' % path)
        try:
            dir = self.store.get_path(path)
        except PathNotFound, e:
            yield -errno.ENOENT
        for r in dir.get_dirents():
            yield fuse.Direntry(r)

    def chmod ( self, path, mode ):
        print '*** chmod', path, oct(mode)
        return -errno.ENOSYS

    def chown ( self, path, uid, gid ):
        print '*** chown', path, uid, gid
        return -errno.ENOSYS

    def fsync ( self, path, isFsyncFile ):
        print '*** fsync', path, isFsyncFile
        return -errno.ENOSYS

    def link ( self, targetPath, linkPath ):
        print '*** link', targetPath, linkPath
        return -errno.ENOSYS

    def mkdir ( self, path, mode ):
        print '*** mkdir', path, oct(mode)
        return -errno.ENOSYS

    def mknod ( self, path, mode, dev ):
        print '*** mknod', path, oct(mode), dev
        return -errno.ENOSYS

    def readlink ( self, path ):
        print '*** readlink', path
        return -errno.ENOSYS

    def rename ( self, oldPath, newPath ):
        print '*** rename', oldPath, newPath
        return -errno.ENOSYS

    def rmdir ( self, path ):
        print '*** rmdir', path
        return -errno.ENOSYS

    def statfs ( self ):
        print '*** statfs'
        return -errno.ENOSYS

    def symlink ( self, targetPath, linkPath ):
        print '*** symlink', targetPath, linkPath
        return -errno.ENOSYS

    def truncate ( self, path, size ):
        print '*** truncate', path, size
        return -errno.ENOSYS

    def unlink ( self, path ):
        logging.info('unlink', path)
        try:
            file = self.store.get_path(path)
            file.backend.delete(file)
            self.store.remove_path(path)
        except Exception, e:
            return -errno.ENOENT

    def utime ( self, path, times ):
        print '*** utime', path, times
        return -errno.ENOSYS

    def main(self, *a, **kw):
        self.file_class = MuscloFSFile
        MuscloFSFile.myFS = self
        return fuse.Fuse.main(self, *a, **kw)

"""
The S3File Class.  fuse-python creates an instance of this class every time a
file is opened.
"""
class MuscloFSFile(object):

    myFS = None
    backend = None

    def __init__(self, path, flags, *mode):
        logging.debug("New MuscloFSFile for %s", path)
        _m, self.tmpfilename = tempfile.mkstemp();
        self.file = open(self.tmpfilename, "r+b")
        self.path = path

        self.backend = self.myFS.store.find_backend(path)
        # File Exists -> writting/downloading
        try:
            self.fs_file = self.myFS.store.get_path(path)
            self.upload = False
        # File do not exists -> reading/uploading
        except Exception, e:
            self.upload = True

        if not self.upload:
            logging.error("UPLOADING")
            self.file.close()
            self.backend.download(self.fs_file, self.file.name)
            self.file = open(self.tmpfilename, "r+b")
            self.fs_file.stat.st_size = os.stat(self.file.name)[stat.ST_SIZE]
        else:
            self.fs_file = self.backend.new_file(path)

    def read(self, length, offset):
        logging.debug("read %s %d", self.path, length)
        self.file.seek(offset)
        buf = self.file.read(length)
        return buf 

    def write(self, buf, offset):
        logging.debug("write %s", self.path)
        if ((offset + len(buf)) > (5 * 1024 * 1024 * 1024)):
            return -errno.EFBIG

        self.file.seek(offset)
        self.file.write(buf)
        # TODO: is this needed?
        self.file.flush()
        return len(buf)

    def release(self, flags):
        logging.debug("release %s", self.path)
        if self.upload:
            try:
                self.backend.upload(self.fs_file, self.file)
            except Exception, e:
                print str(e)
                logging.error(str(e))
        self.file.close()

    def flush(self):
        logging.debug("flush %s", self.path)
        self.file.flush()

    def fsync(self, isfsyncfile):
        logging.debug("fsync %s", self.path)
        # the python documentation suggests flushing first
        self.file.flush()
        os.fsync(self.file.fileno())

    def fgetattr(self):
        logging.debug("fgetattr%s", self.path)
        return self.fs_file.stat

    # truncate in cache file and set dirty flags
    # file will be uploaded on closing
    def ftruncate(self, len):
        logging.debug("ftruncate %s", self.path)
        self.file.truncate(len)
        self.node.size = len
        self.node.isDirty = True


class TemporalTrack():
    title = ""
