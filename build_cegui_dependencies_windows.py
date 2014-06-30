#!/usr/bin/env python2
##############################################################################
#   CEGUI dependencies build script for Windows
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
import argparse
from distutils import dir_util
import subprocess
import shutil
import os
import time

import build_utils


class CEGUIDependenciesSDK:
    def __init__(self, args):
        self.args = args
        self.artifactsPath = args.artifacts_dir
        if not os.path.exists(self.artifactsPath):
            os.mkdir(self.artifactsPath)
        build_utils.setupPath(self.args.temp_dir)

    def build(self):
        print "*** Cloning repository ..."
        srcDir = os.path.join(self.args.temp_dir, "cegui-dependencies")
        build_utils.hgClone(self.args.url, srcDir)
        self.buildCEGUIDeps(srcDir)

    def buildCEGUIDeps(self, srcDir):
        old_path = os.getcwd()
        os.chdir(srcDir)

        depsStartTime = time.time()
        print "*** Building CEGUI deps ..."

        for (compiler, generator, commands) in build_utils.getCompilers():
            compilerStartTime = time.time()
            print "\n*** Using '%s' compiler..." % compiler
            buildDir = os.path.join(srcDir, "build" + compiler)
            build_utils.setupPath(buildDir)
            os.chdir(buildDir)

            build_utils.invokeCMake(srcDir, generator)
            for command in commands:
                print "*** Executing compiler command: ", command
                subprocess.Popen(command).wait()

            print "*** Compilation using '%s' took %d seconds. " % (compiler, time.time() - compilerStartTime)
            self.gatherDeps(compiler)

        print "*** CEGUI Dependencies total build time: ", (time.time() - depsStartTime), " seconds."
        os.chdir(old_path)

    def gatherDeps(self, compiler):
        print "*** Gathering artifacts for CEGUI dependencies for '%s' compiler ..." % compiler
        if not os.path.isdir("dependencies"):
            print "*** ERROR: no dependencies directory found, nothing generated?"
            return

        artifactDirName = "dependencies_" + compiler
        artifactZipName = artifactDirName + ".zip"

        build_utils.makeZip("dependencies", artifactZipName)
        dir_util.copy_tree("dependencies", os.path.join(self.artifactsPath, artifactDirName))
        shutil.copyfile(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))


if __name__ == "__main__":
    build_utils.ensureCanBuildOnWindows()

    currentPath = os.path.abspath(os.path.join(os.path.dirname(__file__)))

    parser = argparse.ArgumentParser(description="Build CEGUI dependencies for Windows.")
    parser.add_argument("--url", default="https://bitbucket.org/cegui/cegui-dependencies",
                        help="URL or path to the mercurial dependencies repository.")
    parser.add_argument("--temp-dir", default=os.path.join(currentPath, "local-temp"),
                        help="Temporary directory where to store intermediate output.")
    parser.add_argument("--artifacts-dir", default=os.path.join(currentPath, "artifacts"),
                        help="Directory where to store the final SDK artifacts")

    args = parser.parse_args()
    print "*** Using args: "
    for key, value in vars(args).iteritems():
        print '     ', key, '=', value

    CEGUIDependenciesSDK(args).build()