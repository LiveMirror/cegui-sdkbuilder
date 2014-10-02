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
from __future__ import print_function
import collections
from distutils import dir_util
import shutil
import os
import time
import build_utils
from sdk_builder import SDKBuilder, BuildDetails, CMakeArgs


class CEGUIDependenciesSDK(SDKBuilder):
    def __init__(self, args):
        SDKBuilder.__init__(self, args, "cegui-dependencies")

    def gatherArtifacts(self, compiler, builds):
        print("*** Gathering artifacts for CEGUI dependencies for '%s' compiler ..." % compiler)

        artifactDirName = build_utils.generateCEGUIDependenciesDirName(builds[0].friendlyName)
        artifactZipName = "%s-%s-%s.zip" % (
            artifactDirName, time.strftime("%Y%m%d"), build_utils.getHgRevision(self.srcDir))
        depsGatherPath = os.path.join(self.artifactsUnarchivedPath, artifactDirName)

        #TODO: skip STATIC libs
        for build in builds:
            depsPath = os.path.join(self.srcDir, build.buildDir, "dependencies")
            print("*** From ", depsPath, " to", depsGatherPath, "...")
            if not os.path.isdir(depsPath):
                print("*** ERROR: no dependencies directory found, nothing will be generated!")
                return

            dir_util.copy_tree(depsPath, depsGatherPath)

        os.chdir(self.artifactsUnarchivedPath)
        build_utils.makeZip([artifactDirName], artifactZipName, [".*\\.ilk"])
        shutil.move(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print("*** Done gathering artifacts for CEGUI dependencies.")

    def createSDKBuilds(self):
        builds = collections.defaultdict(list)
        extraCMakeArgs = []
        for extraLib in ['CORONA', 'DEVIL', 'FREEIMAGE', 'LUA', 'TINYXML', 'XERCES']:
            extraCMakeArgs.append("-DCEGUI_BUILD_%s=YES" % extraLib)

        configs = ["Debug", "RelWithDebInfo"]
        for config in configs:
            builds["mingw"].append(BuildDetails
                                   ("mingw", "mingw", "build-mingw-" + config,
                                    CMakeArgs("MinGW Makefiles", ["-DCMAKE_BUILD_TYPE=" + config] + extraCMakeArgs),
                                    [build_utils.generateMingwMakeCommand()]))

        msvcCompilers = [(9, "msvc2008"), (10, "msvc2010"), (11, "msvc2012"), (12, "msvc2013")]
        for version, friendlyName in msvcCompilers:
            msvc = "msvc" + str(version)
            builds[msvc].append(BuildDetails
                                (msvc, friendlyName, "build-" + msvc,
                                 CMakeArgs("Visual Studio " + (str(version) if version > 9 else '9 2008'), extraCMakeArgs),
                                 [build_utils.generateMSBuildCommand("CEGUI-DEPS.sln", config) for config in configs]))

        return builds

if __name__ == "__main__":
    build_utils.ensureCanBuildOnWindows()
    currentPath = os.getcwd()

    parser = SDKBuilder.getDefaultArgParse("cegui-dependencies")
    parsedArgs = parser.parse_args()
    # we don't have separate revisions for deps (yet)
    if parsedArgs.revision != "default":
        print("*** Overwriting selected revision with 'default' for dependencies ...")
    parsedArgs.revision = "default"

    print("*** Using args: ")
    for key, value in vars(parsedArgs).iteritems():
        print('     ', key, '=', value)

    depsSDK = CEGUIDependenciesSDK(parsedArgs)
    if not parsedArgs.quick_mode:
        depsSDK.cloneRepo()
    depsSDK.build()
