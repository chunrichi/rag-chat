from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
import os
import logging
import asyncio
from datetime import datetime

# 添加配置管理模块导入
from app.config.settings import load_config, update_config, reset_config, init_config, get_config_value

# 添加同步模块导入
from app.sync.master_sync import MasterSync
from app.sync.slave_sync import SlaveSync
from app.sync.ragflow_client import RagflowClient

# 添加Outlook模块导入
from app.outlook.outlook_reader import OutlookReader

# 初始化同步管理器
sync_data_dir = os.path.join(os.path.expanduser("~"), "outlook_tickets", "sync_data")
master_sync = MasterSync(sync_data_dir)
slave_sync = None

# 从配置获取应用模式
config = load_config()
app_mode = config.get("app_mode", "standalone")

# 如果是从应用模式，初始化从应用同步器
if app_mode == "slave":
    slave_sync = SlaveSync()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Outlook工单管理系统",
    description="用于读取Outlook工单邮件并管理的Web应用",
    version="1.0.0"
)

# 配置模板和静态文件
templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# 全局变量
app_state = {
    "last_sync_time": None,
    "total_tickets_processed": 0,
    "is_running": False,
    "current_mode": "standalone"  # standalone, master, slave
}

# 首页路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "app_state": app_state}
    )

# 配置页面路由 - 更新为从配置文件加载
@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request):
    config_data = load_config()
    return templates.TemplateResponse(
        "config.html", 
        {"request": request, "config": config_data}
    )

# 状态页面路由
@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    return templates.TemplateResponse(
        "status.html", 
        {"request": request, "app_state": app_state}
    )

# Ragflow查询页面路由
@app.get("/ragflow", response_class=HTMLResponse)
async def ragflow_page(request: Request):
    return templates.TemplateResponse(
        "ragflow.html", 
        {"request": request}
    )

# API: 获取应用状态
@app.get("/api/status")
async def get_status():
    return JSONResponse(content=app_state)

# API: 更新应用状态
@app.post("/api/status")
async def update_status(request: Request):
    data = await request.json()
    app_state.update(data)
    return JSONResponse(content={"message": "状态更新成功"})

# API: 测试Outlook连接
@app.get("/api/test-outlook")
async def test_outlook():
    try:
        reader = OutlookReader()
        success = reader.connect()
        if success:
            reader.disconnect()
            return JSONResponse(content={"success": True, "message": "Outlook连接测试成功"})
        else:
            return JSONResponse(content={"success": False, "message": "Outlook连接测试失败"})
    except Exception as e:
        logger.error(f"Outlook测试失败: {str(e)}")
        return JSONResponse(content={"success": False, "message": f"测试失败: {str(e)}"})

# API: 手动触发邮件处理
@app.post("/api/process-emails")
async def process_emails(request: Request):
    try:
        # 这里会在实现邮件处理功能后更新
        return JSONResponse(content={"success": True, "message": "邮件处理功能待实现"})
    except Exception as e:
        logger.error(f"处理邮件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理邮件失败: {str(e)}")

# 新增: API: 获取配置
@app.get("/api/config")
async def get_config():
    config_data = load_config()
    return JSONResponse(content=config_data)

# 新增: API: 更新配置
@app.post("/api/config")
async def update_config_api(request: Request):
    try:
        data = await request.json()
        success = update_config(data)
        if success:
            # 更新应用状态中的模式
            if "app_mode" in data:
                app_state["current_mode"] = data["app_mode"]
            return JSONResponse(content={"success": True, "message": "配置保存成功"})
        else:
            return JSONResponse(content={"success": False, "message": "配置保存失败"})
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        return JSONResponse(content={"success": False, "message": f"配置保存失败: {str(e)}"})

# 新增: API: 重置配置
@app.post("/api/config/reset")
async def reset_config_api():
    success = reset_config()
    if success:
        app_state["current_mode"] = "standalone"  # 重置为默认模式
        return JSONResponse(content={"success": True, "message": "配置已重置为默认值"})
    else:
        return JSONResponse(content={"success": False, "message": "配置重置失败"})

# 同步相关API端点

# API: 主应用接收从应用同步数据 (仅主应用模式)
@app.post("/api/sync")
async def receive_sync_data(request: Request):
    global app_state
    
    if app_mode != "master":
        return JSONResponse(content={"status": "error", "message": "当前不是主应用模式"})
    
    try:
        data = await request.json()
        slave_id = data.get("slave_id", "unknown")
        
        # 处理同步数据
        result = await master_sync.handle_slave_sync(slave_id, data)
        
        # 更新应用状态
        app_state["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"处理同步数据失败: {str(e)}")
        return JSONResponse(content={"status": "error", "message": f"处理失败: {str(e)}"})

# API: 获取同步状态
@app.get("/api/sync/status")
async def get_sync_status():
    if app_mode == "master":
        return JSONResponse(content={
            "mode": "master",
            "slaves": master_sync.get_synced_slaves(),
            "report": master_sync.generate_sync_report()
        })
    elif app_mode == "slave" and slave_sync:
        return JSONResponse(content={
            "mode": "slave",
            "status": slave_sync.get_sync_status()
        })
    else:
        return JSONResponse(content={"mode": "standalone", "message": "当前处于独立模式，不支持同步功能"})

# API: 手动触发从应用同步 (仅从应用模式)
@app.post("/api/sync/manual")
async def manual_sync():
    if app_mode != "slave" or not slave_sync:
        return JSONResponse(content={"status": "error", "message": "当前不是从应用模式"})
    
    result = await slave_sync.sync_to_master()
    return JSONResponse(content=result)

# API: 开始从应用同步循环 (仅从应用模式)
@app.post("/api/sync/start")
async def start_sync():
    if app_mode != "slave" or not slave_sync:
        return JSONResponse(content={"status": "error", "message": "当前不是从应用模式"})
    
    if slave_sync.is_running:
        return JSONResponse(content={"status": "error", "message": "同步循环已在运行中"})
    
    # 启动同步循环
    asyncio.create_task(slave_sync.start_sync_loop())
    
    return JSONResponse(content={"status": "success", "message": "同步循环已启动"})

# API: 停止从应用同步循环 (仅从应用模式)
@app.post("/api/sync/stop")
async def stop_sync():
    if app_mode != "slave" or not slave_sync:
        return JSONResponse(content={"status": "error", "message": "当前不是从应用模式"})
    
    if not slave_sync.is_running:
        return JSONResponse(content={"status": "error", "message": "同步循环未在运行中"})
    
    slave_sync.stop_sync_loop()
    return JSONResponse(content={"status": "success", "message": "同步循环已停止"})

# API: 获取同步报告 (仅主应用模式)
@app.get("/api/sync/report")
async def get_sync_report():
    if app_mode != "master":
        return JSONResponse(content={"status": "error", "message": "当前不是主应用模式"})
    
    report = master_sync.generate_sync_report()
    return JSONResponse(content=report)

# Ragflow相关API端点

# API: 测试Ragflow连接
@app.get("/api/ragflow/test")
async def test_ragflow():
    config = load_config()
    ragflow_url = config.get("ragflow_url", "")
    ragflow_api_key = config.get("ragflow_api_key", "")
    
    if not ragflow_url or not ragflow_api_key:
        return JSONResponse(content={"success": False, "message": "Ragflow URL或API Key未配置"})
    
    client = RagflowClient(ragflow_url, ragflow_api_key)
    success = client.test_connection()
    
    if success:
        return JSONResponse(content={"success": True, "message": "Ragflow连接测试成功"})
    else:
        return JSONResponse(content={"success": False, "message": "Ragflow连接测试失败"})

# API: 上传文件到Ragflow
@app.post("/api/ragflow/upload")
async def upload_to_ragflow(request: Request):
    try:
        data = await request.json()
        file_paths = data.get("file_paths", [])
        
        if not file_paths:
            return JSONResponse(content={"success": False, "message": "没有提供要上传的文件路径"})
        
        config = load_config()
        ragflow_url = config.get("ragflow_url", "")
        ragflow_api_key = config.get("ragflow_api_key", "")
        ragflow_dataset_id = config.get("ragflow_dataset_id")
        
        if not ragflow_url or not ragflow_api_key:
            return JSONResponse(content={"success": False, "message": "Ragflow URL或API Key未配置"})
        
        if not ragflow_dataset_id:
            return JSONResponse(content={"success": False, "message": "Ragflow数据集ID未配置"})
        
        client = RagflowClient(ragflow_url, ragflow_api_key, ragflow_dataset_id)
        results = client.upload_files(file_paths)
        
        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {len([r for r in results if r['result'].get('status', '') != 'error'])} 个文件",
            "results": results
        })
    except Exception as e:
        logger.error(f"上传文件到Ragflow失败: {str(e)}")
        return JSONResponse(content={"success": False, "message": f"上传失败: {str(e)}"})

# API: 向Ragflow查询
@app.post("/api/ragflow/query")
async def query_ragflow(request: Request):
    try:
        data = await request.json()
        question = data.get("question", "")
        top_k = data.get("top_k", 3)
        
        if not question:
            return JSONResponse(content={"success": False, "message": "没有提供查询问题"})
        
        config = load_config()
        ragflow_url = config.get("ragflow_url", "")
        ragflow_api_key = config.get("ragflow_api_key", "")
        ragflow_dataset_id = config.get("ragflow_dataset_id")
        
        if not ragflow_url or not ragflow_api_key:
            return JSONResponse(content={"success": False, "message": "Ragflow URL或API Key未配置"})
        
        if not ragflow_dataset_id:
            return JSONResponse(content={"success": False, "message": "Ragflow数据集ID未配置"})
        
        client = RagflowClient(ragflow_url, ragflow_api_key, ragflow_dataset_id)
        result = client.query(question, top_k=top_k)
        
        return JSONResponse(content={"success": True, "result": result})
    except Exception as e:
        logger.error(f"向Ragflow查询失败: {str(e)}")
        return JSONResponse(content={"success": False, "message": f"查询失败: {str(e)}"})

# API: 获取Ragflow数据集列表
@app.get("/api/ragflow/datasets")
async def get_ragflow_datasets():
    config = load_config()
    ragflow_url = config.get("ragflow_url", "")
    ragflow_api_key = config.get("ragflow_api_key", "")
    
    if not ragflow_url or not ragflow_api_key:
        return JSONResponse(content={"success": False, "message": "Ragflow URL或API Key未配置"})
    
    client = RagflowClient(ragflow_url, ragflow_api_key)
    datasets = client.get_datasets()
    
    return JSONResponse(content={"success": True, "datasets": datasets})

# API: 获取图片文件
@app.get("/api/images/{file_path:path}")
async def get_image(file_path: str):
    # 获取配置中的输出目录
    config = load_config()
    output_dir = config.get("output_directory", os.path.join(os.path.expanduser("~"), "outlook_tickets"))
    
    # 构建完整的图片路径
    image_path = os.path.join(output_dir, file_path)
    
    if os.path.exists(image_path) and os.path.isfile(image_path):
        return FileResponse(image_path)
    else:
        raise HTTPException(status_code=404, detail="图片文件未找到")

# 运行应用
if __name__ == "__main__":
    import uvicorn
    
    # 初始化配置
    init_config()
    
    # 从配置加载Web服务器设置
    host = get_config_value("web_host", "0.0.0.0")
    port = get_config_value("web_port", 8000)
    
    # 如果是从应用模式，自动启动同步循环
    if app_mode == "slave" and slave_sync:
        asyncio.create_task(slave_sync.start_sync_loop())
    
    uvicorn.run(
        "app.web.main:app",
        host=host,
        port=port,
        reload=True
    )