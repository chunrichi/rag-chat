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
        """连接到Outlook应用程序，添加容错处理"""
        try:
            # 先尝试获取正在运行的Outlook实例
            try:
                self.outlook = win32com.client.GetActiveObject("Outlook.Application")
                logger.info("成功连接到已运行的Outlook实例")
            except Exception:
                # 如果Outlook未运行，尝试启动它
                logger.info("Outlook未运行，尝试启动...")
                self.outlook = win32com.client.Dispatch("Outlook.Application")
                logger.info("成功启动并连接到Outlook")
            
            self.namespace = self.outlook.GetNamespace("MAPI")
            self.inbox = self.namespace.GetDefaultFolder(6)  # 6 表示收件箱
            logger.info("成功连接到Outlook收件箱")
            return True
        except Exception as e:
            logger.warning(f"无法连接到Outlook: {str(e)}")
            logger.info("Outlook未启动或不可用，程序将继续运行")
            return False
    
    def get_emails_by_subject(self, subject_keyword, folder=None):
        """根据主题关键词过滤邮件，添加容错处理"""
        if not self.outlook:
            if not self.connect():
                logger.info("Outlook不可用，返回空邮件列表")
                return []
        
        try:
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
                    logger.warning(f"处理邮件时出错: {str(e)}")
                    continue
            
            return filtered_emails
        except Exception as e:
            logger.warning(f"获取邮件列表失败: {str(e)}")
            return []
    
    def get_email_details(self, message):
        """获取邮件详细信息，添加容错处理"""
        try:
            email_details = {
                "subject": message.Subject if hasattr(message, 'Subject') else "",
                "sender": message.SenderEmailAddress if hasattr(message, 'SenderEmailAddress') else "",
                "sender_name": message.SenderName if hasattr(message, 'SenderName') else "",
                "received_time": message.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S") if hasattr(message, 'ReceivedTime') else "",
                "body": message.Body if hasattr(message, 'Body') else "",
                "html_body": message.HTMLBody if hasattr(message, 'HTMLBody') else "",
                "attachments_count": message.Attachments.Count if hasattr(message, 'Attachments') else 0
            }
            return email_details
        except Exception as e:
            logger.warning(f"获取邮件详细信息失败: {str(e)}")
            return {
                "subject": "",
                "sender": "",
                "sender_name": "",
                "received_time": "",
                "body": "",
                "html_body": "",
                "attachments_count": 0
            }
    
    def save_attachments(self, message, save_folder):
        """保存邮件附件，添加容错处理"""
        try:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
            
            saved_files = []
            if not hasattr(message, 'Attachments'):
                logger.info("邮件没有附件")
                return saved_files
            
            for attachment in message.Attachments:
                try:
                    if not hasattr(attachment, 'FileName'):
                        logger.warning("找到无效附件")
                        continue
                    
                    # 生成唯一的文件名，避免重名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_extension = os.path.splitext(attachment.FileName)[1]
                    filename = f"{timestamp}_{attachment.FileName}"
                    file_path = os.path.join(save_folder, filename)
                    
                    attachment.SaveAsFile(file_path)
                    saved_files.append(file_path)
                    logger.info(f"保存附件: {file_path}")
                except Exception as e:
                    logger.warning(f"保存附件失败 {getattr(attachment, 'FileName', '未知文件')}: {str(e)}")
                    continue
            
            return saved_files
        except Exception as e:
            logger.warning(f"处理附件时出错: {str(e)}")
            return []
    
    def get_all_folders(self):
        """获取所有邮箱文件夹，添加容错处理"""
        if not self.outlook:
            if not self.connect():
                logger.info("Outlook不可用，返回空文件夹列表")
                return []
        
        try:
            def list_folders(folder, level=0):
                folders = []
                folders.append(("  " * level + folder.Name, folder))
                for subfolder in folder.Folders:
                    folders.extend(list_folders(subfolder, level + 1))
                return folders
            
            return list_folders(self.namespace.GetDefaultFolder(6))  # 从收件箱开始
        except Exception as e:
            logger.warning(f"获取文件夹列表失败: {str(e)}")
            return []
    
    def get_folder_by_name(self, folder_path):
        """根据路径获取文件夹，添加容错处理"""
        if not self.outlook:
            if not self.connect():
                logger.info("Outlook不可用，无法获取文件夹")
                return None
        
        try:
            folder = self.namespace.GetDefaultFolder(6)  # 收件箱
            for folder_name in folder_path.split("/"):
                if folder_name:
                    folder = folder.Folders(folder_name)
            return folder
        except Exception as e:
            logger.warning(f"获取文件夹失败 {folder_path}: {str(e)}")
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