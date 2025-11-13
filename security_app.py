from flask import Flask, request, jsonify, render_template_string
from datetime import datetime

app = Flask(__name__)

# In a real application, this would connect to a database
# For demo purposes, using an in-memory list
security_notifications = []

SECURITY_DASHBOARD_TEMPLATE = '''
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
                    container.innerHTML = '<p>暂无访客信息</p>';
                    return;
                }
                
                visitors.forEach(visitor => {
                    const card = document.createElement('div');
                    card.className = `visitor-card ${visitor.status}`;
                    
                    card.innerHTML = `
                        <h3>访客: ${visitor.name}</h3>
                        <p><strong>电话:</strong> ${visitor.phone}</p>
                        <p><strong>单位:</strong> ${visitor.company}</p>
                        <p><strong>被拜访人:</strong> ${visitor.host_name}</p>
                        <p><strong>预约时间:</strong> ${new Date(visitor.visit_time).toLocaleString()}</p>
                        <p><strong>状态:</strong> <span class="status-${visitor.status}">${getStatusText(visitor.status)}</span></p>
                        <p><strong>访客ID:</strong> ${visitor.id}</p>
                    `;
                    
                    container.appendChild(card);
                });
            } catch (error) {
                console.error('Error loading visitors:', error);
                document.getElementById('visitorsContainer').innerHTML = '<p>加载访客信息失败</p>';
            }
        }
        
        function getStatusText(status) {
            switch(status) {
                case 'approved': return '已批准';
                case 'denied': return '已拒绝';
                case 'pending': return '待确认';
                default: return status;
            }
        }
    </script>
</body>
</html>
'''

@app.route('/security')
def security_dashboard():
    return render_template_string(SECURITY_DASHBOARD_TEMPLATE)

# API endpoint for receiving notifications from the visitor system
@app.route('/api/security/notifications', methods=['POST'])
def receive_notification():
    global security_notifications
    try:
        data = request.get_json()
        
        # Add timestamp
        data['timestamp'] = datetime.now().isoformat()
        
        # Store the notification
        security_notifications.append(data)
        
        return jsonify({'message': 'Notification received successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API to get all security notifications
@app.route('/api/security/notifications', methods=['GET'])
def get_notifications():
    # Sort by timestamp, newest first
    sorted_notifications = sorted(security_notifications, 
                                 key=lambda x: x.get('timestamp', ''), 
                                 reverse=True)
    return jsonify(sorted_notifications)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)