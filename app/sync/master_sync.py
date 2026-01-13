import asyncio
import aiohttp
import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MasterSync:
    def __init__(self, data_directory: str):
        self.data_directory = data_directory
        self.synced_data: Dict[str, Dict] = {}
        self.slaves: List[str] = []
        
        # 确保数据目录存在
        if not os.path.exists(self.data_directory):
            os.makedirs(self.data_directory)
    
    async def handle_slave_sync(self, slave_id: str, data: Dict):
        """处理从应用的同步请求"""
        try:
            logger.info(f"接收来自从应用 {slave_id} 的同步数据")
            
            # 保存同步数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_file = os.path.join(self.data_directory, f"sync_{slave_id}_{timestamp}.json")
            
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的数据
            self.synced_data[slave_id] = {
                "last_sync": timestamp,
                "data": data,
                "file_path": data_file
            }
            
            # 记录从应用
            if slave_id not in self.slaves:
                self.slaves.append(slave_id)
            
            logger.info(f"成功保存从应用 {slave_id} 的同步数据")
            
            # 返回确认信息
            return {
                "status": "success",
                "message": "同步成功",
                "timestamp": timestamp,
                "received_data_size": len(json.dumps(data))
            }
        except Exception as e:
            logger.error(f"处理从应用 {slave_id} 的同步数据失败: {str(e)}")
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}"
            }
    
    def get_synced_slaves(self) -> List[str]:
        """获取已同步的从应用列表"""
        return self.slaves.copy()
    
    def get_slave_data(self, slave_id: str) -> Optional[Dict]:
        """获取特定从应用的同步数据"""
        return self.synced_data.get(slave_id)
    
    def get_all_synced_data(self) -> Dict[str, Dict]:
        """获取所有从应用的同步数据"""
        return self.synced_data.copy()
    
    def clean_old_data(self, days: int = 7):
        """清理指定天数前的旧数据"""
        try:
            import shutil
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime("%Y%m%d")
            
            logger.info(f"开始清理 {days} 天前的同步数据 (截止日期: {cutoff_str})")
            
            files_deleted = 0
            for filename in os.listdir(self.data_directory):
                if filename.startswith("sync_") and filename.endswith(".json"):
                    file_path = os.path.join(self.data_directory, filename)
                    file_date_str = filename.split("_")[2]  # 格式: sync_slaveid_timestamp.json
                    
                    if file_date_str < cutoff_str:
                        os.remove(file_path)
                        files_deleted += 1
                        
                        # 更新内存中的数据
                        for slave_id, data in self.synced_data.items():
                            if data["file_path"] == file_path:
                                del self.synced_data[slave_id]
                                break
            
            logger.info(f"清理完成，共删除 {files_deleted} 个文件")
            return files_deleted
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")
            return 0
    
    async def broadcast_to_slaves(self, message: Dict) -> Dict[str, Dict]:
        """向所有从应用广播消息"""
        results = {}
        
        for slave_id in self.slaves:
            # 这里需要实现与从应用的通信逻辑
            # 实际应用中可能需要维护从应用的IP和端口信息
            logger.info(f"向从应用 {slave_id} 广播消息")
            results[slave_id] = {"status": "pending", "message": "广播请求已发送"}
        
        return results
    
    def generate_sync_report(self) -> Dict:
        """生成同步报告"""
        report = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_slaves": len(self.slaves),
            "synced_data_count": len(self.synced_data),
            "data_directory": self.data_directory,
            "slave_details": []
        }
        
        for slave_id, data in self.synced_data.items():
            slave_report = {
                "slave_id": slave_id,
                "last_sync": data["last_sync"],
                "data_file": data["file_path"],
                "data_size": os.path.getsize(data["file_path"]) if os.path.exists(data["file_path"]) else 0
            }
            report["slave_details"].append(slave_report)
        
        return report

# 测试代码
async def main():
    master = MasterSync("./sync_data")
    
    # 模拟从应用同步
    test_slave_data = {
        "outlook_info": {
            "emails_count": 10,
            "unread_count": 3,
            "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "system_info": {
            "hostname": "slave-pc",
            "ip_address": "192.168.1.101",
            "os": "Windows 10"
        }
    }
    
    result = await master.handle_slave_sync("slave1", test_slave_data)
    print(f"同步结果: {result}")
    
    # 获取同步报告
    report = master.generate_sync_report()
    print(f"同步报告: {json.dumps(report, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())