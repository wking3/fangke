# 访客管理系统 (Visitor Management System)

## 系统概述

本系统是一个基于Web的访客管理系统，允许访客通过扫描二维码进行登记，并通过WeChat或DingTalk通知被拜访人确认，最后通知安保人员放行。

## 系统功能

1. 访客可以通过扫描二维码进入登记页面
2. 登记信息包括：访客姓名、电话号码、单位、被拜访人姓名、单位和电话
3. 系统自动发送通知给被拜访人确认
4. 被拜访人确认后，通知安保app放行访客

## 系统架构

- **访客登记后端** (`main.py`): 处理访客登记、数据存储和通知发送（统一应用）
- **访客登记页面**: Web页面供访客填写信息
- **安保app**: 供安保人员查看访客状态
- **主机确认界面**: 供被拜访人确认访客请求

## 本地安装和部署

### 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 环境变量配置

创建 `.env` 文件配置以下变量：

```bash
# 通知服务设置
NOTIFICATION_SERVICE=webhook        # or 'wechat' or 'dingtalk'
WECHAT_WEBHOOK=https://your-wechat-webhook
DINGTALK_WEBHOOK=https://your-dingtalk-webhook
HOST_NOTIFICATION_WEBHOOK=https://your-generic-webhook

# 安全通知设置
SECURITY_NOTIFICATION_SERVICE=app   # or 'wechat', 'dingtalk', 'webhook'
SECURITY_APP_URL=https://your-security-app-url.com
SECURITY_WECHAT_WEBHOOK=https://your-security-wechat-webhook
SECURITY_DINGTALK_WEBHOOK=https://your-security-dingtalk-webhook
SECURITY_NOTIFICATION_WEBHOOK=https://your-security-generic-webhook
```

### 启动服务

**本地开发模式**:
```bash
python main.py
```
访问 `http://localhost:5000` 进行访客登记，`http://localhost:5000/qr` 查看二维码

**统一应用端点**:
- `GET /` - 访客登记页面
- `GET /qr` - 生成访客登记二维码
- `GET /security` - 安保管理界面
- `GET /host` - 主机确认界面
- `POST /api/visitors` - 提交访客信息
- `GET /api/visitors` - 获取所有访客信息
- `GET /api/visitors/<id>` - 获取特定访客信息
- `PUT /api/visitors/<id>/status` - 更新访客状态为批准/拒绝
- `POST /api/security/notifications` - 安全通知接收接口
- `GET /api/security/notifications` - 获取安全通知列表

## 部署到Railway.app (免费托管)

这个应用程序可以部署到Railway.app免费套餐上。以下是部署步骤：

### 前提条件
1. 注册Railway.app账户 (https://railway.app/)
2. 安装Railway CLI (可选，通过Web界面也可部署)

### 部署步骤 (Web界面部署)

1. **注册Railway账户**:
   - 访问 https://railway.app/
   - 点击 "Sign Up" 或使用GitHub账户登录

2. **创建新项目**:
   - 登录后点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 连接您的GitHub账户
   - 选择包含访客管理系统的仓库
   - 或者使用 "Deploy to Railway" 按钮

3. **配置项目**:
   - 选择 `main.py` 作为主应用文件
   - 在 "Variables" 标签中添加以下环境变量:
     - `NOTIFICATION_SERVICE=webhook`
     - `HOST_NOTIFICATION_WEBHOOK=https://your-notification-service.com/webhook`
     - `SECURITY_NOTIFICATION_SERVICE=app`
     - `SECURITY_APP_URL=https://your-project-name.up.railway.app`

4. **部署**:
   - 点击 "Deploy" 按钮
   - Railway会自动构建并部署您的应用

5. **访问应用**:
   - 部署完成后，您会获得一个URL，如 `https://your-project-name.up.railway.app`
   - 访问该URL即可使用访客管理系统

### 部署步骤 (CLI方式)

如果您选择使用Railway CLI:

1. **安装Railway CLI**:
   - 访问 https://docs.railway.app/cli/installation
   - 根据您的操作系统安装CLI

2. **登录Railway**:
```bash
railway login
```

3. **初始化项目**:
```bash
railway init
```

4. **设置环境变量**:
```bash
railway vars set NOTIFICATION_SERVICE=webhook
railway vars set SECURITY_NOTIFICATION_SERVICE=app
```

5. **部署**:
```bash
railway up
```

## 添加数据库支持 (可选)

如果您希望使用数据库而不是SQLite（推荐用于生产环境）：

1. 在Railway中创建PostgreSQL数据库
2. 在项目变量中添加 `DATABASE_URL` 变量
3. 应用会自动使用PostgreSQL数据库

## 部署到其他平台

#### Render.com (替代方案)
1. 注册Render.com账户
2. 创建Web Service
3. 连接GitHub/GitLab仓库
4. 设置以下环境变量:
   - NOTIFICATION_SERVICE=webhook
   - HOST_NOTIFICATION_WEBHOOK=your-webhook-url
   - SECURITY_NOTIFICATION_SERVICE=app
   - SECURITY_APP_URL=your-app-url

## 通知服务配置

### WeChat工作通知配置

1. 在企业微信管理后台创建应用或使用群机器人
2. 获取Webhook URL
3. 将Webhook URL设置为 `WECHAT_WEBHOOK` 环境变量

### DingTalk通知配置

1. 在钉钉开发者后台创建机器人
2. 获取Webhook URL
3. 将Webhook URL设置为 `DINGTALK_WEBHOOK` 环境变量

### 通用Webhook配置

如果使用自定义通知服务，配置 `HOST_NOTIFICATION_WEBHOOK` 环境变量。

## 工作流程

1. 访客扫描二维码，进入访客登记页面
2. 访客填写信息并提交
3. 系统将状态设为"pending"并通知被拜访人
4. 被拜访人在主机确认界面查看并批准/拒绝访客
5. 批准后，系统通知安保app
6. 安保人员在安保app界面查看访客状态并放行

## 测试

运行测试脚本验证系统功能:

```bash
python test_workflow.py
```

## 部署建议

1. 使用WSGI服务器（如Gunicorn）部署生产环境
2. 配置反向代理（如Nginx）
3. 使用环境变量配置敏感信息
4. 数据库使用生产级数据库（如PostgreSQL、MySQL）

## 安全考虑

1. 实现用户认证和授权
2. 验证和清理所有输入数据
3. 使用HTTPS加密传输
4. 定期备份数据
5. 监控和日志记录

## 维护

- 定期清理旧的访客数据
- 监控通知服务的可用性
- 更新依赖包以确保安全

## 故障排除

- 如果通知未发送，请检查环境变量配置
- 如果页面无法访问，请确认服务器已启动
- 如果数据库错误，请检查数据库连接配置