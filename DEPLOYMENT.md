## 部署到Heroku (免费托管)

这个应用程序可以部署到Heroku免费套餐上。以下是部署步骤：

### 前提条件
1. 注册Heroku账户 (https://signup.heroku.com/)
2. 安装Heroku CLI (https://devcenter.heroku.com/articles/heroku-cli)

### 部署步骤

1. **登录Heroku**:
```bash
heroku login
```

2. **创建Heroku应用**:
```bash
heroku create your-unique-app-name
```

3. **设置环境变量**:
```bash
heroku config:set NOTIFICATION_SERVICE=webhook
heroku config:set HOST_NOTIFICATION_WEBHOOK=https://your-notification-service.com/webhook
heroku config:set SECURITY_NOTIFICATION_SERVICE=webhook
heroku config:set SECURITY_NOTIFICATION_WEBHOOK=https://your-security-webhook.com
```

4. **部署应用**:
```bash
git init
git add .
git commit -m "Initial commit"
heroku git:remote -a your-unique-app-name
git push heroku main
```

5. **打开应用**:
```bash
heroku open
```

### 部署到其他平台

#### Render.com (替代方案)
1. 注册Render.com账户
2. 创建Web Service
3. 连接GitHub/GitLab仓库
4. 设置以下环境变量:
   - NOTIFICATION_SERVICE=webhook
   - HOST_NOTIFICATION_WEBHOOK=your-webhook-url
   - SECURITY_NOTIFICATION_SERVICE=webhook
   - SECURITY_NOTIFICATION_WEBHOOK=your-security-webhook

#### Railway.app (替代方案)
1. 注册Railway账户
2. 导入项目
3. 添加环境变量
4. 部署

## API接口

### 访客登记后端

- `GET /` - 访客登记页面
- `GET /qr` - 生成访客登记二维码
- `POST /api/visitors` - 提交访客信息
- `GET /api/visitors` - 获取所有访客信息（管理用）
- `GET /api/visitors/<id>` - 获取特定访客信息
- `PUT /api/visitors/<id>/status` - 更新访客状态为批准/拒绝

### 安保app接口

- `GET /security` - 安保管理界面
- `POST /api/security/notifications` - 接收访客状态变更通知
- `GET /api/security/notifications` - 获取所有通知

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
- 如果页面无法访问，请确认所有服务已启动
- 如果数据库错误，请检查 `visitors.db` 文件权限