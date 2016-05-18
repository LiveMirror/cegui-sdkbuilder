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
from abc import ABCMeta
import abc
import argparse
import json
import os
import subprocess
import time
from distutils import spawn
import build_utils

#TODO: rename compiler to toolchain?
#TODO: samples


class CMakeArgs:
    def __init__(self, generator, extraArgs):
        self.generator = generator
        self.extraArgs = extraArgs


class BuildDetails:
    def __init__(self, compiler, buildDir, cmakeArgs, buildCommands):
        self.compiler = compiler
        self.buildDir = buildDir
        self.cmakeArgs = cmakeArgs
        self.buildCommands = buildCommands


class SDKBuilder:
    __metaclass__ = ABCMeta
    _toolchainToCMakeGeneratorMappings = {
        "msvc2008": "Visual Studio 9 2008",
        "msvc2010": "Visual Studio 10 2010",
        "msvc2012": "Visual Studio 11 2012",
        "msvc2013": "Visual Studio 12 2013",
        "msvc2015": "Visual Studio 14 2015",
        "mingw": "MinGW Makefiles"
    }

    def __init__(self, args, sdkName):
        print("*** Using args: ")
        for key, value in vars(args).iteritems():
            print('     ', key, '=', value)

        print("*** Builder for", sdkName, "| Current time: ", time.strftime("%c"))

        self.sdkName = sdkName
        self.args = args
        self.srcDir = args.src_dir
        self.artifactsPath = args.artifacts_dir
        self.artifactsUnarchivedPath = args.artifacts_unarchived_dir
        self.toolchain = args.toolchain

        self.ensureCanBuildSDK()

        self.builds = self.createSDKBuilds()
        self.config = self.loadConfig()

        build_utils.setupPath(self.artifactsPath, False)
        build_utils.setupPath(self.artifactsUnarchivedPath, False)

    @staticmethod
    def hasExe(name):
        return spawn.find_executable(name) is not None

    def ensureCanBuildSDK(self):
        def ensureHasExe(name):
            if not self.hasExe(name):
                print("No program named '%s' could be found on PATH! Aborting... " % name)
                exit(1)

        ensureHasExe('cmake')
        if self.toolchain == "mingw":
            ensureHasExe('mingw32-make')
        else:
            ensureHasExe('msbuild')

    def build(self):
        old_path = os.getcwd()
        os.chdir(self.srcDir)

        depsStartTime = time.time()
        print("*** Building ...")

        for compiler, builds in self.builds.iteritems():
            compilerStartTime = time.time()
            print("\n*** Using '%s' compiler... | Current time: %s " % (compiler, time.strftime("%c")))

            for build in builds:
                buildDir = os.path.join(self.srcDir, build.buildDir)
                build_utils.setupPath(buildDir, not self.args.quick_mode)
                os.chdir(buildDir)

                if build_utils.invokeCMake(self.srcDir, build.cmakeArgs.generator, build.cmakeArgs.extraArgs) != 0:
                    print("*** Error configuring CMake for", compiler, "skipping ...")
                    continue

                for command in build.buildCommands:
                    print("*** Executing compiler command:", command)
                    returnCode = subprocess.Popen(command).wait()
                    if returnCode != 0:
                        print("*** Compilation failed!")

                print("*** Compilation using '%s' took %f minutes." % (compiler, self.minsUntilNow(compilerStartTime)))

            self.onAfterBuild(compiler, builds)
            self.gatherArtifacts(compiler, builds)

        self.saveConfig()
        print("***", self.sdkName, "total build time:", self.minsUntilNow(depsStartTime),
              "minutes. | Current time: ", time.strftime("%c"))
        os.chdir(old_path)

    @staticmethod
    def minsUntilNow(startTime):
        return (time.time() - startTime) / 60.0

    @abc.abstractmethod
    def createSDKBuilds(self):
        raise NotImplementedError

    @abc.abstractmethod
    def gatherArtifacts(self, compiler, builds):
        raise NotImplementedError

    def onAfterBuild(self, compiler, builds):
        pass

    @classmethod
    def getAvailableToolchains(cls):
        return cls._toolchainToCMakeGeneratorMappings.keys()

    @classmethod
    def getCMakeGenerator(cls, toolchain):
        return cls._toolchainToCMakeGeneratorMappings[toolchain]

    @classmethod
    def getDefaultArgParse(cls, sdkName):
        currentPath = os.getcwd()

        parser = argparse.ArgumentParser(description="Build " + sdkName + " for Windows.")
        parser.add_argument("-s", "--src-dir", required=True,
                            help="Path to the " + sdkName + " sources")
        parser.add_argument("-t", "--toolchain", required=True,
                            help="The toolchain to be used when generating the SDK",
                            choices=cls.getAvailableToolchains())

        parser.add_argument("--config-file", default=os.path.join(os.path.abspath(os.path.dirname(__file__)), "config.json"),
                            help="Path where to store the configuration file for the builder script.")

        parser.add_argument("--temp-dir", default=os.path.join(currentPath, "local-temp"),
                            help="Temporary directory where to store intermediate output")
        parser.add_argument("--artifacts-dir", default=os.path.join(currentPath, "artifacts"),
                            help="Directory where to store the final artifacts")
        parser.add_argument("--artifacts-unarchived-dir",
                            default=os.path.join(currentPath, "artifacts", "unarchived"),
                            help="Directory where to store the final unarchived artifacts")

        parser.add_argument("--quick-mode", action="store_true", help=argparse.SUPPRESS)
        return parser

    def saveConfig(self):
        with open(self.args.config_file, 'w') as f:
            json.dump(self.config, f)

    def loadConfig(self):
        try:
            with open(self.args.config_file, 'r') as f:
                return json.load(f)
        except:
            print("*** No config file found at", self.args.config_file, ". Creating a default one...")
            with open(self.args.config_file, 'w') as f:
                json.dump({}, f)
            return {}

