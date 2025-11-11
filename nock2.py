#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nockchain Wallet Qt Interface
Interface graphique pour le wallet Nockchain avec support des transactions
"""

import sys
import subprocess
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import re

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QGroupBox, QRadioButton, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QStatusBar, QComboBox,
    QSpinBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# Configuration globale
CONFIG_FILE = Path.home() / ".nockwallet_config.json"
DEFAULT_CONFIG = {
    'wallet_binary': 'nockchain-wallet',
    'wallet_path': '',
    'wallet_imported': False,
    'client_type': 'public',
    'public_server': 'https://nockchain-api.zorp.io',
    'private_port': '50051',
    'last_used_directory': str(Path.home())
}

# Charger la configuration
config = DEFAULT_CONFIG.copy()
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, 'r') as f:
            loaded_config = json.load(f)
            config.update(loaded_config)
    except Exception as e:
        logging.error(f"Erreur chargement config: {e}")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TransactionEngine:
    """Moteur de gestion des transactions"""
    def __init__(self, wallet_binary: str):
        self.wallet_binary = wallet_binary

    def send_funds(self, recipient: str, amount_nicks: int, note_names: List[str], fee: int = 10) -> Dict:
        """Envoie des fonds à un destinataire"""
        try:
            # Construction de la commande
            cmd = [
                self.wallet_binary,
                "create-tx",
                "--recipient", f"{recipient}:{amount_nicks}",
                "--fee", str(fee)
            ]

            if note_names:
                cmd.extend(["--names", f"[{' '.join(note_names)}]"])

            # Création de la transaction
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Extraction du fichier .tx
            tx_file = None
            for line in result.stdout.splitlines():
                if line.endswith(".tx"):
                    tx_file = line.strip()
                    break

            if not tx_file:
                return {"success": False, "error": "Aucun fichier de transaction généré"}

            # Envoi de la transaction
            send_cmd = [self.wallet_binary, "send-tx", tx_file]
            send_result = subprocess.run(
                send_cmd,
                capture_output=True,
                text=True,
                check=True
            )

            # Extraction de l'ID de transaction
            tx_id = None
            for line in send_result.stdout.splitlines():
                if len(line) == 44:  # Longueur typique d'un TX ID
                    tx_id = line.strip()
                    break

            return {
                "success": True,
                "tx_id": tx_id,
                "tx_file": tx_file,
                "message": "Transaction envoyée avec succès"
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": e.stderr.strip() or e.stdout.strip(),
                "cmd": " ".join(e.cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class WalletOutputParser:
    """Parseur pour les sorties de la CLI wallet"""

    @staticmethod
    def parse_balance(output: str) -> Optional[Dict]:
        """Parse le solde du wallet"""
        try:
            # Recherche du solde total
            total_match = re.search(r'Total:\s*([\d.,]+)\s*nicks', output)
            if not total_match:
                return None

            total_nicks = int(total_match.group(1).replace(',', ''))
            total_nock = total_nicks / 65536  # 1 NOCK = 65536 nicks

            # Recherche du solde disponible
            available_match = re.search(r'Available:\s*([\d.,]+)\s*nicks', output)
            available_nicks = int(available_match.group(1).replace(',', '')) if available_match else 0
            available_nock = available_nicks / 65536

            return {
                'total_nicks': total_nicks,
                'total_nock': total_nock,
                'available_nicks': available_nicks,
                'available_nock': available_nock,
                'formatted': f"{total_nock:.6f} NOCK ({available_nock:.6f} disponibles)"
            }
        except Exception as e:
            logger.error(f"Erreur parse balance: {e}")
            return None

    @staticmethod
    def parse_wallet_version(output: str) -> Optional[str]:
        """Parse la version du wallet"""
        try:
            match = re.search(r'Version:\s*(\d+\.\d+\.\d+)', output)
            return match.group(1) if match else None
        except:
            return None

    @staticmethod
    def parse_height(output: str) -> Optional[int]:
        """Parse la hauteur du bloc"""
        try:
            match = re.search(r'Height:\s*([\d.,]+)', output)
            if match:
                height_str = match.group(1).replace(',', '').replace('.', '')
                return int(height_str)
            return None
        except Exception as e:
            logger.error(f"Erreur parse height: {e}")
            return None

    @staticmethod
    def parse_notes(output: str) -> list:
        """Parse la liste des notes"""
        notes = []
        try:
            lines = output.split('\n')
            for line in lines:
                if re.search(r'[0-9a-f]{40,}', line):
                    notes.append(line.strip())
            return notes
        except Exception as e:
            logger.error(f"Erreur parse notes: {e}")
            return []

    @staticmethod
    def extract_success_message(output: str) -> Optional[str]:
        """Extrait le message de succès final"""
        try:
            if "successfully" in output.lower():
                return "✓ Commande exécutée avec succès"
            return None
        except:
            return None

    @staticmethod
    def extract_error(stderr: str) -> str:
        """Extrait l'erreur pertinente du stderr"""
        try:
            lines = stderr.split('\n')
            error_lines = []
            for line in lines:
                line = line.strip()
                if not any(x in line.lower() for x in ['[0m', '[32m', '[33m', 'trace', 'debug']):
                    if line and not line.startswith('--'):
                        error_lines.append(line)
            return '\n'.join(error_lines) if error_lines else stderr
        except:
            return stderr

class LogArea(QTextEdit):
    """Zone de log avec coloration"""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(200)
        font = QFont("Courier", 10)
        self.setFont(font)

    def append_log(self, message: str, log_type: str = "info"):
        """Ajoute un message avec couleur selon le type"""
        colors = {
            "info": "#FFFFFF",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "command": "#2196F3"
        }
        color = colors.get(log_type, "#FFFFFF")
        self.append(f'<span style="color: {color};">{message}</span>')

class NockchainWalletGUI(QMainWindow):
    """Interface principale du wallet Nockchain"""

    def __init__(self):
        super().__init__()
        self.parser = WalletOutputParser()
        self.tx_engine = TransactionEngine(wallet_binary=config['wallet_binary'])
        self.init_ui()
        self._check_binary()

    def _create_transaction_tab(self) -> QWidget:
        """Crée l'onglet de transaction"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Formulaire d'envoi
        form_group = QGroupBox("Envoyer des NOCK")
        form_layout = QFormLayout()

        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Adresse du destinataire (ex: nock1...)")
        form_layout.addRow("Destinataire:", self.recipient_input)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Montant en NOCK (ex: 1.5)")
        form_layout.addRow("Montant:", self.amount_input)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Noms des notes (ex: note1,note2)")
        form_layout.addRow("Notes à utiliser:", self.notes_input)

        self.fee_input = QSpinBox()
        self.fee_input.setRange(1, 1000)
        self.fee_input.setValue(10)
        self.fee_input.setSuffix(" nicks")
        form_layout.addRow("Frais:", self.fee_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Bouton d'envoi
        self.send_btn = QPushButton("📤 Envoyer la transaction")
        self.send_btn.clicked.connect(self._send_transaction)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.send_btn)

        # Zone de statut
        self.tx_status = QLabel("Prêt à envoyer une transaction")
        self.tx_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.tx_status)

        # Historique des transactions (à implémenter plus tard)
        history_group = QGroupBox("Historique des transactions")
        history_layout = QVBoxLayout()
        self.tx_history = QTableWidget()
        self.tx_history.setColumnCount(3)
        self.tx_history.setHorizontalHeaderLabels(["ID", "Montant", "Statut"])
        self.tx_history.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.tx_history)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)

        widget.setLayout(layout)
        return widget

    def _send_transaction(self):
        """Envoie une transaction"""
        recipient = self.recipient_input.text().strip()
        amount = self.amount_input.text().strip()
        notes = self.notes_input.text().strip()
        fee = self.fee_input.value()

        if not all([recipient, amount]):
            QMessageBox.warning(self, "Erreur", "Destinataire et montant sont obligatoires")
            return

        try:
            # Conversion NOCK → nicks (1 NOCK = 65536 nicks)
            amount_nicks = int(float(amount) * 65536)
            note_list = [n.strip() for n in notes.split(',')] if notes else []

            self.log_area.append_log(f"Envoi de {amount} NOCK à {recipient}...", "info")
            self.tx_status.setText("Envoi en cours...")
            self.tx_status.setStyleSheet("color: #2196F3;")

            # Appel au moteur de transaction
            result = self.tx_engine.send_funds(
                recipient=recipient,
                amount_nicks=amount_nicks,
                note_names=note_list,
                fee=fee
            )

            if result.get("success"):
                self.tx_status.setText(f"✓ Transaction envoyée! ID: {result['tx_id']}")
                self.tx_status.setStyleSheet("color: #4CAF50;")
                self.log_area.append_log(f"Transaction réussie (ID: {result['tx_id']})", "success")

                # Ajouter à l'historique
                self._add_to_history(result['tx_id'], amount, "Envoyé")

                QMessageBox.information(
                    self,
                    "Succès",
                    f"Transaction envoyée avec succès!\n"
                    f"ID: {result['tx_id']}\n"
                    f"Montant: {amount} NOCK\n"
                    f"Frais: {fee} nicks"
                )
            else:
                error = result.get("error", "Erreur inconnue")
                self.tx_status.setText(f"✗ Erreur: {error}")
                self.tx_status.setStyleSheet("color: #F44336;")
                self.log_area.append_log(f"Erreur: {error}", "error")
                QMessageBox.critical(self, "Erreur", f"Échec de l'envoi:\n{error}")

        except ValueError:
            QMessageBox.critical(self, "Erreur", "Montant invalide (ex: 1.5)")
        except Exception as e:
            self.log_area.append_log(f"Erreur inattendue: {str(e)}", "error")
            QMessageBox.critical(self, "Erreur", f"Erreur technique:\n{str(e)}")

    def _add_to_history(self, tx_id: str, amount: str, status: str):
        """Ajoute une transaction à l'historique"""
        row = self.tx_history.rowCount()
        self.tx_history.insertRow(row)
        self.tx_history.setItem(row, 0, QTableWidgetItem(tx_id[:8] + "..."))
        self.tx_history.setItem(row, 1, QTableWidgetItem(amount))
        self.tx_history.setItem(row, 2, QTableWidgetItem(status))

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        self.setWindowTitle("Nockchain Wallet Qt Interface")
        self.setGeometry(100, 100, 1000, 700)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Titre
        title = QLabel("🔗 Nockchain Wallet")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Arial", 20, QFont.Weight.Bold)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # Section wallet
        wallet_group = self._create_wallet_section()
        main_layout.addWidget(wallet_group)

        # Tabs principales
        tabs = QTabWidget()
        tabs.addTab(self._create_balance_tab(), "💰 Balance")
        tabs.addTab(self._create_notes_tab(), "📝 Notes")
        tabs.addTab(self._create_transaction_tab(), "💸 Transactions")  # NOUVEAU
        tabs.addTab(self._create_browser_tab(), "🌐 Browser")
        tabs.addTab(self._create_gas_tab(), "⛽ Gas")
        tabs.addTab(self._create_params_tab(), "⚙️ Paramètres")
        main_layout.addWidget(tabs)

        # Zone de logs
        log_label = QLabel("📋 Logs")
        log_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(log_label)

        self.log_area = LogArea()
        main_layout.addWidget(self.log_area)

        # Barre de statut
        self.statusBar().showMessage("Prêt")
        self.log_area.append_log("Interface Nockchain Wallet initialisée", "success")

        # Mettre à jour l'affichage selon la config chargée
        self._update_wallet_display()

    def _update_wallet_display(self):
        """Met à jour l'affichage selon l'état du wallet"""
        if config['wallet_imported'] and config['wallet_path']:
            self.wallet_path_label.setText(config['wallet_path'])
            self.wallet_path_label.setStyleSheet("color: #4CAF50;")
            self.statusBar().showMessage(f"Wallet: {Path(config['wallet_path']).name}")
        else:
            self.wallet_path_label.setText("Aucun wallet chargé")
            self.wallet_path_label.setStyleSheet("color: #FF9800;")

    def _save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            self.log_area.append_log("Configuration sauvegardée", "success")
        except Exception as e:
            self.log_area.append_log(f"Erreur sauvegarde config: {e}", "error")
            logger.error(f"Erreur sauvegarde config: {e}")

    def _create_wallet_section(self) -> QGroupBox:
        """Crée la section de gestion du wallet"""
        group = QGroupBox("💼 Wallet")
        layout = QVBoxLayout()

        # Chemin du wallet
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Chemin:"))
        self.wallet_path_label = QLabel("Aucun wallet chargé")
        self.wallet_path_label.setStyleSheet("color: #FF9800;")
        path_layout.addWidget(self.wallet_path_label)
        path_layout.addStretch()
        layout.addLayout(path_layout)

        # Boutons
        buttons_layout = QHBoxLayout()

        btn_select = QPushButton("📂 Sélectionner")
        btn_select.clicked.connect(self._select_wallet)
        buttons_layout.addWidget(btn_select)

        btn_import = QPushButton("📥 Importer")
        btn_import.clicked.connect(self._import_wallet)
        buttons_layout.addWidget(btn_import)

        btn_export = QPushButton("📤 Exporter")
        btn_export.clicked.connect(self._export_wallet)
        buttons_layout.addWidget(btn_export)

        layout.addLayout(buttons_layout)
        group.setLayout(layout)
        return group

    def _create_balance_tab(self) -> QWidget:
        """Crée l'onglet Balance"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Affichage du solde
        balance_group = QGroupBox("Solde actuel")
        balance_layout = QVBoxLayout()

        self.balance_label = QLabel("Chargement...")
        balance_font = QFont("Arial", 14, QFont.Weight.Bold)
        self.balance_label.setFont(balance_font)
        balance_layout.addWidget(self.balance_label)

        btn_refresh = QPushButton("🔄 Rafraîchir")
        btn_refresh.clicked.connect(self._refresh_balance)
        balance_layout.addWidget(btn_refresh)

        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)

        # Options d'affichage
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.watch_only_cb = QCheckBox("Inclure les notes watch-only")
        options_layout.addWidget(self.watch_only_cb)

        layout.addWidget(options_group)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_notes_tab(self) -> QWidget:
        """Crée l'onglet Notes"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Tableau des notes
        notes_group = QGroupBox("Notes disponibles")
        notes_layout = QVBoxLayout()

        self.notes_table = QTableWidget()
        self.notes_table.setColumnCount(1)
        self.notes_table.setHorizontalHeaderLabels(["Identifiant de note"])
        self.notes_table.horizontalHeader().setStretchLastSection(True)

        btn_load = QPushButton("🔄 Charger les notes")
        btn_load.clicked.connect(self._load_notes)

        notes_layout.addWidget(self.notes_table)
        notes_layout.addWidget(btn_load)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        # Options
        self.watch_only_notes_cb = QCheckBox("Inclure les notes watch-only")
        layout.addWidget(self.watch_only_notes_cb)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_browser_tab(self) -> QWidget:
        """Crée l'onglet Browser"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Navigation par hauteur
        browse_group = QGroupBox("Navigation par hauteur")
        browse_layout = QVBoxLayout()

        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Hauteur:"))
        self.height_input = QSpinBox()
        self.height_input.setRange(0, 21000000)
        height_layout.addWidget(self.height_input)

        btn_get_block = QPushButton("🔍 Obtenir le bloc")
        btn_get_block.clicked.connect(self._get_block)
        height_layout.addWidget(btn_get_block)

        browse_layout.addLayout(height_layout)
        browse_group.setLayout(browse_layout)
        layout.addWidget(browse_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_gas_tab(self) -> QWidget:
        """Crée l'onglet Gas"""
        widget = QWidget()
        layout = QVBoxLayout()

        gas_group = QGroupBox("⛽ Gestion du Gas")
        gas_layout = QVBoxLayout()

        gas_layout.addWidget(QLabel("Fonctionnalités Gas à venir..."))

        gas_group.setLayout(gas_layout)
        layout.addWidget(gas_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_params_tab(self) -> QWidget:
        """Crée l'onglet Paramètres"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Type de client
        client_group = QGroupBox("Type de client")
        client_layout = QVBoxLayout()

        self.public_client_rb = QRadioButton("Public (recommandé)")
        self.private_client_rb = QRadioButton("Privé")
        self.public_client_rb.setChecked(config['client_type'] == 'public')
        self.private_client_rb.setChecked(config['client_type'] == 'private')

        client_layout.addWidget(self.public_client_rb)
        client_layout.addWidget(self.private_client_rb)
        client_group.setLayout(client_layout)
        layout.addWidget(client_group)

        # Configuration serveur public
        public_group = QGroupBox("Configuration serveur public")
        public_layout = QFormLayout()

        self.public_server_input = QLineEdit(config['public_server'])
        public_layout.addRow("Adresse du serveur:", self.public_server_input)
        public_group.setLayout(public_layout)
        layout.addWidget(public_group)

        # Configuration serveur privé
        private_group = QGroupBox("Configuration serveur privé")
        private_layout = QFormLayout()

        self.private_port_input = QLineEdit(config['private_port'])
        private_layout.addRow("Port:", self.private_port_input)
        private_group.setLayout(private_layout)
        layout.addWidget(private_group)

        # Gestion des états
        self.public_client_rb.toggled.connect(self._on_client_type_changed)
        self.private_client_rb.toggled.connect(self._on_client_type_changed)
        self._on_client_type_changed()  # Initialisation

        # Binaire
        binary_group = QGroupBox("Binaire")
        binary_layout = QHBoxLayout()
        binary_layout.addWidget(QLabel("Chemin:"))
        self.binary_path_input = QLineEdit(config['wallet_binary'])
        binary_layout.addWidget(self.binary_path_input)
        btn_browse_binary = QPushButton("📂")
        btn_browse_binary.clicked.connect(self._browse_binary)
        binary_layout.addWidget(btn_browse_binary)
        binary_group.setLayout(binary_layout)
        layout.addWidget(binary_group)

        # Bouton sauvegarder
        btn_save = QPushButton("💾 Sauvegarder")
        btn_save.clicked.connect(self._save_params)
        layout.addWidget(btn_save)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _build_base_command(self, include_wallet: bool = True) -> list:
        """Construit la base de toutes les commandes"""
        cmd = [config['wallet_binary']]

        # Client configuration
        if config['client_type'] == 'public':
            cmd.extend(['--client', 'public'])
            if config['public_server'] and config['public_server'] != 'https://nockchain-api.zorp.io':
                cmd.extend(['--public-grpc-server-addr', config['public_server']])
        else:
            cmd.extend(['--client', 'private'])
            if config['private_port'] and config['private_port'] != '50051':
                cmd.extend(['--private-grpc-server-port', config['private_port']])

        # Wallet path
        if include_wallet and config['wallet_imported']:
            cmd.extend(['--wallet', config['wallet_path']])

        return cmd

    def _check_binary(self):
        """Vérifie que le binaire est accessible"""
        try:
            result = subprocess.run(
                [config['wallet_binary'], '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log_area.append_log(f"✓ Binaire trouvé: {config['wallet_binary']}", "success")
            else:
                self.log_area.append_log(f"⚠ Binaire non fonctionnel", "warning")
        except FileNotFoundError:
            self.log_area.append_log(f"✗ Binaire non trouvé: {config['wallet_binary']}", "error")
            QMessageBox.warning(
                self,
                "Binaire manquant",
                f"Le binaire '{config['wallet_binary']}' est introuvable.\n"
                "Veuillez le configurer dans l'onglet Paramètres."
            )
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")

    def _select_wallet(self):
        """Sélectionne un fichier wallet existant (.wallet)"""
        wallet_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un wallet",
            config['last_used_directory'],
            "Wallet Files (*.wallet);;All Files (*)"
        )

        if wallet_file:
            try:
                if not Path(wallet_file).exists():
                    raise FileNotFoundError("Fichier introuvable")

                config['wallet_path'] = wallet_file
                config['wallet_imported'] = True
                config['last_used_directory'] = str(Path(wallet_file).parent)
                self._save_config()

                self.wallet_path_label.setText(wallet_file)
                self.wallet_path_label.setStyleSheet("color: #4CAF50;")
                self.statusBar().showMessage(f"Wallet: {Path(wallet_file).name}")
                self.log_area.append_log(f"Wallet chargé: {Path(wallet_file).name}", "success")

                # Rafraîchir le solde
                self._refresh_balance()

            except Exception as e:
                self.log_area.append_log(f"✗ Erreur chargement wallet: {str(e)}", "error")
                QMessageBox.critical(self, "Erreur", f"Impossible de charger le wallet:\n{str(e)}")

    def _import_wallet(self):
        """Importe un wallet depuis un fichier de clés"""
        source_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner le fichier de clés",
            config['last_used_directory'],
            "Key Files (*.keys *.txt);;All Files (*)"
        )

        if not source_file:
            return

        try:
            cmd = [config['wallet_binary'], 'import-keys', '--file', source_file]

            # Si un wallet est déjà chargé, l'utiliser comme destination
            if config['wallet_imported'] and config['wallet_path']:
                cmd.extend(['--wallet', config['wallet_path']])

            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # Vérifier si un wallet par défaut a été créé
                default_wallet = Path.home() / ".nockchain" / "wallet.wallet"
                if default_wallet.exists():
                    config['wallet_path'] = str(default_wallet)
                    config['wallet_imported'] = True
                    config['last_used_directory'] = str(default_wallet.parent)
                    self._save_config()

                    self.wallet_path_label.setText(str(default_wallet))
                    self.wallet_path_label.setStyleSheet("color: #4CAF50;")
                    self.statusBar().showMessage(f"Wallet: {default_wallet.name}")
                    self.log_area.append_log(f"Wallet importé: {default_wallet.name}", "success")
                    QMessageBox.information(self, "Succès", f"Wallet importé avec succès!\nFichier: {default_wallet}")
                else:
                    self.log_area.append_log("Import réussi mais aucun wallet trouvé", "warning")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")
                QMessageBox.critical(self, "Erreur", f"Échec de l'import:\n{error}")

        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur import wallet: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur inattendue:\n{str(e)}")

    def _export_wallet(self):
        """Exporte les clés du wallet"""
        if not config['wallet_imported']:
            QMessageBox.warning(self, "Attention", "Aucun wallet chargé à exporter")
            return

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter les clés du wallet",
            config['last_used_directory'] + "/wallet_keys.keys",
            "Key Files (*.keys);;All Files (*)"
        )

        if not output_file:
            return

        try:
            cmd = [
                config['wallet_binary'],
                'export-keys',
                '--wallet', config['wallet_path'],
                '--output', output_file
            ]

            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.log_area.append_log(f"✓ Export réussi: {Path(output_file).name}", "success")
                QMessageBox.information(self, "Succès", f"Wallet exporté vers:\n{output_file}")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")
                QMessageBox.critical(self, "Erreur", f"Échec de l'export:\n{error}")

        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur export wallet: {e}")
            QMessageBox.critical(self, "Erreur", f"Erreur inattendue:\n{str(e)}")

    def _refresh_balance(self):
        """Rafraîchit le solde du wallet"""
        if not config['wallet_imported']:
            self.log_area.append_log("⚠ Veuillez charger un wallet d'abord", "warning")
            return

        try:
            cmd = self._build_base_command(include_wallet=True)
            cmd.append('show-balance')

            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                output = result.stdout

                balance_info = self.parser.parse_balance(output)
                wallet_version = self.parser.parse_wallet_version(output)
                height = self.parser.parse_height(output)

                if balance_info:
                    self.balance_label.setText(balance_info['formatted'])
                    self.log_area.append_log(f"💰 Balance: {balance_info['formatted']}", "success")

                    if wallet_version:
                        self.log_area.append_log(f"📦 Version: {wallet_version}", "info")

                    if height:
                        self.log_area.append_log(f"📊 Hauteur: {height:,}", "info")
                else:
                    self.log_area.append_log("⚠ Impossible de parser le solde", "warning")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")

        except subprocess.TimeoutExpired:
            self.log_area.append_log("✗ Timeout lors de la récupération du solde", "error")
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur refresh balance: {e}")

    def _load_notes(self):
        """Charge la liste des notes"""
        if not config['wallet_imported']:
            return

        try:
            cmd = self._build_base_command(include_wallet=True)
            cmd.append('list-notes')

            if self.watch_only_notes_cb.isChecked():
                cmd.append('--include-watch-only')

            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                output = result.stdout
                notes = self.parser.parse_notes(output)

                self.notes_table.setRowCount(len(notes))

                if notes:
                    self.log_area.append_log(f"📝 {len(notes)} note(s) trouvée(s)", "success")
                    for i, note in enumerate(notes):
                        self.notes_table.setItem(i, 0, QTableWidgetItem(note))
                else:
                    self.log_area.append_log("ℹ Aucune note trouvée", "info")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")

        except subprocess.TimeoutExpired:
            self.log_area.append_log("✗ Timeout lors du chargement des notes", "error")
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur load notes: {e}")

    def _get_block(self):
        """Récupère un bloc par sa hauteur"""
        height = self.height_input.value()
        if height <= 0:
            QMessageBox.warning(self, "Attention", "Veuillez entrer une hauteur valide")
            return

        try:
            cmd = self._build_base_command(include_wallet=False)
            cmd.append('get-block')
            cmd.extend(['--height', str(height)])

            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.log_area.append_log(f"📦 Bloc {height}:", "success")
                self.log_area.append_log(result.stdout, "info")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")

        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur get block: {e}")

    def _on_client_type_changed(self):
        """Gère le changement de type de client"""
        if self.public_client_rb.isChecked():
            self.public_server_input.setEnabled(True)
            self.private_port_input.setEnabled(False)
        else:
            self.public_server_input.setEnabled(False)
            self.private_port_input.setEnabled(True)

    def _browse_binary(self):
        """Parcourir pour sélectionner le binaire"""
        binary_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner le binaire nockchain-wallet",
            str(Path.home()),
            "All Files (*)"
        )

        if binary_file:
            self.binary_path_input.setText(binary_file)

    def _save_params(self):
        """Sauvegarde les paramètres"""
        config['wallet_binary'] = self.binary_path_input.text()
        config['client_type'] = 'public' if self.public_client_rb.isChecked() else 'private'
        config['public_server'] = self.public_server_input.text()
        config['private_port'] = self.private_port_input.text()

        self._save_config()
        self.log_area.append_log("✓ Paramètres sauvegardés", "success")
        QMessageBox.information(self, "Succès", "Paramètres sauvegardés")
        self._check_binary()

def main():
    """Point d'entrée de l'application"""
    app = QApplication(sys.argv)

    # Style sombre pour PyQt6
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)

    window = NockchainWalletGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
