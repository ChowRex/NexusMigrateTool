#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: ChowRex
@contact: zrx879582094@gmail.com
@license: None
@file: exceptions.py
@time: 2021/4/8 3:44 下午
"""

__version__ = (0, 1, 1)
__update_str__ = "增加类型检查异常"
__version_str__ = "当前版本:" + \
                  ".".join([str(x) for x in __version__]) + " 更新内容:" + __update_str__


class RepositoryTypeNotSupport(Exception):
    """存储库类型不支持异常"""
    ...


class RepositoryFormatNotSupport(Exception):
    """存储库格式不支持异常"""
    ...


class AssetExceedMaximum(Exception):
    """资源数量超过最大限制"""
    ...


class UploadComponentError(Exception):
    """上传组件包失败"""
    ...


class MaximumRetriesReached(Exception):
    """达到最大重试次数错误"""
    ...


class GetRepositoryInfoError(Exception):
    """获取存储库信息异常"""
    ...


class MavenClientDeployError(Exception):
    """Maven客户端部署失败异常"""
    ...


class MissingMavenSettingError(Exception):
    """缺少Maven配置信息路径"""
    ...


class MissingSnapshotIdError(Exception):
    """缺少上传快照私服的id"""
    ...
