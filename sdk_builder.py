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
from abc import ABCMeta
import abc
import argparse
import os
import subprocess
import time
import build_utils


class CMakeArgs:
    def __init__(self, generator, extraArgs):
        self.generator = generator
        self.extraArgs = extraArgs


class BuildDetails:
    def __init__(self, compiler, friendlyName, buildDir, cmakeArgs, buildCommands):
        self.compiler = compiler
        self.friendlyName = friendlyName
        self.buildDir = buildDir
        self.cmakeArgs = cmakeArgs
        self.buildCommands = buildCommands


class SDKBuilder:
    __metaclass__ = ABCMeta

    def __init__(self, args, sdkName):
        self.sdkName = sdkName
        self.args = args
        self.srcDir = os.path.join(self.args.temp_dir, sdkName)
        self.artifactsPath = args.artifacts_dir
        self.artifactsUnarchivedPath = args.artifacts_unarchived_dir
        self.builds = self.createSDKBuilds()

        build_utils.setupPath(self.artifactsPath, False)
        build_utils.setupPath(self.artifactsUnarchivedPath, False)
        build_utils.setupPath(self.srcDir, not args.quick_mode)

    def cloneRepo(self, branch="default"):
        print("*** Cloning ", self.sdkName, "repository...")
        build_utils.hgClone(self.args.url, self.srcDir, branch)

    def build(self):
        old_path = os.getcwd()
        os.chdir(self.srcDir)

        depsStartTime = time.time()
        print("*** Building ", self.sdkName, "| Current date: ", time.strftime("%c"), "...")

        for compiler, builds in self.builds.iteritems():
            compilerStartTime = time.time()
            print("\n*** Using '%s' compiler..." % compiler)

            for build in builds:
                buildDir = os.path.join(self.srcDir, build.buildDir)
                build_utils.setupPath(buildDir, not self.args.quick_mode)
                os.chdir(buildDir)

                if build_utils.invokeCMake(self.srcDir, build.cmakeArgs.generator, build.cmakeArgs.extraArgs) != 0:
                    print("*** Error configuring CMake for ", compiler, "skipping ...")
                    continue

                for command in build.buildCommands:
                    print("*** Executing compiler command: ", command)
                    subprocess.Popen(command).wait()

                print("*** Compilation using '%s' took %f minutes." % (compiler, self.minsUntilNow(compilerStartTime)))

            self.gatherArtifacts(compiler, builds)

        print("*** ", self.sdkName, " total build time: ", self.minsUntilNow(depsStartTime), "minutes.")
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

    @classmethod
    def getDefaultArgParse(cls, sdkName):
        currentPath = os.getcwd()

        parser = argparse.ArgumentParser(description="Build " + sdkName + " for Windows.")
        parser.add_argument("--url", default="https://bitbucket.org/cegui/" + sdkName,
                            help="URL or path to the mercurial " + sdkName + " repository where the.")
        parser.add_argument("--temp-dir", default=os.path.join(currentPath, "local-temp"),
                            help="Temporary directory where to store intermediate output.")
        parser.add_argument("--artifacts-dir", default=os.path.join(currentPath, "artifacts"),
                            help="Directory where to store the final artifacts")
        parser.add_argument("--artifacts-unarchived-dir",
                            default=os.path.join(currentPath, "artifacts", "unarchived"),
                            help="Directory where to store the final unarchived artifacts")
        parser.add_argument("--quick-mode", action="store_true", help=argparse.SUPPRESS)

        return parser
