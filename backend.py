from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode
import io
import base64
import requests
import os

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

# HTML template for the visitor registration page
VISITOR_FORM_TEMPLATE = '''
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

@app.route('/')
def visitor_form():
    return render_template_string(VISITOR_FORM_TEMPLATE)

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
            # Direct API call to security app
            security_app_url = os.getenv('SECURITY_APP_URL', 'http://localhost:5001')
            
            payload = {
                'visitor_name': visitor.name,
                'visitor_phone': visitor.phone,
                'visitor_company': visitor.company,
                'host_name': visitor.host_name,
                'visit_time': visitor.visit_time.isoformat(),
                'status': visitor.status,
                'visitor_id': visitor.id
            }
            
            response = requests.post(f'{security_app_url}/api/security/notifications', json=payload)
            print(f"Notification sent to security app: {response.status_code}")
            
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
    # Using localhost for demonstration, in production this would be your public URL
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)