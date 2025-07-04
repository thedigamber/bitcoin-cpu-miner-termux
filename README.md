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
