"""
Train AI from all collected dataset.
Usage: python train_now.py
"""
from train import GameDataCollector, GameAI

print("=" * 50)
print("   TRAIN AI - VUA THOAT HIEM (LSTM)")
print("=" * 50)

collector = GameDataCollector()
df = collector.get_dataframe()

if df is None or len(df) == 0:
    print("\n[ERROR] No data found! Run server.py + vth.py to collect first.")
else:
    print(f"\n[INFO] Total rounds in dataset: {len(df)}")
    ai = GameAI()
    ai.train(df, seq_length=10)
    print("\n[DONE] Model saved to lstm_model.pth")
