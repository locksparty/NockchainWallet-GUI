# 🪙 Nockchain Wallet Qt Interface  
*A lightweight graphical interface for the Nockchain Wallet.*

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)]()
[![UI](https://img.shields.io/badge/UI-PyQt6-yellow.svg)]()

---

## 🚀 Overview

**Nockchain Wallet Qt Interface** is a **PyQt6-based GUI** for the `nockchain-wallet` command-line client.  
It provides an intuitive way to manage wallets, send transactions, and interact with Nockchain nodes — all from a clean desktop interface.

---

## ✨ Features

- 🧰 Full graphical interface for the `nockchain-wallet` CLI  
- ⚙️ Easy configuration via `~/.nockwallet_config.json`  
- 🔁 Auto-refresh of balances and network status  
- 🔒 Support for both **public** and **private** client modes  
- 🪙 Send, receive, and view token transactions  
- 📊 Real-time wallet status and JSON output parsing  
- 🧩 Tabbed interface (Wallet, Transactions, Settings, etc.)  
- 🖥️ Cross-platform: Linux, Windows, macOS  

---

## 🧠 How It Works

The application acts as a **frontend** between the user and the `nockchain-wallet` binary.  
It executes wallet commands through `subprocess`, receives **JSON responses**, and updates the interface dynamically.

**Typical workflow:**
1. Set the wallet binary path and node type (public/private).  
2. Create, open, or import an existing wallet.  
3. View your balances or recent transactions.  
4. Send tokens and confirm results instantly.

---

## 🛠️ Installation

### 1. Clone this repository

git clone https://github.com/yourusername/nockchain-wallet-qt.git
cd nockchain-wallet-qt

### 2. Install dependencies

Make sure you have Python 3.9+ installed, then run:

pip install PyQt6

Or use a virtual environment:

python3 -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install PyQt6

### 3. Launch the app

python3 nockwallet.py


Disclaimer

DISCLAIMER OF WARRANTY. THE SOFTWARE IS PROVIDED “AS IS” AND “AS AVAILABLE,” WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE SOFTWARE IS WITH YOU. SHOULD THE SOFTWARE PROVE DEFECTIVE, YOU ASSUME ALL COSTS OF ALL NECESSARY SERVICING, REPAIR, OR CORRECTION.

LIMITATION OF LIABILITY. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

USE AT YOUR OWN RISK. BY USING THIS SOFTWARE, YOU ACKNOWLEDGE THAT YOU DO SO AT YOUR OWN RISK. YOU AGREE THAT YOU ALONE ARE RESPONSIBLE FOR ANY LOSS, DAMAGE, OR CONSEQUENCE RESULTING FROM ITS USE.
