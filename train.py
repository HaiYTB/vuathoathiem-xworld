import os
import json
import time
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import joblib
import warnings
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
warnings.filterwarnings('ignore')


class GameDataCollector:
    """
    Collect and store game data from websocket messages.

    :param data_file: Path to JSON file for storing data
    :type data_file: str
    """
    def __init__(self, data_file="game_data.json"):
        self.data_file = data_file
        self.data = []
        self.current_round = {}
        self.stats = {
            'total_rounds': 0,
            'rooms_killed': {i: 0 for i in range(1, 9)},
            'collection_start': datetime.now().isoformat()
        }
        self.load_data()

    def load_data(self):
        """Load previously collected data from JSON file."""
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            if isinstance(loaded, dict) and 'data' in loaded:
                self.data = loaded.get('data', [])
                loaded_stats = loaded.get('stats', {})

                if 'rooms_killed' in loaded_stats:
                    rooms_killed = {}
                    for key, value in loaded_stats['rooms_killed'].items():
                        try:
                            rooms_killed[int(key)] = int(value)
                        except:
                            pass
                    loaded_stats['rooms_killed'] = rooms_killed

                self.stats['total_rounds'] = loaded_stats.get('total_rounds', len(self.data))
                self.stats['rooms_killed'].update(loaded_stats.get('rooms_killed', {}))
                self.stats['collection_start'] = loaded_stats.get('collection_start', datetime.now().isoformat())

            elif isinstance(loaded, list):
                self.data = loaded
                self._recalculate_stats()

            print(f"[DATA] Loaded {len(self.data)} records from {self.data_file}")

        except Exception as e:
            print(f"[ERROR] Failed to load data: {e}")
            self.data = []

    def _recalculate_stats(self):
        """Recalculate stats from existing data."""
        self.stats['total_rounds'] = len(self.data)
        self.stats['rooms_killed'] = {i: 0 for i in range(1, 9)}

        for record in self.data:
            killed_room = record.get('killed_room')
            if killed_room:
                try:
                    killed_room = int(killed_room)
                    if 1 <= killed_room <= 8:
                        self.stats['rooms_killed'][killed_room] += 1
                except:
                    pass

    def save_data(self):
        """Save collected data to JSON file."""
        try:
            clean_stats = {
                'total_rounds': self.stats['total_rounds'],
                'rooms_killed': {int(k): int(v) for k, v in self.stats['rooms_killed'].items()},
                'collection_start': self.stats.get('collection_start', datetime.now().isoformat())
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'data': self.data,
                    'stats': clean_stats,
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[ERROR] Failed to save data: {e}")

    def process_websocket_message(self, message):
        """
        Process a websocket message and collect game data.

        :param message: Raw websocket message (str or dict)
        :type message: str/dict
        """
        try:
            data = json.loads(message) if isinstance(message, str) else message
            msg_type = data.get("msg_type")

            if msg_type == "notify_enter_game":
                self.current_round = {
                    "issue_id": data.get("issue_id"),
                    "asset_type": data.get("asset_type"),
                    "timestamp": time.time(),
                    "rooms": {},
                    "last_killed_room": data.get("last_killed_room_id")
                }
                if "room_stat" in data:
                    for room in data["room_stat"]:
                        room_id = int(room["room_id"])
                        self.current_round["rooms"][room_id] = {
                            "user_cnt": room["user_cnt"],
                            "total_bet": room["total_bet_amount"],
                            "last_bet_time": room.get("last_bet_time", 0)
                        }

            elif msg_type == "notify_issue_stat":
                if "rooms" in data and self.current_round and "rooms" in self.current_round:
                    for room in data["rooms"]:
                        room_id = int(room["room_id"])
                        self.current_round["rooms"][room_id] = {
                            "user_cnt": room["user_cnt"],
                            "total_bet": room["total_bet_amount"]
                        }

            elif msg_type == "notify_result":
                if self.current_round:
                    killed_room = int(data.get("killed_room"))
                    self.current_round["killed_room"] = killed_room
                    self.current_round["result_timestamp"] = time.time()

                    if "rooms" in data:
                        for room in data["rooms"]:
                            room_id = int(room["room_id"])
                            if room_id in self.current_round["rooms"]:
                                self.current_round["rooms"][room_id].update({
                                    "final_user_cnt": room["user_cnt"],
                                    "final_total_bet": room["total_bet_amount"]
                                })

                    # Deduplicate by issue_id
                    current_issue = self.current_round.get('issue_id')
                    is_duplicate = any(d.get('issue_id') == current_issue for d in self.data)

                    if not is_duplicate:
                        self.data.append(self.current_round.copy())
                        self.stats['total_rounds'] += 1
                        self.stats['rooms_killed'][killed_room] += 1
                        self.save_data()
                        print(f"[COLLECT] Issue {current_issue} - Room {killed_room} killed (Total: {len(self.data)})")

                    self.current_round = {}

        except Exception as e:
            print(f"[ERROR] process_websocket_message: {e}")

    def get_dataframe(self):
        """
        Convert collected data to a pandas DataFrame.
        Each round becomes one row with all 8 rooms' data as columns.

        :return: DataFrame or None
        :rtype: pd.DataFrame/None
        """
        if not self.data:
            print("[WARNING] No data to convert")
            return None

        records = []
        skipped = 0

        for round_data in self.data:
            if "killed_room" not in round_data or "rooms" not in round_data or not round_data["rooms"]:
                skipped += 1
                continue

            rooms_data = round_data["rooms"]
            record = {
                "issue_id": round_data.get("issue_id", 0),
                "last_killed_room": int(round_data.get("last_killed_room", 0)) if round_data.get("last_killed_room") else 0,
                "killed_room": int(round_data["killed_room"])
            }

            for room_id in range(1, 9):
                if isinstance(rooms_data, dict):
                    room_info = rooms_data.get(room_id) or rooms_data.get(str(room_id)) or {}
                else:
                    room_info = {}

                record[f"room_{room_id}_user"] = int(room_info.get("final_user_cnt", room_info.get("user_cnt", 0)))
                record[f"room_{room_id}_bet"] = float(room_info.get("final_total_bet", room_info.get("total_bet", 0)))

            records.append(record)

        if skipped > 0:
            print(f"[WARNING] Skipped {skipped} invalid records")

        if not records:
            return None

        df = pd.DataFrame(records)
        df = df.sort_values(by="issue_id")
        print(f"[DATA] Created DataFrame with {len(df)} rounds")
        return df


class EscapeRoomLSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super(EscapeRoomLSTM, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.1 if num_layers > 1 else 0)
        self.dropout = nn.Dropout(0.1)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out[:, -1, :])
        out = self.fc(out)
        return out


class GameAI:
    INPUT_SIZE = 17   # 8 rooms * 2 features + last_killed_room
    HIDDEN_SIZE = 64
    NUM_LAYERS = 2
    OUTPUT_SIZE = 8

    def __init__(self, model_path="lstm_model.pth", scaler_path="scaler.pkl"):
        self.model_path = model_path
        self.scaler_path = scaler_path

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = EscapeRoomLSTM(self.INPUT_SIZE, self.HIDDEN_SIZE, self.NUM_LAYERS, self.OUTPUT_SIZE).to(self.device)
        self.scaler = None
        self.feature_names = []
        self.training_history = []
        self.seq_length = 10

        self.load_model()

    def prepare_sequences(self, df, seq_length):
        """
        Convert DataFrame into sequences for LSTM training.

        :param df: Input DataFrame (1 row per round)
        :type df: pd.DataFrame
        :param seq_length: Number of past rounds to use as context
        :type seq_length: int
        :return: (X_sequences, y_labels) or (None, None)
        :rtype: tuple
        """
        feature_cols = []
        for i in range(1, 9):
            feature_cols.extend([f"room_{i}_user", f"room_{i}_bet"])
        feature_cols.append("last_killed_room")
        self.feature_names = feature_cols

        X_raw = df[feature_cols].values
        y_raw = df['killed_room'].values - 1  # 0-indexed

        if self.scaler is None:
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X_raw)
        else:
            X_scaled = self.scaler.transform(X_raw)

        if len(X_scaled) < seq_length:
            return None, None

        X_seq, y_seq = [], []
        for i in range(len(X_scaled) - seq_length + 1):
            X_seq.append(X_scaled[i:i + seq_length])
            y_seq.append(y_raw[i + seq_length - 1])

        return np.array(X_seq), np.array(y_seq)

    def train(self, df, seq_length=10):
        """
        Train the LSTM model on the entire dataset.

        :param df: Training data (1 row per round)
        :type df: pd.DataFrame
        :param seq_length: Sequence length for LSTM input
        :type seq_length: int
        """
        print(f"\n{'='*50}")
        print(f"  TRAINING LSTM (seq_length={seq_length})")
        print(f"{'='*50}\n")

        if len(df) <= seq_length:
            print(f"[ERROR] Need more than {seq_length} rounds. Currently have {len(df)}.")
            return

        self.seq_length = seq_length
        self.scaler = None
        X, y = self.prepare_sequences(df, seq_length)

        if X is None or len(X) == 0:
            print("[ERROR] Not enough data to create sequences")
            return

        print(f"[INFO] Total samples: {len(X)} (Split: 70% Train, 20% Valid, 10% Test)")

        X_tensor = torch.tensor(X, dtype=torch.float32)
        y_tensor = torch.tensor(y, dtype=torch.long)

        # Calculate split sizes: 70% train, 20% valid, 10% test (CHRONOLOGICAL SPLIT)
        total_size = len(X_tensor)
        train_size = int(0.7 * total_size)
        valid_size = int(0.2 * total_size)
        test_size = total_size - train_size - valid_size
        
        if train_size == 0 or valid_size == 0 or test_size == 0:
            print("[ERROR] Dataset quá nhỏ để chia 70/20/10. Cần thu thập thêm dữ liệu!")
            return
            
        train_dataset = TensorDataset(X_tensor[:train_size], y_tensor[:train_size])
        valid_dataset = TensorDataset(X_tensor[train_size:train_size+valid_size], y_tensor[train_size:train_size+valid_size])
        test_dataset = TensorDataset(X_tensor[train_size+valid_size:], y_tensor[train_size+valid_size:])

        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        valid_loader = DataLoader(valid_dataset, batch_size=32, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001, weight_decay=1e-5)

        epochs = 300
        best_val_acc = 0.0
        best_model_state = None
        patience = 100
        patience_counter = 0

        for epoch in range(epochs):
            # Training Phase
            self.model.train()
            train_loss = 0.0
            correct_train = 0
            total_train = 0

            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)

                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

                train_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total_train += batch_y.size(0)
                correct_train += (predicted == batch_y).sum().item()

            train_acc = correct_train / total_train
            
            # Validation Phase
            self.model.eval()
            val_loss = 0.0
            correct_val = 0
            total_val = 0
            
            with torch.no_grad():
                for batch_X, batch_y in valid_loader:
                    batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    val_loss += loss.item()
                    _, predicted = torch.max(outputs.data, 1)
                    total_val += batch_y.size(0)
                    correct_val += (predicted == batch_y).sum().item()
                    
            val_acc = correct_val / total_val
            
            # Save best model based on validation
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_model_state = self.model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
                print(f"  Epoch [{epoch+1}/{epochs}] Train Loss: {train_loss/len(train_loader):.4f} Acc: {train_acc*100:.2f}% | Val Loss: {val_loss/len(valid_loader):.4f} Acc: {val_acc*100:.2f}%")
                
            if patience_counter >= patience:
                print(f"  [EARLY STOPPING] Dung som tai Epoch {epoch+1} do Validation Acc khong tang trong {patience} vong.")
                break

        # Load best model for testing
        if best_model_state is not None:
            self.model.load_state_dict(best_model_state)
            
        # Testing Phase
        self.model.eval()
        correct_test = 0
        total_test = 0
        with torch.no_grad():
            for batch_X, batch_y in test_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                outputs = self.model(batch_X)
                _, predicted = torch.max(outputs.data, 1)
                total_test += batch_y.size(0)
                correct_test += (predicted == batch_y).sum().item()
                
        test_acc = correct_test / total_test
        print(f"\n[SUCCESS] Training complete! Best Validation Acc: {best_val_acc*100:.2f}%")
        print(f"[TEST] Final Test Accuracy on unseen data: {test_acc*100:.2f}%")

        self.training_history.append({
            'timestamp': datetime.now().isoformat(),
            'model_type': 'lstm',
            'seq_length': seq_length,
            'accuracy': float(test_acc),
            'val_accuracy': float(best_val_acc),
            'n_samples': int(len(X))
        })
        self.save_model()

    def predict_room(self, current_room_data, history_data, seq_length=10):
        """
        Predict kill probability for each room based on historical sequence.

        :param current_room_data: Current round's room data {room_id: {user_cnt, total_bet}}
        :type current_room_data: dict
        :param history_data: List of past round data from GameDataCollector
        :type history_data: list
        :param seq_length: Number of past rounds to consider
        :type seq_length: int
        :return: Sorted list of predictions (safest first) or None
        :rtype: list/None
        """
        if self.model is None or self.scaler is None:
            return None

        try:
            self.model.eval()
            sequence_features = []
            recent_history = history_data[-(seq_length - 1):] if len(history_data) >= (seq_length - 1) else history_data

            for round_data in recent_history:
                features = []
                for i in range(1, 9):
                    room_info = round_data.get('rooms', {}).get(i, {})
                    if not room_info:
                        room_info = round_data.get('rooms', {}).get(str(i), {})
                    features.extend([
                        int(room_info.get("final_user_cnt", room_info.get("user_cnt", 0))),
                        float(room_info.get("final_total_bet", room_info.get("total_bet", 0)))
                    ])
                features.append(int(round_data.get("last_killed_room", 0)))
                sequence_features.append(features)

            while len(sequence_features) < seq_length - 1:
                sequence_features.insert(0, [0] * self.INPUT_SIZE)

            current_features = []
            for i in range(1, 9):
                room_info = current_room_data.get(i, current_room_data.get(str(i), {'user_cnt': 0, 'total_bet': 0}))
                current_features.extend([
                    int(room_info.get('user_cnt', 0)),
                    float(room_info.get('total_bet', 0))
                ])
            last_killed = int(recent_history[-1].get("killed_room", 0)) if recent_history else 0
            current_features.append(last_killed)
            sequence_features.append(current_features)
            sequence_features = sequence_features[-seq_length:]

            X_scaled = self.scaler.transform(sequence_features)
            X_tensor = torch.tensor([X_scaled], dtype=torch.float32).to(self.device)

            with torch.no_grad():
                outputs = self.model(X_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)[0].cpu().numpy()

            results = []
            for i in range(8):
                results.append({
                    'room_id': i + 1,
                    'kill_probability': float(probabilities[i]),
                    'safe_probability': float(1 - probabilities[i])
                })

            results.sort(key=lambda x: x['safe_probability'], reverse=True)
            return results

        except Exception as e:
            print(f"[ERROR] predict_room: {e}")
            return None

    def save_model(self):
        """Save model weights, scaler, and metadata to disk."""
        try:
            if self.model and self.scaler:
                torch.save(self.model.state_dict(), self.model_path)
                joblib.dump(self.scaler, self.scaler_path)

                metadata = {
                    'feature_names': self.feature_names,
                    'training_history': self.training_history,
                    'seq_length': self.seq_length,
                    'last_updated': datetime.now().isoformat()
                }
                with open('model_metadata.json', 'w') as f:
                    json.dump(metadata, f, indent=2)

                print(f"[SAVED] Model -> {self.model_path}")
        except Exception as e:
            print(f"[ERROR] save_model: {e}")

    def load_model(self):
        """Load model weights, scaler, and metadata from disk."""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
                self.scaler = joblib.load(self.scaler_path)

                if os.path.exists('model_metadata.json'):
                    with open('model_metadata.json', 'r') as f:
                        metadata = json.load(f)
                        self.feature_names = metadata.get('feature_names', [])
                        self.training_history = metadata.get('training_history', [])
                        self.seq_length = metadata.get('seq_length', 10)

                print(f"[LOADED] Model <- {self.model_path}")
                return True
            except Exception as e:
                print(f"[ERROR] load_model: {e}")
                return False
        return False