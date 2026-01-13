import re
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmailParser:
    def __init__(self):
        # 预定义的工单字段正则表达式
        self.patterns = {
            "ticket_id": r"工单编号[:：]\s*(\w+)\s*",
            "customer_name": r"客户名称[:：]\s*(.+)\s*",
            "contact_info": r"联系方式[:：]\s*(.+)\s*",
            "problem_desc": r"问题描述[:：]\s*(.+?)(?=\n\S+:|$)",
            "priority": r"优先级[:：]\s*(.+?)\s*",
            "status": r"状态[:：]\s*(.+?)\s*",
            "assigned_to": r"指派给[:：]\s*(.+?)\s*",
            "created_time": r"创建时间[:：]\s*([\d-]+\s+[\d:]+)\s*"
        }
    
    def extract_ticket_info(self, email_body):
        """从邮件内容中提取工单信息"""
        ticket_info = {}
        
        for field, pattern in self.patterns.items():
            match = re.search(pattern, email_body, re.DOTALL | re.IGNORECASE)
            if match:
                ticket_info[field] = match.group(1).strip()
            else:
                ticket_info[field] = ""
        
        # 如果没有找到工单编号，生成一个临时的
        if not ticket_info["ticket_id"]:
            ticket_info["ticket_id"] = f"TEMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return ticket_info
    
    def parse_email(self, email_details, attachments=None):
        """解析完整的邮件信息"""
        ticket_info = self.extract_ticket_info(email_details["body"])
        
        parsed_data = {
            "email": email_details,
            "ticket": ticket_info,
            "attachments": attachments or [],
            "parsed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "has_images": any(self._is_image_file(file) for file in attachments or [])
        }
        
        return parsed_data
    
    def _is_image_file(self, file_path):
        """判断文件是否为图片"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]
        return os.path.splitext(file_path)[1].lower() in image_extensions
    
    def save_to_file(self, parsed_data, output_dir):
        """将解析后的数据保存到文件"""
        ticket_id = parsed_data["ticket"]["ticket_id"]
        
        # 创建工单目录
        ticket_dir = os.path.join(output_dir, ticket_id)
        if not os.path.exists(ticket_dir):
            os.makedirs(ticket_dir)
        
        # 保存邮件内容为JSON
        email_json_path = os.path.join(ticket_dir, "email_data.json")
        with open(email_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        
        # 保存邮件正文为文本文件
        email_body_path = os.path.join(ticket_dir, "email_body.txt")
        with open(email_body_path, "w", encoding="utf-8") as f:
            f.write(parsed_data["email"]["body"])
        
        # 如果有HTML内容，也保存
        if parsed_data["email"]["html_body"]:
            email_html_path = os.path.join(ticket_dir, "email_body.html")
            with open(email_html_path, "w", encoding="utf-8") as f:
                f.write(parsed_data["email"]["html_body"])
        
        # 移动附件到工单目录
        if parsed_data["attachments"]:
            attachments_dir = os.path.join(ticket_dir, "attachments")
            if not os.path.exists(attachments_dir):
                os.makedirs(attachments_dir)
            
            for attachment_path in parsed_data["attachments"]:
                try:
                    filename = os.path.basename(attachment_path)
                    new_path = os.path.join(attachments_dir, filename)
                    os.rename(attachment_path, new_path)
                    logger.info(f"移动附件: {attachment_path} → {new_path}")
                except Exception as e:
                    logger.error(f"移动附件失败 {attachment_path}: {str(e)}")
        
        logger.info(f"工单数据已保存到: {ticket_dir}")
        return ticket_dir
    
    def batch_parse_emails(self, emails, output_dir, subject_keyword="工单"):
        """批量解析邮件"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        parsed_results = []
        for email in emails:
            try:
                parsed_data = self.parse_email(email)
                saved_path = self.save_to_file(parsed_data, output_dir)
                parsed_results.append({
                    "ticket_id": parsed_data["ticket"]["ticket_id"],
                    "subject": parsed_data["email"]["subject"],
                    "saved_path": saved_path
                })
            except Exception as e:
                logger.error(f"解析邮件失败: {str(e)}")
                continue
        
        return parsed_results
    
    def extract_text_from_html(self, html_content):
        """从HTML内容中提取纯文本"""
        # 简单的HTML标签移除
        text = re.sub(r'<[^>]+>', '', html_content)
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def get_ticket_summary(self, parsed_data):
        """生成工单摘要"""
        ticket = parsed_data["ticket"]
        email = parsed_data["email"]
        
        summary = f"""
工单编号: {ticket['ticket_id']}
客户名称: {ticket['customer_name']}
问题描述: {ticket['problem_desc'][:100]}...
优先级: {ticket['priority']}
状态: {ticket['status']}
创建时间: {ticket['created_time']}
发件人: {email['sender_name']} ({email['sender']})
附件数量: {len(parsed_data['attachments'])}
包含图片: {parsed_data['has_images']}
        """
        
        return summary.strip()

if __name__ == "__main__":
    # 测试代码
    parser = EmailParser()
    
    # 模拟邮件内容
    sample_email = {
        "subject": "【工单】系统登录问题",
        "sender": "user@example.com",
        "sender_name": "张三",
        "received_time": "2023-10-01 14:30:00",
        "body": """
工单编号：TICKET-20231001-001
客户名称：张三
联系方式：13800138000
问题描述：无法登录系统，提示用户名或密码错误，尝试重置密码后仍然无法登录。
优先级：高
状态：待处理
指派给：技术支持
创建时间：2023-10-01 14:25:00
        """,
        "html_body": "",
        "attachments_count": 2
    }
    
    # 解析邮件
    parsed = parser.parse_email(sample_email, ["/tmp/image1.png", "/tmp/log.txt"])
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    
    # 保存到文件
    output_dir = "/tmp/tickets_test"
    saved_path = parser.save_to_file(parsed, output_dir)
    print(f"数据已保存到: {saved_path}")