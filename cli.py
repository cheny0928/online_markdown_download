#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行接口
提供简单的命令行操作界面
"""

import argparse
import json
import sys
from markdown_downloader import MarkdownDownloader


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='在线教程手册下载器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cli.py https://example.com/tutorial --type class --value urlList
  python cli.py https://example.com/tutorial --config config.json
  python cli.py https://example.com/tutorial --type id --value main-content --filename my_tutorial.md
  # 配置文件中可选 filename 字段，优先作为输出文件名
  # 若未指定 filename，则使用 --filename 参数或默认 tutorial.md
        """
    )
    
    parser.add_argument('url', help='教程主页URL')
    parser.add_argument('--type', choices=['class', 'id', 'tag'], default='class',
                       help='元素类型 (默认: class)')
    parser.add_argument('--value', help='元素值')
    parser.add_argument('--config', help='配置文件路径 (JSON格式)')
    parser.add_argument('--filename', default='tutorial.md', help='输出文件名 (默认: tutorial.md)，如配置文件有filename则优先')
    parser.add_argument('--delay', type=float, default=1.0, help='请求间隔时间(秒) (默认: 1.0)')
    parser.add_argument('--pre-remove-type', choices=['class', 'id', 'tag'], help='预处理要删除的元素类型')
    parser.add_argument('--pre-remove-value', help='预处理要删除的元素值')
    
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        sys.exit(1)


def validate_config(config: dict) -> bool:
    """验证配置是否有效"""
    required_fields = ['type', 'value']
    for field in required_fields:
        if field not in config:
            print(f"配置缺少必需字段: {field}")
            return False
    
    if config['type'] not in ['class', 'id', 'tag']:
        print(f"不支持的元素类型: {config['type']}")
        return False
    
    return True


def main():
    """主函数"""
    args = parse_arguments()
    
    # 确定配置和输出文件名，优先级：配置文件filename > 命令行--filename > 默认值
    output_filename = args.filename  # 先用命令行或默认
    pre_remove_type = None
    pre_remove_value = None
    if args.config:
        config = load_config(args.config)
        if not validate_config(config):
            sys.exit(1)
        if 'filename' in config and config['filename']:
            output_filename = config['filename']
        pre_remove_type = config.get('pre_remove_type')
        pre_remove_value = config.get('pre_remove_value')
    else:
        if not args.value:
            print("错误: 必须指定 --value 参数或使用 --config 配置文件")
            sys.exit(1)
        config = {
            'type': args.type,
            'value': args.value
        }
        if args.pre_remove_type and args.pre_remove_value:
            pre_remove_type = args.pre_remove_type
            pre_remove_value = args.pre_remove_value
    # 传递给downloader
    print(f"预处理删除元素: type={pre_remove_type}, value={pre_remove_value}")
    
    print(f"开始下载教程...")
    print(f"URL: {args.url}")
    print(f"配置: {config}")
    print(f"输出文件: {output_filename}")
    print("-" * 50)
    
    try:
        # 创建下载器并执行
        downloader = MarkdownDownloader(args.url, config, pre_remove_type=pre_remove_type, pre_remove_value=pre_remove_value)
        downloader.run(output_filename)
        print(f"\n下载完成! 文件已保存为: {output_filename}")
        
    except KeyboardInterrupt:
        print("\n用户中断下载")
        sys.exit(1)
    except Exception as e:
        print(f"下载过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 