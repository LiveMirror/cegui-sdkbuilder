#!/usr/bin/env python2
##############################################################################
#   CEGUI SDK build script for Windows
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
import collections
from distutils import dir_util
import shutil
import os
import time
import build_utils
from sdk_builder import BuildDetails, CMakeArgs, SDKBuilder

#TODO: pack boost python in PyCEGUI build
class CEGUISDK(SDKBuilder):
    def __init__(self, args):
        SDKBuilder.__init__(self, args, "cegui")

    def gatherArtifacts(self, compiler, builds):
        print("*** Gathering artifacts of CEGUI for '%s' compiler ..." % compiler)

        compilerFriendlyName = builds[0].friendlyName
        artifactZipNamePrefix = "cegui-sdk-%s-%s-%s-%s" % (compilerFriendlyName, time.strftime("%Y%m%d"), self.revision,
                                                           build_utils.getHgRevision(self.srcDir))
        artifactDirName = "cegui-sdk-%s-%s" % (compilerFriendlyName, self.revision)

        depsGatherPath = os.path.join(self.artifactsUnarchivedPath, artifactDirName)
        for build in builds:
            buildDir = os.path.join(self.srcDir, build.buildDir)
            # copy source-level includes to the built ones
            dir_util.copy_tree(os.path.join(self.srcDir, "cegui/include"), os.path.join(buildDir, "include"))
            dir_util.copy_tree(os.path.join(buildDir, "cegui/include"), os.path.join(buildDir, "include"))

            for dir in ["bin", "lib", "include"]:
                dirPath = os.path.join(self.srcDir, build.buildDir, dir)
                dirGatherPath = os.path.join(depsGatherPath, dir)

                print("*** From", dirPath, "to", dirGatherPath, "...")
                if not os.path.isdir(dirPath):
                    print("*** ERROR: no", dir, "directory found, nothing will be generated!")
                    return

                dir_util.copy_tree(dirPath, dirGatherPath)

        dir_util.copy_tree(os.path.join(self.srcDir, "datafiles"), os.path.join(depsGatherPath, "datafiles"))
        os.remove(os.path.join(depsGatherPath, "datafiles", "CMakeLists.txt"))
        dir_util.copy_tree(
            os.path.join(self.srcDir, builds[0].buildDir, "datafiles", "samples"),
            os.path.join(depsGatherPath, "datafiles", "samples"))

        doxygenDocDir = os.path.join(self.getDoxygenBuildDir(builds[0]), "html")
        if os.path.exists(doxygenDocDir):
            dir_util.copy_tree(doxygenDocDir, os.path.join(depsGatherPath, "doc"))

        print("*** Gathering dependencies...")
        self.copyFiles(self.getDependenciesPath(compilerFriendlyName), depsGatherPath)
        self.copyFiles(os.path.join(self.getDependenciesPath(compilerFriendlyName), 'bin'), os.path.join(depsGatherPath, 'bin'))
        dir_util.copy_tree(
            os.path.join(self.getDependenciesPath(compilerFriendlyName), 'include'), os.path.join(depsGatherPath, 'include'))
        self.copyFiles(
            os.path.join(self.getDependenciesPath(compilerFriendlyName), 'lib', 'dynamic'),
            os.path.join(depsGatherPath, 'lib'))

        for extraFile in ["README.md", "COPYING"]:
            shutil.copy2(os.path.join(self.srcDir, extraFile), depsGatherPath)

        os.chdir(self.artifactsUnarchivedPath)
        if self.__shouldBuildPyCEGUI(compilerFriendlyName):
            artifactWithPyCEGUIZipName = artifactZipNamePrefix + "-pycegui.zip"
            build_utils.makeZip([artifactDirName], artifactWithPyCEGUIZipName, [".*\\.ilk", "PyCEGUI.*\\.pdb"])
            shutil.move(artifactWithPyCEGUIZipName, os.path.join(self.artifactsPath, artifactWithPyCEGUIZipName))

        artifactZipName = artifactZipNamePrefix + ".zip"
        build_utils.makeZip([artifactDirName], artifactZipName, [".*\\.ilk", "PyCEGUI.*"])
        shutil.move(artifactZipName, os.path.join(self.artifactsPath, artifactZipName))

        print("*** Done gathering artifacts for CEGUI.")

    def onAfterBuild(self, compiler, builds):
        self.compileDocumentation(builds[0])

    @staticmethod
    def copyFiles(src, dst):
        if not os.path.exists(dst):
            os.mkdir(dst)

        for item in os.listdir(src):
            srcPath = os.path.join(src, item)
            dstPath = os.path.join(dst, item)

            if os.path.isdir(srcPath):
                continue

            shutil.copy2(srcPath, dstPath)

    def compileDocumentation(self, build):
        hasDoxygen = build_utils.hasExe('doxygen')
        hasDot = build_utils.hasExe('dot')

        if not hasDoxygen:
            print("*** No doxygen executable exists in PATH, will NOT generate documentation!")
            return

        if not hasDot:
            print("*** No dot executable exists in PATH, will NOT generate images for documentation!")

        build_utils.invokeDoxygen(self.getDoxygenBuildDir(build))

    def getDoxygenBuildDir(self, build):
        return os.path.join(self.srcDir, build.buildDir, "doc", "doxygen")

    def generateCEGUISDKDirName(self, friendlyName, revision):
        return "cegui-sdk-%s-%s_%s-%s" %\
               (friendlyName, time.strftime("%Y%m%d"), revision, build_utils.getHgRevision(self.srcDir))

    def getDependenciesPath(self, compiler):
        return os.path.join(self.args.dependencies_dir, build_utils.generateCEGUIDependenciesDirName(compiler))

    def getDefaultCMakeArgs(self, compilerFriendlyName):
        args = ["-DCMAKE_PREFIX_PATH=" +
                self.getDependenciesPath(compilerFriendlyName),
                "-DCEGUI_SAMPLES_ENABLED=TRUE",
                "-DCEGUI_BUILD_LUA_GENERATOR=FALSE",
                "-DCEGUI_BUILD_LUA_MODULE=FALSE",
                "-DCEGUI_BUILD_TESTS=FALSE",
                "-DCEGUI_SAMPLE_DATAPATH=\"../datafiles\""]

        if self.__shouldBuildPyCEGUI(compilerFriendlyName):
            args.extend(["-DBoost_INCLUDE_DIR=" + self.args.boost_include_dir,
                         "-DBoost_LIBRARY_DIR=" + self.args.boost_library_dir])

        args.append("-DCEGUI_BUILD_PYTHON_MODULES=" +
                    ("TRUE" if self.__shouldBuildPyCEGUI(compilerFriendlyName) else "FALSE"))

        return args

    def __shouldBuildPyCEGUI(self, compilerFriendlyName):
        return compilerFriendlyName == "msvc2008" and\
            self.args.boost_include_dir is not None and self.args.boost_library_dir is not None

    def createSDKBuilds(self):
        builds = collections.defaultdict(list)
        configs = ["Debug", "RelWithDebInfo"]

        for config in configs:
            cmakeArgs = ["-DCMAKE_BUILD_TYPE=" + config]
            cmakeArgs.extend(self.getDefaultCMakeArgs("mingw"))
            builds["mingw"].append(BuildDetails
                                   ("mingw", "mingw", "build-mingw-" + config,
                                    CMakeArgs("MinGW Makefiles", cmakeArgs),
                                    [build_utils.generateMingwMakeCommand()]))

        msvcCompilers = [(9, "msvc2008"), (10, "msvc2010"), (11, "msvc2012"), (12, "msvc2013")]
        for version, friendlyName in msvcCompilers:
            msvc = "msvc" + str(version)
            builds[msvc].append(BuildDetails
                                (msvc, friendlyName, "build-" + msvc,
                                 CMakeArgs("Visual Studio " + (str(version) if version > 9 else '9 2008'), self.getDefaultCMakeArgs(friendlyName)),
                                 [build_utils.generateMSBuildCommand("cegui.sln", config) for config in configs]))
        return builds

if __name__ == "__main__":
    build_utils.ensureCanBuildOnWindows()
    currentPath = os.getcwd()

    parser = SDKBuilder.getDefaultArgParse("cegui")
    parser.add_argument("--dependencies-dir", default=os.path.join(currentPath, "artifacts", "unarchived"),
                        help="Directory where to find CEGUI dependencies. The directory needs to contain a subdirectory "
                             "named '%s', where X is a compiler: mingw, msvc2008, msvc2010, msvc2012 or msvc2013."
                             "The CEGUI SDK will be built only for compilers which have their dependencies built." %
                             build_utils.generateCEGUIDependenciesDirName('X'))
    parser.add_argument("--boost-include-dir", default=None,
                        help="Boost include dir")
    parser.add_argument("--boost-library-dir", default=None,
                        help="Boost library dir")

    parsedArgs = parser.parse_args()
    print("*** Using args: ")
    for key, value in vars(parsedArgs).iteritems():
        print('     ', key, '=', value)

    ceguiSDK = CEGUISDK(parsedArgs)
    if not parsedArgs.quick_mode:
        ceguiSDK.cloneRepo()
    ceguiSDK.build()
