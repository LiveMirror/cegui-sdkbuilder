##############################################################################
#   CEGUI SDK Builder build utils
#
#   Copyright (C) 2014        Timotei Dolean <timotei21@gmail.com>
#                             and contributing authors (see AUTHORS file)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################
from __future__ import print_function
from distutils import spawn
import multiprocessing
import os
import subprocess
import zipfile
import shutil
import re


def setupPath(path, cleanExisting=True):
    if cleanExisting and os.path.isdir(path):
        print("*** Cleaning up '%s' ... " % path)
        shutil.rmtree(path)

    if not os.path.exists(path):
        print("*** Creating path '%s' ..." % path)
        os.makedirs(path)


def ensureCanBuildOnWindows():
    def has_exe(name):
        if spawn.find_executable(name) is None:
            print("No program named '%s' could be found on PATH! Aborting... " % name)
            exit(1)
        return True

    has_exe('msbuild')
    has_exe('cmake')
    has_exe('mingw32-make')
    has_exe('hg')

#TODO: add deflate compression
def makeZip(sources, zipName, patternsToIgnore=None):
    if not patternsToIgnore:
        patternsToIgnore = []
    zipFile = zipfile.ZipFile(zipName, 'w')
    print("*** Creating zip archive in", zipName, " with sources ", sources, "...")

    for source in sources:
        for root, dirs, files in os.walk(source):
            for _file in files:
                skip = False
                for pattern in patternsToIgnore:
                    if re.match(pattern, _file):
                        skip = True
                        break

                if not skip:
                    zipFile.write(os.path.join(root, _file))

    zipFile.close()


def invokeCMake(sourceDir, generator, extraParams=None):
    if not extraParams:
        extraParams = []

    cmakeCmd = ["cmake", "-G", generator]
    cmakeCmd.extend(extraParams)
    cmakeCmd.append(sourceDir)

    print("*** Invoking CMake '%s' ..." % cmakeCmd)
    cmakeProc = subprocess.Popen(cmakeCmd).wait()
    print("*** CMake generation return code: ", cmakeProc)
    return cmakeProc


def hgClone(url, target, rev="default"):
    print("*** Cloning from '%s' to '%s' ..." % (url, target))
    assert(subprocess.Popen(["hg", "clone", url, target, "--rev", rev]).wait() == 0)


def getHgRevision(repoDir, length=6):
    p = subprocess.Popen(["hg", "id", "--id", repoDir], stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.rstrip()[:length]


def generateCEGUIDependenciesDirName(compiler):
    return "cegui-dependencies-" + compiler


def generateMSBuildCommand(filename, configuration):
    return ["msbuild", filename, "/p:Configuration=" + configuration, "/maxcpucount"]


def generateMingwMakeCommand(target=None):
    command = ["mingw32-make", "-j", str(multiprocessing.cpu_count())]
    if target is not None:
        command.append(target)
    return command
