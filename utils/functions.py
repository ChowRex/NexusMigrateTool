#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: ChowRex
@contact: zrx879582094@gmail.com
@license: None
@file: functions.py
@time: 2021/4/20 9:12 上午
"""

__version__ = (0, 0, 1)
__update_str__ = "初始创建"
__version_str__ = "当前版本:" + \
    ".".join([str(x) for x in __version__]) + " 更新内容:" + __update_str__

import os
import yaml
import tempfile
from collections import Iterable
from shutil import rmtree
from multiprocessing import Pool

from utils.classes import Nexus, Log, POM, MavenClient
from utils.exceptions import AssetExceedMaximum
from utils.exceptions import MissingMavenSettingError
from utils.exceptions import MissingSnapshotIdError

DEFAULT_POOL = 10


def migrate_maven2_repository(
        src_repo: Nexus.Repository,
        dst_repo: Nexus.Repository,
        config: str,
        processes: int = DEFAULT_POOL,
        logger: Log().logger = None):
    with open(config, "r", encoding="utf-8") as conf:
        yml = yaml.safe_load(conf)
    excludes = yml.get("excludes", [])
    tmp_dir = yml.get("tmp_dir", tempfile.mkdtemp())
    url_mapping = yml.get("pom_url_mapping")
    logger = logger if logger else Log().logger
    if src_repo.maven_version_policy == "RELEASE":
        pool = Pool(processes)
        for getter in src_repo.iter_component_getter:
            for component in getter.components:
                pool.apply_async(
                    migrate_maven_release_component, args=(
                        component,
                        dst_repo,
                        url_mapping,
                        excludes,
                        tmp_dir,
                        logger))
        pool.close()
        pool.join()
    elif src_repo.maven_version_policy == "SNAPSHOT":
        setting = os.path.join(os.path.dirname(config), yml.get("settings"))
        if not os.path.exists(setting):
            msg = "Missing the maven client settings.xml"
            raise MissingMavenSettingError(msg)
        snapshot_id = yml.get("snapshot_id")
        if not snapshot_id:
            msg = "Missing the id in {setting.xml}/settings/servers/server, " \
                  "which was used for upload snapshots."
            raise MissingSnapshotIdError(msg)
        pool = Pool(processes)
        for getter in src_repo.iter_component_getter:
            for component in getter.components:
                pool.apply_async(
                    migrate_maven_snapshot_component,
                    args=(
                        component,
                        dst_repo,
                        setting,
                        snapshot_id,
                        url_mapping,
                        excludes,
                        tmp_dir,
                        logger))
        pool.close()
        pool.join()


def migrate_maven_release_component(
        component: Nexus.Component,
        repository: Nexus.Repository,
        url_mapping: dict,
        excludes: Iterable = None,
        tmp_dir: str = None,
        logger: Log().logger = Log().logger):
    """
    迁移生产组件
    :param component: Component类 需要迁移的component实例
    :param repository: Repository类 迁移的目标存储库实例
    :param url_mapping: dict 用于替换pom文件的URL地址映射字典
    :param excludes: Iterable 可迭代对象, 包含排除拓展名文件
    :param tmp_dir: str 临时存储目录
    :param logger: logging.logger类 日志记录器
    :return: None
    """
    excludes = excludes if excludes else []
    tmp_dir = tmp_dir if tmp_dir else tempfile.mkdtemp()
    files = {
        "maven2.groupId": (None, component.group),
        "maven2.artifactId": (None, component.name),
        "maven2.version": (None, component.version)
    }
    num = 0
    _dir = ""
    for asset in component.assets:
        # 排除自动生成文件
        if asset.extension in excludes:
            continue
        num += 1
        # pom文件需要执行下载并修改对应目录
        if asset.extension == "pom":
            os.makedirs(tmp_dir, exist_ok=True)
            _dir = tempfile.mkdtemp(dir=tmp_dir)
            pom = POM(asset.download(_dir))
            pom.replace("url", url_mapping)
            files[f"maven2.asset{num}"] = (asset.name, open(pom.path, "rb"))
        else:
            files[f"maven2.asset{num}"] = (asset.name, asset.stream)
        files[f"maven2.asset{num}.extension"] = (None, asset.extension)
        # 如果是sources文件, 则需要添加classifier
        if asset.extension == "jar" and "sources" in asset.name:
            files[f"maven2.asset{num}.classifier"] = (None, "sources")
    # 检查asset数量
    if num > 3:
        msg = f"组件[{component.name}]的资源数量超过3, 无法上传!"
        raise AssetExceedMaximum(msg)
    repository.upload_component(files)
    if os.path.exists(_dir):
        rmtree(_dir)
    logger.info(f"已上传[{component.name}]")


def migrate_maven_snapshot_component(
        component: Nexus.Component,
        repository: Nexus.Repository,
        setting: str,
        snapshot_id: str,
        url_mapping: dict,
        excludes: Iterable = None,
        tmp_dir: str = None,
        logger: Log().logger = Log().logger):
    """
    迁移快照maven组件
    :param component: Component类 需要迁移的component实例
    :param repository: Repository类 迁移的目标存储库实例
    :param setting: str 配置文件的路径
    :param snapshot_id: str 用于上传snapshots的配置ID
    :param url_mapping: dict 用于替换pom文件的URL地址映射字典
    :param excludes: Iterable 可迭代对象, 包含排除拓展名文件
    :param tmp_dir: str 临时存储目录
    :param logger: logging.logger类 日志记录器
    :return: None
    """
    excludes = excludes if excludes else []
    tmp_dir = tmp_dir if tmp_dir else tempfile.mkdtemp()
    # 下载资源并获取资源文件路径列表
    assets = component.download(tmp_dir, excludes)
    # 构造参数字典
    args_dict = {
        "-DgroupId": component.group,
        "-DartifactId": component.name,
        "-Dversion": component.version,
        "-Dpackaging": "jar",
        "-Durl": repository.url,
        "-DrepositoryId": snapshot_id,
    }
    for asset in assets:
        if asset.endswith(".jar"):
            if "sources" in asset:
                args_dict["-Dsources"] = asset
            else:
                args_dict["-Dfile"] = asset
        elif asset.endswith(".pom"):
            pom = POM(asset)
            pom.replace("url", url_mapping)
            args_dict["-DpomFile"] = asset
    maven = MavenClient(setting=setting)
    maven.args = [f"{k}={v}" for k, v in args_dict.items()]
    if "-Dfile" in args_dict.keys():
        maven.deploy()
    rmtree(component.directory)
    logger.info(f"已上传[{component.name}]")
