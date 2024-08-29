# SPDX-FileCopyrightText: 2023 Michael Reuter
#
# SPDX-License-Identifier: MIT
import dataclasses
import os
import pathlib
import shutil
import sys
import tomllib
import zipfile

import requests

__all__ = ["CopyOptions", "DownloadOptions", "MqttInformation", "ProjectHandler"]

CIRCUITPY_DIR = "CIRCUITPY"
MPY_EXT = ".mpy"
CODE_FILE = "code.py"
SETTINGS_FILE = "settings.toml"
BOOT_PY = "boot.py"
TEMP_SETTINGS = "settings_temp.toml"
WEB_DEV_SETTINGS = "settings_circuitpy_web.toml"
BOOT_OUT_FILE = "boot_out.txt"


@dataclasses.dataclass
class MqttInformation:
    """MQTT Information"""

    no_test: bool
    sensor_name: str | None
    adafruitio_group: str | None


@dataclasses.dataclass
class CopyOptions:
    """Options for copying project files."""

    code: bool
    settings: bool
    dependencies: bool
    media: bool

    @property
    def all(self):
        return not (self.code or self.settings or self.dependencies or self.media)


@dataclasses.dataclass
class DownloadOptions:
    """Options for downloading CircuitPython."""

    boards: bool
    cross_compiler: bool
    bundles: bool

    @property
    def all(self):
        return not (self.boards or self.cross_compiler or self.bundles)

    @property
    def version(self):
        return self.boards and self.cross_compiler


class ProjectHandler:
    def __init__(
        self,
        project_file: pathlib.Path | None = None,
        copy_options: CopyOptions | None = None,
        mqtt_info: MqttInformation | None = None,
        download_options: DownloadOptions | None = None,
        debug_dir: pathlib.Path | None = None,
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
        self.copy_options = copy_options
        self.mqtt_info = mqtt_info
        self.download_options = download_options

    def _check_download(self, resp: requests.Response) -> bool:
        """Ensure the download completed successfully.

        Parameters
        ----------
        resp : requests.Response
            The response from the requests.get

        Returns
        -------
        bool
            True if download was successful, False if not.
        """
        return resp.ok and resp.status_code == 200

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

    def _copy_media(self) -> None:
        """Copy media items to project location."""
        media_types = ["fonts", "images"]
        try:
            for media_type in media_types:
                media_dir = self.circuitboard_location / media_type
                media_dir.mkdir(0o755, exist_ok=True)
                input_media_dir = self.top_dir / media_type
                for media in self.project_info["media"][media_type]:
                    shutil.copy(input_media_dir / media, media_dir)
        except KeyError:
            pass

    def _create_settings_file(self) -> pathlib.Path | None:
        """Create settings file.

        Returns
        -------
        pathlib.Path or None
            The temporary settings file.
        """
        if "settings" not in self.project_info:
            return None
        temp_file = self.top_dir / "settings_tmp.toml"
        settings_dict = {}
        use_aio = False
        for setting in self.project_info["settings"]["general"]:
            if setting == "aio":
                use_aio = True
            sfile_name = self.top_dir / f"settings_{setting}.toml"
            with sfile_name.open("rb") as sifile:
                sdict = tomllib.load(sifile)
                settings_dict.update(sdict)

        if "local" in self.project_info["settings"]:
            local_settings = (
                self.project_file.parent / self.project_info["settings"]["local"]
            )
            with local_settings.open("rb") as slifile:
                ldict = tomllib.load(slifile)
                settings_dict.update(ldict)

        if use_aio:
            if self.mqtt_info.adafruitio_group is not None:
                settings_dict["ADAFRUIT_AIO_GROUP"] = self.mqtt_info.adafruitio_group
            else:
                raise RuntimeError("Adafruit IO requested, but group name not given.")

        if self.mqtt_info.sensor_name is not None:
            settings_dict["MQTT_SENSOR_NAME"] = self.mqtt_info.sensor_name

        if self.mqtt_info.no_test:
            for key, value in settings_dict.items():
                if "MEASUREMENT" in key:
                    settings_dict[key] = value.split("test")[-1]

        with temp_file.open("w") as sofile:
            for key, value in settings_dict.items():
                line = f'{key}="{value}"' + os.linesep
                sofile.write(line)

        return temp_file

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

    def _save_downloaded_file(
        self, content: bytes, save_dir: pathlib.Path, save_file: str
    ) -> pathlib.Path:
        """Save the file to the specified directory.

        Parameters
        ----------
        content
            The file content.
        save_dir : pathlib.Path
            The directory to save the file to.
        save_file : str
            The file to save.

        Returns
        -------
        pathlib.Path
            Fully qualified save path.
        """
        fq_save = save_dir / save_file
        with fq_save.open("wb") as sfile:
            sfile.write(content)
        return fq_save

    def clean_circuitpython_board(self) -> None:
        """Clean the currently mounted CircuitPython board."""
        font_dir = self.circuitboard_location / "fonts"
        shutil.rmtree(font_dir, ignore_errors=True)

        settings_file = self.circuitboard_location / SETTINGS_FILE
        settings_file.unlink()
        settings_file.touch()

        shutil.rmtree(self.circuitboard_lib, ignore_errors=True)
        self.circuitboard_lib.mkdir(0o755, exist_ok=True)

        code_file = self.circuitboard_location / CODE_FILE
        code_file.unlink()

        with code_file.open("w") as cofile:
            cofile.write('print("Hello World!")' + os.linesep)

    def clean_debug_dir(self) -> None:
        """Clean the debug directory for project testing."""
        shutil.rmtree(self.circuitboard_location, ignore_errors=True)
        self.circuitboard_lib.mkdir(0o755, parents=True)

    def copy_project(self) -> None:
        """Copy project based on TOML configuration."""
        self._check_project_file()

        with self.modules_info.open("rb") as mfile:
            self.module_info = tomllib.load(mfile)

        with self.project_file.expanduser().open("rb") as ifile:
            self.project_info = tomllib.load(ifile)

        if self.copy_options.settings or self.copy_options.all:
            temp_settings_file = self._create_settings_file()
            if temp_settings_file is not None:
                shutil.copy(
                    temp_settings_file,
                    self.circuitboard_location / SETTINGS_FILE,
                )
                temp_settings_file.unlink()

        if self.copy_options.code or self.copy_options.all:
            project_dir = self.project_file.parent
            shutil.copy(
                project_dir / self.project_info["code"],
                self.circuitboard_location / CODE_FILE,
            )

        if self.copy_options.dependencies or self.copy_options.all:
            self._copy_file_or_directory("defaults", "adafruit")

            if "local" in self.project_info["imports"]:
                local_imports = self.project_info["imports"]["local"]
                for local_import in local_imports:
                    shutil.copy(
                        self.local_modules / (local_import + MPY_EXT),
                        self.circuitboard_lib,
                    )
                    self._copy_file_or_directory(local_import, "adafruit")

            self._copy_file_or_directory("imports", "adafruit", use_project_info=True)

        if self.copy_options.media or self.copy_options.all:
            self._copy_media()

    def get_board_info(self) -> None:
        """Get the circuitboard's UID and CircuitPython version."""
        boot_file = self.circuitboard_location / BOOT_OUT_FILE
        lines = boot_file.read_text().strip()
        for line in lines.split(os.linesep):
            if line.startswith("Adafruit"):
                parts = line.split()
                print(f"{' '.join(parts[:3])}")
            if line.startswith("UID"):
                print(line)

    def get_circuitpython(self, version: str, bundle_date: str) -> None:
        """Download CircuitPython, bundles and cross-compiler for version.

        Parameters
        ----------
        version : str
            The CircuitPython version.
        bundle_data : str
            The Adafruit/Community bundle date in YYYYMMDD format.
        """
        main_dir = pathlib.Path("~/code/adafruit").expanduser()
        main_dir.mkdir(exist_ok=True)
        bootload_dir = main_dir / "bootloader" / version
        bootload_dir.mkdir(exist_ok=True)
        bundle_version = f"{version.split('.')[0]}.x"

        circuitpython_info = self.top_dir / "projects" / "circuitpython.toml"
        with circuitpython_info.open("rb") as mfile:
            circuitpython_info = tomllib.load(mfile)

        base_url = circuitpython_info["storage_url"]
        locale = circuitpython_info["locale"]

        if (
            self.download_options.boards
            or self.download_options.version
            or self.download_options.all
        ):
            for board in circuitpython_info["boards"]:
                bootloader = f"adafruit-circuitpython-{board}-{locale}-{version}.uf2"
                url = f"{base_url}/bin/{board}/{locale}/{bootloader}"
                response = requests.get(url)
                if self._check_download(response):
                    _ = self._save_downloaded_file(
                        response.content, bootload_dir, bootloader
                    )
                else:
                    print(f"{bootloader} download failed.")

        if self.download_options.bundles or self.download_options.all:
            for bundle in ["adafruit", "community"]:
                if bundle == "adafruit":
                    bundle_stem = "adafruit-circuitpython"
                if bundle == "community":
                    bundle_stem = "circuitpython-community"
                bundle_file = (
                    f"{bundle_stem}-bundle-{bundle_version}-mpy-{bundle_date}.zip"
                )
                url = f"{base_url}/bundles/{bundle}/{bundle_file}"
                response = requests.get(url)
                if self._check_download(response):
                    bdl = self._save_downloaded_file(
                        response.content, main_dir, bundle_file
                    )
                    bdl_dir = bdl.stem
                    uz_bld_dir = main_dir / bdl_dir
                    zf = zipfile.ZipFile(bdl)
                    zf.extractall(main_dir)
                    zf.close()
                    bdl.unlink()
                    link_dir = uz_bld_dir.name.strip(f"-{bundle_date}")
                    uz_link_dir = main_dir / link_dir
                    if uz_link_dir.exists():
                        uz_link_dir.unlink()
                    uz_link_dir.symlink_to(uz_bld_dir)
                else:
                    print(f"{bundle_file} download failed.")

        if (
            self.download_options.cross_compiler
            or self.download_options.version
            or self.download_options.all
        ):
            cross_compiler = f"mpy-cross-linux-amd64-{version}.static"
            url = f"{base_url}/bin/mpy-cross/linux-amd64/{cross_compiler}"
            bin_dir = pathlib.Path("~/bin").expanduser()
            response = requests.get(url)
            if self._check_download(response):
                cc = self._save_downloaded_file(
                    response.content, bin_dir, cross_compiler
                )
                cc.chmod(0o755)
                cc_link = bin_dir / "mpy"
                if cc_link.exists():
                    cc_link.unlink()
                cc_link.symlink_to(cc)
            else:
                print(f"{cross_compiler} download failed.")

    def web_development(self, undo: bool) -> None:
        """Setup a board for web development mode.

        Parameters
        ----------
        undo : bool
            Provide information for undoing web development mode.
        """
        boot_file = self.circuitboard_location / BOOT_PY
        if boot_file.exists():
            print("Circuitboard already setup for web developement.")
            sys.exit(0)

        if undo:
            print("import storage")
            print("import os")
            print("storage.remount('/', False)")
            print("os.remove('/boot.py')")
        else:
            settings_file = self.circuitboard_location / SETTINGS_FILE
            settings_temp = self.top_dir / TEMP_SETTINGS
            shutil.copy(settings_file, settings_temp)

            with settings_temp.open("rb") as itsfile:
                settings_dict = tomllib.load(itsfile)

            settings_temp.unlink()

            settings_web_dev = self.top_dir / WEB_DEV_SETTINGS
            with settings_web_dev.open("rb") as iwdfile:
                wddict = tomllib.load(iwdfile)
                settings_dict.update(wddict)

            with settings_temp.open("w") as sofile:
                for key, value in settings_dict.items():
                    line = f'{key}="{value}"' + os.linesep
                    sofile.write(line)

            shutil.copy(settings_temp, settings_file)

            with boot_file.open("w") as bofile:
                bofile.write("import storage" + os.linesep)
                bofile.write("storage.disable_usb_drive()" + os.linesep)
