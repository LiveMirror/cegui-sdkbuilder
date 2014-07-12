#!/usr/bin/env python2
##############################################################################
#   CEGUI SDK build script for Windows
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

# TODO:
# - mingw debug build


class CEGUISDK:
    def __init__(self, args):
        self.args = args
        self.artifactsPath = args.artifacts_dir
        self.srcDir = os.path.join(self.args.temp_dir, "cegui")
        build_utils.setupPath(self.artifactsPath, False)
        build_utils.setupPath(self.srcDir)

    def cloneRepo(self):
        print "*** Cloning CEGUI repository ..."
        build_utils.hgClone(self.args.url, self.srcDir)

    def build(self):
        old_path = os.getcwd()
        os.chdir(self.srcDir)

        depsStartTime = time.time()
        print "*** Building CEGUI ..."

        for (compiler, generator, commands) in self.getCompilers():
            compilerStartTime = time.time()
            print "\n*** Using '%s' compiler..." % compiler
            buildDir = os.path.join(self.srcDir, "build" + compiler)
            build_utils.setupPath(buildDir)
            os.chdir(buildDir)

            extraCMakeArgs = [
                "-DCMAKE_PREFIX_PATH=" +
                os.path.join(self.artifactsPath, build_utils.generateCEGUIDependenciesDirName(compiler)),
                "-DCEGUI_SAMPLES_ENABLED=FALSE",
                "-DCEGUI_BUILD_LUA_GENERATOR=FALSE",
                "-DCEGUI_BUILD_LUA_MODULE=FALSE",
                "-DCEGUI_BUILD_PYTHON_MODULES=FALSE",
                "-DCEGUI_BUILD_TESTS=FALSE",
                ]

            if build_utils.invokeCMake(self.srcDir, generator, extraCMakeArgs) != 0:
                print "*** Could not find dependencies for '%s', skipping..." % compiler
                continue

            for command in commands:
                print "*** Executing compiler command: ", command
                subprocess.Popen(command).wait()

            print "*** Compilation using '%s' took %f minutes." % (compiler, (time.time() - compilerStartTime) / 60.0)
            self.gatherLibs(compiler)

        print "*** CEGUI Dependencies total build time: ", (time.time() - depsStartTime / 60.0), "minutes."
        os.chdir(old_path)

    def gatherLibs(self, compiler):
        print "*** Gathering libraries of CEGUI for '%s' compiler ..." % compiler
        if not os.path.isdir("bin") or not os.path.isdir("lib"):
            print "*** ERROR: no 'bin' and 'lib' directory found, nothing generated?"
            return

        artifactDirName = build_utils.generateCEGUISDKDirName(compiler)
        artifactZipName = artifactDirName + ".zip"

        dir_util.copy_tree(os.path.join(self.srcDir, "cegui/include"), "include")
        build_utils.makeZip(["bin", "lib", "include"], artifactZipName, [".*\\.ilk"])
        shutil.copyfile(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print "*** Done gathering libraries for CEGUI."

    @staticmethod
    def getMSVCCompiler(version):
        return ('msvc' + str(version),
                "Visual Studio " + (str(version) if version > 9 else '9 2008'),
                [build_utils.generateMSBuildCommand("cegui.sln", config) for config in ["RelWithDebInfo", "Debug"]])

    def getCompilers(self):
        return [
            item for sublist in
            [
                [('mingw', 'MinGW Makefiles', [build_utils.generateMingwMakeCommand()])],
                [self.getMSVCCompiler(x) for x in list(xrange(9, 13))]
            ]
            for item in sublist
        ]


if __name__ == "__main__":
    build_utils.ensureCanBuildOnWindows()

    currentPath = os.getcwd()

    parser = argparse.ArgumentParser(description="Build CEGUI for Windows.")
    parser.add_argument("--url", default="https://bitbucket.org/cegui/cegui",
                        help="URL or path to the mercurial dependencies repository.")
    parser.add_argument("--temp-dir", default=os.path.join(currentPath, "local-temp"),
                        help="Temporary directory where to store intermediate output.")
    parser.add_argument("--artifacts-dir", default=os.path.join(currentPath, "artifacts"),
                        help="Directory where to store the final SDK artifacts")
    parser.add_argument("--dependencies-dir", default=os.path.join(currentPath, "artifacts"),
                        help="Directory where to find CEGUI dependencies. The directory needs to contain a subdirectory "
                             "named '%s', where X is a compiler: mingw or msvc9 through msvc12."
                             "The CEGUI SDK will be built only for compilers which have their dependencies built." %
                             build_utils.generateCEGUIDependenciesDirName('X'))

    parsedArgs = parser.parse_args()
    print "*** Using args: "
    for key, value in vars(parsedArgs).iteritems():
        print '     ', key, '=', value

    ceguiSDK = CEGUISDK(parsedArgs)
    ceguiSDK.cloneRepo()
    ceguiSDK.build()