# 项目架构设计

## 1. 项目概述
本项目是一个用于读取Outlook工单邮件、处理附件并构建向量数据库数据源的Python应用程序，同时提供Web界面进行配置管理和主从同步功能。

## 2. 目录结构
```
/Users/lei/Desktop/bmw/bot/
├── app/
│   ├── outlook/      # Outlook邮件读取模块
│   ├── parser/       # 邮件内容解析模块
│   ├── image/        # 图片处理模块
│   ├── web/          # FastAPI Web应用
│   ├── config/       # 配置管理模块
│   ├── sync/         # 主从同步模块
│   ├── templates/    # Jinja2模板
│   └── static/       # 静态文件
├── requirements.txt  # 项目依赖
├── .env              # 环境配置
├── main.py           # 主程序入口
└── ARCHITECTURE.md   # 架构文档
```

## 3. 核心模块设计

### 3.1 Outlook邮件读取模块 (app/outlook/)
- `outlook_reader.py`: 使用pywin32读取Outlook邮件和附件
- 功能：连接Outlook，过滤工单邮件，获取邮件内容和附件

### 3.2 邮件内容解析模块 (app/parser/)
- `email_parser.py`: 解析邮件内容，提取工单信息
- 功能：解析邮件正文，识别工单编号、标题、描述等信息

### 3.3 图片处理模块 (app/image/)
- `image_processor.py`: 处理邮件中的图片附件
- 功能：图片压缩、格式转换、特征提取（为向量数据库准备）

### 3.4 Web应用模块 (app/web/)
- `main.py`: FastAPI应用入口
- `routes.py`: API路由定义
- `templates/`: Jinja2模板文件
- 功能：提供配置管理界面，展示系统状态

### 3.5 配置管理模块 (app/config/)
- `config.py`: 配置类定义
- `settings.py`: 配置文件读写
- 功能：管理应用程序配置参数

### 3.6 主从同步模块 (app/sync/)
- `master_sync.py`: 主应用同步逻辑
- `slave_sync.py`: 从应用同步逻辑
- 功能：实现两台电脑之间的Outlook信息同步

## 4. 数据流设计
1. 从Outlook读取邮件 → 2. 解析邮件内容 → 3. 提取附件和图片 → 4. 处理图片 → 5. 写入文件系统 → 6. 向量数据库生成

## 5. 主从同步机制
- 主应用：接收从应用的同步请求，管理全局数据
- 从应用：定期收集本地Outlook信息，发送到主应用
- 同步协议：基于HTTP的RESTful API

## 6. 技术栈
- Python 3.10+
- FastAPI (Web框架)
- Jinja2 (模板引擎)
- pywin32 (Outlook操作)
- Pillow (图片处理)
- Transformers (可选，图片特征提取)
- Pydantic (数据验证)
