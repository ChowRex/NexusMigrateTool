   * [中文说明](#中文说明)
      * [如何使用](#如何使用)
   * [English](#english)
      * [How to use](#how-to-use)
   
# 中文说明

Nexus存储库迁移工具, 支持Nexus OSS 3.x 单个存储库的迁移

## 如何使用

1. 克隆本项目, 或下载zip包

2. 修改`conf/config.ini`, 修改信息

   ```ini
    ; 源Nexus信息
    [SourceNexus]
    address = 127.0.0.1
    port = 8081
    username = admin
    password = abc123
    
    ; 目标Nexus信息
    [TargetNexus]
    address = nexus.YourCompany.com
    port = 80
    username = deploy-user
    password = temp_passwd_for_deploy
    
    ; Maven客户端配置文件名称
    [Maven]
    config = maven.yaml
   ```

3. 修改`conf/maven.yaml`文件

   ```yaml
   # Maven 客户端用户配置文件名称
   settings: settings.xml
   # 用于上传snapshot的配置ID
   snapshot_id: snapshots
   # 跳过拓展名
   excludes:
     - md5
     - sha1
     - sha256
     - sha512
   # 临时目录名称
   tmp_dir: assets
   # POM修改映射信息, 由源库地址替换为新库地址
   pom_url_mapping:
     "http://127.0.0.1:8081/repository/maven-snapshots/": "http://nexus.YourCompany.com/repository/maven-hosted-devel/"
     "http://127.0.0.1:8081/repository/maven-releases/": "http://nexus.YourCompany.com/repository/maven-hosted-prod/"
   
   ```

4. 修改`conf/settings.xml`文件

   ```xml
   <settings>
       <servers>
           <server>
               <id>releases</id>
               <!--修改为目标Nexus的部署用户-->
               <username>deploy-user</username>
               <password>temp_passwd_for_deploy</password>
           </server>
           <server>
               <id>snapshots</id>
               <!--修改为目标Nexus的部署用户-->
               <username>deploy-user</username>
               <password>temp_passwd_for_deploy</password>
           </server>
       </servers>
       <mirrors>
           <mirror>
               <id>nexus</id>
               <mirrorOf>*</mirrorOf>
               <!--这里可以修改为Nexus的代理地址 / 其他中央仓库 / 源Nexus仓库, 用于处理依赖-->
               <url>http://nexus.yourcompany.com/repository/maven-group-proxys/</url>
           </mirror>
       </mirrors>
       <profiles>
           <profile>
               <id>nexus</id>
               <repositories>
                   <repository>
                       <id>central</id>
                       <url>http://central</url>
                       <releases>
                           <enabled>true</enabled>
                       </releases>
                       <snapshots>
                           <enabled>true</enabled>
                       </snapshots>
                   </repository>
               </repositories>
               <pluginRepositories>
                   <pluginRepository>
                       <id>central</id>
                       <url>http://central</url>
                       <releases>
                           <enabled>true</enabled>
                       </releases>
                       <snapshots>
                           <enabled>true</enabled>
                       </snapshots>
                   </pluginRepository>
               </pluginRepositories>
           </profile>
       </profiles>
       <activeProfiles>
           <!--make the profile active all the time -->
           <activeProfile>nexus</activeProfile>
       </activeProfiles>
   </settings>
   ```

5. 执行命令

   ```shell
   pip install -r requirements.txt
   ./nexus_migrate_tool -h
   usage: nexus_migrate_tool [-h] [-c CONFIG] [-p POOL] -s SOURCE -t TARGET [--settings SETTINGS] [-v] [-vv]
   
   Migrate Repository Between Nexuses.
   
   optional arguments:
     -h, --help            show this help message and exit
     -c CONFIG, --config CONFIG
                           The path of the configure file. (default: ./conf/config.ini)
     -p POOL, --pool POOL  The number of the processes. (default: 10)
     -s SOURCE, --source SOURCE
                           The name of the source Nexus repository. (default: )
     -t TARGET, --target TARGET
                           The name of the target Nexus repository. (default: )
     --settings SETTINGS   The path of the maven client settings.xml. (default: ./conf/settings.xml)
     -v, --version         Show version of this script
     -vv, --verbose        Enable DEBUG level logging. (default: False)
   
   ```

   

6. [可选]如果迁移的maven库的jar包类型为`SNAPSHOT`, 则需要安装`maven客户端`

   ```shell
   # 如果是Mac用户, 并且安装了 homebrew
   brew install mvn
   # 如果是Linux用户或Windows用户, 则访问官方网站下载客户端即可.
   # https://maven.apache.org/download.cgi
   # 前置依赖为JDK 1.7+
   # https://www.oracle.com/java/technologies/javase/javase-jdk8-downloads.html
   mvn -h
   # 上述命令未报错的情况下, 方可迁移SNAPSHOT库, 否则仅支持迁移RELEASE
   ```

# English

The tool for migrate Nexus repository, support single repository migration of Nexus OSS 3.x.

## How to use

1. Clone this project or just download the `.zip` file

2. Modify `conf/config.ini`, correct the information

   ```ini
    ; The info of source Nexus
    [SourceNexus]
    address = 127.0.0.1
    port = 8081
    username = admin
    password = abc123
    
    ; The info of target Nexus
    [TargetNexus]
    address = nexus.YourCompany.com
    port = 80
    username = deploy-user
    password = temp_passwd_for_deploy
    
    ; Maven Client config file name
    [Maven]
    config = maven.yaml
   ```

3. Modify`conf/maven.yaml`

   ```yaml
   # Maven Client User profile name
   settings: settings.xml
   # The server id for upload snapshot jars
   snapshot_id: snapshots
   # The extensions which needs ignored
   excludes:
     - md5
     - sha1
     - sha256
     - sha512
   # The name of temporary directory
   tmp_dir: assets
   # The mapping dict for POM file, which need to replace the old url to new ones.
   pom_url_mapping:
     "http://127.0.0.1:8081/repository/maven-snapshots/": "http://nexus.YourCompany.com/repository/maven-hosted-devel/"
     "http://127.0.0.1:8081/repository/maven-releases/": "http://nexus.YourCompany.com/repository/maven-hosted-prod/"
   
   ```

4. Modify`conf/settings.xml`

   ```xml
   <settings>
       <servers>
           <server>
               <id>releases</id>
               <!--Target Nexus deploy user-->
               <username>deploy-user</username>
               <password>temp_passwd_for_deploy</password>
           </server>
           <server>
               <id>snapshots</id>
               <!--Target Nexus deploy user-->
               <username>deploy-user</username>
               <password>temp_passwd_for_deploy</password>
           </server>
       </servers>
       <mirrors>
           <mirror>
               <id>nexus</id>
               <mirrorOf>*</mirrorOf>
               <!--This can be the proxy of Nexus Maven proxy / other central / source Nexus Repo, just used for solve the dependencies-->
               <url>http://nexus.yourcompany.com/repository/maven-group-proxys/</url>
           </mirror>
       </mirrors>
       <profiles>
           <profile>
               <id>nexus</id>
               <repositories>
                   <repository>
                       <id>central</id>
                       <url>http://central</url>
                       <releases>
                           <enabled>true</enabled>
                       </releases>
                       <snapshots>
                           <enabled>true</enabled>
                       </snapshots>
                   </repository>
               </repositories>
               <pluginRepositories>
                   <pluginRepository>
                       <id>central</id>
                       <url>http://central</url>
                       <releases>
                           <enabled>true</enabled>
                       </releases>
                       <snapshots>
                           <enabled>true</enabled>
                       </snapshots>
                   </pluginRepository>
               </pluginRepositories>
           </profile>
       </profiles>
       <activeProfiles>
           <!--make the profile active all the time -->
           <activeProfile>nexus</activeProfile>
       </activeProfiles>
   </settings>
   ```

5. Execute the shell command

   ```shell
   pip install -r requirements.txt
   ./nexus_migrate_tool -h
   usage: nexus_migrate_tool [-h] [-c CONFIG] [-p POOL] -s SOURCE -t TARGET [--settings SETTINGS] [-v] [-vv]
   
   Migrate Repository Between Nexuses.
   
   optional arguments:
     -h, --help            show this help message and exit
     -c CONFIG, --config CONFIG
                           The path of the configure file. (default: ./conf/config.ini)
     -p POOL, --pool POOL  The number of the processes. (default: 10)
     -s SOURCE, --source SOURCE
                           The name of the source Nexus repository. (default: )
     -t TARGET, --target TARGET
                           The name of the target Nexus repository. (default: )
     --settings SETTINGS   The path of the maven client settings.xml. (default: ./conf/settings.xml)
     -v, --version         Show version of this script
     -vv, --verbose        Enable DEBUG level logging. (default: False)
   
   ```

   

6. [Optional] If you want to migrate the maven repository type is `SNAPSHOT`, then you need install`maven client` first.

   ```shell
   # If using Mac, and the homebrew was installed.
   brew install mvn
   # If using Linux or Windows, then you need go to the official website to download the client
   # https://maven.apache.org/download.cgi
   # JDK 1.7+ is required.
   # https://www.oracle.com/java/technologies/javase/javase-jdk8-downloads.html
   mvn -h
   # The SNAPSHOT repository can only be migrated if the above command does not report an error, otherwise only the RELEASE migration is supported.
   ```

