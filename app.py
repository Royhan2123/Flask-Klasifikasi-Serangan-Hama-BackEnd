from flask import Flask, request, jsonify
import joblib
import numpy as np
from PIL import Image
from skimage.feature import graycomatrix, graycoprops
from skimage.color import rgb2gray
from skimage.io import imread
import cv2
import io
import base64
import sqlite3
from datetime import datetime
import uuid
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

app = Flask(__name__)

# ====================================
# 1. INISIALISASI DATABASE
# ====================================
def init_database():
    conn = sqlite3.connect('prediction_logs.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            prediction_class TEXT,
            prediction_label TEXT,
            confidence REAL,
            contrast REAL,
            correlation REAL,
            energy REAL,
            homogeneity REAL,
            image_name TEXT,
            all_probabilities TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Fungsi untuk save log ke database
def save_prediction_log(prediction_data, image_name=None):
    conn = sqlite3.connect('prediction_logs.db')
    cursor = conn.cursor()
    
    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO predictions 
        (id, timestamp, prediction_class, prediction_label, confidence, 
         contrast, correlation, energy, homogeneity, image_name, all_probabilities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        log_id,
        timestamp,
        prediction_data['prediction'],
        prediction_data['prediction_label'],
        prediction_data['confidence'],
        prediction_data['glcm_features']['contrast'],
        prediction_data['glcm_features']['correlation'],
        prediction_data['glcm_features']['energy'],
        prediction_data['glcm_features']['homogeneity'],
        image_name,
        str(prediction_data['probabilities'])
    ))
    
    conn.commit()
    conn.close()
    
    return log_id

# ====================================
# 2. INISIALISASI
# ====================================
# Init database dulu
init_database()

# Load model
model = joblib.load("models/naive_bayes_glcm.pkl")

# ====================================
# 3. FUNGSI EKSTRAKSI GLCM
# ====================================
def extract_glcm_features(image_array):
    """
    Ekstrak fitur GLCM dari array gambar (sama seperti di Colab)
    """
    # Konversi ke grayscale
    if len(image_array.shape) == 3:
        img_gray = rgb2gray(image_array)
    else:
        img_gray = image_array
    
    # Konversi ke uint8 (0-255)
    img_gray = (img_gray * 255).astype('uint8')
    
    # Hitung GLCM (sama seperti di Colab Anda)
    glcm = graycomatrix(img_gray, 
                        distances=[1],
                        angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                        symmetric=True, 
                        normed=True)
    
    # Ekstrak properti GLCM
    contrast = graycoprops(glcm, 'contrast').mean()
    correlation = graycoprops(glcm, 'correlation').mean()
    energy = graycoprops(glcm, 'energy').mean()
    homogeneity = graycoprops(glcm, 'homogeneity').mean()
    
    return [contrast, correlation, energy, homogeneity], img_gray

def create_probability_chart(probabilities, class_labels):
    """
    Buat grafik probabilitas seperti di gambar yang Anda tunjukkan
    """
    plt.figure(figsize=(10, 6))
    
    # Extract probabilities
    probs = [p['probability'] for p in probabilities]
    classes = [p['class'] for p in probabilities]
    
    # Create the plot
    plt.plot(classes, probs, 'b-', linewidth=3, marker='o', markersize=10, 
             markerfacecolor='red', markeredgecolor='red', markeredgewidth=2)
    
    # Styling
    plt.title('Probabilitas Klasifikasi (GaussianNB + GLCM)', fontsize=16, fontweight='bold')
    plt.xlabel('Kelas', fontsize=12)
    plt.ylabel('Probabilitas', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.ylim(-0.2, 1.0)
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45, ha='right')
    
    # Add value labels on points
    for i, (cls, prob) in enumerate(zip(classes, probs)):
        plt.annotate(f'{prob:.3f}', (i, prob), textcoords="offset points", 
                    xytext=(0,10), ha='center', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    # Save to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return chart_base64

# ====================================
# 4. ROUTES/ENDPOINTS
# ====================================

@app.route("/")
def home():
    return "API Naive Bayes untuk klasifikasi hama sawi sudah jalan 🚀"

@app.route("/admin")
def admin():
    # Halaman admin sederhana
    return '''
    <h2>🔧 Admin Panel - Klasifikasi Hama Sawi</h2>
    <p><a href="/logs" target="_blank">📊 View Logs</a></p>
    <p><a href="/stats" target="_blank">📈 View Stats</a></p>
    <p><a href="/test" target="_blank">🧪 Test Model</a></p>
    '''

@app.route("/predict", methods=["POST"])
def predict():
    try:
        # Cek apakah ada file gambar yang diupload
        if 'image' in request.files:
            # Cara 1: Upload file langsung
            file = request.files['image']
            image = Image.open(file.stream)
            image_array = np.array(image)
            
        elif request.content_type == 'application/json':
            data = request.get_json(force=True)
            
            if 'image_base64' in data:
                # Cara 2: Gambar dalam format base64
                image_data = base64.b64decode(data['image_base64'])
                image = Image.open(io.BytesIO(image_data))
                image_array = np.array(image)
                
            elif 'features' in data:
                # Cara 3: Fitur manual (backward compatibility)
                features = np.array(data["features"]).reshape(1, -1)
                prediction = model.predict(features)
                return jsonify({
                    "prediction": prediction.tolist(),
                    "status": "success"
                })
            else:
                return jsonify({
                    "error": "No image_base64 or features found",
                    "status": "error"
                }), 400
        else:
            return jsonify({
                "error": "Unsupported content type",
                "status": "error"
            }), 400
        
        # Ekstrak fitur GLCM dari gambar DAN dapatkan gambar grayscale
        glcm_features, img_gray = extract_glcm_features(image_array)
        features = np.array(glcm_features).reshape(1, -1)
        
        # Konversi gambar grayscale ke base64
        gray_pil = Image.fromarray(img_gray)
        gray_buffer = io.BytesIO()
        gray_pil.save(gray_buffer, format='JPEG')
        gray_base64 = base64.b64encode(gray_buffer.getvalue()).decode('utf-8')
        
        # Prediksi
        prediction = model.predict(features)[0]
        probabilities = model.predict_proba(features)[0]
        
        # Mapping label (sesuaikan dengan dataset Anda)
        class_labels = model.classes_  # ["sehat", "hama_keong", "hama_kutu", "hama_ulat"]
        
        # Cari kelas dengan probabilitas tertinggi
        max_class_idx = np.argmax(probabilities)
        max_class = class_labels[max_class_idx]
        max_proba = np.max(probabilities)
        
        # Buat data untuk grafik probabilitas
        probability_data = []
        for i, class_name in enumerate(class_labels):
            probability_data.append({
                "class": class_name,
                "probability": float(probabilities[i])
            })
        
        # Buat grafik probabilitas
        chart_base64 = create_probability_chart(probability_data, class_labels)
        
        # Siapkan data response
        response_data = {
            "prediction": prediction,
            "prediction_label": max_class,
            "confidence": float(max_proba),
            "probabilities": probability_data,
            "glcm_features": {
                "contrast": float(glcm_features[0]),
                "correlation": float(glcm_features[1]), 
                "energy": float(glcm_features[2]),
                "homogeneity": float(glcm_features[3])
            },
            "processed_image": gray_base64,  # TAMBAHAN: Gambar grayscale
            "probability_chart": chart_base64,  # TAMBAHAN: Grafik probabilitas
            "status": "success",
            "message": "Klasifikasi berhasil!"
        }
        
        # Save log ke database
        image_name = f"prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        log_id = save_prediction_log(response_data, image_name)
        
        # Tambahkan log_id ke response
        response_data["log_id"] = log_id
        response_data["timestamp"] = datetime.now().isoformat()
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/logs", methods=["GET"])
def get_logs():
    """Endpoint untuk melihat semua log prediksi"""
    try:
        conn = sqlite3.connect('prediction_logs.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, prediction_class, prediction_label, 
                   confidence, contrast, correlation, energy, homogeneity, image_name
            FROM predictions 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')
        
        logs = cursor.fetchall()
        conn.close()
        
        # Format hasil
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": log[0],
                "timestamp": log[1],
                "prediction_class": log[2],
                "prediction_label": log[3],
                "confidence": log[4],
                "glcm_features": {
                    "contrast": log[5],
                    "correlation": log[6],
                    "energy": log[7],
                    "homogeneity": log[8]
                },
                "image_name": log[9]
            })
        
        return jsonify({
            "logs": formatted_logs,
            "total_predictions": len(formatted_logs),
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    """Endpoint untuk statistik prediksi"""
    try:
        conn = sqlite3.connect('prediction_logs.db')
        cursor = conn.cursor()
        
        # Hitung jumlah per kelas
        cursor.execute('''
            SELECT prediction_label, COUNT(*) as count
            FROM predictions 
            GROUP BY prediction_label
            ORDER BY count DESC
        ''')
        
        class_counts = cursor.fetchall()
        
        # Hitung total
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total = cursor.fetchone()[0]
        
        # Rata-rata confidence
        cursor.execute('SELECT AVG(confidence) FROM predictions')
        avg_confidence = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "total_predictions": total,
            "average_confidence": float(avg_confidence) if avg_confidence else 0,
            "class_distribution": [
                {"class": row[0], "count": row[1], "percentage": (row[1]/total)*100 if total > 0 else 0}
                for row in class_counts
            ],
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/test", methods=["GET"])
def test():
    """Endpoint untuk test apakah model loaded dengan benar"""
    try:
        # Info tentang model
        return jsonify({
            "model_classes": model.classes_.tolist(),
            "model_type": str(type(model)),
            "status": "Model loaded successfully"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "Model load failed"
        }), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)