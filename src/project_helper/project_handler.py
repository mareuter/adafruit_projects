# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT
import pathlib
import shutil
import tomllib

__all__ = ["ProjectHandler"]

CIRCUITPY_DIR = "CIRCUITPY"
MPY_EXT = ".mpy"
CODE_FILE = "code.py"
SETTINGS_FILE = "settings.toml"


class ProjectHandler:
    def __init__(
        self, project_file: pathlib.Path, debug_dir: pathlib.Path | None = None
    ):
        """Class constructor.

        Parameters
        ----------
        project_file : pathlib.Path
            The TOML file containing the project configuration.
        debug_dir : pathlib.Path | None, optional
            Directory used for testing project installation, by default None
        """
        self.top_dir = pathlib.Path(".").resolve()
        self.local_modules = self.top_dir / "modules"
        self.modules_info = self.top_dir / "projects" / "modules.toml"
        if debug_dir is not None:
            self.circuitboard_location = debug_dir / CIRCUITPY_DIR
        else:
            self.circuitboard_location = (
                pathlib.Path("/media") / self.top_dir.parents[2].name / CIRCUITPY_DIR
            )
        self.circuitboard_lib = self.circuitboard_location / "lib"
        self.project_file = project_file

    def _check_project_file(self) -> None:
        """Check to see if the project file is set.

        Raises
        ------
        RuntimeError
            If the project file is not set.
        """
        if self.project_file is None:
            raise RuntimeError("Please set the project file first.")

    def _copy_file_or_directory(
        self, module_type: str, module_name: str, use_project_info: bool = False
    ) -> None:
        """Copy a file or directory from a module.

        Parameters
        ----------
        module_type : str
            The key in the configuration describing the type of modules.
        module_name : str
            The module to get dependencies from.
        use_project_info : bool, optional
            Flag to use project info instead of module info, by default False.
        """
        try:
            if use_project_info:
                dependencies = self.project_info[module_type][module_name]
            else:
                dependencies = self.module_info[module_type][module_name]
            is_directory = self.module_info[module_name]["is_directory"]
            module_path = self._get_module_location(module_name)
            for dependency in dependencies:
                if dependency not in is_directory:
                    shutil.copy(
                        module_path / (dependency + MPY_EXT), self.circuitboard_lib
                    )
                else:
                    shutil.copytree(
                        module_path / dependency,
                        self.circuitboard_lib / dependency,
                        dirs_exist_ok=True,
                    )
        except KeyError:
            pass

    def _get_module_location(self, name: str) -> pathlib.Path:
        """Construct the path for adafruit or circuitpython library bundles.

        Parameters
        ----------
        name : str
            Library bundle to construct path.

        Returns
        -------
        pathlib.Path
            The fully qualified path for the library bundle.
        """
        dep_type = self.module_info[name]
        top_loc = pathlib.Path(dep_type["module_location"]).expanduser()
        return top_loc / dep_type["bundle"] / "lib"

    def copy_project(self) -> None:
        """Copy project based on TOML configuration."""
        self._check_project_file()

        with self.modules_info.open("rb") as mfile:
            self.module_info = tomllib.load(mfile)

        with self.project_file.expanduser().open("rb") as ifile:
            self.project_info = tomllib.load(ifile)

        project_dir = self.project_file.parent
        shutil.copy(
            project_dir / self.project_info["settings"],
            self.circuitboard_location / SETTINGS_FILE,
        )
        shutil.copy(
            project_dir / self.project_info["code"],
            self.circuitboard_location / CODE_FILE,
        )

        self._copy_file_or_directory("defaults", "adafruit")

        local_imports = self.project_info["imports"]["local"]
        for local_import in local_imports:
            shutil.copy(
                self.local_modules / (local_import + MPY_EXT), self.circuitboard_lib
            )
            self._copy_file_or_directory(local_import, "adafruit")

        self._copy_file_or_directory("imports", "adafruit", use_project_info=True)
