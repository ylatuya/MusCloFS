from datetime import datetime
import sys
import os
import errno
import optparse
import traceback
import logging

import fuse

from musclofs.fs import MusCloFS

fuse.fuse_python_api = (0, 2)

def get_backends():
#    from musclofs.backends.test import TestBackend
#    return [TestBackend()]
    from musclofs.backends.soundcloud import SoundCloudBackend
    return [SoundCloudBackend()]

def setup_logging(foreground):
    l = logging.getLogger("")
    l.setLevel(logging.DEBUG)

    logdir = os.environ.get("HOME") + "/.musclofs/logs/"
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    logfile = logdir + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".err"

    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.WARNING)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s: %(module) 8s (%(lineno)3s) - %(message)s"))
    l.addHandler(fh)

    # also log to stderr if run in foreground mode
    if foreground:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(levelname)-8s: %(module) 8s (%(lineno)3s) - %(message)s"))
        l.addHandler(ch)

    # never show debug or info messages from the boto library
    logging.getLogger("boto").setLevel(logging.WARNING)

def main():
    usage="MusCloFS: A filesystem for music cloud services" +\
          fuse.Fuse.fusage
    args = sys.argv[1:]

    _uid = os.getuid
    _guid = os.getgid

    fs = MusCloFS(get_backends(), version="%prog " + fuse.__version__,
                      usage=usage, dash_s_do='setsingle')
    fs.parser.add_option('-b', '--backends', action='store',
                      type='string', dest='backends',
                      default='test',
                      help='Comma-separated list of backends to use')

    arg_res = fs.parse(values=args, errex=1)

    if arg_res.getmod("showhelp"):
        # help message was already printed, exit
        sys.exit(0)

    setup_logging(arg_res.getmod("foreground"))

    fs.main()
    print >> sys.stderr, "Shutting down"
    shutdown()

if __name__ == "__main__":
    main()
