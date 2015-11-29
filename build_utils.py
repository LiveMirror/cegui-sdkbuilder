##############################################################################
#   CEGUI SDK Builder build utils
#
#   Copyright (C) 2014-2015   Timotei Dolean <timotei21@gmail.com>
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

import fnmatch
from distutils import spawn
import multiprocessing
import os
import subprocess
import zipfile
import shutil
import re


def hasExe(name):
    return spawn.find_executable(name) is not None


def ensureCanBuildOnWindows():
    def ensureHasExe(name):
        if not hasExe(name):
            print("No program named '%s' could be found on PATH! Aborting... " % name)
            exit(1)

    ensureHasExe('msbuild')
    ensureHasExe('cmake')
    ensureHasExe('mingw32-make')
    ensureHasExe('hg')


def setupPath(path, cleanExisting=True):
    if cleanExisting and os.path.isdir(path):
        print("*** Cleaning up '%s' ... " % path)
        shutil.rmtree(path)

    if not os.path.exists(path):
        print("*** Creating path '%s' ..." % path)
        os.makedirs(path)


def makeZip(sources, zipName, patternsToIgnore=None):
    def shouldIgnorePath(path):
        for pattern in patternsToIgnore:
            if re.match(pattern, path):
                return True

        return False

    if not patternsToIgnore:
        patternsToIgnore = []
    zipFile = zipfile.ZipFile(zipName, 'w', zipfile.ZIP_DEFLATED)
    print("*** Creating zip archive in", zipName, "with sources", sources, "...")

    for source in sources:
        for root, dirs, files in os.walk(source):
            if shouldIgnorePath(root):
                continue

            for file in files:
                if not shouldIgnorePath(file):
                    zipFile.write(os.path.join(root, file))

    zipFile.close()


def invokeCMake(sourceDir, generator, extraParams=None):
    if not extraParams:
        extraParams = []

    cmakeCmd = ["cmake", "-G", generator]
    cmakeCmd.extend(extraParams)
    cmakeCmd.append(sourceDir)

    print("*** Invoking CMake '%s' ..." % cmakeCmd)
    cmakeProc = subprocess.Popen(cmakeCmd).wait()
    print("*** CMake generation return code:", cmakeProc)
    return cmakeProc


def invokeDoxygen(doxygenBuildDir):
    oldWorkingDirectory = os.getcwd()
    os.chdir(doxygenBuildDir)

    print("*** Invoking doxygen on folder '%s' ..." % doxygenBuildDir)
    doxygenCommand = ["doxygen", os.path.join(doxygenBuildDir, "doxyfile")]
    doxygenProc = subprocess.Popen(doxygenCommand).wait()
    print("*** Doxygen return code:", doxygenProc)

    os.chdir(oldWorkingDirectory)


def hgClone(url, target, rev="default"):
    print("*** Cloning from '%s' to '%s' ..." % (url, target))
    assert subprocess.Popen(["hg", "clone", url, target, "--rev", rev]).wait() == 0


def getHgRevision(repoDir, length=6):
    p = subprocess.Popen(["hg", "id", "--id", repoDir], stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.rstrip()[:length]


def getCompilerFriendlyName(compiler):
    friendlyNames = {
        "msvc9": "msvc2008",
        "msvc10": "msvc2010",
        "msvc11": "msvc2012",
        "msvc12": "msvc2013",
        "msvc14": "msvc2015",
        "mingw": "mingw"
    }

    if compiler in friendlyNames:
        return friendlyNames[compiler]

    return compiler


def generateCEGUIDependenciesDirName(compiler):
    return "cegui-dependencies-" + compiler


def generateMSBuildCommand(filename, configuration):
    return ["msbuild", filename, "/p:Configuration=" + configuration, "/maxcpucount", "/m", "/verbosity:minimal",
            "/fl", "/flp:logfile=build%s.log" % configuration]


def generateMingwMakeCommand(target=None):
    command = ["mingw32-make", "-j", str(multiprocessing.cpu_count())]
    if target is not None:
        command.append(target)
    return command


def doCopy(src, dst, ignore=None):
    print("*** From", src, "to", dst, "...")
    if not os.path.isdir(src):
        print("*** ERROR: no", dir, "directory found as source, nothing will be copied!")
        return

    copytree(src, dst, ignore)


def ignoreNonMatchingFiles(*patterns):
    def _ignore_patterns(path, names):
        ignored_names = []
        for pattern in patterns:
            ignored_names.extend(set(names).difference(fnmatch.filter(names, pattern)))
        return set(ignored_names)
    return _ignore_patterns


def copyFiles(src, dst):
    if not os.path.exists(dst):
        os.mkdir(dst)

    for item in os.listdir(src):
        srcPath = os.path.join(src, item)
        dstPath = os.path.join(dst, item)

        if os.path.isdir(srcPath):
            continue

        shutil.copy2(srcPath, dstPath)


def copytree(src, dst, ignore=None):
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    if os.path.isdir(src) and not os.path.isdir(dst):
        os.makedirs(dst)

    for name in names:
        srcname = os.path.join(src, name)
        if not os.path.isdir(srcname) and name in ignored_names:
            continue

        dstname = os.path.join(dst, name)
        if os.path.isdir(srcname):
            copytree(srcname, dstname, ignore)
        else:
            shutil.copy2(srcname, dstname)
