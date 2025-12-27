from flask import Flask, request, jsonify
from flask_cors import CORS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests
import time
import json
import base64
import asyncio

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Protobuf setup ---
from google.protobuf import message_factory
from google.protobuf import descriptor_pool

pool = descriptor_pool.Default()
fd = pool.AddSerializedFile(b'\n\ndata.proto"7\n\x12InnerNestedMessage\x12\x0f\n\x07\x66ield_6\x18\x06 \x01(\x03\x12\x10\n\x08\x66ield_14\x18\x0e \x01(\x03"\x87\x01\n\nNestedItem\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x0f\n\x07\x66ield_3\x18\x03 \x01(\x05\x12\x0f\n\x07\x66ield_4\x18\x04 \x01(\x05\x12\x0f\n\x07\x66ield_5\x18\x05 \x01(\x05\x12$\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\x13.InnerNestedMessage"@\n\x0fNestedContainer\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12\x1c\n\x07\x66ield_2\x18\x02 \x03(\x0b\x32\x0b.NestedItem"A\n\x0bMainMessage\x12\x0f\n\x07\x66ield_1\x18\x01 \x01(\x05\x12!\n\x07\x66ield_2\x18\x02 \x03(\x0b\x32\x10.NestedContainerb\x06proto3')

MainMessage = message_factory.GetMessageClass(pool.FindMessageTypeByName('MainMessage'))
NestedContainer = message_factory.GetMessageClass(pool.FindMessageTypeByName('NestedContainer'))
NestedItem = message_factory.GetMessageClass(pool.FindMessageTypeByName('NestedItem'))
InnerNestedMessage = message_factory.GetMessageClass(pool.FindMessageTypeByName('InnerNestedMessage'))

# --- Encryption setup ---
key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
freefire_version = "OB51"

def decode_jwt_noverify(token: str):
    """JWT ko bina verify kiye payload decode karta hai"""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)  # padding fix
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        return payload
    except Exception:
        return None

def get_server_url(lock_region: str):
    """Region ke hisaab se Free Fire endpoint select kare"""
    region = lock_region.upper()
    
    # Region to URL mapping
    region_map = {
        "IND": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",  # Indonesia
        "ME": "https://clientbp.ggblueshark.com/SetPlayerGalleryShowInfo",   # Middle East
        "VN": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Vietnam
        "BD": "https://clientbp.ggwhitehawk.com/SetPlayerGalleryShowInfo",   # Bangladesh
        "PK": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Pakistan
        "SG": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Singapore
        "BR": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo", # Brazil
        "NA": "https://client.us.freefiremobile.com/SetPlayerGalleryShowInfo", # North America
        "ID": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Indonesia
        "RU": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Russia
        "TH": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo",   # Thailand
        "TW": "https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo"    # Taiwan
    }
    
    # Agar region mapping mein hai to woh URL use karo
    if region in region_map:
        return region_map[region]
    else:
        # Default URL for all other regions
        return "https://client.ind.freefiremobile.com/SetPlayerGalleryShowInfo"

@app.route('/add-profile', methods=['GET'])
def add_profile():
    jwt_token = request.args.get('token')
    itemid_str = request.args.get('itemid')
    
    if not jwt_token or not itemid_str:
        return jsonify({
            "status": False,
            "message": "Missing token or itemid parameter"
        }), 400

    # --- JWT decode karke lock_region nikalna ---
    payload = decode_jwt_noverify(jwt_token)
    if not payload:
        return jsonify({
            "status": False,
            "message": "Invalid JWT token"
        }), 400

    lock_region = payload.get("lock_region", "IND").upper()  # agar missing hai to default IND
    url = get_server_url(lock_region)

    # --- Process item IDs ---
    item_ids = itemid_str.split('/')[:15]
    if not item_ids:
        return jsonify({"status": False, "message": "At least one item ID required"}), 400

    # Build protobuf message using the structure from old code
    data = MainMessage()
    data.field_1 = 1
    
    container1 = data.field_2.add()
    container1.field_1 = 1
    
    # Item combinations from old code
    items = [
        {"field_1": 2, "field_4": 1},
        {"field_1": 2, "field_4": 1, "field_5": 4},
        {"field_1": 2, "field_4": 1, "field_5": 2},
        {"field_1": 13, "field_3": 1},
        {"field_1": 13, "field_3": 1, "field_4": 2},
        {"field_1": 13, "field_3": 1, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 2, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 2, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 4},
        {"field_1": 13, "field_3": 1, "field_4": 4, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 4, "field_5": 4},
        {"field_1": 13, "field_3": 1, "field_4": 6},
        {"field_1": 13, "field_3": 1, "field_4": 6, "field_5": 2},
        {"field_1": 13, "field_3": 1, "field_4": 6, "field_5": 4}
    ]
    
    for i, item_id in enumerate(item_ids):
        if i >= len(items):
            break
        item_data = items[i]
        item = container1.field_2.add()
        item.field_1 = item_data.get("field_1", 0)
        if "field_3" in item_data:
            item.field_3 = item_data["field_3"]
        if "field_4" in item_data:
            item.field_4 = item_data["field_4"]
        if "field_5" in item_data:
            item.field_5 = item_data["field_5"]
        inner = InnerNestedMessage()
        inner.field_6 = int(item_id)
        item.field_6.CopyFrom(inner)

    # Additional container from old code
    container2 = data.field_2.add()
    container2.field_1 = 9
    
    item7 = container2.field_2.add()
    item7.field_4 = 3
    inner7 = InnerNestedMessage()
    inner7.field_14 = 3048205855
    item7.field_6.CopyFrom(inner7)
    
    item8 = container2.field_2.add()
    item8.field_4 = 3
    item8.field_5 = 3
    inner8 = InnerNestedMessage()
    inner8.field_14 = 3048205855
    item8.field_6.CopyFrom(inner8)

    # --- Encrypt protobuf ---
    data_bytes = data.SerializeToString()
    padded_data = pad(data_bytes, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(padded_data)

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Accept-Encoding": "gzip"
    }

    try:
        response = requests.post(url, headers=headers, data=encrypted_data, timeout=10)
    except Exception as e:
        return jsonify({
            "status": False,
            "message": f"External request failed: {str(e)}"
        }), 500

    current_time = int(time.time())
    add_profile_list = [{"add_time": current_time, f"item_id{i+1}": int(item_id)} 
                        for i, item_id in enumerate(item_ids)]

    if response.status_code == 200:
        return jsonify({
            "message": "Item added to profile",
            "status": True,
            "lock_region": lock_region,
            "server_used": url,
            "Add-profile": add_profile_list,
            "response_code": response.status_code
        })
    else:
        return jsonify({
            "status": False,
            "message": f"External server returned status {response.status_code}",
            "lock_region": lock_region,
            "server_used": url,
            "external_response": response.text,
            "request_size": len(encrypted_data),
            "response_code": response.status_code
        }), 400

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": True,
        "message": "API is running successfully",
        "version": "1.0",
        "freefire_version": freefire_version
    })

@app.route('/get-access-token', methods=['GET'])
def get_access_token():
    """Proxy endpoint to retrieve access token from external service"""
    eat_token = request.args.get('eat_token')
    
    if not eat_token:
        return jsonify({"error": "EAT token is required"}), 400
    
    try:
        # Make request to the external service
        external_url = f"https://danger-access-token.vercel.app/eat-to-access?eat_token={eat_token}"
        response = requests.get(external_url, timeout=10)
        
        # Return the response from the external service
        return jsonify(response.json()), response.status_code
        
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve access token: {str(e)}"}), 500

@app.route('/regions', methods=['GET'])
def get_regions():
    """Get all supported regions"""
    regions = {
        "IND": "India",
        "BR": "Brazil", 
        "US": "United States",
        "SAC": "South America",
        "NA": "North America",
        "BD": "Bangladesh",
        "SG": "Singapore",
        "ME": "Middle East",
        "PK": "Pakistan",
        "EU": "Europe",
        "ID": "Indonesia",
        "VN": "Vietnam",
        "TH": "Thailand",
        "PH": "Philippines",
        "MY": "Malaysia",
        "TR": "Turkey",
        "RU": "Russia",
        "TW": "Taiwan",
        "DEFAULT": "Other Regions"
    }
    return jsonify({
        "status": True,
        "regions": regions
    })

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Free Fire Profile API Documentation</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --primary: #2d3436;
            --secondary: #0984e3;
            --accent: #00cec9;
            --success: #00b894;
            --error: #d63031;
            --warning: #fdcb6e;
            --light: #f5f6fa;
            --dark: #2d3436;
            --gray: #636e72;
        }
        
        body {
            font-family: 'Ubuntu', 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: var(--dark);
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(10px);
        }
        
        .logo {
            font-size: 3rem;
            color: var(--secondary);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        
        .logo::before, .logo::after {
            content: "»";
            color: var(--accent);
            font-size: 2rem;
        }
        
        h1 {
            font-size: 2.8rem;
            background: linear-gradient(45deg, var(--secondary), var(--accent));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            margin-bottom: 15px;
        }
        
        .tagline {
            font-size: 1.2rem;
            color: var(--gray);
            max-width: 600px;
            margin: 0 auto 25px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.08);
            border-left: 5px solid var(--secondary);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.15);
        }
        
        .card h3 {
            color: var(--secondary);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.5rem;
        }
        
        .card h3::before {
            content: "#";
            color: var(--accent);
            font-weight: bold;
        }
        
        .endpoint-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--light);
        }
        
        .method {
            background: var(--secondary);
            color: white;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.9rem;
            letter-spacing: 1px;
        }
        
        .endpoint-path {
            font-family: 'Monaco', 'Consolas', monospace;
            background: var(--light);
            padding: 12px 20px;
            border-radius: 10px;
            flex-grow: 1;
            border: 1px solid #e0e0e0;
            font-size: 1.1rem;
            color: var(--dark);
        }
        
        .param-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: var(--light);
            border-radius: 10px;
            overflow: hidden;
        }
        
        .param-table th {
            background: var(--secondary);
            color: white;
            padding: 15px;
            text-align: left;
        }
        
        .param-table td {
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .param-table tr:last-child td {
            border-bottom: none;
        }
        
        .required {
            color: var(--error);
            font-weight: bold;
            font-size: 0.9rem;
        }
        
        .optional {
            color: var(--gray);
            font-size: 0.9rem;
        }
        
        .code-block {
            background: #282c34;
            color: #abb2bf;
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            overflow-x: auto;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.95rem;
            line-height: 1.5;
            border: 1px solid #3e4451;
        }
        
        .keyword { color: #c678dd; }
        .string { color: #98c379; }
        .number { color: #d19a66; }
        .comment { color: #5c6370; }
        .function { color: #61afef; }
        
        .response {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .response-box {
            padding: 20px;
            border-radius: 10px;
            background: var(--light);
        }
        
        .response-box.success {
            border-top: 4px solid var(--success);
        }
        
        .response-box.error {
            border-top: 4px solid var(--error);
        }
        
        .region-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .region-card {
            background: var(--light);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .region-card:hover {
            background: var(--secondary);
            color: white;
            transform: scale(1.05);
        }
        
        .region-code {
            font-weight: bold;
            font-size: 1.2rem;
            color: var(--secondary);
            margin-bottom: 5px;
        }
        
        .region-card:hover .region-code {
            color: white;
        }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            margin: 5px;
        }
        
        .status-true {
            background: rgba(0, 184, 148, 0.1);
            color: var(--success);
            border: 1px solid rgba(0, 184, 148, 0.3);
        }
        
        .status-false {
            background: rgba(214, 48, 49, 0.1);
            color: var(--error);
            border: 1px solid rgba(214, 48, 49, 0.3);
        }
        
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
            margin: 2px;
        }
        
        .badge-get { background: #61affe; color: white; }
        .badge-post { background: #49cc90; color: white; }
        .badge-put { background: #fca130; color: white; }
        .badge-delete { background: #f93e3e; color: white; }
        
        .footer {
            text-align: center;
            margin-top: 50px;
            padding: 30px;
            color: white;
            font-size: 1.1rem;
        }
        
        .footer-logo {
            font-family: 'Monaco', monospace;
            font-size: 1.8rem;
            color: var(--accent);
            letter-spacing: 2px;
            margin-bottom: 15px;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header {
                padding: 20px 15px;
            }
            
            h1 {
                font-size: 2rem;
            }
            
            .endpoint-header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .region-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }
            
            .response {
                grid-template-columns: 1fr;
            }
        }
        
        .linux-terminal {
            background: #1e1e1e;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            color: #00ff00;
            font-family: 'Monaco', 'Consolas', monospace;
            position: relative;
            border: 1px solid #333;
        }
        
        .terminal-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }
        
        .terminal-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }
        
        .terminal-dot.red { background: #ff5f56; }
        .terminal-dot.yellow { background: #ffbd2e; }
        .terminal-dot.green { background: #27ca3f; }
        
        .terminal-content {
            color: #00ff00;
            line-height: 1.6;
        }
        
        .terminal-prompt {
            color: #61afef;
        }
        
        .cursor {
            animation: blink 1s infinite;
        }
        
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <i class="fas fa-fire"></i>
            </div>
            <h1>Free Fire Profile API</h1>
            <p class="tagline">
                <i class="fas fa-code"></i> A robust API for managing Free Fire profile items with JWT authentication and multi-region support
            </p>
            <div style="display: flex; gap: 15px; justify-content: center; margin-top: 20px;">
                <span class="badge badge-get"><i class="fas fa-shield-alt"></i> Secure</span>
                <span class="badge badge-post"><i class="fas fa-bolt"></i> Fast</span>
                <span class="badge badge-put"><i class="fas fa-globe"></i> Multi-Region</span>
                <span class="badge badge-delete"><i class="fas fa-code"></i> RESTful</span>
            </div>
        </header>

        <!-- Linux Terminal Demo -->
        <div class="card">
            <h3><i class="fab fa-linux"></i> Linux Terminal Example</h3>
            <div class="linux-terminal">
                <div class="terminal-header">
                    <div class="terminal-dot red"></div>
                    <div class="terminal-dot yellow"></div>
                    <div class="terminal-dot green"></div>
                    <span style="color: #888; font-size: 0.9rem;">terminal@linux:~</span>
                </div>
                <div class="terminal-content">
                    <div><span class="terminal-prompt">$</span> curl -X GET "http://api.example.com:5000/add-profile?token=eyJhbGciOiJIUzI1NiIs...&itemid=12345/67890/54321"</div>
                    <div><span class="terminal-prompt">$</span> <span class="cursor">_</span></div>
                    <div style="margin-top: 10px; color: #61afef;">
                        # Response will be in JSON format<br>
                        # Max 15 items per request<br>
                        # JWT token required for authentication
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Endpoint -->
        <div class="card">
            <div class="endpoint-header">
                <span class="method">GET</span>
                <div class="endpoint-path">/add-profile</div>
                <span class="status-indicator status-true">
                    <i class="fas fa-check-circle"></i> Active
                </span>
            </div>
            
            <p style="margin-bottom: 20px; color: var(--gray);">
                <i class="fas fa-info-circle"></i> This endpoint adds items to Free Fire profile. Supports JWT authentication and multiple regions.
            </p>
            
            <h4><i class="fas fa-cogs"></i> Parameters</h4>
            <table class="param-table">
                <thead>
                    <tr>
                        <th>Parameter</th>
                        <th>Type</th>
                        <th>Required</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>token</code></td>
                        <td>String</td>
                        <td><span class="required">Required</span></td>
                        <td>JWT authentication token</td>
                    </tr>
                    <tr>
                        <td><code>itemid</code></td>
                        <td>String</td>
                        <td><span class="required">Required</span></td>
                        <td>Item IDs separated by '/' (max 15 items)</td>
                    </tr>
                </tbody>
            </table>
            
            <h4 style="margin-top: 30px;"><i class="fas fa-code"></i> Example Request</h4>
            <div class="code-block">
<span class="comment"># Linux cURL command</span>
<span class="function">curl</span> -X <span class="keyword">GET</span> \
  <span class="string">"http://your-server.com:5000/add-profile?token=eyJhbGciOiJIUzI1NiIs...&itemid=12345/67890/54321"</span> \
  -H <span class="string">"Accept: application/json"</span>
            </div>
            
            <h4><i class="fas fa-exchange-alt"></i> Response</h4>
            <div class="response">
                <div class="response-box success">
                    <h5><i class="fas fa-check success"></i> Success Response</h5>
                    <div class="code-block">
{
  <span class="string">"status"</span>: <span class="keyword">true</span>,
  <span class="string">"message"</span>: <span class="string">"Items added to profile successfully"</span>,
  <span class="string">"lock_region"</span>: <span class="string">"IND"</span>,
  <span class="string">"server_used"</span>: <span class="string">"https://clientbp.ggpolarbear.com/SetPlayerGalleryShowInfo"</span>,
  <span class="string">"items_added"</span>: [
    {
      <span class="string">"add_time"</span>: <span class="number">1700000000</span>,
      <span class="string">"item_id"</span>: <span class="number">12345</span>
    },
    {
      <span class="string">"add_time"</span>: <span class="number">1700000000</span>,
      <span class="string">"item_id"</span>: <span class="number">67890</span>
    }
  ],
  <span class="string">"timestamp"</span>: <span class="number">1700000000</span>,
  <span class="string">"request_id"</span>: <span class="string">"ff-api-req-123456"</span>
}
                    </div>
                </div>
                
                <div class="response-box error">
                    <h5><i class="fas fa-times error"></i> Error Response</h5>
                    <div class="code-block">
{
  <span class="string">"status"</span>: <span class="keyword">false</span>,
  <span class="string">"message"</span>: <span class="string">"Invalid JWT token"</span>,
  <span class="string">"error_code"</span>: <span class="string">"AUTH_001"</span>,
  <span class="string">"timestamp"</span>: <span class="number">1700000000</span>,
  <span class="string">"docs"</span>: <span class="string">"https://api-docs.example.com/errors/AUTH_001"</span>
}
                    </div>
                </div>
            </div>
        </div>

        <!-- Supported Regions -->
        <div class="card">
            <h3><i class="fas fa-globe-americas"></i> Supported Regions</h3>
            <div class="region-grid">
                <div class="region-card">
                    <div class="region-code">IND</div>
                    <div>India</div>
                </div>
                <div class="region-card">
                    <div class="region-code">BR / US</div>
                    <div>Americas</div>
                </div>
                <div class="region-card">
                    <div class="region-code">SG</div>
                    <div>Singapore</div>
                </div>
                <div class="region-card">
                    <div class="region-code">BD</div>
                    <div>Bangladesh</div>
                </div>
                <div class="region-card">
                    <div class="region-code">ME / TR</div>
                    <div>Middle East</div>
                </div>
                <div class="region-card">
                    <div class="region-code">EU / RU</div>
                    <div>Europe</div>
                </div>
                <div class="region-card">
                    <div class="region-code">ID / VN</div>
                    <div>Southeast Asia</div>
                </div>
                <div class="region-card">
                    <div class="region-code">TW</div>
                    <div>Taiwan</div>
                </div>
            </div>
        </div>

        <!-- Additional Endpoints -->
        <div class="card">
            <h3><i class="fas fa-plug"></i> Additional Endpoints</h3>
            
            <div style="margin-top: 20px;">
                <div class="endpoint-header">
                    <span class="method">GET</span>
                    <div class="endpoint-path">/health</div>
                </div>
                <p style="color: var(--gray); margin: 10px 0;">
                    <i class="fas fa-heartbeat"></i> Health check endpoint to verify API status
                </p>
                
                <div class="endpoint-header" style="margin-top: 25px;">
                    <span class="method">GET</span>
                    <div class="endpoint-path">/regions</div>
                </div>
                <p style="color: var(--gray); margin: 10px 0;">
                    <i class="fas fa-list"></i> Get list of all supported regions with status
                </p>
                
                <div class="endpoint-header" style="margin-top: 25px;">
                    <span class="method">GET</span>
                    <div class="endpoint-path">/docs</div>
                </div>
                <p style="color: var(--gray); margin: 10px 0;">
                    <i class="fas fa-book"></i> Complete API documentation (OpenAPI/Swagger)
                </p>
            </div>
        </div>

        <!-- Status Codes -->
        <div class="card">
            <h3><i class="fas fa-info-circle"></i> Status Codes & Responses</h3>
            <div style="margin-top: 20px;">
                <div style="display: flex; flex-wrap: wrap; gap: 15px;">
                    <div style="flex: 1; min-width: 200px;">
                        <h4><i class="fas fa-check success"></i> Success Status</h4>
                        <p>Status: <span class="status-indicator status-true">true</span></p>
                        <ul style="margin-top: 10px; padding-left: 20px; color: var(--gray);">
                            <li>Operation successful</li>
                            <li>Items added to profile</li>
                            <li>Valid response data returned</li>
                        </ul>
                    </div>
                    
                    <div style="flex: 1; min-width: 200px;">
                        <h4><i class="fas fa-times error"></i> Error Status</h4>
                        <p>Status: <span class="status-indicator status-false">false</span></p>
                        <ul style="margin-top: 10px; padding-left: 20px; color: var(--gray);">
                            <li>Authentication failed</li>
                            <li>Invalid parameters</li>
                            <li>Server error</li>
                            <li>Rate limit exceeded</li>
                        </ul>
                    </div>
                </div>
                
                <div style="margin-top: 30px; background: var(--light); padding: 20px; border-radius: 10px;">
                    <h4><i class="fas fa-lightbulb"></i> Best Practices</h4>
                    <ul style="margin-top: 10px; padding-left: 20px; color: var(--gray);">
                        <li>Always validate JWT tokens before requests</li>
                        <li>Limit requests to 15 items maximum</li>
                        <li>Implement exponential backoff for retries</li>
                        <li>Cache region information locally</li>
                        <li>Monitor rate limits (100 req/hour per token)</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <footer class="footer">
            <div class="footer-logo">linuxxxxxxxxxxxxx</div>
            <p>
                <i class="fas fa-code-branch"></i> Free Fire Profile API v2.1.0 |
                <i class="fas fa-server"></i> Powered by Linux |
                <i class="fas fa-shield-alt"></i> Secure JWT Authentication
            </p>
            <p style="margin-top: 15px; font-size: 0.9rem; opacity: 0.8;">
                <i class="fas fa-terminal"></i> Optimized for Linux environments |
                <i class="fab fa-docker"></i> Docker container available |
                <i class="fab fa-github"></i> Source on GitHub
            </p>
        </footer>
    </div>

    <script>
        // Add terminal typing effect
        document.addEventListener('DOMContentLoaded', function() {
            const cursor = document.querySelector('.cursor');
            let visible = true;
            
            setInterval(() => {
                visible = !visible;
                cursor.style.opacity = visible ? '1' : '0';
            }, 500);
            
            // Add copy functionality to code blocks
            document.querySelectorAll('.code-block').forEach(block => {
                block.addEventListener('click', function() {
                    const text = this.innerText;
                    navigator.clipboard.writeText(text).then(() => {
                        const original = this.innerHTML;
                        this.innerHTML = '<i class="fas fa-check" style="color: #00ff00;"></i> Copied!';
                        setTimeout(() => {
                            this.innerHTML = original;
                        }, 1500);
                    });
                });
                block.style.cursor = 'pointer';
                block.title = 'Click to copy';
            });
        });
    </script>
</body>
</html>
    """

import sys

async def startup():
    """Startup function to initialize the application."""
    print("[✅] Application initialized successfully")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"[🚀] Starting {__name__.upper()} on port {port} ...")
    try:
        asyncio.run(startup())
    except Exception as e:
        print(f"[⚠️] Startup warning: {e} — continuing without full initialization")
    app.run(host='0.0.0.0', port=port, debug=False)