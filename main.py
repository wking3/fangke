from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import io
import base64
import requests
import os

# Create the main Flask application to handle all services
app = Flask(__name__)

# Configure database - use PostgreSQL in production, SQLite in development
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///visitors.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace('postgres://', 'postgresql://') if DATABASE_URL.startswith('postgres://') else DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    host_name = db.Column(db.String(100), nullable=False)
    host_company = db.Column(db.String(100), nullable=False)
    host_phone = db.Column(db.String(20), nullable=False)
    visit_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, denied

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'company': self.company,
            'host_name': self.host_name,
            'host_company': self.host_company,
            'host_phone': self.host_phone,
            'visit_time': self.visit_time.isoformat(),
            'status': self.status
        }

# Create tables
with app.app_context():
    db.create_all()

# In-memory storage for security notifications (in production, use a database)
security_notifications = []

def visitor_form_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>访客登记系统</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .form-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px; margin: 0 auto; }
        h1 { color: #333; text-align: center; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
        button { background-color: #007bff; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; width: 100%; }
        button:hover { background-color: #0056b3; }
        .message { padding: 15px; margin: 20px 0; border-radius: 4px; display: none; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; display: block; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; display: block; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>访客登记表</h1>
        <form id="visitorForm">
            <div class="form-group">
                <label for="name">访客姓名:</label>
                <input type="text" id="name" name="name" required>
            </div>
            
            <div class="form-group">
                <label for="phone">访客电话号码:</label>
                <input type="tel" id="phone" name="phone" required>
            </div>
            
            <div class="form-group">
                <label for="company">访客单位:</label>
                <input type="text" id="company" name="company" required>
            </div>
            
            <div class="form-group">
                <label for="host_name">被拜访人姓名:</label>
                <input type="text" id="host_name" name="host_name" required>
            </div>
            
            <div class="form-group">
                <label for="host_company">被拜访人单位:</label>
                <input type="text" id="host_company" name="host_company" required>
            </div>
            
            <div class="form-group">
                <label for="host_phone">被拜访人电话号码:</label>
                <input type="tel" id="host_phone" name="host_phone" required>
            </div>
            
            <button type="submit">提交登记</button>
        </form>
        
        <div id="message" class="message"></div>
    </div>

    <script>
        document.getElementById('visitorForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/visitors', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                const messageDiv = document.getElementById('message');
                if (response.ok) {
                    messageDiv.className = 'message success';
                    messageDiv.textContent = '登记成功！请等待被拜访人确认...';
                    e.target.reset();
                } else {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = result.error || '提交失败，请重试';
                }
            } catch (error) {
                document.getElementById('message').className = 'message error';
                document.getElementById('message').textContent = '网络错误，请重试';
            }
        });
    </script>
</body>
</html>
'''

def security_dashboard_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>安保管理系统</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .visitor-card { 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 4px; 
            background-color: #fafafa;
        }
        .visitor-card.approved { border-left: 5px solid #28a745; }
        .visitor-card.denied { border-left: 5px solid #dc3545; }
        .status-approved { color: #28a745; font-weight: bold; }
        .status-denied { color: #dc3545; font-weight: bold; }
        .status-pending { color: #ffc107; font-weight: bold; }
        .controls { margin-top: 20px; }
        button { padding: 8px 15px; margin-right: 10px; border: none; border-radius: 4px; cursor: pointer; }
        .approve-btn { background-color: #28a745; color: white; }
        .deny-btn { background-color: #dc3545; color: white; }
        .refresh-btn { background-color: #007bff; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>安保管理系统</h1>
        <p>实时接收访客预约确认信息</p>
        
        <div id="visitorsContainer">
            <!-- Visitor cards will be inserted here -->
        </div>
        
        <div class="controls">
            <button class="refresh-btn" onclick="loadVisitors()">刷新列表</button>
        </div>
    </div>

    <script>
        // Load visitors on page load
        window.onload = loadVisitors;
        
        async function loadVisitors() {
            try {
                const response = await fetch('/api/security/notifications');
                const visitors = await response.json();
                
                const container = document.getElementById('visitorsContainer');
                container.innerHTML = '';
                
                if (visitors.length === 0) {
                    container.innerHTML = '<p>\\u6682\\u65e0\\u8bbf\\u5ba2\\u4fe1\\u606f</p>';
                    return;
                }
                
                visitors.forEach(function(visitor) {
                    var card = document.createElement('div');
                    card.className = 'visitor-card ' + visitor.status;
                    
                    card.innerHTML = 
                        '<h3>\\u8bbf\\u5ba2: ' + visitor.name + '</h3>' +
                        '<p><strong>\\u7535\\u8bdd:</strong> ' + visitor.phone + '</p>' +
                        '<p><strong>\\u5355\\u4f4d:</strong> ' + visitor.company + '</p>' +
                        '<p><strong>\\u88ab\\u62dc\\u8bbf\\u4eba:</strong> ' + visitor.host_name + '</p>' +
                        '<p><strong>\\u9884\\u7ea6\\u65f6\\u95f4:</strong> ' + new Date(visitor.visit_time).toLocaleString() + '</p>' +
                        '<p><strong>\\u72b6\\u6001:</strong> <span class="status-' + visitor.status + '">' + getStatusText(visitor.status) + '</span></p>' +
                        '<p><strong>\\u8bbf\\u5ba2ID:</strong> ' + visitor.id + '</p>';
                    
                    container.appendChild(card);
                });
            } catch (error) {
                console.error('Error loading visitors:', error);
                document.getElementById('visitorsContainer').innerHTML = '<p>\\u52a0\\u8f7d\\u8bbf\\u5ba2\\u4fe1\\u606f\\u5931\\u8d25</p>';
            }
        }
        
        function getStatusText(status) {
            switch(status) {
                case 'approved': return '\\u5df2\\u6279\\u51c6';
                case 'denied': return '\\u5df2\\u62d2\\u7edd';
                case 'pending': return '\\u5f85\\u786e\\u8ba4';
                default: return status;
            }
        }
    </script>
</body>
</html>
'''

def host_confirmation_template():
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>访客确认系统</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 800px; margin: 0 auto; }
        h1 { color: #333; text-align: center; }
        .visitor-card { 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 4px; 
            background-color: #fafafa;
        }
        .visitor-card.pending { border-left: 5px solid #ffc107; }
        .visitor-card.approved { border-left: 5px solid #28a745; }
        .visitor-card.denied { border-left: 5px solid #dc3545; }
        .status-approved { color: #28a745; font-weight: bold; }
        .status-denied { color: #dc3545; font-weight: bold; }
        .status-pending { color: #ffc107; font-weight: bold; }
        .controls { margin-top: 15px; }
        button { padding: 8px 15px; margin-right: 10px; border: none; border-radius: 4px; cursor: pointer; }
        .approve-btn { background-color: #28a745; color: white; }
        .deny-btn { background-color: #dc3545; color: white; }
        .refresh-btn { background-color: #007bff; color: white; }
        .message { padding: 10px; margin: 10px 0; border-radius: 4px; display: none; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <div class="container">
        <h1>访客确认系统</h1>
        <p>请确认访客预约请求</p>
        
        <div id="message" class="message"></div>
        
        <div id="visitorsContainer">
            <!-- Visitor cards will be inserted here -->
        </div>
        
        <div class="controls">
            <button class="refresh-btn" onclick="loadVisitors()">刷新列表</button>
        </div>
    </div>

    <script>
        // Load visitors on page load
        window.onload = loadVisitors;
        
        async function loadVisitors() {
            try {
                const response = await fetch('/api/visitors');
                const visitors = await response.json();
                
                const container = document.getElementById('visitorsContainer');
                container.innerHTML = '';
                
                if (visitors.length === 0) {
                    container.innerHTML = '<p>\\u6682\\u65e0\\u8bbf\\u5ba2\\u9884\\u7ea6</p>';
                    return;
                }
                
                visitors.forEach(function(visitor) {
                    if (visitor.status !== 'pending') return; // Only show pending requests
                    
                    var card = document.createElement('div');
                    card.className = 'visitor-card ' + visitor.status;
                    
                    card.innerHTML = 
                        '<h3>\\u8bbf\\u5ba2ID: ' + visitor.id + '</h3>' +
                        '<p><strong>\\u8bbf\\u5ba2\\u59d3\\u540d:</strong> ' + visitor.name + '</p>' +
                        '<p><strong>\\u8bbf\\u5ba2\\u7535\\u8bdd:</strong> ' + visitor.phone + '</p>' +
                        '<p><strong>\\u8bbf\\u5ba2\\u5355\\u4f4d:</strong> ' + visitor.company + '</p>' +
                        '<p><strong>\\u9884\\u7ea6\\u65f6\\u95f4:</strong> ' + new Date(visitor.visit_time).toLocaleString() + '</p>' +
                        '<p><strong>\\u72b6\\u6001:</strong> <span class="status-' + visitor.status + '">' + getStatusText(visitor.status) + '</span></p>' +
                        '<div class="controls">' +
                        '<button class="approve-btn" onclick="updateStatus(' + visitor.id + ', \'approved\')">\\u6279\\u51c6</button>' +
                        '<button class="deny-btn" onclick="updateStatus(' + visitor.id + ', \'denied\')">\\u62d2\\u7edd</button>' +
                        '</div>';
                    
                    container.appendChild(card);
                });
                
                // Show non-pending visitors separately
                var nonPendingVisitors = visitors.filter(function(v) { return v.status !== 'pending'; });
                if (nonPendingVisitors.length > 0) {
                    var historyTitle = document.createElement('h3');
                    historyTitle.textContent = '\\u5386\\u53f2\\u8bb0\\u5f55';
                    container.appendChild(historyTitle);
                    
                    nonPendingVisitors.forEach(function(visitor) {
                        var card = document.createElement('div');
                        card.className = 'visitor-card ' + visitor.status;
                        
                        card.innerHTML = 
                            '<h4>\\u8bbf\\u5ba2ID: ' + visitor.id + '</h4>' +
                            '<p><strong>\\u8bbf\\u5ba2\\u59d3\\u540d:</strong> ' + visitor.name + '</p>' +
                            '<p><strong>\\u8bbf\\u5ba2\\u7535\\u8bdd:</strong> ' + visitor.phone + '</p>' +
                            '<p><strong>\\u8bbf\\u5ba2\\u5355\\u4f4d:</strong> ' + visitor.company + '</p>' +
                            '<p><strong>\\u9884\\u7ea6\\u65f6\\u95f4:</strong> ' + new Date(visitor.visit_time).toLocaleString() + '</p>' +
                            '<p><strong>\\u72b6\\u6001:</strong> <span class="status-' + visitor.status + '">' + getStatusText(visitor.status) + '</span></p>';
                        
                        container.appendChild(card);
                    });
                }
            } catch (error) {
                showMessage('\\u52a0\\u8f7d\\u8bbf\\u5ba2\\u4fe1\\u606f\\u5931\\u8d25', 'error');
            }
        }
        
        async function updateStatus(visitorId, status) {
            try {
                const response = await fetch('/api/visitors/' + visitorId + '/status', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ status: status })
                });
                
                if (response.ok) {
                    showMessage('\\u8bbf\\u5ba2 ' + visitorId + ' \\u5df2' + (status === 'approved' ? '\\u6279\\u51c6' : '\\u62d2\\u7edd'), 'success');
                    setTimeout(loadVisitors, 1000); // Refresh after 1 second
                } else {
                    const result = await response.json();
                    showMessage(result.error || '\\u64cd\\u4f5c\\u5931\\u8d25', 'error');
                }
            } catch (error) {
                showMessage('\\u7f51\\u7edc\\u9519\\u8bef\\uff0c\\u8bf7\\u91cd\\u8bd5', 'error');
            }
        }
        
        function showMessage(text, type) {
            var messageDiv = document.getElementById('message');
            messageDiv.textContent = text;
            messageDiv.className = 'message ' + type;
            messageDiv.style.display = 'block';
            
            // Hide message after 5 seconds
            setTimeout(function() {
                messageDiv.style.display = 'none';
            }, 5000);
        }
        
        function getStatusText(status) {
            switch(status) {
                case 'approved': return '\\u5df2\\u6279\\u51c6';
                case 'denied': return '\\u5df2\\u62d2\\u7edd';
                case 'pending': return '\\u5f85\\u786e\\u8ba4';
                default: return status;
            }
        }
    </script>
</body>
</html>
'''

# Main visitor registration page
@app.route('/')
def visitor_form():
    return visitor_form_template()

# Security dashboard
@app.route('/security')
def security_dashboard():
    return security_dashboard_template()

# Host confirmation interface
@app.route('/host')
def host_confirmation_interface():
    return host_confirmation_template()

# Generate QR code for visitor registration page
@app.route('/qr')
def generate_qr():
    # Generate QR code pointing to the visitor registration page
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    # Using the root URL of the current request
    qr.add_data(request.url_root)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for display in HTML
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    qr_template = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>访客登记二维码</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
            .qr-container {{ margin: 0 auto; max-width: 400px; }}
            h1 {{ color: #333; }}
        </style>
    </head>
    <body>
        <div class="qr-container">
            <h1>访客登记二维码</h1>
            <p>用微信扫描下方二维码进行访客登记</p>
            <img src="data:image/png;base64,{img_str}" alt="QR Code" style="width: 300px; height: 300px;">
            <p>扫描二维码或直接访问: {request.url_root}</p>
        </div>
    </body>
    </html>
    '''
    return qr_template

# API endpoint to handle visitor registration
@app.route('/api/visitors', methods=['POST'])
def register_visitor():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'phone', 'company', 'host_name', 'host_company', 'host_phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create new visitor record
        visitor = Visitor(
            name=data['name'],
            phone=data['phone'],
            company=data['company'],
            host_name=data['host_name'],
            host_company=data['host_company'],
            host_phone=data['host_phone']
        )
        
        db.session.add(visitor)
        db.session.commit()
        
        # Send notification to host for confirmation
        send_notification_to_host(visitor)
        
        return jsonify({'message': 'Visitor registered successfully', 'id': visitor.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def send_notification_to_host(visitor):
    """Send notification to the host for confirmation via WeChat or DingTalk"""
    try:
        # Determine which notification service to use based on environment variable
        notification_service = os.getenv('NOTIFICATION_SERVICE', 'webhook').lower()
        
        message = f'有新的访客预约:\n姓名: {visitor.name}\n电话: {visitor.phone}\n单位: {visitor.company}\n\n请确认是否同意接待，访问ID: {visitor.id}'
        
        if notification_service == 'wechat':
            # WeChat Work notification
            wechat_webhook = os.getenv('WECHAT_WEBHOOK')
            if not wechat_webhook:
                print("WeChat webhook not configured")
                return
                
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(wechat_webhook, json=payload)
            print(f"WeChat notification sent: {response.status_code}")
            
        elif notification_service == 'dingtalk':
            # DingTalk notification
            dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK')
            if not dingtalk_webhook:
                print("DingTalk webhook not configured")
                return
                
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(dingtalk_webhook, json=payload)
            print(f"DingTalk notification sent: {response.status_code}")
            
        else:
            # Generic webhook fallback
            webhook_url = os.getenv('HOST_NOTIFICATION_WEBHOOK', 'https://example.com/webhook')
            
            payload = {
                'text': message,
                'visitor_id': visitor.id,
                'visitor_name': visitor.name,
                'visitor_phone': visitor.phone,
                'visitor_company': visitor.company,
                'host_name': visitor.host_name,
                'host_company': visitor.host_company,
                'host_phone': visitor.host_phone
            }
            
            response = requests.post(webhook_url, json=payload)
            print(f"Generic notification sent: {response.status_code}")
        
    except Exception as e:
        print(f"Error sending notification to host: {str(e)}")

# API endpoint for host to approve or deny visitor
@app.route('/api/visitors/<int:visitor_id>/status', methods=['PUT'])
def update_visitor_status(visitor_id):
    try:
        visitor = Visitor.query.get_or_404(visitor_id)
        data = request.get_json()
        
        new_status = data.get('status')
        if new_status not in ['approved', 'denied']:
            return jsonify({'error': 'Status must be approved or denied'}), 400
        
        visitor.status = new_status
        db.session.commit()
        
        # Send notification to security
        send_notification_to_security(visitor)
        
        return jsonify({'message': f'Visitor status updated to {new_status}'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def send_notification_to_security(visitor):
    """Send notification to security app"""
    try:
        # Determine which notification service to use for security
        security_notification_service = os.getenv('SECURITY_NOTIFICATION_SERVICE', 'webhook').lower()
        
        message = f'访客状态更新:\n访客姓名: {visitor.name}\n访客电话: {visitor.phone}\n访客单位: {visitor.company}\n被拜访人: {visitor.host_name}\n状态: {visitor.status}\n访客ID: {visitor.id}'
        
        if security_notification_service == 'wechat':
            # WeChat Work notification for security
            wechat_webhook = os.getenv('SECURITY_WECHAT_WEBHOOK')
            if not wechat_webhook:
                print("Security WeChat webhook not configured")
                return
                
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(wechat_webhook, json=payload)
            print(f"Security WeChat notification sent: {response.status_code}")
            
        elif security_notification_service == 'dingtalk':
            # DingTalk notification for security
            dingtalk_webhook = os.getenv('SECURITY_DINGTALK_WEBHOOK')
            if not dingtalk_webhook:
                print("Security DingTalk webhook not configured")
                return
                
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
            response = requests.post(dingtalk_webhook, json=payload)
            print(f"Security DingTalk notification sent: {response.status_code}")
            
        elif security_notification_service == 'app':
            # Add to in-memory security notifications
            notification_data = {
                'visitor_name': visitor.name,
                'visitor_phone': visitor.phone,
                'visitor_company': visitor.company,
                'host_name': visitor.host_name,
                'visit_time': visitor.visit_time.isoformat(),
                'status': visitor.status,
                'visitor_id': visitor.id,
                'timestamp': datetime.now().isoformat()
            }
            
            # In a real app, you would store this in a database
            # For this demo, we're using an in-memory list
            global security_notifications
            security_notifications.append(notification_data)
            
            print(f"Notification added to security app: visitor {visitor.id}, status: {visitor.status}")
            
        else:
            # Generic webhook fallback for security
            webhook_url = os.getenv('SECURITY_NOTIFICATION_WEBHOOK', 'https://example.com/security_webhook')
            
            payload = {
                'visitor_name': visitor.name,
                'visitor_phone': visitor.phone,
                'visitor_company': visitor.company,
                'host_name': visitor.host_name,
                'visit_time': visitor.visit_time.isoformat(),
                'status': visitor.status,
                'visitor_id': visitor.id
            }
            
            response = requests.post(webhook_url, json=payload)
            print(f"Security notification sent to webhook: {response.status_code}")
        
    except Exception as e:
        print(f"Error sending notification to security: {str(e)}")

# API to get all visitors (for admin/security interface)
@app.route('/api/visitors', methods=['GET'])
def get_all_visitors():
    visitors = Visitor.query.order_by(Visitor.visit_time.desc()).all()
    return jsonify([visitor.to_dict() for visitor in visitors])

# API to get a specific visitor
@app.route('/api/visitors/<int:visitor_id>', methods=['GET'])
def get_visitor(visitor_id):
    visitor = Visitor.query.get_or_404(visitor_id)
    return jsonify(visitor.to_dict())

# Security app API endpoints
@app.route('/api/security/notifications', methods=['POST'])
def receive_security_notification():
    """Receive notification from visitor system"""
    try:
        data = request.get_json()
        
        # Add timestamp
        data['timestamp'] = datetime.now().isoformat()
        
        # Store the notification
        global security_notifications
        security_notifications.append(data)
        
        return jsonify({'message': 'Notification received successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API to get all security notifications
@app.route('/api/security/notifications', methods=['GET'])
def get_security_notifications():
    # Sort by timestamp, newest first
    sorted_notifications = sorted(security_notifications, 
                                 key=lambda x: x.get('timestamp', ''), 
                                 reverse=True)
    return jsonify(sorted_notifications)

if __name__ == '__main__':
    # Use PORT environment variable for Heroku, default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)