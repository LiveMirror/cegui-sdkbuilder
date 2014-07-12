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
from itertools import chain
import subprocess
import shutil
import os
import time

import build_utils


#TODO:
# - mingw debug build

class CEGUIDependenciesSDK:
    def __init__(self, args):
        self.args = args
        self.artifactsPath = args.artifacts_dir
        self.srcDir = os.path.join(self.args.temp_dir, "cegui-dependencies")
        if not os.path.exists(self.artifactsPath):
            os.mkdir(self.artifactsPath)
        build_utils.setupPath(self.srcDir)

    def cloneRepo(self):
        print "*** Cloning dependencies repository ..."
        build_utils.hgClone(self.args.url, self.srcDir)

    def build(self):
        self.buildCEGUIDeps()

    def buildCEGUIDeps(self):
        old_path = os.getcwd()
        os.chdir(self.srcDir)

        depsStartTime = time.time()
        print "*** Building CEGUI dependencies ..."

        for (compiler, generator, commands) in self.getCompilers():
            compilerStartTime = time.time()
            print "\n*** Using '%s' compiler..." % compiler
            buildDir = os.path.join(self.srcDir, "build" + compiler)
            build_utils.setupPath(buildDir)
            os.chdir(buildDir)

            if build_utils.invokeCMake(self.srcDir, generator) != 0:
                print "*** Error configuring CMake for ", compiler, "skipping ..."
                continue

            for command in commands:
                print "*** Executing compiler command: ", command
                subprocess.Popen(command).wait()

            print "*** Compilation using '%s' took %f minutes." % (compiler, (time.time() - compilerStartTime) / 60.0)
            self.gatherDeps(compiler)

        print "*** CEGUI Dependencies total build time: ", (time.time() - depsStartTime) / 60.0, "minutes."
        os.chdir(old_path)

    def gatherDeps(self, compiler):
        print "*** Gathering artifacts for CEGUI dependencies for '%s' compiler ..." % compiler
        if not os.path.isdir("dependencies"):
            print "*** ERROR: no dependencies directory found, nothing generated?"
            return

        artifactDirName = build_utils.generateCEGUIDependenciesDirName(compiler)
        artifactZipName = "%s-%s-%s.zip" % (
            artifactDirName, time.strftime("%Y%m%d"), build_utils.getHgRevision(self.srcDir))

        dir_util.copy_tree("dependencies", os.path.join(self.artifactsPath, artifactDirName))
        build_utils.makeZip(["dependencies"], artifactZipName, [".*\\.ilk"])
        shutil.copyfile(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print "*** Done gathering artifacts for CEGUI dependencies."

    @staticmethod
    def getMSVCCompiler(version):
        return ('msvc' + str(version),
                "Visual Studio " + (str(version) if version > 9 else '9 2008'),
                list(chain.from_iterable(
                    (
                        # dftables is required to be built first to prevent any problems later on
                        build_utils.generateMSBuildCommand(
                            "src/pcre-8.12/CEGUI-BUILD/dftables." + ("vcxproj" if version > 9 else "vcproj"), config),
                        build_utils.generateMSBuildCommand("CEGUI-DEPS.sln", config)
                    ) for config in ["RelWithDebInfo", "Debug"])))

    @staticmethod
    def getMingwCompiler():
        return ('mingw', 'MinGW Makefiles',
                 [build_utils.generateMingwMakeCommand('dftables'), build_utils.generateMingwMakeCommand()])

    def getCompilers(self):
        return [
            item for sublist in
            [
                [self.getMingwCompiler()],
                [self.getMSVCCompiler(x) for x in list(xrange(9, 13))]
            ]
            for item in sublist
        ]


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

    parsedArgs = parser.parse_args()
    print "*** Using args: "
    for key, value in vars(parsedArgs).iteritems():
        print '     ', key, '=', value

    depsSDK = CEGUIDependenciesSDK(parsedArgs)
    depsSDK.cloneRepo()
    depsSDK.build()