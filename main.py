from fastapi import FastAPI, HTTPException, Response, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any
from markdown_downloader import MarkdownDownloader
import os
import urllib.parse

app = FastAPI(title="在线Markdown教程下载API")
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

class DownloadRequest(BaseModel):
    url: str
    config: Dict[str, Any]
    filename: Optional[str] = None
    pre_remove_type: Optional[str] = None
    pre_remove_value: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/form_download/")
def form_download(
    request: Request,
    url: str = Form(...),
    type_: str = Form(...),
    value: str = Form(...),
    filename: str = Form(...),
    pre_remove_type: str = Form(None),
    pre_remove_value: str = Form(None),
):
    config = {"type": type_, "value": value}
    kwargs = {}
    if pre_remove_type:
        kwargs["pre_remove_type"] = pre_remove_type
    if pre_remove_value:
        kwargs["pre_remove_value"] = pre_remove_value
    try:
        downloader = MarkdownDownloader(url, config, **kwargs)
        downloader.run(filename)
        domain = downloader.get_domain_folder()
        file_path = os.path.join(domain, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail="Markdown文件未生成")
        def iterfile():
            with open(file_path, 'rb') as f:
                yield from f
        quoted_filename = urllib.parse.quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{quoted_filename}"
        }
        return StreamingResponse(iterfile(), media_type='text/markdown', headers=headers)
    except Exception as e:
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

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
