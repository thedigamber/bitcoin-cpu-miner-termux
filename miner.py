#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import time
import requests
import json
import socket
import threading
from datetime import datetime
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# Configuration
CPUMINER_REPO = "https://github.com/JayDDee/cpuminer-opt.git"
MINER_DIR = "cpuminer-opt"
CONFIG_FILE = "miner_config.json"
BENCHMARK_FILE = "benchmark_results.txt"
STATS_FILE = "mining_stats.json"
UPDATE_INTERVAL = 300  # 5 minutes for stats update

# Pool configuration (auto-select best pool)
POOLS = [
    {
        "name": "SlushPool",
        "url": "stratum+tcp://stratum.slushpool.com",
        "ports": [3333, 443],
        "fee": 2.0,
        "score": 0
    },
    {
        "name": "F2Pool",
        "url": "stratum+tcp://btc.f2pool.com",
        "ports": [1314, 3333],
        "fee": 2.5,
        "score": 0
    },
    {
        "name": "ViaBTC",
        "url": "stratum+tcp://btc.viabtc.com",
        "ports": [3333, 25],
        "fee": 2.0,
        "score": 0
    }
]

class TermuxMiner:
    def __init__(self):
        self.wallet_address = ""
        self.current_pool = None
        self.miner_process = None
        self.hashrate = 0
        self.shares = {"accepted": 0, "rejected": 0}
        self.running = False
        self.benchmark_mode = False
        self.worker_name = socket.gethostname() or "termux_worker"
        self.check_network()

    def check_network(self):
        """Check internet connectivity"""
        try:
            requests.get("https://google.com", timeout=5)
            return True
        except:
            print(Fore.RED + "No internet connection. Please check your network.")
            sys.exit(1)

    def install_dependencies(self):
        """Install all required dependencies (2025 Termux compatible)"""
        # Updated working Termux packages (no "-dev")
        required = [
            "git", "autoconf", "automake", "libtool", "pkg-config",
            "make", "clang", "curl", "libcurl", "openssl",
            "libjansson", "libgmp", "zlib"
        ]

        print(Fore.YELLOW + "Checking and installing dependencies...")

        for pkg in required:
            try:
                subprocess.run(["dpkg", "-s", pkg], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(Fore.GREEN + f"{pkg} is already installed")
            except subprocess.CalledProcessError:
                print(Fore.YELLOW + f"Installing {pkg}...")
                try:
                    subprocess.run(["pkg", "install", "-y", pkg], check=True)
                    print(Fore.GREEN + f"Successfully installed {pkg}")
                except subprocess.CalledProcessError as e:
                    print(Fore.RED + f"Failed to install {pkg}: {str(e)}")
                    sys.exit(1)

    def clone_and_build(self):
        """Clone and build cpuminer-opt with optimizations"""
        if os.path.exists(MINER_DIR):
            print(Fore.YELLOW + "Removing existing miner directory...")
            shutil.rmtree(MINER_DIR)
        
        print(Fore.CYAN + "Cloning cpuminer-opt repository...")
        subprocess.run(["git", "clone", "--depth", "1", CPUMINER_REPO, MINER_DIR], check=True)
        
        os.chdir(MINER_DIR)
        
        print(Fore.CYAN + "Building cpuminer with optimizations...")
        build_steps = [
            ["./build.sh"],
            ["./autogen.sh"],
            ["./configure", "CFLAGS=-O3", "CXXFLAGS=-O3", "--with-curl", "--with-crypto"],
            ["make", "-j", str(os.cpu_count() or 2)]  # Use all available cores for compilation
        ]
        
        for step in build_steps:
            print(Fore.BLUE + "Running: " + " ".join(step))
            try:
                result = subprocess.run(step, check=True)
                print(Fore.GREEN + f"Step completed successfully: {' '.join(step)}")
            except subprocess.CalledProcessError as e:
                print(Fore.RED + f"Build failed at step {' '.join(step)}: {str(e)}")
                print(Fore.YELLOW + "Trying to continue with next step...")
                continue
        
        # Verify the miner binary was created
        miner_binary = self.get_miner_binary_path()
        if not os.path.exists(miner_binary):
            print(Fore.RED + "Miner binary not found after build. Build likely failed.")
            print(Fore.YELLOW + "Trying to build with simpler configuration...")
            try:
                subprocess.run(["make", "clean"], check=True)
                subprocess.run(["./configure"], check=True)
                subprocess.run(["make", "-j", str(os.cpu_count() or 2)], check=True)
            except subprocess.CalledProcessError as e:
                print(Fore.RED + f"Simpler build also failed: {str(e)}")
                sys.exit(1)
        
        if not os.path.exists(miner_binary):
            print(Fore.RED + "Miner binary still not found after second build attempt.")
            sys.exit(1)
        
        os.chdir("..")
        print(Fore.GREEN + "Build completed successfully!")

    def get_miner_binary_path(self):
        """Get the path to the miner binary, checking multiple possible locations"""
        possible_paths = [
            os.path.join(MINER_DIR, "cpuminer"),
            os.path.join(MINER_DIR, "minerd"),
            os.path.join(MINER_DIR, "cpuminer-avx2"),
            os.path.join(MINER_DIR, "cpuminer-opt")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        return possible_paths[0]  # Return default path even if not found

    def load_config(self):
        """Load or create configuration"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                self.wallet_address = config.get("wallet_address", "")
                self.worker_name = config.get("worker_name", self.worker_name)
                
                if not self.validate_wallet(self.wallet_address):
                    raise ValueError("Invalid wallet address in config")
                    
                print(Fore.YELLOW + f"Using saved wallet address: {self.wallet_address}")
                return
            except Exception as e:
                print(Fore.RED + f"Error loading config: {str(e)}")
        
        self.setup_config()

    def setup_config(self):
        """Interactive configuration setup"""
        print(Fore.CYAN + "=== Miner Configuration ===")
        
        # Get wallet address
        while True:
            print(Fore.CYAN + "Please enter your Bitcoin wallet address:")
            wallet = input("> ").strip()
            if self.validate_wallet(wallet):
                self.wallet_address = wallet
                break
            print(Fore.RED + "Invalid wallet address. Bitcoin addresses are 26-35 alphanumeric characters.")
        
        # Get worker name
        print(Fore.CYAN + f"Enter worker name (default: {self.worker_name}):")
        worker = input("> ").strip()
        if worker:
            self.worker_name = worker
        
        # Save config
        config = {
            "wallet_address": self.wallet_address,
            "worker_name": self.worker_name,
            "created": datetime.now().isoformat()
        }
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        
        print(Fore.GREEN + "Configuration saved!")

    def validate_wallet(self, address):
        """Basic wallet address validation"""
        if not address:
            return False
        if len(address) < 26 or len(address) > 35:
            return False
        return all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in address)

    def select_best_pool(self):
        """Test and select the best mining pool"""
        print(Fore.CYAN + "Testing available pools...")
        
        best_pool = None
        best_score = -1
        
        for pool in POOLS:
            try:
                # Test connection to each port
                for port in pool["ports"]:
                    test_url = f"{pool['url']}:{port}"
                    print(Fore.YELLOW + f"Testing {pool['name']} on port {port}...")
                    
                    # Simple ping test
                    start_time = time.time()
                    try:
                        sock = socket.create_connection(
                            (pool['url'].replace("stratum+tcp://", "").split(":")[0], port), 
                            timeout=5
                        )
                        sock.close()
                        latency = (time.time() - start_time) * 1000  # ms
                        
                        # Calculate score (lower latency and fee = better)
                        score = (1000 / latency) * (1 - (pool['fee'] / 100))
                        pool['score'] = score
                        
                        print(Fore.GREEN + f"{pool['name']} latency: {latency:.2f}ms, score: {score:.2f}")
                        
                        if score > best_score:
                            best_score = score
                            best_pool = {
                                "name": pool['name'],
                                "url": test_url,
                                "fee": pool['fee']
                            }
                        break
                    except socket.error:
                        continue
            except Exception as e:
                print(Fore.RED + f"Error testing {pool['name']}: {str(e)}")
                continue
        
        if not best_pool:
            print(Fore.RED + "Could not connect to any pools. Check your internet connection.")
            sys.exit(1)
        
        self.current_pool = best_pool
        print(Fore.GREEN + f"Selected pool: {best_pool['name']} ({best_pool['url']}) with fee {best_pool['fee']}%")

    def run_benchmark(self):
        """Run performance benchmark"""
        print(Fore.MAGENTA + "=== Starting Benchmark Mode ===")
        self.benchmark_mode = True
        
        miner_binary = self.get_miner_binary_path()
        if not os.path.exists(miner_binary):
            print(Fore.RED + "Miner binary not found. Trying to build first...")
            self.clone_and_build()
            miner_binary = self.get_miner_binary_path()
            if not os.path.exists(miner_binary):
                print(Fore.RED + "Miner binary still not found after build.")
                return
        
        command = [
            miner_binary,
            "--benchmark",
            "--algo=sha256d",
            "--time-limit=30"  # 30 second benchmark
        ]
        
        print(Fore.CYAN + "Running benchmark (this will take 30 seconds)...")
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            benchmark_results = []
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
                    benchmark_results.append(output.strip())
            
            # Save benchmark results
            with open(BENCHMARK_FILE, "w") as f:
                f.write("\n".join(benchmark_results))
            
            print(Fore.GREEN + f"Benchmark results saved to {BENCHMARK_FILE}")
            
        except Exception as e:
            print(Fore.RED + f"Benchmark failed: {str(e)}")
        
        self.benchmark_mode = False

    def start_mining(self):
        """Start the mining process"""
        miner_binary = self.get_miner_binary_path()
        
        if not os.path.exists(miner_binary):
            print(Fore.RED + "Miner binary not found. Trying to build first...")
            self.clone_and_build()
            miner_binary = self.get_miner_binary_path()
            if not os.path.exists(miner_binary):
                print(Fore.RED + "Miner binary still not found after build.")
                return
        
        if not self.current_pool:
            self.select_best_pool()
        
        command = [
            miner_binary,
            "-a", "sha256d",
            "-o", self.current_pool["url"],
            "-u", f"{self.wallet_address}.{self.worker_name}",
            "-p", "x",
            "--stats",
            "--retries=5",
            "--timeout=30",
            "--temp-cutoff=95",  # Stop if CPU reaches 95°C
            "--temp-hysteresis=3",
            "--cpu-priority=3",  # Slightly elevated priority
            "--quiet"  # Less verbose output
        ]
        
        # Add platform-specific optimizations
        if "aarch64" in os.uname().machine:
            command.extend(["--asm=armv8"])
        else:
            command.extend(["--asm=yes"])
        
        print(Fore.GREEN + "Starting miner with optimized settings...")
        print(Fore.YELLOW + "Command: " + " ".join(command))
        print(Fore.CYAN + "Press CTRL+C to stop mining")
        
        self.running = True
        self.miner_process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Start stats monitoring thread
        stats_thread = threading.Thread(target=self.monitor_stats)
        stats_thread.daemon = True
        stats_thread.start()
        
        # Display output in real-time with colors
        while self.running:
            output = self.miner_process.stdout.readline()
            if output == '' and self.miner_process.poll() is not None:
                break
            if output:
                self.parse_output(output)
        
        if self.miner_process.returncode != 0 and not self.benchmark_mode:
            print(Fore.RED + "Miner process crashed. Restarting in 10 seconds...")
            time.sleep(10)
            self.start_mining()

    def parse_output(self, output):
        """Parse miner output and update stats"""
        output = output.strip()
        
        # Update hashrate
        if "kH/s" in output:
            try:
                self.hashrate = float(output.split()[2])
            except:
                pass
        
        # Update shares
        if "ACCEPTED" in output:
            self.shares["accepted"] += 1
            print(Fore.GREEN + output)
        elif "REJECTED" in output:
            self.shares["rejected"] += 1
            print(Fore.RED + output)
        elif "yay!!!" in output:
            print(Fore.MAGENTA + Style.BRIGHT + ">>> BLOCK FOUND! <<<")
            print(Fore.MAGENTA + output)
        elif "stratum" in output.lower():
            print(Fore.CYAN + output)
        else:
            print(output)

    def monitor_stats(self):
        """Monitor and save mining statistics"""
        start_time = time.time()
        
        while self.running:
            try:
                # Calculate uptime
                uptime = time.time() - start_time
                hours, remainder = divmod(uptime, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                # Calculate rejection rate
                total_shares = self.shares["accepted"] + self.shares["rejected"]
                rejection_rate = (self.shares["rejected"] / total_shares * 100) if total_shares > 0 else 0
                
                # Calculate estimated earnings (very rough estimate)
                # Note: This is just for display, actual earnings depend on many factors
                btc_per_day = 0
                if self.hashrate > 0:
                    # Very simplified estimation (not accurate for real mining)
                    btc_per_day = (self.hashrate / 1000000) * 0.0001  # Placeholder formula
                
                # Prepare stats
                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "uptime": f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
                    "hashrate": self.hashrate,
                    "shares": self.shares.copy(),
                    "rejection_rate": rejection_rate,
                    "estimated_earnings": btc_per_day,
                    "pool": self.current_pool["name"]
                }
                
                # Save stats to file
                with open(STATS_FILE, "w") as f:
                    json.dump(stats, f, indent=2)
                
                # Display stats
                os.system('clear')  # Clear screen for better display
                print(Fore.MAGENTA + Style.BRIGHT + "=== Mining Statistics ===")
                print(Fore.CYAN + f"Pool: {self.current_pool['name']} ({self.current_pool['url']})")
                print(Fore.CYAN + f"Fee: {self.current_pool['fee']}%")
                print(Fore.YELLOW + f"Uptime: {stats['uptime']}")
                print(Fore.GREEN + f"Hashrate: {self.hashrate:.2f} kH/s")
                print(Fore.BLUE + f"Shares: {self.shares['accepted']} accepted, {self.shares['rejected']} rejected")
                print(Fore.RED + f"Rejection rate: {rejection_rate:.2f}%")
                print(Fore.MAGENTA + f"Estimated earnings: {btc_per_day:.8f} BTC/day")
                print(Fore.YELLOW + "\n[Live output] (Press CTRL+C to stop)")
                
                time.sleep(UPDATE_INTERVAL)
                
            except Exception as e:
                print(Fore.RED + f"Error in stats monitor: {str(e)}")
                time.sleep(10)

    def show_stats(self):
        """Display saved statistics"""
        if not os.path.exists(STATS_FILE):
            print(Fore.RED + "No statistics available. Start mining first.")
            return
        
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
        
        print(Fore.MAGENTA + Style.BRIGHT + "=== Mining Statistics ===")
        for key, value in stats.items():
            if key == "shares":
                print(Fore.BLUE + f"Shares: {value['accepted']} accepted, {value['rejected']} rejected")
            else:
                print(Fore.CYAN + f"{key.replace('_', ' ').title()}: {value}")

    def cleanup(self):
        """Clean up before exit"""
        self.running = False
        if self.miner_process:
            self.miner_process.terminate()
        print(Fore.YELLOW + "\nMiner stopped. Cleaning up...")

    def show_menu(self):
        """Display main menu"""
        while True:
            os.system('clear')
            print(Fore.MAGENTA + Style.BRIGHT + """
            Bitcoin CPU Miner for Termux
            ---------------------------
            [1] Start Mining
            [2] Run Benchmark
            [3] Show Statistics
            [4] Change Configuration
            [5] Update Miner
            [6] Exit
            """)
            
            choice = input(Fore.CYAN + "Select an option: ").strip()
            
            if choice == "1":
                try:
                    self.start_mining()
                except KeyboardInterrupt:
                    self.cleanup()
            elif choice == "2":
                self.run_benchmark()
                input(Fore.YELLOW + "Press Enter to continue...")
            elif choice == "3":
                self.show_stats()
                input(Fore.YELLOW + "Press Enter to continue...")
            elif choice == "4":
                self.setup_config()
            elif choice == "5":
                self.update_miner()
            elif choice == "6":
                self.cleanup()
                sys.exit(0)
            else:
                print(Fore.RED + "Invalid choice. Please try again.")
                time.sleep(1)

    def update_miner(self):
        """Update the miner software"""
        print(Fore.YELLOW + "Updating miner...")
        
        if not os.path.exists(MINER_DIR):
            print(Fore.RED + "Miner directory not found. Building fresh...")
            self.clone_and_build()
            return
        
        os.chdir(MINER_DIR)
        
        try:
            subprocess.run(["git", "pull"], check=True)
            subprocess.run(["make", "clean"], check=True)
            subprocess.run(["./build.sh"], check=True)
            subprocess.run(["./autogen.sh"], check=True)
            subprocess.run(["./configure", "CFLAGS=-O3", "CXXFLAGS=-O3", "--with-curl", "--with-crypto"], check=True)
            subprocess.run(["make", "-j", str(os.cpu_count() or 2)], check=True)
            print(Fore.GREEN + "Miner updated successfully!")
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"Update failed: {str(e)}")
            print(Fore.YELLOW + "Trying simpler build...")
            try:
                subprocess.run(["make", "clean"], check=True)
                subprocess.run(["./configure"], check=True)
                subprocess.run(["make", "-j", str(os.cpu_count() or 2)], check=True)
                print(Fore.GREEN + "Miner updated with simpler configuration!")
            except subprocess.CalledProcessError as e:
                print(Fore.RED + f"Simpler build also failed: {str(e)}")
        finally:
            os.chdir("..")

def main():
    try:
        # Check network first
        miner = TermuxMiner()
        
        # Show disclaimer
        print(Fore.RED + Style.BRIGHT + """
        DISCLAIMER:
        ----------
        Bitcoin CPU mining is NOT profitable with standard hardware.
        This script is for educational purposes only.
        
        Mining will generate heat and may reduce device lifespan.
        You are solely responsible for any damage caused.
        
        By using this software, you accept these risks.
        """)
        
        input(Fore.YELLOW + "Press Enter to acknowledge and continue...")
        
        # Install dependencies if needed
        miner.install_dependencies()
        
        # Build the miner if not already built
        miner_binary = miner.get_miner_binary_path()
        if not os.path.exists(miner_binary):
            print(Fore.YELLOW + "Building miner for the first time...")
            miner.clone_and_build()
        
        # Load or create config
        miner.load_config()
        
        # Show main menu
        miner.show_menu()
        
    except KeyboardInterrupt:
        miner.cleanup()
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
