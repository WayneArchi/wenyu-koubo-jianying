# wenyu-koubo-jianying

口播与访谈剪辑工作流：完整原话剪辑稿、剪映原生可编辑草稿、原生字幕与重点包装。

## 当前版本

此提交保存课程学习改进前的既有 Skill 基线。原有运行规则保持不变；本次同步不代表课程方法已写入，也不代表陌生素材迁移测试通过。

## 使用

在支持 Agent Skills 的客户端安装本仓库的 `skills/wenyu-koubo-jianying/` 后调用 `$wenyu-koubo-jianying`，提供本次素材和所需交付范围。

## 依赖

macOS、剪映专业版、Python 3、FFmpeg/FFprobe，以及独立配置的 `volcengine-audio-transcription` 和 `jianying-editor`。按 Skill 引用的方法，还需对应 dbskill 内容工具。此仓库不打包这些组件、媒体工具或凭据；原有复现包中的 dependencies 需在目标机独立安装和核验。安装 Skill 不等于这些执行依赖已具备。

## 安装验证状态

仓库资源进行静态检查；GitHub 来源的 `npx skills add` 安装尚未验证，不提供已验证安装的承诺。私有仓库下载需要具备访问权限。

## 版本与回退

在同一仓库维护一个 Skill 名称。先保存基线提交，再在候选分支记录改进；用旧能力回归和陌生素材验证后决定保留。回退规则使用 Git revert 形成新提交，保留历史，不强制覆盖远端。回退 Skill 不会自动回退剪映工程、安装依赖或删除媒体文件。

`BASELINE_MANIFEST.json` 记录这次基线的完整文件清单与校验值。后续改动单独提交并说明验证范围。

课程视频、练习素材、成片、原始转写、私密测试和密钥均不进入此仓库。字体等配置是旧版状态，不代表跨画幅通用参数。
