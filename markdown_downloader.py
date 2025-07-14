#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线教程手册下载器
用于下载在线教程并将内容转换为Markdown格式
"""

import requests
import time
import os
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import html2text
import json
from typing import List, Dict, Optional
import logging
from collections import OrderedDict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MarkdownDownloader:
    """在线教程手册下载器主类"""
    
    def __init__(self, base_url: str, config: Dict, pre_remove_type=None, pre_remove_value=None):
        """
        初始化下载器
        
        Args:
            base_url (str): 教程主页URL
            config (Dict): 配置信息，包含type和value字段
            pre_remove_type (str): 预处理要删除的元素类型
            pre_remove_value (str): 预处理要删除的元素值
        """
        self.base_url = base_url
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = False
        self.h2t.body_width = 0  # 不限制行宽
        self.pre_remove_type = pre_remove_type
        self.pre_remove_value = pre_remove_value
        
    def get_page_content(self, url: str) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url (str): 页面URL
            
        Returns:
            Optional[str]: 页面HTML内容，失败时返回None
        """
        try:
            logger.info(f"正在获取页面: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            
            content = response.text
            logger.info(f"页面获取成功，状态码: {response.status_code}")
            logger.info(f"页面编码: {response.encoding}")
            logger.info(f"页面内容长度: {len(content)} 字符")
            
            # # 保存页面内容用于调试
            # debug_filename = f"debug_page_{url.replace('://', '_').replace('/', '_').replace(':', '_')}.html"
            # try:
            #     with open(debug_filename, 'w', encoding='utf-8') as f:
            #         f.write(content)
            #     logger.info(f"页面内容已保存到: {debug_filename}")
            # except Exception as e:
            #     logger.warning(f"保存调试页面失败: {e}")
            
            return content
            
        except requests.RequestException as e:
            logger.error(f"获取页面失败 {url}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"响应状态码: {e.response.status_code}")
                logger.error(f"响应头: {e.response.headers}")
            return None
    
    def find_target_elements(self, html_content: str):
        """
        查找所有目标元素
        Args:
            html_content (str): 页面HTML内容
        Returns:
            list: 所有找到的目标元素列表
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            element_type = self.config.get('type', 'class')
            element_value = self.config.get('value', '')
            logger.info(f"开始查找所有目标元素: type={element_type}, value={element_value}")
            if element_type == 'class':
                elements = soup.find_all(class_=element_value)
            elif element_type == 'id':
                elements = soup.find_all(id=element_value)
            elif element_type == 'tag':
                elements = soup.find_all(element_value)
            else:
                logger.error(f"不支持的元素类型: {element_type}")
                return []
            logger.info(f"共找到 {len(elements)} 个目标元素")
            for i, elem in enumerate(elements):
                logger.info(f"  元素 {i+1}: {elem.name} - {elem.get_text()[:100]}...")
            return elements
        except Exception as e:
            logger.error(f"查找目标元素失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def extract_links(self, elements) -> List[str]:
        """
        从所有目标元素中提取所有链接，顺序去重
        
        Args:
            elements (List[BeautifulSoup] or BeautifulSoup): 目标元素或元素列表
        Returns:
            List[str]: 提取到的去重后链接列表，顺序保持
        """
        links = []
        try:
            # 兼容单个元素和元素列表
            if not isinstance(elements, list):
                elements = [elements]
            logger.info(f"开始从 {len(elements)} 个目标元素中提取链接")
            
            # 获取主页的域名部分
            from urllib.parse import urlparse
            base_parsed = urlparse(self.base_url)
            base_domain = f"{base_parsed.scheme}://{base_parsed.netloc}"
            logger.info(f"主页域名: {base_domain}")
            
            total_a_tags = 0
            for idx, element in enumerate(elements):
                logger.info(f"处理第 {idx+1} 个元素: {element.name}")
                all_links = element.find_all('a', href=True)
                logger.info(f"  找到 {len(all_links)} 个a标签")
                total_a_tags += len(all_links)
                for i, link in enumerate(all_links):
                    href = link['href'].strip()
                    link_text = link.get_text().strip()
                    original_href = href
                    final_href = href
                    # 处理各种相对链接
                    if href.startswith('http://') or href.startswith('https://'):
                        final_href = href
                    elif href.startswith('//'):
                        final_href = base_parsed.scheme + ':' + href
                    elif href.startswith('/'):
                        final_href = base_domain + href
                    else:
                        final_href = urljoin(self.base_url, href)
                    logger.info(f"    链接 {i+1}: {link_text} -> 原始: {original_href} | 拼接后: {final_href}")
                    if final_href.startswith('#') or final_href.startswith('javascript:') or final_href.split("/")[-1].startswith('#'):
                        logger.info(f"      跳过链接: {final_href} (锚点或javascript)")
                        continue
                    links.append(final_href)
                    logger.info(f"      添加链接: {final_href}")
            logger.info(f"所有元素共找到 {total_a_tags} 个a标签，合并后共 {len(links)} 个链接（未去重）")
            # 顺序去重
            unique_links = list(OrderedDict.fromkeys(links))
            logger.info(f"去重后剩余 {len(unique_links)} 个链接")
            for i, link in enumerate(unique_links):
                logger.info(f"  链接 {i+1}: {link}")
            return unique_links
        except Exception as e:
            logger.error(f"提取链接失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return []
    
    def html_to_markdown(self, html_content: str) -> str:
        """
        将HTML内容转换为Markdown格式
        
        Args:
            html_content (str): HTML内容
            
        Returns:
            str: Markdown格式的内容
        """
        try:
            # 使用html2text转换
            markdown_content = self.h2t.handle(html_content)

            # 清理多余的空行
            lines = markdown_content.split('\n')
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line.strip() == '':
                    if not prev_empty:
                        cleaned_lines.append(line)
                    prev_empty = True
                else:
                    cleaned_lines.append(line)
                    prev_empty = False
            md = '\n'.join(cleaned_lines)

            # 用正则去除所有HTML a标签，只保留内容
            import re
            # 去除<a ...>内容</a>，保留内容
            md = re.sub(r'<a [^>]*>(.*?)</a>', r'\1', md, flags=re.DOTALL|re.IGNORECASE)
            # 去除自闭合a标签 <a .../>
            md = re.sub(r'<a [^>]*/>', '', md, flags=re.DOTALL|re.IGNORECASE)
            return md
        except Exception as e:
            logger.error(f"HTML转Markdown失败: {e}")
            return f"转换失败: {e}\n\n原始内容:\n{html_content}"
    
    def download_and_convert(self, url: str, index: int) -> Optional[str]:
        """
        下载页面并转换为Markdown
        
        Args:
            url (str): 页面URL
            index (int): 页面索引
            
        Returns:
            Optional[str]: Markdown内容，失败时返回None
        """
        try:
            # 获取页面内容
            html_content = self.get_page_content(url)
            if not html_content:
                return None
            
            # 转换为Markdown
            markdown_content = self.html_to_markdown(html_content)
            
            # 添加页面信息
            page_info = f"# 页面 {index + 1}\n\n**URL:** {url}\n\n---\n\n"
            return page_info + markdown_content
            
        except Exception as e:
            logger.error(f"处理页面失败 {url}: {e}")
            return None
    
    def save_markdown(self, content: str, filename: str = "tutorial.md"):
        """
        保存Markdown内容到文件
        
        Args:
            content (str): Markdown内容
            filename (str): 文件名
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Markdown文件已保存: {filename}")
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
    
    def safe_filename(self, url_path: str, ext: str = '.md') -> str:
        """
        将url路径转换为安全的文件名
        """
        # 去除开头的/
        url_path = url_path.lstrip('/')
        # 替换特殊符号
        safe = re.sub(r'[^\w\-_\.]+', '_', url_path)
        if not safe:
            safe = 'index'
        return safe + ext

    def get_domain_folder(self) -> str:
        """
        获取downloads/域名/目录，域名特殊符号替换为_
        """
        from urllib.parse import urlparse
        parsed = urlparse(self.base_url)
        domain = re.sub(r'[^\w\-_\.]+', '_', parsed.netloc)
        folder = os.path.join('downloads', domain)
        os.makedirs(folder, exist_ok=True)
        return folder

    def save_html(self, content: str, filename: str):
        """
        保存html到指定文件
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

    def fix_md_links(self, md: str, url_map: dict, base_url: str) -> str:
        """
        修正md中的a/img等链接为本地md或完整url
        """
        from urllib.parse import urljoin, urlparse
        def repl_a(match):
            text, href = match.group(1), match.group(2)
            if href in url_map:
                return f'[{text}]({url_map[href]})'
            # 相对链接补全
            if not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)
            return f'[{text}]({href})'
        def repl_img(match):
            alt, src = match.group(1), match.group(2)
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            return f'![{alt}]({src})'
        # 修正a标签
        md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_a, md)
        # 修正图片
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl_img, md)
        return md

    def remove_config_element(self, html: str) -> str:
        """
        删除config.value指定的元素（class、id、tag）
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            element_type = self.config.get('type', 'class')
            element_value = self.config.get('value', '')
            if element_type == 'class':
                for tag in soup.find_all(class_=element_value):
                    tag.decompose()
            elif element_type == 'id':
                for tag in soup.find_all(id=element_value):
                    tag.decompose()
            elif element_type == 'tag':
                for tag in soup.find_all(element_value):
                    tag.decompose()
            return str(soup)
        except Exception as e:
            logger.warning(f"删除指定元素失败: {e}")
            return html

    def remove_root_a_tags(self, html: str) -> str:
        """
        删除页面中不包含其它元素的根节点a标签
        """
        from bs4 import NavigableString
        try:
            soup = BeautifulSoup(html, 'lxml')
            # 只查找body下的直接a标签和html/body下的直接a标签
            for a in soup.find_all('a'):
                # 1. 只保留没有子标签的a（即a.contents全是NavigableString）
                if all(isinstance(c, NavigableString) for c in a.contents):
                    # 2. 父节点是body或html或直接是根节点
                    parent = a.parent
                    if parent and parent.name in ['body', 'html', '[document]']:
                        a.decompose()
            return str(soup)
        except Exception as e:
            logger.warning(f"删除根节点a标签失败: {e}")
            return html

    def pre_remove_elements(self, html: str) -> str:
        """
        在转markdown前预处理删除指定元素，支持多个value用|分隔
        """
        if not self.pre_remove_type or not self.pre_remove_value:
            return html
        try:
            soup = BeautifulSoup(html, 'lxml')
            values = [v.strip() for v in str(self.pre_remove_value).split('|') if v.strip()]
            for value in values:
                if self.pre_remove_type == 'class':
                    for tag in soup.find_all(class_=value):
                        tag.decompose()
                elif self.pre_remove_type == 'id':
                    for tag in soup.find_all(id=value):
                        tag.decompose()
                elif self.pre_remove_type == 'tag':
                    for tag in soup.find_all(value):
                        tag.decompose()
            return str(soup)
        except Exception as e:
            logger.warning(f"预处理删除元素失败: {e}")
            return html

    def run(self, output_filename: str = "all_in_one.md"):
        logger.info(f"开始下载教程: {self.base_url}")
        main_page_content = self.get_page_content(self.base_url)
        if not main_page_content:
            logger.error("无法获取主页内容")
            return
        target_elements = self.find_target_elements(main_page_content)
        if not target_elements:
            logger.error("未找到目标元素")
            return
        links = self.extract_links(target_elements)
        if not links:
            logger.error("未找到任何链接")
            return
        # 生成html保存文件夹
        from urllib.parse import urlparse
        base_parsed = urlparse(self.base_url)
        domain = re.sub(r'[^\w\-_\.]+', '_', base_parsed.netloc)
        html_folder = os.path.join('downloads', 'ori_html', domain)
        os.makedirs(html_folder, exist_ok=True)
        # md保存文件夹
        md_folder = os.path.join('downloads', domain)
        os.makedirs(md_folder, exist_ok=True)
        # 主页也保存
        # 去除URL中的锚点，避免重复
        def strip_fragment(url):
            return url.split('#')[0]
        all_urls = [strip_fragment(self.base_url)] + [strip_fragment(link) for link in links]
        # 顺序去重
        from collections import OrderedDict
        all_urls = list(OrderedDict.fromkeys(all_urls))
        url_to_title = {}
        url_to_anchor = {}
        url_to_html = {}
        # 1. 下载所有页面，提取标题，保存html
        for url in all_urls:
            logger.info(f"下载页面: {url}")
            html = self.get_page_content(url)
            if not html:
                logger.warning(f"页面下载失败: {url}")
                continue
            # 保存html到downloads/ori_html/域名/
            parsed = urlparse(url)
            path = parsed.path if parsed.path else 'index'
            if path.endswith('/'):
                path += 'index'
            html_name = self.safe_filename(path, '.html')
            html_path = os.path.join(html_folder, html_name)
            self.save_html(html, html_path)
            logger.info(f"已保存html: {html_path}")
            url_to_html[url] = html_path
            # 提取标题
            soup = BeautifulSoup(html, 'lxml')
            title = soup.title.string.strip() if soup.title and soup.title.string else path
            url_to_title[url] = title
            # 生成锚点
            anchor = re.sub(r'[^\w\-]+', '', title.lower())
            url_to_anchor[url] = anchor
        # 2. 生成目录
        toc_lines = ["# 目录\n"]
        for url in all_urls:
            if url in url_to_title:
                toc_lines.append(f"- [{url_to_title[url]}](#{url_to_anchor[url]})")
        toc = '\n'.join(toc_lines) + '\n\n---\n\n'
        # 3. 生成正文，每个页面加锚点和标题
        all_content = [toc]
        for url in all_urls:
            if url not in url_to_html:
                continue
            html = open(url_to_html[url], encoding='utf-8').read()
            # 统一：所有页面都先预处理删除元素
            html = self.pre_remove_elements(html)
            # 其它页面再删config元素和根a标签
            if url == self.base_url:
                html_clean = html
            else:
                html_clean = self.remove_config_element(html)
                html_clean = self.remove_root_a_tags(html_clean)
            md = self.html_to_markdown(html_clean)
            # 修正md内链接和图片（图片全部补全为完整url）
            md_fixed = self.fix_md_links_fullurl(md, url_to_anchor, url, url_to_title)
            # 页面标题（不再插入<a id=...>）
            all_content.append(f'# {url_to_title[url]}\n\n')
            all_content.append(md_fixed)
            all_content.append('\n\n---\n\n')
        # 4. 保存总md
        # 在md文件开头插入主链接
        main_link_info = f'> **主链接：[{self.base_url}]({self.base_url})**\n\n'
        all_md = main_link_info + ''.join(all_content)
        md_path = os.path.join(md_folder, output_filename)
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(all_md)
        logger.info(f"全部页面已合并为: {md_path}")

    def fix_md_links_local(self, md: str, url_to_md: dict, base_url: str, images_folder: str) -> str:
        """
        修正md中的a/img等链接为本地md或本地图片路径/完整url
        """
        from urllib.parse import urljoin, urlparse
        import requests
        def repl_a(match):
            text, href = match.group(1), match.group(2)
            # 本地页面跳转
            for url, mdfile in url_to_md.items():
                if href == url or href.rstrip('/') == url.rstrip('/'):
                    return f'[{text}]({mdfile})'
            # 相对链接补全
            if not href.startswith(('http://', 'https://', '#')):
                href = urljoin(base_url, href)
            return f'[{text}]({href})'
        def repl_img(match):
            alt, src = match.group(1), match.group(2)
            # 下载本地图片
            if not src.startswith(('http://', 'https://')):
                src_full = urljoin(base_url, src)
            else:
                src_full = src
            try:
                # 只下载同域名图片
                base_domain = urlparse(base_url).netloc
                src_domain = urlparse(src_full).netloc
                if src_domain == '' or src_domain == base_domain:
                    img_ext = os.path.splitext(src_full)[-1]
                    img_name = re.sub(r'[^\w\-_\.]+', '_', os.path.basename(src_full))
                    if not img_ext:
                        img_ext = '.jpg'
                    img_file = img_name if img_name.endswith(img_ext) else img_name + img_ext
                    img_path = os.path.join(images_folder, img_file)
                    if not os.path.exists(img_path):
                        r = requests.get(src_full, timeout=10)
                        if r.status_code == 200:
                            with open(img_path, 'wb') as f:
                                f.write(r.content)
                            logger.info(f"已下载图片: {img_path}")
                        else:
                            logger.warning(f"图片下载失败: {src_full}")
                    rel_path = os.path.relpath(img_path, os.path.dirname(images_folder))
                    return f'![{alt}](images/{img_file})'
                else:
                    return f'![{alt}]({src_full})'
            except Exception as e:
                logger.warning(f"图片处理失败: {src_full}, {e}")
                return f'![{alt}]({src_full})'
        # 修正a标签
        md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_a, md)
        # 修正图片
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl_img, md)
        return md

    def fix_md_links_fullurl(self, md: str, url_to_anchor: dict, base_url: str, url_to_title: dict) -> str:
        """
        修正md中的a/img等链接为本地锚点或完整url，图片全部补全为完整url
        """
        from urllib.parse import urljoin
        def repl_a(match):
            text, href = match.group(1), match.group(2)
            # 如果是本地页面，跳转锚点
            for url, anchor in url_to_anchor.items():
                if href == url or href.rstrip('/') == url.rstrip('/'):
                    return f'[{text}](#{anchor})'
            # 相对链接补全
            if not href.startswith(('http://', 'https://', '#')):
                href = urljoin(base_url, href)
            return f'[{text}]({href})'
        def repl_img(match):
            alt, src = match.group(1), match.group(2)
            # 全部补全为完整url
            if not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
            return f'![{alt}]({src})'
        # 修正a标签
        md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl_a, md)
        # 修正图片
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', repl_img, md)
        return md


def main():
    """主函数示例"""
    # 示例配置
    base_url = "https://example.com/tutorial"
    config = {
        "type": "class",
        "value": "urlList"
    }
    
    # 创建下载器并执行
    downloader = MarkdownDownloader(base_url, config)
    downloader.run()


if __name__ == "__main__":
    main() 