# app.py

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
# Import the modified function
from timetable_logic import generate_multiple_timetables_api
import os
import json
import uuid

# ---------------------------------------
# ✅ Flask App Configuration
# ---------------------------------------
app = Flask(
    __name__,
    static_folder='frontend',       # Folder containing CSS, JS, etc.
    template_folder='frontend'      # Folder containing index.html
)

# ✅ Enable Cross-Origin Requests (for frontend-backend connection)
CORS(app)

# Ensure the PDF directory exists
if not os.path.exists("timetables_pdf"):
    os.makedirs("timetables_pdf")

# ---------------------------------------
# ✅ Routes
# ---------------------------------------

@app.route('/')
def serve_frontend():
    """Serve the main frontend HTML page."""
    return render_template('index.html')

@app.route('/api/generate-timetables', methods=['POST'])
def generate_api():
    """Handle timetable generation requests from the frontend."""
    try:
        # Get JSON data from frontend
        data = request.get_json()
        print("✅ Received data from frontend:", data)

        # Generate a unique session ID for this generation
        session_id = str(uuid.uuid4())[:8]
        
        # Generate timetables using your logic module
        result = generate_multiple_timetables_api(data, session_id)
        
        # If timetables generated successfully
        if result and 'timetables' in result:
            return jsonify({
                'success': True, 
                'timetables': result['timetables'],
                'pdf_files': result['pdf_files'],
                'session_id': session_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not generate a feasible timetable. Try adjusting constraints.'
            }), 400

    except Exception as e:
        print("❌ An error occurred:", e)
        return jsonify({
            'success': False,
            'message': f'An internal server error occurred: {str(e)}'
        }), 500

@app.route('/api/download-pdf/<session_id>/<filename>')
def download_pdf(session_id, filename):
    """Serve generated PDF files for download"""
    try:
        pdf_path = os.path.join("timetables_pdf", session_id, filename)
        if os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True)
        else:
            return jsonify({'success': False, 'message': 'PDF not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ---------------------------------------
# ✅ Main Entry Point
# ---------------------------------------
if __name__ == '__main__':
    # Run Flask App
    app.run(debug=True)
