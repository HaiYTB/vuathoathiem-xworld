import json
import numpy as np
from scipy import stats
import math

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)['data']
    
    # Extract sequence of killed rooms (1-8)
    sequence = []
    for d in data:
        if 'killed_room' in d:
            sequence.append(int(d['killed_room']))
    return sequence

def chi_square_test(sequence, num_bins=8):
    print("\n--- 1. Chi-Square Test (Kiem tra tinh dong deu) ---")
    counts = np.bincount(sequence)[1:] # Ignore 0 index
    expected = len(sequence) / num_bins
    
    chi2, p_value = stats.chisquare(counts, f_exp=[expected]*num_bins)
    
    print(f"Chi-square statistic: {chi2:.4f}")
    print(f"P-value: {p_value:.4f}")
    if p_value < 0.05:
        print("=> Ket luan: Du lieu KHONG dong deu (Co dau hieu thao tung hoac PRNG yeu).")
    else:
        print("=> Ket luan: Du lieu phan bo RAT dong deu (Giong random that hoac PRNG xin).")

def autocorrelation_test(sequence, max_lag=10):
    print(f"\n--- 2. Autocorrelation Test (Kiem tra tinh phu thuoc cac van truoc) ---")
    seq_mean = np.mean(sequence)
    seq_var = np.var(sequence)
    
    print("Lag | Tuong quan (Cang gan 0 cang tot)")
    print("-" * 40)
    for lag in range(1, max_lag + 1):
        cov = np.sum((sequence[:-lag] - seq_mean) * (sequence[lag:] - seq_mean)) / (len(sequence) - lag)
        corr = cov / seq_var
        
        # Approximate 95% confidence interval for correlation = 1.96 / sqrt(N)
        threshold = 1.96 / math.sqrt(len(sequence))
        
        flag = "!" if abs(corr) > threshold else " "
        print(f"{lag:3d} | {corr:10.4f}  {flag}")
    
    print(f"(Dau '!' nghia la co moi lien he thong ke dang ke voi van thu N truoc do)")

def runs_test(sequence):
    print("\n--- 3. Runs Test (Kiem tra chuoi lien tiep) ---")
    # Convert to binary: > median vs <= median (or odd/even)
    # Let's do Odd / Even
    binary_seq = [1 if x % 2 == 0 else 0 for x in sequence]
    
    n1 = sum(binary_seq)
    n0 = len(binary_seq) - n1
    
    runs = 1
    for i in range(1, len(binary_seq)):
        if binary_seq[i] != binary_seq[i-1]:
            runs += 1
            
    expected_runs = ((2 * n0 * n1) / (n0 + n1)) + 1
    variance = (2 * n0 * n1 * (2 * n0 * n1 - n0 - n1)) / (((n0 + n1)**2) * (n0 + n1 - 1))
    
    z_stat = (runs - expected_runs) / math.sqrt(variance)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    
    print(f"Tong so van: {len(sequence)}")
    print(f"So luong chuoi (Runs) thuc te: {runs}")
    print(f"So luong chuoi ly thuyet: {expected_runs:.1f}")
    print(f"Z-statistic: {z_stat:.4f}")
    print(f"P-value: {p_value:.4f}")
    
    if p_value < 0.05:
        print("=> Ket luan: Cac chuoi phong an/thua KHONG ngau nhien (Co dau hieu set up).")
    else:
        print("=> Ket luan: Cac chuoi phong ngau nhien dung tieu chuan.")

def entropy_test(sequence, num_bins=8):
    print("\n--- 4. Shannon Entropy (Do do hon loan) ---")
    counts = np.bincount(sequence)[1:]
    probs = counts / len(sequence)
    
    entropy = -np.sum(probs * np.log2(probs))
    max_entropy = math.log2(num_bins) # For 8 rooms, max entropy is 3.0
    
    print(f"Entropy: {entropy:.4f} bits (Max: {max_entropy:.4f})")
    print(f"Ty le hoan hao: {entropy/max_entropy*100:.2f}%")
    if entropy/max_entropy > 0.99:
         print("=> Ket luan: Do hon loan gan nhu tuyet doi, rat kho du doan.")
    else:
         print("=> Ket luan: Do hon loan thap, co the bẻ khoá duoc!")

if __name__ == "__main__":
    file_path = 'game_data.json'
    try:
         seq = load_data(file_path)
         print(f"Da tai {len(seq)} van game. Bat dau phan tich do ngau nhien (RNG)...\n")
         chi_square_test(seq)
         autocorrelation_test(seq)
         runs_test(seq)
         entropy_test(seq)
    except Exception as e:
         print(f"Loi: {e}")
