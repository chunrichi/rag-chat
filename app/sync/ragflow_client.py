import requests
import logging
import os
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RagflowClient:
    def __init__(self, ragflow_url: str, api_key: str, dataset_id: Optional[int] = None):
        self.ragflow_url = ragflow_url.rstrip('/')
        self.api_key = api_key
        self.dataset_id = dataset_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def test_connection(self) -> bool:
        """测试与Ragflow的连接"""
        try:
            url = f"{self.ragflow_url}/api/v1/datasets"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"测试Ragflow连接失败: {str(e)}")
            return False
    
    def upload_file(self, file_path: str, dataset_id: Optional[int] = None) -> Dict:
        """上传文件到Ragflow"""
        try:
            dataset_id = dataset_id or self.dataset_id
            if not dataset_id:
                raise ValueError("需要提供数据集ID")
            
            url = f"{self.ragflow_url}/api/v1/datasets/{dataset_id}/documents/upload"
            
            # 使用multipart/form-data上传文件
            files = {
                'file': (os.path.basename(file_path), open(file_path, 'rb'))
            }
            
            # 不使用headers中的Content-Type，让requests自动处理
            upload_headers = {"Authorization": self.headers["Authorization"]}
            
            response = requests.post(url, headers=upload_headers, files=files, timeout=300)
            response.raise_for_status()
            
            logger.info(f"文件 {file_path} 上传到Ragflow成功")
            result = response.json()
            
            # 如果是图片文件，添加图片标记
            if self._is_image_file(file_path):
                result["is_image"] = True
                result["image_path"] = file_path
            
            return result
        except Exception as e:
            logger.error(f"上传文件 {file_path} 到Ragflow失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _is_image_file(self, file_path: str) -> bool:
        """判断文件是否为图片"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]
        return os.path.splitext(file_path)[1].lower() in image_extensions
    
    def upload_files(self, file_paths: List[str], dataset_id: Optional[int] = None) -> List[Dict]:
        """批量上传文件到Ragflow"""
        results = []
        for file_path in file_paths:
            if os.path.exists(file_path):
                result = self.upload_file(file_path, dataset_id)
                results.append({
                    "file_path": file_path,
                    "result": result
                })
            else:
                logger.warning(f"文件 {file_path} 不存在，跳过上传")
                results.append({
                    "file_path": file_path,
                    "result": {"status": "error", "message": "文件不存在"}
                })
        return results
    
    def query(self, question: str, dataset_id: Optional[int] = None, top_k: int = 3) -> Dict:
        """向Ragflow查询问题"""
        try:
            dataset_id = dataset_id or self.dataset_id
            if not dataset_id:
                raise ValueError("需要提供数据集ID")
            
            url = f"{self.ragflow_url}/api/v1/datasets/{dataset_id}/chat/completions"
            data = {
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "top_k": top_k,
                "stream": False
            }
            
            response = requests.post(url, headers=self.headers, json=data, timeout=60)
            response.raise_for_status()
            
            logger.info(f"向Ragflow查询成功: {question}")
            return response.json()
        except Exception as e:
            logger.error(f"向Ragflow查询失败: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def get_datasets(self) -> List[Dict]:
        """获取所有数据集"""
        try:
            url = f"{self.ragflow_url}/api/v1/datasets"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取Ragflow数据集失败: {str(e)}")
            return []
    
    def get_dataset_info(self, dataset_id: Optional[int] = None) -> Optional[Dict]:
        """获取特定数据集的信息"""
        try:
            dataset_id = dataset_id or self.dataset_id
            if not dataset_id:
                raise ValueError("需要提供数据集ID")
            
            url = f"{self.ragflow_url}/api/v1/datasets/{dataset_id}"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取数据集信息失败: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            url = f"{self.ragflow_url}/api/v1/documents/{document_id}"
            response = requests.delete(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            logger.info(f"删除文档 {document_id} 成功")
            return True
        except Exception as e:
            logger.error(f"删除文档 {document_id} 失败: {str(e)}")
            return False

# 测试代码
if __name__ == "__main__":
    # 示例用法
    client = RagflowClient(
        ragflow_url="http://localhost:9380",
        api_key="your_api_key_here",
        dataset_id=1
    )
    
    # 测试连接
    # print(f"连接测试: {client.test_connection()}")
    
    # 上传文件
    # result = client.upload_file("test.txt")
    # print(f"上传结果: {result}")
    
    # 查询
    # result = client.query("测试问题")
    # print(f"查询结果: {result}")