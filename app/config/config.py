from pydantic_settings import BaseSettings
import os
from typing import Optional

class Settings(BaseSettings):
    # Outlook配置
    outlook_folder: str = "收件箱"
    subject_keyword: str = "工单"
    
    # 存储配置
    output_directory: str = os.path.join(os.path.expanduser("~"), "outlook_tickets")
    
    # 同步配置
    master_ip: str = "127.0.0.1"
    master_port: int = 8000
    sync_interval: int = 300  # 秒
    
    # 应用模式配置
    app_mode: str = "standalone"  # standalone, master, slave
    
    # 图片处理配置
    image_quality: int = 85
    max_image_size: int = 1024
    
    # Web服务器配置
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    
    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Ragflow配置
    ragflow_url: str = "http://localhost:9380"
    ragflow_api_key: str = ""
    ragflow_dataset_id: Optional[int] = None
    ragflow_upload_timeout: int = 300
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# 创建全局配置实例
def get_settings() -> Settings:
    return Settings()

# 默认配置
default_settings = {
    "outlook_folder": "收件箱",
    "subject_keyword": "工单",
    "output_directory": os.path.join(os.path.expanduser("~"), "outlook_tickets"),
    "master_ip": "127.0.0.1",
    "master_port": 8000,
    "sync_interval": 300,
    "app_mode": "standalone",
    "image_quality": 85,
    "max_image_size": 1024,
    "web_host": "0.0.0.0",
    "web_port": 8000,
    "log_level": "INFO",
    "log_file": None,
    "ragflow_url": "http://localhost:9380",
    "ragflow_api_key": "",
    "ragflow_dataset_id": None,
    "ragflow_upload_timeout": 300
}