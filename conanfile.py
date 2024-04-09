import os

from pathlib import Path

from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout
from conan.tools.files import copy, mkdir
from conan.tools.build import check_min_cppstd
from conan import ConanFile


required_conan_version = ">=1.50.0"


class PySavitarConan(ConanFile):
    name = "pysavitar"
    license = "LGPL-3.0"
    author = "Ultimaker B.V."
    url = "https://github.com/Ultimaker/pySavitar"
    description = "pySavitar is a c++ implementation of 3mf loading with SIP python bindings"
    topics = ("conan", "cura", "3mf", "c++")
    settings = "os", "compiler", "build_type", "arch"
    revision_mode = "scm"
    exports = "LICENSE*"
    generators = "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    python_requires = "lulzbase/[>=0.1.7]@lulzbot/stable", "pyprojecttoolchain/[>=0.1.6]@lulzbot/stable", "sipbuildtool/[>=0.2.3]@lulzbot/stable"
    python_requires_extend = "umbase.UMBaseConanfile"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "py_build_requires": ["ANY"],
        "py_build_backend": ["ANY"],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "py_build_requires": '"sip >=6, <7", "setuptools>=40.8.0", "wheel"',
        "py_build_backend": "sipbuild.api",
    }
    scm = {
        "type": "git",
        "subfolder": ".",
        "url": "auto",
        "revision": "auto"
    }

    def set_version(self):
        if self.version is None:
            self.version = self._umdefault_version()

    def requirements(self):
        self.requires("standardprojectsettings/[>=0.1.0]@lulzbot/stable")  # required for the CMake build modules
        self.requires("sipbuildtool/0.2.3@lulzbot/stable")  # required for the CMake build modules
        for req in self._um_data()["requirements"]:
            self.requires(req)

    def config_options(self):
        if self.options.shared and self.settings.compiler == "Visual Studio":
            del self.options.fPIC

    def configure(self):
        self.options["savitar"].shared = self.options.shared
        self.options["cpython"].shared = True

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def generate(self):
        pp = self.python_requires["pyprojecttoolchain"].module.PyProjectToolchain(self)
        pp.blocks["tool_sip_project"].values["sip_files_dir"] = Path("python").as_posix()
        mkdir(self, self.build_path)  # FIXME: bad, this should not be necessary
        pp.blocks["tool_sip_bindings"].values["name"] = "pySavitar"
        pp.blocks["tool_sip_metadata"].values["name"] = "pySavitar"
        pp.blocks.remove("extra_sources")
        pp.generate()

        tc = CMakeToolchain(self)
        tc.variables["Python_EXECUTABLE"] = self.deps_user_info["cpython"].python.replace("\\", "/")
        tc.variables["Python_USE_STATIC_LIBS"] = not self.options["cpython"].shared
        tc.variables["Python_ROOT_DIR"] = self.deps_cpp_info["cpython"].rootpath.replace("\\", "/")
        tc.variables["Python_FIND_FRAMEWORK"] = "NEVER"
        tc.variables["Python_FIND_REGISTRY"] = "NEVER"
        tc.variables["Python_FIND_IMPLEMENTATIONS"] = "CPython"
        tc.variables["Python_FIND_STRATEGY"] = "LOCATION"
        tc.variables["Python_SITEARCH"] = "site-packages"
        tc.generate()

        # Generate the Source code from SIP
        sip = self.python_requires["sipbuildtool"].module.SipBuildTool(self)
        sip.configure()
        sip.build()

    def layout(self):
        cmake_layout(self)

        if self.settings.os in ["Linux", "FreeBSD", "Macos"]:
            self.cpp.package.system_libs = ["pthread"]

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        for ext in (".pyi", ".so", ".lib", ".a", ".pyd"):
            copy(self, f"pySavitar{ext}", self.build_folder, self.package_path.joinpath("lib"), keep_path = False)

        for ext in (".dll", ".so", ".dylib"):
            copy(self, f"pySavitar{ext}", self.build_folder, self.package_path.joinpath("bin"), keep_path = False)

    def package_info(self):
        self.cpp_info.libdirs = [ os.path.join(self.package_folder, "lib")]
        if self.in_local_cache:
            self.runenv_info.append_path("PYTHONPATH", os.path.join(self.package_folder, "lib"))
        else:
            self.runenv_info.append_path("PYTHONPATH", self.build_folder)
