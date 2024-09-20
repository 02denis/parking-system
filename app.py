import base64
from io import BytesIO
from flask import Flask, render_template, request, jsonify
import numpy as np
from pymongo import MongoClient
from bson import ObjectId
from flask_cors import CORS
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit
import pytz
import qrcode
import cv2
import pytesseract

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
CORS(app, support_credentials=True)

client = MongoClient('mongodb://localhost:27017/')
db = client['parking-system']
collectionVehicle = db['vehicle']
collectionParkingLot = db['parkinglot']
collectionPayment = db['payment']
collectionCamera = db['camera']

@app.route('/vehicles', methods=['GET'])
def get_vehicles():
    result = collectionVehicle.find({})
    vehicles = []
    for doc in result:
        doc['_id'] = str(doc['_id'])
        vehicles.append(doc)
    return jsonify(vehicles)

@app.route('/vehicles', methods=['POST'])
def add_vehicle():
    current_time = datetime.now(pytz.utc).isoformat()
    data = request.get_json()
    if data:
        data['timeIn'] = current_time
        collectionVehicle.insert_one(data)
        socketio.emit('new_plate', {'plateNumber': data['plateNumber']})
        return jsonify({"message": "Vehicle added successfully"}), 201
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/vehicles/<string:id>', methods=['PUT'])
def update_vehicle(id):
    data = request.get_json()
    if data:
        collectionVehicle.update_one({'_id': ObjectId(id)}, {'$set': data})
        return jsonify({"message": "Vehicle updated successfully"})
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/vehicles/<string:id>', methods=['DELETE'])
def delete_vehicle(id):
    collectionVehicle.delete_one({'_id': ObjectId(id)})
    return jsonify({"message": "Vehicle deleted successfully"})

@app.route('/payment', methods=['GET'])
def get_payments():
    result = collectionPayment.find({})
    payments = []
    for doc in result:
        doc['_id'] = str(doc['_id'])
        payments.append(doc)
    return jsonify(payments)

@app.route('/payment', methods=['POST'])
def add_payment():
    data = request.get_json()
    if data:
        collectionPayment.insert_one(data)
        return jsonify({"message": "Payment added successfully"}), 201
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/payment/<string:id>', methods=['PUT'])
def update_payment(id):
    data = request.get_json()
    if data:
        collectionPayment.update_one({'_id': ObjectId(id)}, {'$set': data})
        return jsonify({"message": "Payment updated successfully"})
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/payment/<string:id>', methods=['DELETE'])
def delete_payment(id):
    collectionPayment.delete_one({'_id': ObjectId(id)})
    return jsonify({"message": "Payment deleted successfully"})

@app.route('/camera', methods=['GET'])
def get_cameras():
    result = collectionCamera.find({})
    cameras = []
    for doc in result:
        doc['_id'] = str(doc['_id'])
        cameras.append(doc)
    return jsonify(cameras)

@app.route('/camera', methods=['POST'])
def add_camera():
    data = request.get_json()
    if data:
        collectionCamera.insert_one(data)
        return jsonify({"message": "Camera added successfully"}), 201
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/camera/<string:id>', methods=['PUT'])
def update_camera(id):
    data = request.get_json()
    if data:
        collectionCamera.update_one({'_id': ObjectId(id)}, {'$set': data})
        return jsonify({"message": "Camera updated successfully"})
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/camera/<string:id>', methods=['DELETE'])
def delete_camera(id):
    collectionCamera.delete_one({'_id': ObjectId(id)})
    return jsonify({"message": "Camera deleted successfully"})

@app.route('/parking-lot', methods=['GET'])
def get_parking_lots():
    result = collectionParkingLot.find({})
    parkingLot = []
    for doc in result:
        doc['_id'] = str(doc['_id'])
        parkingLot.append(doc)
    return jsonify(parkingLot)

@app.route('/parking-lot', methods=['POST'])
def add_parking_lot():
    data = request.get_json()
    if data:
        collectionParkingLot.insert_one(data)
        return jsonify({"message": "Parking lot added successfully"}), 201
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/parking-lot/<string:id>', methods=['PUT'])
def update_parking_lot(id):
    data = request.get_json()
    if data:
        collectionParkingLot.update_one({'_id': ObjectId(id)}, {'$set': data})
        return jsonify({"message": "Parking lot updated successfully"})
    else:
        return jsonify({"error": "No data provided"}), 400

@app.route('/parking-lot/<string:id>', methods=['DELETE'])
def delete_parking_lot(id):
    collectionParkingLot.delete_one({'_id': ObjectId(id)})
    return jsonify({"message": "Parking lot deleted successfully"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/qr-codes')
def qr():
    return render_template('qr.html')

@app.route('/all-vehicles')
def all_vehicles():
    return render_template('vehicles.html')

@app.route('/enter')
def enter_page():
    return render_template('enter.html')

@app.route('/payments')
def payments_page():
    return render_template('payments.html')

@app.route('/parking-lots')
def parking_lots_page():
    return render_template('parking-lots.html')

@app.route('/exit', methods=['GET'])
def exit_page():
    return render_template('exit.html')

@app.route('/exit', methods=['POST'])
def register_exit():
    data = request.get_json()
    if data and 'plateNumber' in data:
        plate_number = data['plateNumber']

        vehicle = collectionVehicle.find_one({'plateNumber': plate_number}, sort=[('timeIn', -1)])
        if not vehicle:
            return jsonify({"error": "Vehicle not found"}), 404

        current_time = datetime.now(pytz.utc).isoformat()

        time_in = datetime.fromisoformat(vehicle['timeIn'])
        time_out = datetime.fromisoformat(current_time)
        duration = time_out - time_in
        print(duration)
        hours_parked = duration.total_seconds() // 3600
        additional_hours = max(0, hours_parked - 1)
        to_pay = additional_hours * 25
        business_id = "sb-gx4747430506731@business.example.com"

        collectionVehicle.update_one(
            {'_id': vehicle['_id']},
            {'$set': {'timeOut': current_time, 'toPay': to_pay}}
        )

        if to_pay > 0 and not vehicle.get('paid', False):
            pay_url = f"https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_xclick&business={business_id}&item_name=Parking+Fee&amount={to_pay}&currency_code=USD"
            qr_text = pay_url
        else:
            qr_text = f'Plate number: {plate_number}'

        qr_text += f'\nExit Time: {current_time}'
        

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_text)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        qr_code_url = f"data:image/png;base64,{img_str}"
        socketio.emit('exit_plate', {
            'plateNumber': plate_number,
            'qrCodeUrl': qr_code_url,
            'toPay': to_pay,
            'paid': vehicle.get('paid', False),
            'exitTime': current_time
        })
        return jsonify({"message": "Exit registered successfully", "exitTime": current_time, "toPay": to_pay}), 200
    else:
        return jsonify({"error": "No plate number provided"}), 400
    

@socketio.on('video_frame')
def handle_video_frame(data):
    plat_detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_russian_plate_number.xml")
    frame_data = data.split(",")[1]
    frame = np.fromstring(base64.b64decode(frame_data), np.uint8)
    img = cv2.imdecode(frame, cv2.IMREAD_COLOR)

    plates = plat_detector.detectMultiScale(img, scaleFactor=1.2, minNeighbors=5, minSize=(25, 25))

    plate_text = ""
    for (x, y, w, h) in plates:
        plate_img = img[y:y+h, x:x+w]
        
        gray_plate = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        _, thresh_plate = cv2.threshold(gray_plate, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        plate_text = pytesseract.image_to_string(thresh_plate, config='--psm 9')
        print(plate_text)
        
        cv2.putText(img, text=plate_text, org=(x, y-5), fontFace=cv2.FONT_HERSHEY_SIMPLEX, 
                    color=(0, 0, 255), thickness=1, fontScale=0.6)
        cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 2)

    emit('new_plate', {'plateNumber': "AR16HLN"})
    
if __name__ == '__main__':
    socketio.run(app, debug=True)
