# v2 原生识别字幕与分层包装

先读 [内容判断规则](content-packaging-v2.md)。本阶段复用已确认粗剪、原始转写和本次源范围；只粗剪时不自动包装。已有直接制作授权时不反复确认；用户要求半程停，则先交该检查点，不擅自做后半段。

## 两条制作通路

普通字幕：在剪映对本次目标视频/原声原生识别，批量校对、改分句和设置样式；本次固定白色#FFFFFF、13号、无描边、65%阴影，不能把标题/重点花字黄色套给字幕。核对实际音轨、时间线及选区，避免跨时间线操作。火山转写仍供选内容与找源时间，不能替代本次要求的剪映识别。当前helper不实现识别或批量UI操作，能力不可用时应明确说明，不用普通text叠字冒充识别字幕。

已有覆盖本次目标范围、来源可核对且仍与当前粗剪对应的剪映识别字幕时优先复用，只识别缺失范围；不能再次全量识别叠出重复字幕。剪口或选区变化后核对已有字幕是否同步，不能仅凭text类型判定来源或正确性。

识别后的校字与分段按[原生字幕合分](native-subtitles.md)执行：审错字、过长换行、过短孤立片段和跨主题断句，结合语义与实际字形宽度合分；不按固定字数或逐字均分。右侧“字幕”逐句列表的语义断点按Return拆为两段，下一句句首Backspace合并上一句；“文本”页用于字体参数，手动换行不算字幕重分。Return与Backspace各有本轮单次实测，两者都须另核对同步与完整字幕范围。

包装：新素材先依据原片独立确定内容方案、主题、时长、留删理由与顺序，再做视觉包装；已确认方案沿用。Agent读完整稿与必要原声上下文，自主选择重点、步骤、对比和章节，记录原话依据、理由及形式；不要求用户先给关键词。逐字引用保留原话，忠实概括用verbatim:false并保留条件与否定。参考片仅用于视觉形式、字体候选、颜色与层级，序数/总结词不自动成为放大的重点。本轮已看过参考，不当严格盲测。

原生字幕和既有文字可以同时存在；helper保留它们的所有字段，只追加包装轨。不能推断任意text轨都是剪映识别结果；识别来源仍靠实际UI过程记录。要清理旧版伪字幕或迁移既有包装，须明确目标轨道，按原生草稿流程在可信当前状态上单独处理；helper不自动删轨。

## 输入及映射

粗剪计划沿用audit_plan.py；仅包装阶段另加本次canvas:{width,height}。恒定1x的源时间按具体clip_index（从0开始）映射；变速/倒放应另行适配，不能改原速度来通过校验。

包装计划可含texts及checkpoint_end_us。不再支持非空captions：普通字幕走剪映识别。旧emphasis可作为只做强调的兼容入口，但不能与texts同时使用。

```json
{
  "checkpoint_end_us": 2000000,
  "texts": [{
    "id": "chapter-1", "role": "chapter", "layer": 0,
    "source_spans": [
      {"clip_index": 0, "source_start_us": 0, "source_end_us": 1000000},
      {"clip_index": 1, "source_start_us": 5000000, "source_end_us": 6000000}
    ],
    "text": "本次方法标题", "verbatim": false,
    "evidence_quote": "与该方法直接对应的实际原话", "reason": "持续提示当前方法，不逐句抢字幕",
    "style": {"size": 8, "color": [1,0.9607843137254902,0.596078431372549], "bold": true, "x": 0, "y": 0.55,
      "border": null, "shadow": {"alpha": 0.65, "color": [0,0,0], "diffuse": 15, "distance": 5, "angle": -45},
      "font": {"from_material_id": "替换为本次UI确认字体的真实原生文字材料ID"}},
    "motion": "none"
  }]
}
```

示例不是实际证据、剪口或默认风格，其中字体材料ID是必须替换的说明占位，不能直接运行。示例RGB对应本次标题/重点花字的常用强调色#FFF598，不能用于普通字幕。单剪口项也可使用clip_index/source_start_us/source_end_us三个字段；与source_spans互斥。

跨剪口source_spans必须按连续成片顺序覆盖相邻保留片段，目标区间无洞、无重叠，不能包含已删掉的话。helper为一项创建一个连续文字片段，即使跨源文件也不按剪口拆字卡；motion:pop只在该文字首次开始运行一次。章节驻留多久是内容和用户选择，不是课程强制规则。

role可取chapter、step、explanation、comparison、quote、emphasis，表示文字任务；layer是0至1000的排序值。每个role/layer一条原生文字轨，按layer、role稳定排序。不同角色/层可以同时出现；同角色同层不得重叠，相邻章节采用半开区间。相同显示时段仍须检查遮挡和信息负担，脚本不会自动理解画面。

所有项均需非空evidence_quote和reason，证据须出现在所覆盖word_intervals中。verbatim默认为true，展示文本须与证据词面相符；false允许Agent忠实概括。标点/空白忽略的匹配不证明语义、因果和限定正确，必须人工/Agent回到完整上下文核查。非BMP/emoji的文字范围尚未核实，当前拒绝而不猜UTF-16规则。

只有句级ASR、没有可信word_intervals时，不把一句均分成假词时间，也不伪造字段通过helper。先复用已有原始词时间或实际校准记录；确实缺失时，可完成无时码重点方案并标包装未生成，继续现有剪映字幕的独立校对。获取新的词级结果须遵守本轮转写授权与复用原则，不能为校验自动重复付费请求。

## 字形、层级和动态

style支持size、color、bold、x、y、border、shadow、font。size是原生JSON单位，不能声称等于UI13号；x/y为半画幅位移、正y向上，不能把UI高度75%直接写成y=.75。实际字号与位置先在本次画幅校准。无描边用border:null；需要描边时显式指定{color,width,alpha}，width为原生0至1数值。

shadow:null关闭阴影，或提供alpha、RGB color、diffuse、distance、angle。SDK序列化使用diffuse/600，其他字段按SDK原值；这是候选映射，未做v2原生UI实测。阴影和字体复制到所有局部高亮样式段，避免只作用于首段。

读取[当前样式配置](../config/style-preferences.json)：字幕和标题花字首选新青年体，后现代体备选，必须经剪映UI确认真实选中和资源；禁止默默用系统默认。先在本次目标原生文字中选好字体，保存后读取可信当前快照，再用{from_material_id:"该真实字体样本的文字材料ID"}复制已有font元数据。helper本身不新增按字体名选择/下载能力，不证明复制的资源就是指定字体；仍需核对实际显示和保存重开。font:system在底层接口只表示不写资源，本任务不得把它作为交付字体或失败回退。helper拒绝无样本字体名、虚构资源ID和SDK的C:/D:占位路径。highlights以精确word设置color、size、bold；本次标题/重点花字常用黄色#FFF598对应RGB[1,0.9607843137254902,0.596078431372549]，普通字幕保持白色#FFFFFF，不应用此黄色。缺词或重叠样式拒绝。

参照成片只支持视觉字形辨识与候选比较，不能声称从扁平MP4读取到了准确font或资源ID。没有真实原生字体样本时保留字体待确认，不能拿系统字生成结果后宣称完成。

布局必须经过[原生安全区验收](native-safe-area.md)：实际打开抖音预览与字幕操作安全区，对普通字幕、标题、花字及脸/动作证据检查平台遮挡。双白框外框绝不越、内框尽量不越；按真实字形、阴影、换行和动画峰值核对，不能用固定画布比例或helper坐标校验冒充此步骤。helper没有打开安全区或自动检测遮挡的能力。

motion支持none、pop，pop最短200000us。keyframes可附多个{property,points}：property为scale/x/y/rotation，points为递增的{time_offset_us,value}，只支持线性；所有偏移在一个文字片段的总时长内。已有pop不能再附scale关键帧。通用位置/旋转关键帧及新字号/阴影/字体均需原生重开验证，不能继承v1冒烟结果。

新增文字render_index至少15000并高于既有最大层级，is_tone_modify:false，省略hdr_settings。原平台、原视频、原音频、HLG及既有字幕参数不改；不得为新文字兼容性强改旧工程平台头。

图片、自动图形资产、音效选择/插入、特殊资源动画、原生识别与UI批改不在该helper实现范围；传入未支持字段会报错。可在目标环境确有已验证能力时另行执行，不能说helper已完成这些工作。

## 命令与阶段状态

```bash
python3 scripts/build_packaging.py --rough-plan /absolute/rough.json --packaging-plan /absolute/package.json --validate-only
python3 scripts/build_packaging.py --rough-plan /absolute/rough.json --packaging-plan /absolute/package.json --draft-input /absolute/current-plain.json --out /absolute/work/staged-package.json
```

输出只能是全新暂存文件，不接受真实草稿目录、原生默认文件名、覆盖源或覆盖旧文件。此前已有v1/v2管理标记或保留名轨道时拒绝重复应用；迁移/继续需单独核对已有层，不能简单再跑一遍。

checkpoint_end_us限制新增包装的最晚结束；越过就报错，不自动裁短章节。已有粗剪视频与字幕仍完整保留，后半段包装记录not_started。Agent需在实际检查点停止并交付，不自行继续；后续等待用户反馈后按新授权恢复。

checkpoint_end_us不保护已确认的前段。继续半成品时，先记录本次目标时间线ID、已完成时间区间及其轨道/材料ID，锁定已确认范围；新增只落在用户授权区间，不能重建或改掉前段。已有v2管理标记会拒绝再次套用；不能删标记绕过，应在可信当前状态上做有范围的原生局部更新或另行审查迁移。新时间线也逐一记录ID，不能默认工程根文件或第一个子时间线就是目标。

canvas和总时长匹配不证明实际源引用/剪口/调序相同；写入前逐段交叉核对。登记、主子时间线同步、可信明文获取、加密处理和原生重开继续遵守[native-draft.md](native-draft.md)。未听校、未核对原生字幕、未检查字形/阴影/关键帧，都分别记录。交付重点依据、实际完成范围及检查点，不默认导出。
