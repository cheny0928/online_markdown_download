# 在线教程手册下载器

一个用于下载在线教程并将内容转换为Markdown格式的Python工具。

## 功能特性

- 🔍 **智能元素查找**: 支持通过class、id或标签名查找目标元素
- 🔗 **链接提取**: 自动提取目标元素中的所有链接
- 📝 **Markdown转换**: 将HTML页面内容转换为格式化的Markdown
- 📁 **批量下载**: 支持批量下载多个页面
- 📊 **详细日志**: 完整的日志记录，便于问题排查
- 📂 **原始HTML保存**: 所有页面html只保存到downloads/ori_html/域名/目录
- 🗂️ **一键汇总**: 所有页面内容合并为一份md文件
- 🏷️ **目录跳转**: 支持目录和标题锚点跳转，快速切换页面
- 🖼️ **图片补全**: md中的图片链接全部补全为完整url

## 安装依赖

```bash
uv sync
```

## 使用方法

### 1. 命令行使用

```bash
uv run python .\cli.py https://docs.wxauto.org/docs/ --type class --value hextra-scrollbar --filename wxauto使用说明.md
```

### 2. API服务使用

本项目支持通过FastAPI对外提供接口服务。

#### 启动API服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 调用API示例

POST `/download/`

请求体（JSON）：
```json
{
  "url": "https://example.com/tutorial",
  "config": {
    "type": "class",
    "value": "urlList"
  },
  "filename": "my_tutorial.md",
  "pre_remove_type": "class",
  "pre_remove_value": "ad-banner|footer"
}
```

- `pre_remove_type` 和 `pre_remove_value` 可选，用于在转换前批量删除页面上的指定元素（如广告、页脚等）。
- `pre_remove_value` 支持用 `|` 分隔多个值。

返回：
- **直接返回Markdown文件流**，浏览器或curl会自动下载，响应头带有`Content-Disposition`，支持中文文件名。

curl命令示例：
```bash
curl -X POST "http://127.0.0.1:8000/download/" \
  -H "Content-Type: application/json" \
  -o my_tutorial.md \
  -d '{
    "url": "https://example.com/tutorial",
    "config": {"type": "class", "value": "urlList"},
    "filename": "my_tutorial.md",
    "pre_remove_type": "class",
    "pre_remove_value": "ad-banner|footer"
  }'
```

> 如需下载中文文件名，建议用`-OJ`参数（curl 7.20+）：
> ```bash
> curl -X POST "http://127.0.0.1:8000/download/" -H "Content-Type: application/json" -OJ -d '{...}'
> ```

### 3. 编程使用

```python
from markdown_downloader import MarkdownDownloader

base_url = "https://example.com/tutorial"
config = {
    "type": "class",
    "value": "urlList"
}
downloader = MarkdownDownloader(base_url, config)
downloader.run()  # 会生成downloads/ori_html/域名/下的html和downloads/域名/all_in_one.md
```

### 4. 网页可视化界面使用

本项目内置了一个网页前端，支持通过浏览器可视化填写参数并一键下载Markdown文件。

#### 启动服务

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 使用方法
1. 启动服务后，在浏览器访问：http://127.0.0.1:8000
2. 填写各项参数：
   - **下载URL**：教程主页网址
   - **元素类型(type)**：选择 class、id 或 tag
   - **元素值(value)**：目标元素的值
   - **输出文件名**：下载保存的Markdown文件名
   - **预移除元素类型/值**（可选）：如需批量移除广告、页脚等元素，可填写类型和值（多个值用 | 分隔）
3. 点击“开始下载”按钮，页面会自动下载生成的Markdown文件。
4. 如遇错误，页面会有红色提示。

> 前端页面无需额外配置，所有功能均已集成在本项目中。

## 文件结构说明

- `downloads/ori_html/域名/` 目录下：
    - 每个页面保存为 `xxx.html`，文件名根据url路径自动生成
- `downloads/域名/all_in_one.md`：所有页面内容合并为一份md，顶部有主链接和目录，正文可跳转
- `download.log`：详细日志

## Markdown文件说明

- 所有导出的md文件**开头会自动写入主链接**，便于溯源
- md中的a标签如果是本地页面，自动跳转到md内锚点，否则补全为完整url
- md中的图片全部补全为完整url，保证本地阅读时可访问

## 示例

### 下载Python官方教程

```bash
uv run cli.py https://docs.python.org/zh-cn/3.13/tutorial/ --type class --value toctree-wrapper --filename python官方文档.md --pre-remove-type class --pre-remove-value "sphinxsidebar|related|footer|inline-search|mobile-nav"
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。
