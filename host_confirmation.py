from flask import Flask, request, jsonify, render_template_string
import requests
import os

app = Flask(__name__)

# In a real application, this would connect to a database
# For demo purposes, we'll use a simple variable to store the backend URL
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')

HOST_CONFIRMATION_TEMPLATE = '''
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
        const BACKEND_URL = 'http://localhost:5000'; // In production, this would be your backend URL
        
        // Load visitors on page load
        window.onload = loadVisitors;
        
        async function loadVisitors() {
            try {
                const response = await fetch(`${BACKEND_URL}/api/visitors`);
                const visitors = await response.json();
                
                const container = document.getElementById('visitorsContainer');
                container.innerHTML = '';
                
                if (visitors.length === 0) {
                    container.innerHTML = '<p>暂无访客预约</p>';
                    return;
                }
                
                visitors.forEach(visitor => {
                    if (visitor.status !== 'pending') return; // Only show pending requests
                    
                    const card = document.createElement('div');
                    card.className = `visitor-card ${visitor.status}`;
                    
                    card.innerHTML = `
                        <h3>访客ID: ${visitor.id}</h3>
                        <p><strong>访客姓名:</strong> ${visitor.name}</p>
                        <p><strong>访客电话:</strong> ${visitor.phone}</p>
                        <p><strong>访客单位:</strong> ${visitor.company}</p>
                        <p><strong>预约时间:</strong> ${new Date(visitor.visit_time).toLocaleString()}</p>
                        <p><strong>状态:</strong> <span class="status-${visitor.status}">${getStatusText(visitor.status)}</span></p>
                        <div class="controls">
                            <button class="approve-btn" onclick="updateStatus(${visitor.id}, 'approved')">批准</button>
                            <button class="deny-btn" onclick="updateStatus(${visitor.id}, 'denied')">拒绝</button>
                        </div>
                    `;
                    
                    container.appendChild(card);
                });
                
                // Show non-pending visitors separately
                const nonPendingVisitors = visitors.filter(v => v.status !== 'pending');
                if (nonPendingVisitors.length > 0) {
                    const historyTitle = document.createElement('h3');
                    historyTitle.textContent = '历史记录';
                    container.appendChild(historyTitle);
                    
                    nonPendingVisitors.forEach(visitor => {
                        const card = document.createElement('div');
                        card.className = `visitor-card ${visitor.status}`;
                        
                        card.innerHTML = `
                            <h4>访客ID: ${visitor.id}</h4>
                            <p><strong>访客姓名:</strong> ${visitor.name}</p>
                            <p><strong>访客电话:</strong> ${visitor.phone}</p>
                            <p><strong>访客单位:</strong> ${visitor.company}</p>
                            <p><strong>预约时间:</strong> ${new Date(visitor.visit_time).toLocaleString()}</p>
                            <p><strong>状态:</strong> <span class="status-${visitor.status}">${getStatusText(visitor.status)}</span></p>
                        `;
                        
                        container.appendChild(card);
                    });
                }
            } catch (error) {
                showMessage('加载访客信息失败', 'error');
                console.error('Error loading visitors:', error);
            }
        }
        
        async function updateStatus(visitorId, status) {
            try {
                const response = await fetch(`${BACKEND_URL}/api/visitors/${visitorId}/status`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ status: status })
                });
                
                if (response.ok) {
                    showMessage(`访客 ${visitorId} 已${status === 'approved' ? '批准' : '拒绝'}`, 'success');
                    setTimeout(loadVisitors, 1000); // Refresh after 1 second
                } else {
                    const result = await response.json();
                    showMessage(result.error || '操作失败', 'error');
                }
            } catch (error) {
                showMessage('网络错误，请重试', 'error');
                console.error('Error updating status:', error);
            }
        }
        
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.textContent = text;
            messageDiv.className = `message ${type}`;
            messageDiv.style.display = 'block';
            
            // Hide message after 5 seconds
            setTimeout(() => {
                messageDiv.style.display = 'none';
            }, 5000);
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

@app.route('/')
def host_confirmation_interface():
    return render_template_string(HOST_CONFIRMATION_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)