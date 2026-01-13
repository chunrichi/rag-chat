import win32com.client
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OutlookReader:
    def __init__(self):
        self.outlook = None
        self.namespace = None
        self.inbox = None
    
    def connect(self):
        """连接到Outlook应用程序"""
        try:
            self.outlook = win32com.client.Dispatch("Outlook.Application")
            self.namespace = self.outlook.GetNamespace("MAPI")
            self.inbox = self.namespace.GetDefaultFolder(6)  # 6 表示收件箱
            logger.info("成功连接到Outlook")
            return True
        except Exception as e:
            logger.error(f"连接Outlook失败: {str(e)}")
            return False
    
    def get_emails_by_subject(self, subject_keyword, folder=None):
        """根据主题关键词过滤邮件"""
        if not self.outlook:
            if not self.connect():
                return []
        
        target_folder = folder if folder else self.inbox
        messages = target_folder.Items
        messages.Sort("ReceivedTime", True)  # 按接收时间降序排序
        
        filtered_emails = []
        for message in messages:
            try:
                if subject_keyword in message.Subject:
                    filtered_emails.append(message)
                    logger.info(f"找到邮件: {message.Subject}")
            except Exception as e:
                logger.error(f"处理邮件时出错: {str(e)}")
                continue
        
        return filtered_emails
    
    def get_email_details(self, message):
        """获取邮件详细信息"""
        email_details = {
            "subject": message.Subject,
            "sender": message.SenderEmailAddress if hasattr(message, 'SenderEmailAddress') else "",
            "sender_name": message.SenderName if hasattr(message, 'SenderName') else "",
            "received_time": message.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S"),
            "body": message.Body,
            "html_body": message.HTMLBody if hasattr(message, 'HTMLBody') else "",
            "attachments_count": message.Attachments.Count
        }
        return email_details
    
    def save_attachments(self, message, save_folder):
        """保存邮件附件"""
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        
        saved_files = []
        for attachment in message.Attachments:
            try:
                # 生成唯一的文件名，避免重名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_extension = os.path.splitext(attachment.FileName)[1]
                filename = f"{timestamp}_{attachment.FileName}"
                file_path = os.path.join(save_folder, filename)
                
                attachment.SaveAsFile(file_path)
                saved_files.append(file_path)
                logger.info(f"保存附件: {file_path}")
            except Exception as e:
                logger.error(f"保存附件失败 {attachment.FileName}: {str(e)}")
        
        return saved_files
    
    def get_all_folders(self):
        """获取所有邮箱文件夹"""
        if not self.outlook:
            if not self.connect():
                return []
        
        def list_folders(folder, level=0):
            folders = []
            folders.append(("  " * level + folder.Name, folder))
            for subfolder in folder.Folders:
                folders.extend(list_folders(subfolder, level + 1))
            return folders
        
        return list_folders(self.namespace.GetDefaultFolder(6))  # 从收件箱开始
    
    def get_folder_by_name(self, folder_path):
        """根据路径获取文件夹"""
        if not self.outlook:
            if not self.connect():
                return None
        
        folder = self.namespace.GetDefaultFolder(6)  # 收件箱
        try:
            for folder_name in folder_path.split("/"):
                if folder_name:
                    folder = folder.Folders(folder_name)
            return folder
        except Exception as e:
            logger.error(f"获取文件夹失败 {folder_path}: {str(e)}")
            return None
    
    def disconnect(self):
        """断开与Outlook的连接"""
        if self.outlook:
            try:
                self.outlook = None
                self.namespace = None
                self.inbox = None
                logger.info("已断开与Outlook的连接")
            except Exception as e:
                logger.error(f"断开连接失败: {str(e)}")

if __name__ == "__main__":
    # 测试代码
    reader = OutlookReader()
    if reader.connect():
        # 测试获取所有文件夹
        folders = reader.get_all_folders()
        for folder_name, folder in folders:
            print(folder_name)
        
        # 测试读取工单邮件
        emails = reader.get_emails_by_subject("工单")
        print(f"找到 {len(emails)} 封工单邮件")
        
        if emails:
            # 获取第一封邮件的详细信息
            email_details = reader.get_email_details(emails[0])
            print(f"邮件主题: {email_details['subject']}")
            print(f"发件人: {email_details['sender_name']}")
            print(f"接收时间: {email_details['received_time']}")
            print(f"附件数量: {email_details['attachments_count']}")
            
            # 保存附件
            if email_details['attachments_count'] > 0:
                save_folder = os.path.join(os.getcwd(), "attachments_test")
                saved_files = reader.save_attachments(emails[0], save_folder)
                print(f"已保存 {len(saved_files)} 个附件到 {save_folder}")
        
        reader.disconnect()
    else:
        print("无法连接到Outlook")