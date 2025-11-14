# Avatar Plugin

MaiBot 头像表情包插件 - 提供表情包生成和头像分析功能。

## 功能特性

### 1. 表情包生成

- **命令模式**: 通过 `/menu` 和 `/meme` 命令手动生成表情包
- **智能模式**: AI 自动选择合适的表情包（15% 触发概率）
- **自动依赖安装**: 首次运行时自动检测并安装 `meme-generator` 依赖

### 2. 头像分析

- 自动获取 QQ 用户头像
- 使用 MaiBot 视觉模型分析头像内容
- 存储头像描述到独立数据库表
- 供其他功能调用获取用户头像信息

## 快速开始

### 安装

1. 将插件文件夹放入 `MaiBot/plugins/` 目录
2. 插件会在首次运行时自动安装依赖（优先使用 `uv`，否则使用 `pip`）

### 配置

在 `config/config.toml` 中配置插件行为：

```toml
[plugin]
enabled = true

[meme]
enable_command_mode = true    # 启用命令模式
enable_action_mode = true     # 启用智能模式

[avatar]
enable_analysis = true        # 启用头像分析
analysis_prompt = "分析这个QQ头像，简洁描述图片内容（50字内）"
```

## 使用方法

### 表情包命令

#### 查看菜单
```
/menu
```
显示所有可用的表情包列表，按分类展示。

#### 生成表情包
```
/meme <表情包名> [文字1] [文字2]...
```

示例：
```
/meme 鲁迅 我没说过这句话
/meme 这就是爱 上面文字 下面文字
```

### 智能表情包

无需手动调用，AI 会在适当时机自动发送表情包（15% 概率）。

### 头像分析 API

插件提供 `get_head_description_for_prompt(person_id)` 接口供其他模块调用：

```python
from plugins.avatar_plugin.plugin_api import get_head_description_for_prompt

# 在生成 prompt 时添加头像描述
head_desc = get_head_description_for_prompt(person_id)
if head_desc:
    prompt += f"\n用户头像: {head_desc}"
```

## 技术架构

### 核心组件

1. **MemeManager**: 单例模式管理表情包加载和生成
2. **AvatarAnalyzer**: 头像获取和视觉分析
3. **Database Models**: 独立的 `avatar_descriptions` 表

### 依赖自动安装

插件启动时执行依赖检查：

```
检查 meme-generator 是否安装
  ↓ 未安装
检查 uv 是否可用
  ↓ 是
uv pip install meme-generator
  ↓ 否
pip install meme-generator
```

### 数据库表结构

**avatar_descriptions**
- `person_id` (INT): 关联 MaiBot 的 person 表
- `platform` (TEXT): 平台类型（qq/discord）
- `user_id` (TEXT): 平台用户 ID
- `head_description` (TEXT): 头像描述
- `analyzed_at` (DATETIME): 分析时间
- `avatar_url` (TEXT): 头像 URL

## 注意事项

1. **视觉模型配置**: 需要在 MaiBot 配置中设置 `vision_general` 模型
2. **平台支持**: 目前仅支持 QQ 平台的头像获取
3. **依赖网络**: 表情包生成和头像获取需要网络连接
4. **自动安装**: 首次运行可能需要较长时间安装依赖

## 常见问题

### Q: 表情包功能未启用？
A: 检查 `meme-generator` 是否安装成功，或手动执行：
```bash
pip install meme-generator
# 或使用 uv
uv pip install meme-generator
```

### Q: 头像分析失败？
A: 确认以下配置：
- MaiBot 配置中有 `vision_general` 模型
- 视觉模型 API 可用且配额充足
- 网络连接正常

### Q: 如何禁用某个功能？
A: 在配置文件中设置对应选项为 `false`：
```toml
[meme]
enable_action_mode = false  # 禁用智能模式

[avatar]
enable_analysis = false     # 禁用头像分析
```

## 开发说明

### 插件组件

- `MemeMenuCommand`: 菜单命令组件
- `MemeGenerateCommand`: 生成命令组件
- `AutoMemeAction`: 智能表情包 Action
- `AnalyzeAvatarAction`: 头像分析 Action


## 许可证

与 MaiBot 主项目保持一致。
