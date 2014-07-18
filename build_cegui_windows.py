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
from __future__ import print_function
import collections
from distutils import dir_util
import shutil
import os
import time
import build_utils
from sdk_builder import BuildDetails, CMakeArgs, SDKBuilder


class CEGUISDK(SDKBuilder):
    def __init__(self, args):
        SDKBuilder.__init__(self, args, "cegui")

    def gatherArtifacts(self, compiler, builds):
        print("*** Gathering artifacts of CEGUI for '%s' compiler ..." % compiler)

        friendlyName = builds[0].friendlyName
        artifactDirName = "cegui-sdk-%s-%s" % (friendlyName, self.branch)
        artifactZipName = "cegui-sdk-%s-%s-%s-%s.zip" % \
                          (friendlyName, time.strftime("%Y%m%d"), self.branch, build_utils.getHgRevision(self.srcDir))

        depsGatherPath = os.path.join(self.artifactsUnarchivedPath, artifactDirName)

        dirsToGather = ["bin", "lib", "include"]

        for build in builds:
            buildDir = os.path.join(self.srcDir, build.buildDir)
            # copy source-level includes to the built ones
            dir_util.copy_tree(os.path.join(self.srcDir, "cegui/include"), os.path.join(buildDir, "include"))
            dir_util.copy_tree(os.path.join(buildDir, "cegui/include"), os.path.join(buildDir, "include"))

            for dir in dirsToGather:
                dirPath = os.path.join(self.srcDir, build.buildDir, dir)
                dirGatherPath = os.path.join(depsGatherPath, dir)

                print("*** From ", dirPath, " to", dirGatherPath, "...")
                if not os.path.isdir(dirPath):
                    print("*** ERROR: no ", dir, " directory found, nothing will be generated!")
                    return

                dir_util.copy_tree(dirPath, dirGatherPath)

        os.chdir(self.artifactsUnarchivedPath)
        build_utils.makeZip([artifactDirName], artifactZipName, [".*\\.ilk"])
        shutil.move(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print("*** Done gathering artifacts for CEGUI.")

    def generateCEGUISDKDirName(self, friendlyName, branch):
        return "cegui-sdk-%s-%s_%s-%s" %\
               (friendlyName, time.strftime("%Y%m%d"), branch, build_utils.getHgRevision(self.srcDir))

    def createSDKBuilds(self):
        builds = collections.defaultdict(list)
        configs = ["Debug", "RelWithDebInfo"]

        def getDefaultCMakeArgs(compiler):
            return ["-DCMAKE_PREFIX_PATH=" +
                    os.path.join(self.args.dependencies_dir, build_utils.generateCEGUIDependenciesDirName(compiler)),
                    "-DCEGUI_SAMPLES_ENABLED=FALSE",
                    "-DCEGUI_BUILD_LUA_GENERATOR=FALSE",
                    "-DCEGUI_BUILD_LUA_MODULE=FALSE",
                    "-DCEGUI_BUILD_PYTHON_MODULES=FALSE",
                    "-DCEGUI_BUILD_TESTS=FALSE"]

        for config in configs:
            cmakeArgs = ["-DCMAKE_BUILD_TYPE=" + config]
            cmakeArgs.extend(getDefaultCMakeArgs("mingw"))
            builds["mingw"].append(BuildDetails
                                   ("mingw", "mingw", "build-mingw-" + config,
                                    CMakeArgs("MinGW Makefiles", cmakeArgs),
                                    [build_utils.generateMingwMakeCommand()]))
        msvcCompilers = [(9, "msvc2008"), (10, "msvc2010"), (11, "msvc2012"), (12, "msvc2013")]
        for version, friendlyName in msvcCompilers:
            msvc = "msvc" + str(version)
            builds[msvc].append(BuildDetails
                                (msvc, friendlyName, "build-" + msvc,
                                 CMakeArgs("Visual Studio " + (str(version) if version > 9 else '9 2008'), getDefaultCMakeArgs(friendlyName)),
                                 [build_utils.generateMSBuildCommand("cegui.sln", config) for config in configs]))
        return builds

if __name__ == "__main__":
    build_utils.ensureCanBuildOnWindows()
    currentPath = os.getcwd()

    parser = SDKBuilder.getDefaultArgParse("cegui")
    parser.add_argument("--dependencies-dir", default=os.path.join(currentPath, "artifacts", "unarchived"),
                        help="Directory where to find CEGUI dependencies. The directory needs to contain a subdirectory "
                             "named '%s', where X is a compiler: mingw, msvc2008, msvc2010 or msvc2012."
                             "The CEGUI SDK will be built only for compilers which have their dependencies built." %
                             build_utils.generateCEGUIDependenciesDirName('X'))

    parsedArgs = parser.parse_args()
    print("*** Using args: ")
    for key, value in vars(parsedArgs).iteritems():
        print('     ', key, '=', value)

    ceguiSDK = CEGUISDK(parsedArgs)
    if not parsedArgs.quick_mode:
        ceguiSDK.cloneRepo()
    ceguiSDK.build()
