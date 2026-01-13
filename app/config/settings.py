import json
import os
import logging
from app.config.config import default_settings, get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "config.json")

def save_config(config_data):
    """保存配置到文件"""
    try:
        # 确保配置目录存在
        config_dir = os.path.dirname(CONFIG_FILE_PATH)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 保存配置
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"配置已保存到 {CONFIG_FILE_PATH}")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False

def load_config():
    """从文件加载配置"""
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            logger.info(f"配置已从 {CONFIG_FILE_PATH} 加载")
            return config_data
        else:
            logger.info(f"配置文件 {CONFIG_FILE_PATH} 不存在，使用默认配置")
            return default_settings.copy()
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return default_settings.copy()

def update_config(config_data):
    """更新配置"""
    # 加载现有配置
    current_config = load_config()
    
    # 更新配置
    current_config.update(config_data)
    
    # 保存配置
    return save_config(current_config)

def get_config_value(key, default=None):
    """获取单个配置值"""
    config = load_config()
    return config.get(key, default)

def set_config_value(key, value):
    """设置单个配置值"""
    config = load_config()
    config[key] = value
    return save_config(config)

def reset_config():
    """重置配置为默认值"""
    return save_config(default_settings.copy())

# 初始化配置目录
def init_config():
    """初始化配置系统"""
    # 确保输出目录存在
    config = load_config()
    output_dir = config.get("output_directory", default_settings["output_directory"])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"已创建输出目录: {output_dir}")
    
    # 确保日志目录存在
    if config.get("log_file"):
        log_dir = os.path.dirname(config["log_file"])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logger.info(f"已创建日志目录: {log_dir}")

# 合并默认配置和用户配置
def merge_config(user_config):
    """合并默认配置和用户配置"""
    merged = default_settings.copy()
    merged.update(user_config)
    return merged

if __name__ == "__main__":
    # 测试配置功能
    print("测试配置功能...")
    
    # 保存配置
    test_config = {
        "outlook_folder": "工单",
        "subject_keyword": "IT工单",
        "output_directory": "/tmp/test_tickets"
    }
    
    save_config(test_config)
    
    # 加载配置
    loaded_config = load_config()
    print(f"加载的配置: {loaded_config}")
    
    # 更新配置
    update_config({"sync_interval": 600})
    
    # 获取配置值
    interval = get_config_value("sync_interval")
    print(f"同步间隔: {interval}秒")
    
    # 重置配置
    reset_config()
    print("配置已重置为默认值")