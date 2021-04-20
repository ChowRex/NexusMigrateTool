#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: ChowRex
@contact: zrx879582094@gmail.com
@license: None
@file: migrate_repo_between_nexus.py
@time: 2021/4/8 3:39 下午
"""

import os
import argparse
from configparser import ConfigParser
from utils.classes import Nexus, Log
from utils.functions import migrate_maven2_repository
from utils.exceptions import RepositoryTypeNotSupport
from utils.exceptions import RepositoryFormatNotSupport

__version__ = (0, 1, 5)
__update_str__ = "增加参数方法"
__version_str__ = "当前版本:" + \
                  ".".join([str(x) for x in __version__]) + " 更新内容:" + __update_str__

DEFAULT_CONF_PATH = "./conf/config.ini"
DEFAULT_SETTING_PATH = "./conf/settings.xml"
SUPPORT_FORMAT = ["maven2"]
DEFAULT_POOL = 10


def main():
    """
    主函数
    :return: None
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Migrate Repository Between Nexuses."
    )
    parser.add_argument(
        "-c",
        "--config",
        help="The path of the configure file.",
        type=str,
        default=DEFAULT_CONF_PATH)
    parser.add_argument(
        "-p",
        "--pool",
        help="The number of the processes.",
        type=int,
        default=DEFAULT_POOL)
    parser.add_argument(
        "-s",
        "--source",
        help="The name of the source Nexus repository.",
        type=str,
        default="", required=True)
    parser.add_argument(
        "-t",
        "--target",
        help="The name of the target Nexus repository.",
        type=str,
        default="", required=True)
    parser.add_argument(
        "--settings",
        help="The path of the maven client settings.xml.",
        type=str,
        default=DEFAULT_SETTING_PATH)
    parser.add_argument(
        "-v",
        "--version",
        help="Show version of this script",
        action="version",
        version=__version_str__)
    parser.add_argument(
        "-vv",
        "--verbose",
        help="Enable DEBUG level logging.",
        action="store_true")
    args = parser.parse_args()

    workdir = os.path.abspath(os.path.dirname(__file__))
    config_path = os.path.join(workdir, args.config)
    config = ConfigParser()
    config.read(config_path)
    level = "DEBUG" if args.verbose else "INFO"
    logger = Log(level=level).logger
    src_nexus = Nexus(**config["SourceNexus"], logger=logger)
    dst_nexus = Nexus(**config["TargetNexus"], logger=logger)

    src_repo = src_nexus.repository(args.source)
    if src_repo.type != "hosted":
        msg = f"{src_repo.type} is NOT supported!"
        raise RepositoryTypeNotSupport(msg)
    if src_repo.format not in SUPPORT_FORMAT:
        msg = f"{src_repo.format} is NOT supported!"
        raise RepositoryFormatNotSupport(msg)

    dst_repo = dst_nexus.repository(args.target)
    logger.info(f"Migrating From [{src_repo.name}] -> [{dst_repo.name}]")
    if src_repo.format == "maven2":
        maven_conf = os.path.join(
            os.path.dirname(config_path),
            config["Maven"]["config"])
        migrate_maven2_repository(
            src_repo,
            dst_repo,
            maven_conf,
            logger=logger)
    logger.info("Migration Completed!")


if __name__ == "__main__":
    main()
