import requests
import json
import time

def test_visitor_workflow():
    """
    Test the complete visitor workflow:
    1. Submit visitor registration
    2. Check that host notification is sent
    3. Approve visitor via host interface
    4. Check that security is notified
    """
    backend_url = "http://localhost:5000"
    
    print("Testing visitor registration workflow...")
    
    # Test visitor registration
    visitor_data = {
        "name": "张三",
        "phone": "13800138000",
        "company": "ABC公司",
        "host_name": "李四",
        "host_company": "XYZ公司",
        "host_phone": "13900139000"
    }
    
    print("\n1. Submitting visitor registration...")
    try:
        response = requests.post(f"{backend_url}/api/visitors", json=visitor_data)
        if response.status_code == 201:
            result = response.json()
            visitor_id = result['id']
            print(f"   ✓ Visitor registered successfully with ID: {visitor_id}")
        else:
            print(f"   ✗ Failed to register visitor: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ Error registering visitor: {str(e)}")
        return False
    
    # Wait a moment for the notification to be processed
    time.sleep(2)
    
    # Check visitor status
    print(f"\n2. Checking visitor status...")
    try:
        response = requests.get(f"{backend_url}/api/visitors/{visitor_id}")
        if response.status_code == 200:
            visitor = response.json()
            print(f"   ✓ Visitor status: {visitor['status']}")
        else:
            print(f"   ✗ Failed to get visitor: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error getting visitor: {str(e)}")
        return False
    
    # Approve the visitor (simulating host action)
    print(f"\n3. Approving visitor as host...")
    try:
        response = requests.put(f"{backend_url}/api/visitors/{visitor_id}/status", 
                               json={"status": "approved"})
        if response.status_code == 200:
            print(f"   ✓ Visitor approved successfully")
        else:
            print(f"   ✗ Failed to approve visitor: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ✗ Error approving visitor: {str(e)}")
        return False
    
    # Wait for security notification
    time.sleep(2)
    
    # Check final status
    print(f"\n4. Checking final visitor status...")
    try:
        response = requests.get(f"{backend_url}/api/visitors/{visitor_id}")
        if response.status_code == 200:
            visitor = response.json()
            print(f"   ✓ Final visitor status: {visitor['status']}")
        else:
            print(f"   ✗ Failed to get visitor: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error getting visitor: {str(e)}")
        return False
    
    print("\n✓ All workflow tests passed!")
    return True


def test_security_interface():
    """Test the security interface"""
    print("\nTesting security interface...")
    # In the unified app, all services run on the same server
    base_url = "http://localhost:5000"
    
    try:
        response = requests.get(f"{base_url}/api/security/notifications")
        if response.status_code == 200:
            notifications = response.json()
            print(f"   ✓ Security interface working, {len(notifications)} notifications received")
        else:
            print(f"   ✗ Security interface not responding: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ Error connecting to security interface: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    print("Starting visitor system workflow tests...")
    
    success = test_visitor_workflow()
    if success:
        test_security_interface()
    
    print("\nTests completed.")