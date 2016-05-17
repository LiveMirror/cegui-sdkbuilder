#!/usr/bin/env python2
##############################################################################
#   CEGUI dependencies build script for Windows
#
#   Copyright (C) 2014-2016   Timotei Dolean <timotei21@gmail.com>
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
import re
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

        artifactDirName = build_utils.generateCEGUIDependenciesDirName(builds[0].compiler)
        artifactZipName = "%s-%s-%s.zip" % (
            artifactDirName, time.strftime("%Y%m%d"), self.revision)
        depsGatherPath = os.path.join(self.artifactsUnarchivedPath, artifactDirName)

        for build in builds:
            depsPath = os.path.join(self.srcDir, build.buildDir, "dependencies")
            print("*** From", depsPath, "to", depsGatherPath, "...")
            if not os.path.isdir(depsPath):
                print("*** ERROR: no dependencies directory found, nothing will be generated!")
                return

            dir_util.copy_tree(depsPath, depsGatherPath)

        shutil.copy(os.path.join(self.srcDir, "README.md"), depsGatherPath)

        os.chdir(self.artifactsUnarchivedPath)
        patternsToIgnore = [".*\\.ilk", ".*" + re.escape(os.path.join("lib", "static"))]
        build_utils.makeZip([artifactDirName], artifactZipName, patternsToIgnore)
        shutil.move(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print("*** Done gathering artifacts for CEGUI dependencies.")

    def createSDKBuilds(self):
        builds = collections.defaultdict(list)
        extraCMakeArgs = []

        def toCMakeSwitchTuples(libs, val):
            return [(lib, val) for lib in libs]

        enabledLibs = ['CORONA', 'EXPAT', 'FREEIMAGE', 'FREETYPE2', 'GLEW', 'GLFW', 'GLM', 'MINIZIP', 'PCRE', 'SILLY', 'TINYXML', 'XERCES', 'ZLIB']
        disabledLibs = ['DEVIL', 'EFFECTS11', 'LUA']

        for libBuildMapping in toCMakeSwitchTuples(enabledLibs, 'YES') + toCMakeSwitchTuples(disabledLibs, 'NO'):
            extraCMakeArgs.append("-DCEGUI_BUILD_%s=%s" % libBuildMapping)

        configs = ["Debug", "RelWithDebInfo"]
        cmakeGenerator = self.getCMakeGenerator(self.toolchain)
        if self.toolchain == "mingw":
            for config in configs:
                builds["mingw"].append(
                    BuildDetails("mingw", "build-mingw-" + config,
                                 CMakeArgs(cmakeGenerator, ["-DCMAKE_BUILD_TYPE=" + config] + extraCMakeArgs),
                                 [build_utils.generateMingwMakeCommand()]))
        else:
            builds[self.toolchain].append(
                BuildDetails(self.toolchain, "build-" + self.toolchain,
                             CMakeArgs(cmakeGenerator, extraCMakeArgs),
                             [build_utils.generateMSBuildCommand("CEGUI-DEPS.sln", config) for config in configs]))

        return builds

if __name__ == "__main__":
    parser = SDKBuilder.getDefaultArgParse("cegui-dependencies")
    depsSDK = CEGUIDependenciesSDK(parser.parse_args())
    depsSDK.build()
