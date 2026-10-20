# wenyu-koubo-jianying

口播与访谈剪辑工作流：完整原话剪辑稿、剪映原生可编辑草稿、原生字幕与重点包装。

## 当前版本

2026-10-21：在原 Skill 上合并 L02 完整口播实践的素材核验、重录比较、语义 B-Roll、原生字幕、配乐、验收及返修流程。保留原名和入口；只粗剪、只改字幕等任务不自动扩展。字号、阴影和位置改为按项目校准，历史参数保留为案例。

这次是规则与参考资料更新；案例已获用户认可，陌生素材迁移及独立盲测尚未完成。已完成案例的 Agent 实际听校缺项与用户反馈分别记录，不以用户认可补写未做过的检查。

## 在另一台Mac上安装

这是私有仓库。先让目标设备具备该GitHub账号的Git访问权限；浏览器登录和Git命令行登录不是同一件事。不要把密钥或token粘贴到聊天或仓库。

请让目标设备上的Agent执行：

1. 将本仓库克隆到该设备固定的Skill源目录。已有仓库时先核对来源与本地修改，不另建重复副本。
2. 在仓库根目录运行 `bash install.sh`。
3. 核验公共入口、必要的专属入口和引用资源；运行依赖另行检查。

```bash
git clone https://github.com/WayneArchi/wenyu-koubo-jianying.git
cd wenyu-koubo-jianying
bash install.sh
```

安装复用随仓库保存的dbs-install-skill脚本，公共入口指向本设备的源目录，不包含Mini或T7的固定路径。不要在安装后移动源目录。打开新会话后使用 `$wenyu-koubo-jianying`。

## 更新

在这个固定仓库目录运行：

```bash
bash update.sh
```

更新只接受本仓库的main分支和快进更新；存在本地修改、来源不符或分支不符时停止并保留现场。需要Git具备私有仓库访问权限。源文件更新后公共入口仍指向同一位置，不再重复安装另一份Skill。ZIP下载可以用于临时安装和核对，但需要更新时应使用固定Git克隆目录。

## 修改与回退

所有修改保存在同一仓库，每次变更单独提交。候选改进先测试，通过后再进入main。恢复旧能力使用Git revert形成新提交，不强推、不重写历史。回退Skill不自动改动剪映工程或媒体。

合并前版本保存在远端分支 `backup/pre-course-merge-20261021`，基线提交为 `20d3676c4c1ecab666eff7248da2afa7a4ba42d0`。需要撤销这次合并时，在 main 上对本次流程合并提交执行 `git revert <提交号>`，检查后正常推送；不要用 reset 或强推覆盖后续历史。

`BASELINE_MANIFEST.json`仍记录最初16个Skill文件的历史校验值，不用于宣称更新后的文件与旧版相同。旧样式参数保存在具名历史案例中，不代表跨画幅通用参数。

## 执行依赖

macOS、剪映专业版、Python 3、FFmpeg/FFprobe，以及独立配置的volcengine-audio-transcription、jianying-editor和所需dbskill内容工具。仓库不打包这些执行组件、媒体工具或凭据；旧复现包dependencies需在目标机独立安装核验。安装Skill不等于执行环境已就绪。

## 验证与文件范围

本次通过 Skill frontmatter、YAML/JSON、内部引用与脚本语法检查，24项原有包装脚本回归测试全部通过。结构检查保留1项提醒：沿用已有 config 目录，不为符合目录建议而迁移并破坏引用。新流程另做边界规则复核；这不是陌生素材执行测试或盲测。此前已核对原始16文件基线和隔离安装入口。GitHub来源的npx安装未验证，本仓库使用上面的Git克隆与安装脚本路径。另一台实体设备尚需实际执行安装核验，不能把Mini上的检查称作MacBook已安装。

tools/dbs-install-skill/scripts中的安装器原样复用本机dbs-install-skill版本。本仓库不包含课程视频、练习素材、成片、原始转写、私密样本和密钥。

## 给另一台设备上的Agent

安装时可以直接发送：

> 请从私有仓库 https://github.com/WayneArchi/wenyu-koubo-jianying 安装wenyu-koubo-jianying。先核验本机GitHub的Git访问权限，将仓库克隆到固定目录，运行bash install.sh并核验入口及引用资源。已有同名Skill时先检查来源和本地改动，不覆盖不同来源；缺运行依赖时继续配置可配置部分并列明剩余项。

更新时可以直接发送：

> 请更新wenyu-koubo-jianying：找到它的固定源仓库，核对远端和本地改动，运行bash update.sh，报告更新前后提交；有本地修改时先保留，不强行覆盖。
