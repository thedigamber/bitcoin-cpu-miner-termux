# 💰 Bitcoin CPU Miner for Termux (Pro Edition)

Mine real Bitcoin from your Android using `cpuminer-opt` compiled directly inside Termux with intelligent pool selection, benchmarks, live stats, and more.

---

## ⚙️ Installation

```bash
pkg update && pkg upgrade -y
pkg install git wget build-essential autoconf automake clang curl -y
pkg install libtool pkg-config openssl-dev libcurl-dev libjansson-dev libgmp-dev zlib-dev -y
pkg install python -y

git clone https://github.com/thedigamber/bitcoin-cpu-miner-termux
cd bitcoin-cpu-miner-termux
pip install -r requirements.txt

python3 miner.py
```
✅ 1. ❌ Remove Old Installation (Clean Reset)
```bash
cd ~
rm -rf bitcoin-cpu-miner-termux cpuminer-opt miner_config.json benchmark_results.txt mining_stats.json
```
✅ 2. 📥 Reinstall & Fresh Run
# Step 1: Update Termux & install
```bash
pkg update && pkg upgrade -y
pkg install git wget build-essential autoconf automake clang curl -y
pkg install libtool pkg-config openssl-dev libcurl-dev libjansson-dev libgmp-dev zlib-dev -y
pkg install python -y
```
# Step 2: Clone your tool
```bash
git clone https://github.com/thedigamber/bitcoin-cpu-miner-termux
cd bitcoin-cpu-miner-termux
```
# Step 3: Install Python requirements
```bash
pip install -r requirements.txt
```
# Step 4: Run the tool
```bash
python3 miner.py
```
✅ 3. 🔁 Run Tool Again (after reboot or exit)
```bash
cd ~/bitcoin-cpu-miner-termux
python3 miner.py
```
✅ 4. 🔄 Update Tool & Miner
```bash
cd ~/bitcoin-cpu-miner-termux
python3 miner.py
```
# Then choose option:
[5] Update Miner

✅ 5. 💣 Hard Reset Config (if wallet or worker name needs reset)
```bash
rm miner_config.json
cd ~/bitcoin-cpu-miner-termux
python3 miner.py
```
✅ Bonus Tip: Auto Start Miner (for automation)
```bash
cd ~/bitcoin-cpu-miner-termux && python3 miner.py
```
Or add to .bashrc or .zshrc if you want it to auto-run on Termux startup.




---

🔥 Features

✅ Auto-pool selection (SlushPool, F2Pool, ViaBTC)
✅ Wallet configuration saved
✅ Auto-benchmarking
✅ Full mining stats (hashrate, shares, estimated BTC/day)
✅ Fail-safe restart if miner crashes
✅ Auto-updating miner
✅ Built-in temperature control
✅ Interactive menu system


---

📸 Screenshots

[1] Start Mining  
[2] Run Benchmark  
[3] Show Statistics  
[4] Change Configuration  
[5] Update Miner  
[6] Exit


---

📋 Dependencies

Python 3

cpuminer-opt

clang, make, autoconf

colorama

requests



---

⚠️ Disclaimer

> ❗ This project is for educational purposes only.
Mining on mobile devices is extremely inefficient and may damage your hardware.
You are solely responsible for any usage or consequences.




---

💎 Developed by @thedigamber

---
