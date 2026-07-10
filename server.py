"""
AI Server for Vua Thoat Hiem.
Provides /collect, /predict, and /train endpoints.
Usage: python server.py
"""
from flask import Flask, request, jsonify
from train import GameDataCollector, GameAI
import threading

app = Flask(__name__)
collector = GameDataCollector()
ai = GameAI()


@app.route('/collect', methods=['POST'])
def collect():
    """Receive websocket message and store in dataset."""
    try:
        data = request.json
        if data:
            collector.process_websocket_message(data)
            return jsonify({"status": "ok", "msg": "Collected"})
        return jsonify({"status": "error", "msg": "No data"}), 400
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


@app.route('/predict', methods=['GET'])
def predict():
    """Predict the safest room based on current round data and history."""
    try:
        room_data = {}
        for rid in range(1, 9):
            user_cnt = request.args.get(f'r{rid}u', 0, type=int)
            total_bet = request.args.get(f'r{rid}b', 0, type=float)
            room_data[rid] = {
                'user_cnt': user_cnt,
                'total_bet': total_bet
            }

        predictions = ai.predict_room(room_data, collector.data, seq_length=ai.seq_length)

        if predictions:
            safest_room = predictions[0]
            return jsonify({
                "code": 0,
                "msg": "success",
                "safest_room": {
                    "room_id": safest_room['room_id'],
                    "safe_probability": safest_room['safe_probability']
                },
                "all_predictions": predictions
            })
        else:
            return jsonify({"code": -1, "msg": "Model not ready"}), 400

    except Exception as e:
        return jsonify({"code": -1, "msg": str(e)}), 500


@app.route('/train', methods=['POST'])
def train():
    """Retrain the model on all collected data (runs in background)."""
    seq_length = request.args.get('seq_length', 10, type=int)

    def background_train():
        df = collector.get_dataframe()
        if df is not None:
            ai.train(df, seq_length=seq_length)

    thread = threading.Thread(target=background_train)
    thread.start()

    return jsonify({"status": "ok", "msg": f"Training started (seq_length={seq_length})"})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
