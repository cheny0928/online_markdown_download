from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
from markdown_downloader import MarkdownDownloader
import os
import urllib.parse

app = FastAPI(title="在线Markdown教程下载API")

class DownloadRequest(BaseModel):
    url: str
    config: Dict[str, Any]
    filename: Optional[str] = None
    pre_remove_type: Optional[str] = None
    pre_remove_value: Optional[str] = None

@app.post("/download/")
def download_markdown(req: DownloadRequest):
    output_filename = req.filename or "tutorial.md"
    pre_remove_type = req.pre_remove_type or req.config.get('pre_remove_type')
    pre_remove_value = req.pre_remove_value or req.config.get('pre_remove_value')
    try:
        downloader = MarkdownDownloader(req.url, req.config, pre_remove_type=pre_remove_type, pre_remove_value=pre_remove_value)
        downloader.run(output_filename)
        domain = downloader.get_domain_folder()
        file_path = os.path.join(domain, output_filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Markdown文件未生成")
        with open(file_path, 'rb') as f:
            content = f.read()
        quoted_filename = urllib.parse.quote(output_filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"
        }
        return Response(content, media_type='text/markdown', headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
