import asyncio
import aiohttp
import logging
import json
import os
import socket
from datetime import datetime
from typing import Dict, Optional
from app.outlook.outlook_reader import OutlookReader
from app.config.settings import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SlaveSync:
    def __init__(self):
        self.config = load_config()
        self.master_url = f"http://{self.config['master_ip']}:{self.config['master_port']}"
        self.slave_id = self._get_slave_id()
        self.is_running = False
        self.last_sync_time = None
        self.last_sync_result = None
    
    def _get_slave_id(self) -> str:
        """生成从应用的唯一ID"""
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return f"{hostname}_{ip_address}"
    
    async def collect_outlook_info(self) -> Dict:
        """收集本地Outlook信息"""
        try:
            logger.info("开始收集Outlook信息")
            
            reader = OutlookReader()
            if not reader.connect():
                return {
                    "status": "error",
                    "message": "无法连接到Outlook"
                }
            
            # 获取邮件信息
            emails = reader.get_emails_by_subject(self.config.get("subject_keyword", "工单"))
            
            # 收集关键信息
            outlook_info = {
                "total_emails": len(emails),
                "last_collected": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "subject_keyword": self.config.get("subject_keyword", "工单"),
                "outlook_folder": self.config.get("outlook_folder", "收件箱"),
                "recent_emails": []
            }
            
            # 获取最近的5封邮件信息
            for i, email in enumerate(emails[:5]):
                try:
                    email_details = reader.get_email_details(email)
                    outlook_info["recent_emails"].append({
                        "subject": email_details["subject"],
                        "sender": email_details["sender_name"],
                        "received_time": email_details["received_time"],
                        "attachments_count": email_details["attachments_count"]
                    })
                except Exception as e:
                    logger.error(f"获取邮件 {i+1} 信息失败: {str(e)}")
                    continue
            
            reader.disconnect()
            logger.info(f"成功收集Outlook信息，共找到 {len(emails)} 封邮件")
            
            return outlook_info
        except Exception as e:
            logger.error(f"收集Outlook信息失败: {str(e)}")
            return {
                "status": "error",
                "message": f"收集失败: {str(e)}"
            }
    
    async def collect_system_info(self) -> Dict:
        """收集系统信息"""
        import platform
        
        system_info = {
            "hostname": socket.gethostname(),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "collect_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return system_info
    
    async def sync_to_master(self):
        """同步数据到主应用"""
        try:
            logger.info(f"开始向主应用 {self.master_url} 同步数据")
            
            # 收集数据
            outlook_info = await self.collect_outlook_info()
            system_info = await self.collect_system_info()
            
            # 构建同步数据
            sync_data = {
                "slave_id": self.slave_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "outlook_info": outlook_info,
                "system_info": system_info,
                "config": self.config
            }
            
            # 发送到主应用
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.master_url}/api/sync",
                    json=sync_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    result = await response.json()
                    logger.info(f"同步结果: {result}")
                    
                    # 更新状态
                    self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.last_sync_result = result
                    
                    return result
        except Exception as e:
            logger.error(f"同步到主应用失败: {str(e)}")
            self.last_sync_result = {
                "status": "error",
                "message": f"同步失败: {str(e)}"
            }
            return self.last_sync_result
    
    async def start_sync_loop(self):
        """开始同步循环"""
        self.is_running = True
        logger.info(f"开始同步循环，间隔 {self.config['sync_interval']} 秒")
        
        while self.is_running:
            await self.sync_to_master()
            
            # 等待下一次同步
            for _ in range(self.config['sync_interval']):
                if not self.is_running:
                    break
                await asyncio.sleep(1)
    
    def stop_sync_loop(self):
        """停止同步循环"""
        self.is_running = False
        logger.info("同步循环已停止")
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            "is_running": self.is_running,
            "last_sync_time": self.last_sync_time,
            "last_sync_result": self.last_sync_result,
            "slave_id": self.slave_id,
            "master_url": self.master_url,
            "sync_interval": self.config.get("sync_interval", 300)
        }

# 测试代码
async def main():
    slave = SlaveSync()
    
    # 测试收集Outlook信息
    outlook_info = await slave.collect_outlook_info()
    print(f"Outlook信息: {json.dumps(outlook_info, ensure_ascii=False, indent=2)}")
    
    # 测试收集系统信息
    system_info = await slave.collect_system_info()
    print(f"系统信息: {json.dumps(system_info, ensure_ascii=False, indent=2)}")
    
    # 测试同步（需要主应用运行）
    # result = await slave.sync_to_master()
    # print(f"同步结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())