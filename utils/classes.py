#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
@author: ChowRex
@contact: zrx879582094@gmail.com
@license: None
@file: classes.py
@time: 2021/4/8 3:39 下午
"""

import json
import logging
import os
import re
import subprocess
import tempfile
from collections import Iterable
from hashlib import md5
from logging import handlers
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests

from utils.exceptions import GetRepositoryInfoError
from utils.exceptions import MavenClientDeployError
from utils.exceptions import UploadComponentError

__version__ = (0, 1, 7)
__update_str__ = "增加日志记录器, 增加提取单个repo的方法"
__version_str__ = "当前版本:" + \
                  ".".join([str(x) for x in __version__]) + " 更新内容:" + __update_str__


class Nexus(object):
    """Nexus类"""
    BASE_URL = "service/rest/"
    HEADERS = {"accept": "application/json"}
    REPOSITORIES_API = "v1/repositories"

    def __init__(
            self,
            address: str,
            port: int = 80,
            protocol: str = "http",
            username: str = None,
            password: str = None,
            logger: logging.Logger = None):
        """
        初始化
        :param address: str 域名或IP
        :param port: int 端口
        :param protocol: str 协议, http或https
        :param username: str 用户名
        :param password: str 密码
        :param logger: logging.Logger类 日志记录器
        """
        self.address = address
        self.port = port
        self.protocol = protocol
        self.url = f"{self.protocol}://{self.address}:{self.port}"
        self.api_url = urljoin(
            self.url,
            self.BASE_URL)
        self.username = username
        self.password = password
        self.auth = (self.username, self.password)
        self.logger = logger if logger else Log().logger
        self._repositories = []

    def __str__(self):
        return f"<Nexus URL={self.url}>"

    def __repr__(self):
        return self.__str__()

    @property
    def repositories(self):
        """
        返回所有存储库
        :return: list
        """
        if not self._repositories:
            self._repositories = self._get_repositories()
        return self._repositories

    def _get_repositories(self):
        """
        获取所有存储库方法
        :return: list
        """
        url = urljoin(self.api_url, self.REPOSITORIES_API)
        response = requests.get(url, auth=self.auth, headers=self.HEADERS)
        j = json.loads(response.content.decode("utf-8"))
        repositories = []
        for d in j:
            repositories.append(
                self.Repository(
                    **d,
                    api_url=self.api_url,
                    auth=self.auth,
                    headers=self.HEADERS,
                    logger=self.logger))
        return repositories

    def repository(self, name: str):
        """
        获取指定名称的存储库实例
        :param name: str 存储库名称
        :return: self.Repository类
        """
        for repo in self.repositories:
            if repo.name == name:
                return repo
        return None

    class Repository(object):
        """Repository类"""

        MANAGEMENT_API = "v1/repositories/{format}/{type}/{repository}"
        COMPONENTS_API = "v1/components"
        REPOSITORIES_KEY = "repository"

        def __init__(
                self,
                name: str,
                format: str,
                type: str,
                api_url: str,
                auth: tuple = None,
                logger: logging.Logger = None,
                **kwargs):
            """
            初始化
            :param name: str 存储库名称
            :param format: str 存储库格式
            :param type: str 存储库类型
            :param api_url: str API请求地址
            :param auth: tuple 源数据认证信息
            :param logger: logging.Logger 日志记录器
            :param kwargs: dict 接受其他参数:
             - headers: dict 请求头字典
             - url: str 存储库地址
            """
            self.name = name
            self.format = format
            self.type = type
            self.api_url = api_url
            self.auth = auth
            self.logger = logger if logger else Log().logger
            self.kwargs = kwargs
            self.headers = self.kwargs.get("headers", Nexus.HEADERS)
            self.manage_api_url = None
            self._info = None

        def __str__(self):
            return f"<Repository Name={self.name} Format={self.format} Type={self.type} URL={self.url}>"

        def __repr__(self):
            return self.__str__()

        def _get_info(self):
            """
            获取存储库信息方法
            :return: dict 信息字典
            """
            # 如果是maven2类型, 管理API请求为maven, 并非maven2
            if self.format == "maven2":
                _format = "maven"
            else:
                _format = self.format
            manage_api = self.MANAGEMENT_API.format(
                format=_format,
                type=self.type,
                repository=self.name
            )
            # 拼接管理API请求地址
            self.manage_api_url = urljoin(self.api_url, manage_api)
            response = requests.get(
                self.manage_api_url,
                auth=self.auth,
                headers=self.headers)
            content = response.content.decode("utf-8")
            if response.status_code == 404 and content == "Repository not found":
                msg = "404异常, 如果您确定存储库存在, 请登录Nexus检查用户权限!" \
                      "应至少包含" \
                      f"'nx-repository-admin-{self.format}-{self.name}-read' 权限!"
                raise GetRepositoryInfoError(msg)
            if response.status_code not in [200, 204]:
                self.logger.error(content)
                raise GetRepositoryInfoError(response.status_code)
            return json.loads(content)

        @property
        def info(self):
            """
            返回当前存储库信息
            :return: dict
            """
            if not self._info:
                self._info = self._get_info()
            return self._info

        @property
        def url(self):
            """
            返回当前存储库连接地址
            :return: str
            """
            return self.kwargs.get("url", self.info.get("url"))

        @property
        def online(self):
            """
            返回当前存储库是否在线
            :return: bool
            """
            return self.info.get("online")

        @property
        def storage(self):
            """
            返回当前存储库的存储信息
            :return: dict
            """
            return self.info.get("storage")

        @property
        def blob(self):
            """
            返回当前存储库的Blob信息
            :return: str
            """
            return self.storage.get("blobStoreName")

        @property
        def policies(self):
            """
            返回当前存储库的清理规则
            :return: list
            """
            return self.info.get("cleanup", {}).get("policyNames", [])

        @property
        def remote(self):
            """
            返回当前存储库的代理地址 (仅适用于类型为proxy的存储库)
            :return: str or None
            """
            if self.type == "proxy":
                return self.info["proxy"]["remoteUrl"]
            else:
                return None

        @property
        def members(self):
            """
            返回当前存储库的组成员信息 (仅适用于类型为group的存储库)
            :return: list
            """
            if self.type == "group":
                return self.info.get(self.type)["memberNames"]
            else:
                return []

        @property
        def docker_v1_enabled(self):
            """
            返回当前存储库的是否支持v1版本 (仅适用于类型为docker的存储库)
            :return: bool or None
            """
            if self.format == "docker":
                return self.info.get(self.format)["v1Enabled"]
            else:
                return None

        @property
        def docker_force_basic_auth(self):
            """
            返回当前存储库的是否强制认证 (仅适用于类型为docker的存储库)
            :return: bool or None
            """
            if self.format == "docker":
                return self.info.get(self.format)["forceBasicAuth"]
            else:
                return None

        @property
        def docker_http_port(self):
            """
            返回当前存储库的http端口 (仅适用于类型为docker的存储库)
            :return: int or None
            """
            if self.format == "docker":
                return int(self.info.get(self.format)["httpPort"])
            else:
                return None

        @property
        def docker_https_port(self):
            """
            返回当前存储库的https端口 (仅适用于类型为docker的存储库)
            :return: int or None
            """
            if self.format == "docker":
                return int(self.info.get(self.format)["httpsPort"])
            else:
                return None

        @property
        def maven_version_policy(self):
            """
            返回当前存储库的maven版本策略 (仅适用于类型为maven2的存储库)
            :return: str or None
            """
            if self.format == "maven2" and self.type != "group":
                return self.info.get("maven")["versionPolicy"]
            else:
                return None

        @property
        def maven_layout_policy(self):
            """
            返回当前存储库的maven布局策略 (仅适用于类型为maven2的存储库)
            :return: str or None
            """
            if self.format == "maven2" and self.type != "group":
                return self.info.get("maven")["layoutPolicy"]
            else:
                return None

        @property
        def iter_component_getter(self):
            """
            获取部件获取器的迭代器
            :return: Iterable()
            """
            iterator = Nexus.IteratorComponentGetter(
                self.api_url, self.name, auth=self.auth, headers=self.headers)
            return iterator

        def upload_component(self, files: dict):
            """
            上传组件方法
            :param files: dict 上传的数据
            :return: None
            """
            url = urljoin(self.api_url, self.COMPONENTS_API)
            params = {self.REPOSITORIES_KEY: self.name}
            response = requests.post(
                url, params=params, files=files, auth=self.auth)
            if response.status_code not in [200, 204]:
                self.logger.error("*" * 50)
                self.logger.error(response.content.decode("utf-8"))
                self.logger.error(f"请求URL: {url}, 参数: {json.dumps(params)}")
                self.logger.error("*" * 50)
                raise UploadComponentError(response.status_code)

    class IteratorComponentGetter(object):
        """部件获取器迭代器"""

        def __init__(
                self,
                api_url: str,
                repository: str,
                auth: tuple = None,
                headers: dict = None,
                logger: logging.Logger = None):
            """
            初始化
            :param api_url: str API请求地址
            :param repository: str 存储库名称
            :param auth: tuple 认证信息
            :param headers: dict 请求头字典
            :param logger: logging.Logger 日志记录器
            """
            self.api_url = api_url
            self.repository = repository
            self.auth = auth
            self.headers = headers if headers else Nexus.HEADERS
            self.logger = logger if logger else Log().logger
            self.token = None
            self._started = False

        def __str__(self):
            """显示当前类信息"""
            return f"<{self.__doc__} API_URL={self.api_url} Repository={self.repository}>"

        def __repr__(self):
            return self.__str__()

        def __iter__(self):
            """
            默认迭代方法
            :return: self
            """
            return self

        def __next__(self):
            """
            遍历下一项默认方法
            :return: ComponentGetter
            """
            # 当且仅当token变回None时退出迭代
            if not self.token and self._started:
                raise StopIteration
            self._started = True
            getter = Nexus.ComponentGetter(
                self.api_url,
                self.repository,
                auth=self.auth,
                token=self.token,
                headers=self.headers,
                logger=self.logger)
            self.token = getter.continue_token
            return getter

    class ComponentGetter(object):
        """部件获取器"""

        TOKEN_KEY = "continuationToken"

        def __init__(
                self,
                api_url: str,
                repository: str,
                auth: tuple = None,
                token: str = None,
                headers: dict = None,
                logger: logging.Logger = None):
            """
            初始化
            :param api_url: str API请求地址
            :param repository: str 存储库名称
            :param auth: tuple 认证信息
            :param token: str 迭代器父token
            :param headers: dict 请求头字典
            :param logger: logging.Logger 日志记录器
            """
            self.COMPONENTS_API = Nexus.Repository.COMPONENTS_API
            self.REPOSITORIES_KEY = Nexus.Repository.REPOSITORIES_KEY
            self.api_url = api_url
            self.url = urljoin(self.api_url, self.COMPONENTS_API)
            self.repository = repository
            self.auth = auth
            self.token = token
            self.headers = headers if headers else Nexus.HEADERS
            self.logger = logger if logger else Log().logger
            kwargs = {
                "headers": self.headers, "params": {
                    self.REPOSITORIES_KEY: self.repository}}
            if self.auth:
                kwargs["auth"] = self.auth
            if self.token:
                kwargs["params"][self.TOKEN_KEY] = self.token
            response = requests.get(self.url, **kwargs)
            j = json.loads(response.content.decode("utf8"))
            self._items = j["items"]
            self.continue_token = j[self.TOKEN_KEY]
            self._components = []

        def __str__(self):
            """显示当前类信息"""
            return f"<{self.__doc__} API_URL={self.url} Repository={self.repository} Token={self.token}>"

        def __repr__(self):
            return self.__str__()

        @property
        def components(self):
            """
            返回所有组件
            :return: list
            """
            if not self._components:
                self._components = self._get_components()
            return self._components

        def _get_components(self):
            """
            获取当前获取器所获取到的所有组件
            :return:
            """
            components = []
            for item in self._items:
                components.append(
                    Nexus.Component(
                        **item,
                        api_url=self.api_url,
                        auth=self.auth,
                        logger=self.logger))
            return components

    class Component(object):
        """部件类"""

        COMPONENT_API = "v1/components/{id}"

        def __init__(
                self,
                id: str,
                api_url: str,
                auth: tuple = None,
                logger: logging.Logger = None,
                **kwargs):
            """
            初始化
            :param id: str 当前组件id
            :param api_url: str API请求地址
            :param auth: tuple 源地址认证信息
            :param logger: logging.Logger类 日志记录器
            :param kwargs: 允许传入其他信息:
             - headers: dict 请求头字典
             - repository: str 当前组件所属存储库名称
             - name: str 当期组件的名称
             - format: str 当前组件的格式
             - group: str 当前组件的组ID
             - version: str 当前组件的版本
            """
            self.id = id
            self.api_url = api_url
            self.auth = auth
            self.info_api_url = urljoin(
                self.api_url,
                self.COMPONENT_API.format(
                    id=self.id))
            self.logger = logger if logger else Log().logger
            self.kwargs = kwargs
            self.headers = self.kwargs.get("headers", Nexus.HEADERS)
            self._info = None
            self._directory = None

        def __str__(self):
            """显示当前类信息"""
            info = "<" \
                   f"{self.__doc__} " \
                   f"ID={self.id} " \
                   f"Repository={self.repository} " \
                   f"Name={self.name} " \
                   f"Format={self.format} " \
                   f"Group={self.group} " \
                   f"Version={self.version}" \
                   ">"
            return info

        def __repr__(self):
            return self.__str__()

        def _get_info(self):
            """
            获取当前组件信息方法
            :return: dict 信息字典
            """
            # 拼接管理API请求地址
            response = requests.get(
                self.info_api_url,
                auth=self.auth,
                headers=self.headers)
            return json.loads(response.content.decode("utf-8"))

        @property
        def info(self):
            """
            返回当前组件信息
            :return: dict
            """
            if not self._info:
                self._info = self._get_info()
            return self._info

        @property
        def repository(self):
            """
            返回当前组件的存储库名称
            :return: str
            """
            return self.kwargs.get("repository", self.info["repository"])

        @property
        def name(self):
            """
            返回当前组件的名称
            :return: str
            """
            return self.kwargs.get("name", self.info["name"])

        @property
        def format(self):
            """
            返回当前组件的格式
            :return: str
            """
            return self.kwargs.get("format", self.info["format"])

        @property
        def group(self):
            """
            返回当前组件的组信息
            :return: str
            """
            return self.kwargs.get("group", self.info["group"])

        @property
        def version(self):
            """
            返回当前组件的版本信息
            :return: str
            """
            return self.kwargs.get("version", self.info["version"])

        @property
        def _assets(self):
            """
            返回当前组件的资源列表
            :return: list
            """
            return self.kwargs.get("assets", self.info["assets"])

        @property
        def assets(self):
            """
            返回当前部件的所有资源
            :return: list
            """
            assets = []
            for d in self._assets:
                d["api_url"] = self.api_url
                d["auth"] = self.auth
                assets.append(Nexus.Asset(**d))
            return assets

        @property
        def directory(self):
            """
            获取当前部件的下载目录
            :return: str 下载目录
            """
            return self._directory

        def download(
                self,
                path: str = os.getcwd(),
                exclude: Iterable = None):
            """
            下载当前组件的所有资源
            :param path: str 基础路径, 默认为当前目录
            :param exclude: Iterable 排除列表, 可以是元组/列表/集合等
            :return: list 资源的保存路径
            """
            if not exclude:
                exclude = []
            os.makedirs(path, exist_ok=True)
            self._directory = tempfile.mkdtemp(dir=path)
            d = os.path.join(self._directory, self.name)
            if not os.path.exists(d):
                os.makedirs(d, exist_ok=True)
            files = []
            for asset in self.assets:
                # 排除自动生成文件
                if asset.extension in exclude:
                    continue
                files.append(asset.download(d))
            return files

    class Asset(object):
        """资源类"""

        ASSET_API = "v1/assets/{id}"

        def __init__(
                self,
                id: str,
                api_url: str,
                auth: tuple = None,
                logger: logging.Logger = None,
                **kwargs):
            """
            初始化资源类
            :param id: str 资源ID
            :param api_url: str API请求地址
            :param auth: str 源地址认证信息
            :param logger: logging.Logger类 日志记录器
            :param kwargs: dict 允许传入其他信息
             - path: str 资源路径
             - repository: str 资源存储库名
             - format: str 资源格式
             - download_url: str 资源下载链接
            """
            self.id = id
            self.api_url = api_url
            self.auth = auth
            self.info_api_url = urljoin(
                self.api_url,
                self.ASSET_API.format(
                    id=self.id))
            self.logger = logger if logger else Log().logger
            self.kwargs = kwargs
            self.headers = self.kwargs.get("headers", Nexus.HEADERS)
            self._info = None

        def __str__(self):
            """显示当前类信息"""
            info = "<" \
                   f"{self.__doc__} " \
                   f"ID={self.id} " \
                   f"Repository={self.repository} " \
                   f"Name={self.name} " \
                   f"Format={self.format} " \
                   f"DownloadURL={self.download_url} " \
                   ">"
            return info

        def __repr__(self):
            return self.__str__()

        def _get_info(self):
            """
            获取当前资源信息方法
            :return: dict 信息字典
            """
            # 拼接管理API请求地址
            response = requests.get(
                self.info_api_url,
                auth=self.auth,
                headers=self.headers)
            return json.loads(response.content.decode("utf-8"))

        @property
        def info(self):
            """
            返回当前组件信息
            :return: dict
            """
            if not self._info:
                self._info = self._get_info()
            return self._info

        @property
        def path(self):
            """
            返回当前资源的路径
            :return: str
            """
            return self.kwargs.get("path", self.info["path"])

        @property
        def name(self):
            """
            返回当前资源的名称
            :return: str
            """
            return os.path.basename(self.path)

        @property
        def extension(self):
            """
            返回当前资源的拓展名
            :return: str
            """
            return self.name.split(".")[-1]

        @property
        def download_url(self):
            """
            返回当前资源的下载URL
            :return: str
            """
            return self.kwargs.get(
                "download_url", self.info["downloadUrl"])

        @property
        def repository(self):
            """
            返回当前资源的存储库名称
            :return: str
            """
            return self.kwargs.get(
                "repository", self.info["repository"])

        @property
        def format(self):
            """
            返回当前组件的格式
            :return: str
            """
            return self.kwargs.get("format", self.info["format"])

        @property
        def checksum(self):
            """
            返回当前资源的校验信息
            :return: str
            """
            return self.kwargs.get("checksum", self.info["checksum"])

        @property
        def md5(self):
            """
            返回当前资源的md5校验值
            :return: str
            """
            return self.checksum.get("md5")

        @property
        def sha1(self):
            """
            返回当前资源的sha1校验值
            :return: str
            """
            return self.checksum.get("sha1")

        @property
        def sha256(self):
            """
            返回当前资源的sha256校验值
            :return: str
            """
            return self.checksum.get("sha256")

        @property
        def sha512(self):
            """
            返回当前资源的sha512校验值
            :return: str
            """
            return self.checksum.get("sha512")

        @property
        def stream(self):
            """
            获取当前资源的字节流
            :return: bytes
            """
            return requests.get(
                self.download_url,
                auth=self.auth,
                stream=True).content

        def download(self, directory: str = os.getcwd()):
            """
            下载当前资源到指定目录
            :param directory: str 下载目录
            :return: str 文件路径
            """
            file = File(os.path.join(directory, self.name))
            # 如果文件已存在, 则检查md5, 不一致才需要下载
            if file.exists:
                if self.md5 == file.md5():
                    return file.path
            with open(file.path, "wb") as f:
                f.write(self.stream)
            return file.path


class File(object):
    """文件类"""

    def __init__(self, path: str):
        """
        初始化
        :param path: str 文件路径
        """
        self.path = path
        self.name = os.path.basename(self.path)
        self.extension = self.name.split(".")[-1]

    def __str__(self):
        return f"<{self.__doc__} Path={self.path}>"

    def __repr__(self):
        return self.__str__()

    @property
    def exists(self):
        """
        检查文件是否存在
        :return: bool
        """
        return os.path.exists(self.path)

    def md5(self, chunk: int = 4096):
        """
        获取文件md5值
        :param chunk: int 分块大小
        :return: str md5值
        """
        _md5 = md5()
        with open(self.path, "rb") as f:
            for chk in iter(lambda: f.read(chunk), b""):
                _md5.update(chk)
        return _md5.hexdigest()


class POM(object):
    """POM类"""

    def __init__(self, path: str):
        """
        初始化
        :param path: str POM文件地址
        """
        self.path = path
        self._tree = None

    @property
    def namespace(self):
        """
        返回命名空间
        :return: str
        """
        tag = self.tree.getroot().tag
        result = re.findall(r"{(.*)}", tag)
        if len(result) == 1:
            return result[0]
        else:
            return None

    @property
    def tree(self):
        """
        返回tree
        :return: ElementTree
        """
        if not self._tree:
            self._tree = ElementTree.parse(self.path)
        return self._tree

    @property
    def children(self):
        """
        子元素生成器
        :return: Element
        """
        for child in self.tree.getroot():
            yield child

    def replace(self, key: str, mapping: dict):
        """
        通过映射字典替换URL
        :param key: str 查询的关键字
        :param mapping: dict 映射字典
        :return: None
        """
        search = f".//{{{self.namespace}}}{key}"
        results = self.tree.getroot().findall(search)
        for result in results:
            result.text = mapping.get(result.text, result.text)
        ElementTree.register_namespace("", self.namespace)
        self.tree.write(self.path)


class MavenClient(object):
    """Maven客户端类"""

    DEFAULT_BIN = "mvn"
    DEFAULT_CONF = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../conf/settings.xml"))

    def __init__(self, binary: str = DEFAULT_BIN,
                 setting: str = DEFAULT_CONF,
                 logger: logging.Logger = None):
        """
        初始化
        :param binary: str 二进制可执行客户端路径
        :param setting: str 指定默认配置文件路径
        :param logger: logging.Logger类 日志记录器
        """
        self.binary = binary
        self.setting = setting
        self.logger = logger if logger else Log().logger
        self._args = []

    def __str__(self):
        return f"<{self.__doc__} Binary={self.binary} Setting={self.setting}>"

    def __repr__(self):
        return self.__str__()

    @property
    def args(self):
        """
        返回参数列表
        :return: list
        """
        return self._args

    @args.setter
    def args(self, args: Iterable):
        """
        修改参数列表项
        :param args: Iterable 可迭代对象
        :return: None
        """
        self._args.extend(args)

    @property
    def shell(self):
        """
        返回执行的shell命令
        :return: str
        """
        return f"{self.binary} --settings {self.setting} {' '.join(self._args)}"

    def deploy(self):
        """
        执行上传命令
        :return: None or raise MavenClientDeployError
        """
        self._args.insert(0, "deploy:deploy-file")
        command = [self.binary, "--settings", self.setting] + self.args
        try:
            out = subprocess.check_output(command).decode("utf-8").strip()
            self.logger.info(out)
        except subprocess.CalledProcessError as e:
            self.logger.error("*" * 50)
            self.logger.error(f"执行命令: {self.shell}")
            self.logger.error("错误信息:")
            self.logger.error(e.output.decode("utf-8").strip())
            self.logger.error("*" * 50)
            raise MavenClientDeployError(e.returncode)


class Singleton(type):
    """单例模式"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


class Log(object, metaclass=Singleton):
    """日志类"""

    DEFAULT_FORMAT = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"

    def __init__(
            self,
            name: str = __name__,
            level: str = "INFO",
            directory: str = os.path.join(os.getcwd(), "log"),
            **kwargs):
        """
        初始化日志类
        :param name: str 指定日志名称
        :param level: str 指定日志等级
        :param kwargs: 允许传入其他参数
         - info_file: str info日志名称
         - error_file: str error日志名称
        """
        self.name = name
        self.level = level.upper()
        self.directory = directory
        self.info_file = kwargs.get("info_file", f"{__name__}_info.log")
        self.error_file = kwargs.get("error_file", f"{__name__}_error.log")
        self.format = kwargs.get("format", self.DEFAULT_FORMAT)
        self.info_path = os.path.join(self.directory, self.info_file)
        self.error_path = os.path.join(self.directory, self.error_file)
        self._logger = None

    @property
    def logger(self):
        """
        返回日志记录器
        :return: logger
        """
        if not self._logger:
            self._logger = self._get_logger()
        return self._logger

    def _get_logger(self):
        """
        获取日志记录器
        :return: logging.getLogger()
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        formatter = logging.Formatter(self.format)
        # 创建屏幕流
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(self.level)
        stream_handler.setFormatter(formatter)

        os.makedirs(self.directory, exist_ok=True)
        # 创建INFO文件处理器
        file_handler_info = handlers.TimedRotatingFileHandler(
            self.info_path, when="D")
        file_handler_info.setFormatter(formatter)
        file_handler_info.setLevel(logging.INFO)
        # 创建ERROR文件处理器
        file_handler_error = handlers.TimedRotatingFileHandler(
            self.error_path, when="D")
        file_handler_error.setFormatter(formatter)
        file_handler_error.setLevel(logging.ERROR)
        # 添加所有处理器
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler_info)
        logger.addHandler(file_handler_error)
        return logger
