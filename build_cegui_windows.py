#!/usr/bin/env python2
##############################################################################
#   CEGUI SDK build script for Windows
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
import subprocess
from distutils import dir_util
import shutil
import os
import build_utils
from build_utils import doCopy
from sdk_builder import BuildDetails, CMakeArgs, SDKBuilder


class CEGUISDK(SDKBuilder):
    def __init__(self, args):
        SDKBuilder.__init__(self, args, "cegui")

    def gatherArtifacts(self, compiler, builds):
        print("*** Gathering artifacts of CEGUI for '%s' compiler ..." % compiler)

        artifactZipNamePrefix = "cegui-sdk-%s" % compiler
        artifactDirName = "cegui-sdk-%s" % compiler
        depsGatherPath = os.path.join(self.artifactsUnarchivedPath, artifactDirName)

        for build in builds:
            buildDir = os.path.join(self.srcDir, build.buildDir)

            # copy source-level includes to the build directory
            doCopy(os.path.join(buildDir, "cegui/include"), os.path.join(buildDir, "include"))
            doCopy(os.path.join(self.srcDir, "cegui/include"), os.path.join(buildDir, "include"))

            doCopy(os.path.join(buildDir, 'datafiles/samples'), os.path.join(depsGatherPath, 'datafiles/samples'), build_utils.ignoreNonMatchingFiles('samples.xml'))
            doCopy(os.path.join(buildDir, 'bin'), os.path.join(depsGatherPath, 'bin'), shutil.ignore_patterns('*.ilk'))
            doCopy(os.path.join(buildDir, 'lib'), os.path.join(depsGatherPath, 'lib'), shutil.ignore_patterns('*.exp'))
            doCopy(os.path.join(buildDir, 'include'), os.path.join(depsGatherPath, 'include'), build_utils.ignoreNonMatchingFiles('*.h'))

        doCopy(os.path.join(self.srcDir, "datafiles"), os.path.join(depsGatherPath, "datafiles"), shutil.ignore_patterns('CMakeLists.txt'))

        doxygenDocDir = os.path.join(self.getDoxyfileDir(builds[0]), "html")
        if os.path.exists(doxygenDocDir):
            dir_util.copy_tree(doxygenDocDir, os.path.join(depsGatherPath, "doc"))

        print("*** Adding dependencies to the artifact output...")
        build_utils.copyFiles(self.args.dependencies_dir, depsGatherPath)
        for src, dst in [("bin", "bin"), ("include", "include"), ("lib/dynamic", "lib")]:
            doCopy(
                os.path.join(self.args.dependencies_dir, src),
                os.path.join(depsGatherPath, dst))

        for extraFile in ["README.md", "COPYING"]:
            shutil.copy2(os.path.join(self.srcDir, extraFile), depsGatherPath)

        os.chdir(self.artifactsUnarchivedPath)
        if self.shouldBuildPyCEGUI(compiler):
            artifactWithPyCEGUIZipName = artifactZipNamePrefix + "-pycegui.zip"
            build_utils.makeZip([artifactDirName], artifactWithPyCEGUIZipName, [".*\\.ilk", "PyCEGUI.*\\.pdb"])
            shutil.move(artifactWithPyCEGUIZipName, os.path.join(self.artifactsPath, artifactWithPyCEGUIZipName))

        artifactZipName = artifactZipNamePrefix + ".zip"
        build_utils.makeZip([artifactDirName], artifactZipName, [".*\\.ilk", "PyCEGUI.*"])
        shutil.move(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print("*** Done gathering artifacts for CEGUI.")

    def onAfterBuild(self, compiler, builds):
        self.compileDocumentation(builds[0])

    def compileDocumentation(self, build):
        hasDoxygen = self.hasExe('doxygen')
        hasDot = self.hasExe('dot')

        if not hasDoxygen:
            print("*** No doxygen executable exists in PATH, will NOT generate documentation!")
            return

        if not hasDot:
            print("*** No dot executable exists in PATH, will NOT generate images for documentation!")

        self.invokeDoxygen(self.getDoxyfileDir(build))

    @staticmethod
    def invokeDoxygen(doxyfileDir):
        oldWorkingDirectory = os.getcwd()
        os.chdir(doxyfileDir)

        print("*** Invoking doxygen on folder '%s' ..." % doxyfileDir)
        doxygenCommand = ["doxygen", os.path.join(doxyfileDir, "doxyfile")]
        doxygenProc = subprocess.Popen(doxygenCommand).wait()
        print("*** Doxygen return code:", doxygenProc)

        os.chdir(oldWorkingDirectory)

    def getDoxyfileDir(self, build):
        return os.path.join(self.srcDir, build.buildDir, "doc", "doxygen")

    def getDefaultCMakeArgs(self):
        args = ["-DCMAKE_PREFIX_PATH=" +
                self.args.dependencies_dir,
                "-DCEGUI_SAMPLES_ENABLED=TRUE",
                "-DCEGUI_BUILD_LUA_GENERATOR=FALSE",
                "-DCEGUI_BUILD_LUA_MODULE=FALSE",
                "-DCEGUI_BUILD_TESTS=FALSE",
                "-DCEGUI_SAMPLE_DATAPATH=\"../datafiles\""]

        if self.shouldBuildPyCEGUI(self.toolchain):
            args.extend(["-DBoost_INCLUDE_DIR=" + self.args.boost_include_dir,
                         "-DBoost_LIBRARY_DIR=" + self.args.boost_library_dir])

        args.append("-DCEGUI_BUILD_PYTHON_MODULES=" +
                    ("TRUE" if self.shouldBuildPyCEGUI(self.toolchain) else "FALSE"))

        return args

    def shouldBuildPyCEGUI(self, compiler):
        return compiler == "msvc2008" and\
            self.args.boost_include_dir is not None and self.args.boost_library_dir is not None

    def createSDKBuilds(self):
        builds = collections.defaultdict(list)
        configs = ["Debug", "RelWithDebInfo"]
        cmakeGenerator = self.getCMakeGenerator(self.toolchain)

        if self.toolchain == "mingw":
            for config in configs:
                cmakeArgs = ["-DCMAKE_BUILD_TYPE=" + config] + self.getDefaultCMakeArgs()
                builds["mingw"].append(
                    BuildDetails("mingw", "build-mingw-" + config,
                                 CMakeArgs(cmakeGenerator, cmakeArgs),
                                 [build_utils.generateMingwMakeCommand()]))
        else:
            builds[self.toolchain].append(
                BuildDetails(self.toolchain, "build-" + self.toolchain,
                             CMakeArgs(cmakeGenerator, self.getDefaultCMakeArgs()),
                             [build_utils.generateMSBuildCommand("cegui.sln", config) for config in configs]))
        return builds

if __name__ == "__main__":
    currentPath = os.getcwd()

    parser = SDKBuilder.getDefaultArgParse("cegui")
    parser.add_argument("-d", "--dependencies-dir", required=True,
                        help="Directory where to find CEGUI dependencies associated with currently selected toolchain")
    parser.add_argument("--boost-include-dir", default=None,
                        help="Boost include dir")
    parser.add_argument("--boost-library-dir", default=None,
                        help="Boost library dir")

    ceguiSDK = CEGUISDK(parser.parse_args())
    ceguiSDK.build()
