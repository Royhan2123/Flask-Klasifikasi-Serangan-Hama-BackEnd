from flask import Flask, render_template_string, request, redirect, url_for, flash
import requests
import base64
import json
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# URL API utama
API_BASE_URL = 'http://127.0.0.1:5000'

# Template HTML untuk upload
UPLOAD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Test Upload - Klasifikasi Hama Sawi</title>
    <style>
        body { 
            font-family: 'Segoe UI', Arial; 
            margin: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh;
            padding: 20px;
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: white; 
            padding: 40px; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
        }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
        .upload-area { 
            border: 3px dashed #4CAF50; 
            padding: 50px; 
            text-align: center; 
            margin: 20px 0; 
            border-radius: 15px; 
            background: #f8f9fa;
            transition: all 0.3s ease;
        }
        .upload-area:hover { 
            background: #e8f5e8; 
            border-color: #45a049; 
        }
        .btn { 
            background: #4CAF50; 
            color: white; 
            padding: 12px 30px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            transition: all 0.3s ease;
        }
        .btn:hover { 
            background: #45a049; 
            transform: translateY(-2px);
        }
        .result { 
            margin-top: 30px; 
            padding: 25px; 
            background: #f0f8f0; 
            border-left: 5px solid #4CAF50; 
            border-radius: 8px; 
        }
        .error { 
            background: #fff3cd; 
            border-left-color: #ffc107; 
            color: #856404;
        }
        
        /* Image comparison styles */
        .image-comparison {
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 25px 0;
            gap: 20px;
            flex-wrap: wrap;
        }
        .image-container {
            text-align: center;
            flex: 1;
            min-width: 250px;
        }
        .image-container img {
            max-width: 100%;
            max-height: 300px;
            border: 3px solid #4CAF50;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        .image-container img:hover {
            transform: scale(1.05);
        }
        .image-label {
            margin-top: 10px;
            font-weight: bold;
            color: #2c3e50;
            font-size: 14px;
        }
        .arrow {
            font-size: 30px;
            color: #4CAF50;
            margin: 0 15px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.6; }
            100% { opacity: 1; }
        }
        
        .feature-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 15px 0; 
            background: white;
        }
        .feature-table th, .feature-table td { 
            padding: 12px; 
            border: 1px solid #ddd; 
            text-align: left;
        }
        .feature-table th { 
            background: #4CAF50; 
            color: white; 
        }
        .probability-bar {
            background: #e0e0e0;
            height: 20px;
            border-radius: 10px;
            overflow: hidden;
            margin: 5px 0;
        }
        .probability-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.5s ease;
        }
        .nav-links {
            text-align: center;
            margin: 20px 0;
        }
        .nav-links a {
            margin: 0 15px;
            padding: 10px 20px;
            background: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: background 0.3s ease;
        }
        .nav-links a:hover {
            background: #0056b3;
        }
        .flash-message {
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
        }
        
        @media (max-width: 768px) {
            .image-comparison {
                flex-direction: column;
            }
            .arrow {
                transform: rotate(90deg);
                margin: 15px 0;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌿 Klasifikasi Serangan Hama Pada Tanaman Sawi Berdasarkan Citra Ciri Menggunakan Algoritma Naive Bayes</h1>
        
        <div class="nav-links">
            <a href="/view_logs">📊 Lihat Log Database</a>
            <a href="/view_stats">📈 Lihat Statistik</a>
            <a href="{{ API_BASE_URL }}/admin" target="_blank">🔧 API Admin</a>
        </div>
        
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="flash-message">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST" enctype="multipart/form-data">
            <div class="upload-area">
                <h3>📷 Pilih Gambar Tanaman Sawi yang di uji</h3>
                <input type="file" name="image" accept="image/*" required 
                       style="margin: 20px 0; padding: 10px; font-size: 16px;">
                <br>
                <button type="submit" class="btn">🔍 Analisis Gambar</button>
            </div>
        </form>
        
        {% if result %}
        <div class="result">
            <h2>🖼️ Perbandingan Gambar</h2>
            <div class="image-comparison">
                <div class="image-container">
                    <img src="data:image/jpeg;base64,{{ result.original_image }}" alt="Gambar Asli">
                    <div class="image-label">📸 Gambar Input</div>
                </div>
                
                <div class="arrow">➡️</div>
                
                <div class="image-container">
                    <img src="data:image/jpeg;base64,{{ result.processed_image }}" alt="Gambar Grayscale">
                    <div class="image-label">⚫ Hasil Preprocessing</div>
                </div>
            </div>
            
            <h2>🎯 Hasil Klasifikasi</h2>
            <p><strong>Prediksi:</strong> <span style="color: #2c3e50; font-size: 20px;">{{ result.prediction_label }}</span></p>
            <p><strong>Confidence:</strong> {{ "%.1f"|format(result.confidence * 100) }}%</p>
            <p><strong>Log ID:</strong> {{ result.log_id }}</p>
            <p><strong>Timestamp:</strong> {{ result.timestamp }}</p>
            
            <h3>📊 Probabilitas Semua Kelas</h3>
            {% for prob in result.probabilities %}
            <div style="margin: 10px 0;">
                <strong>{{ prob.class }}:</strong> {{ "%.1f"|format(prob.probability * 100) }}%
                <div class="probability-bar">
                    <div class="probability-fill" style="width: {{ prob.probability * 100 }}%;
                         background: {% if prob.probability == result.confidence %}#4CAF50{% else %}#2196F3{% endif %};"></div>
                </div>
            </div>
            {% endfor %}
            
            <h3>🔢 Fitur GLCM yang Diekstrak</h3>
            <table class="feature-table">
                <tr><th>Fitur</th><th>Nilai</th></tr>
                <tr><td>Contrast</td><td>{{ "%.6f"|format(result.glcm_features.contrast) }}</td></tr>
                <tr><td>Correlation</td><td>{{ "%.6f"|format(result.glcm_features.correlation) }}</td></tr>
                <tr><td>Energy</td><td>{{ "%.6f"|format(result.glcm_features.energy) }}</td></tr>
                <tr><td>Homogeneity</td><td>{{ "%.6f"|format(result.glcm_features.homogeneity) }}</td></tr>
            </table>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

LOGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Database Logs - Klasifikasi Hama Sawi</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; border: 1px solid #ddd; text-align: left; }
        th { background: #4CAF50; color: white; }
        tr:nth-child(even) { background: #f9f9f9; }
        .back-btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }
        .confidence { font-weight: bold; }
        .high-confidence { color: #27ae60; }
        .medium-confidence { color: #f39c12; }
        .low-confidence { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Database Logs - Prediksi Hama Sawi</h1>
        <a href="/" class="back-btn">⬅ Kembali ke Upload</a>
        
        <h3>Total Prediksi: {{ logs|length }}</h3>
        
        {% if logs %}
        <table>
            <tr>
                <th>No</th>
                <th>Timestamp</th>
                <th>Prediksi</th>
                <th>Confidence</th>
                <th>Contrast</th>
                <th>Correlation</th>
                <th>Energy</th>
                <th>Homogeneity</th>
            </tr>
            {% for log in logs %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ log.timestamp[:19] }}</td>
                <td><strong>{{ log.prediction_label }}</strong></td>
                <td class="confidence {% if log.confidence > 0.8 %}high-confidence{% elif log.confidence > 0.6 %}medium-confidence{% else %}low-confidence{% endif %}">
                    {{ "%.1f"|format(log.confidence * 100) }}%
                </td>
                <td>{{ "%.4f"|format(log.glcm_features.contrast) }}</td>
                <td>{{ "%.4f"|format(log.glcm_features.correlation) }}</td>
                <td>{{ "%.4f"|format(log.glcm_features.energy) }}</td>
                <td>{{ "%.4f"|format(log.glcm_features.homogeneity) }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>Belum ada prediksi. Silakan upload gambar terlebih dahulu!</p>
        {% endif %}
    </div>
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def test_upload():
    """Halaman utama untuk test upload gambar"""
    if request.method == "POST":
        try:
            # Cek apakah ada file yang diupload
            if 'image' not in request.files:
                flash('Tidak ada file yang dipilih!')
                return redirect(request.url)
            
            file = request.files['image']
            if file.filename == '':
                flash('Tidak ada file yang dipilih!')
                return redirect(request.url)
            
            # Konversi gambar ke base64
            image_data = file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Kirim ke API predict
            response = requests.post(
                f'{API_BASE_URL}/predict',
                headers={'Content-Type': 'application/json'},
                json={'image_base64': base64_image},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Tambahkan gambar original untuk ditampilkan
                result['original_image'] = base64_image
                flash(f'✅ Prediksi berhasil! Hasil: {result["prediction_label"]} (Confidence: {result["confidence"]*100:.1f}%)')
                return render_template_string(UPLOAD_TEMPLATE, result=result, API_BASE_URL=API_BASE_URL)
            else:
                error_msg = response.json().get('error', 'Unknown error')
                flash(f'❌ Error dari API: {error_msg}')
                
        except requests.exceptions.ConnectionError:
            flash('❌ Tidak dapat terhubung ke API utama! Pastikan app.py sudah running di port 5000')
        except Exception as e:
            flash(f'❌ Error: {str(e)}')
    
    return render_template_string(UPLOAD_TEMPLATE, result=None, API_BASE_URL=API_BASE_URL)

@app.route("/view_logs")
def view_logs():
    """Lihat semua log dari database via API"""
    try:
        response = requests.get(f'{API_BASE_URL}/logs', timeout=10)
        if response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            return render_template_string(LOGS_TEMPLATE, logs=logs)
        else:
            return f"Error mengambil logs: {response.status_code}"
    except Exception as e:
        return f"Error koneksi ke API: {str(e)}"

@app.route("/view_stats")
def view_stats():
    """Lihat statistik dari database via API"""
    try:
        response = requests.get(f'{API_BASE_URL}/stats', timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            stats_html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Statistik - Klasifikasi Hama Sawi</title>
                <style>
                    body {{ font-family: Arial; margin: 20px; background: #f5f5f5; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                    .stat-box {{ background: #4CAF50; color: white; padding: 20px; border-radius: 8px; margin: 15px 0; text-align: center; }}
                    .class-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #4CAF50; }}
                    .back-btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📈 Statistik Prediksi</h1>
                    <a href="/" class="back-btn">⬅ Kembali</a>
                    
                    <div class="stat-box">
                        <h2>{data['total_predictions']}</h2>
                        <p>Total Prediksi</p>
                    </div>
                    
                    <div class="stat-box">
                        <h2>{data['average_confidence']*100:.1f}%</h2>
                        <p>Rata-rata Confidence</p>
                    </div>
                    
                    <h3>📊 Distribusi Kelas:</h3>
            '''
            
            for class_data in data['class_distribution']:
                stats_html += f'''
                    <div class="class-item">
                        <strong>{class_data['class']}</strong>: {class_data['count']} prediksi ({class_data['percentage']:.1f}%)
                    </div>
                '''
            
            stats_html += '''
                </div>
            </body>
            </html>
            '''
            
            return stats_html
        else:
            return f"Error mengambil stats: {response.status_code}"
    except Exception as e:
        return f"Error koneksi ke API: {str(e)}"

@app.route("/test_api")
def test_api():
    """Test koneksi ke API utama"""
    try:
        response = requests.get(f'{API_BASE_URL}/', timeout=5)
        if response.status_code == 200:
            return f"✅ API Connected: {response.text}"
        else:
            return f"❌ API Error: {response.status_code}"
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

if __name__ == "__main__":
    print("🚀 Starting Test Upload Server...")
    print("📍 Access: http://127.0.0.1:8000")
    print("⚠️  Make sure main API is running on port 5000!")
    app.run(debug=True, host='0.0.0.0', port=8000)