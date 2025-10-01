"""
Inbound Interceptor Runner

This script starts rapid copy+purge workers for all active email accounts.
Each account gets a dedicated thread that monitors INBOX for new messages
and immediately intercepts them.

Usage:
    python scripts/run_inbound_interceptors.py

Press Ctrl+C to stop all interceptors gracefully.
"""

import sys
import os
import time
import sqlite3
import logging
from typing import List

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.interception import RapidCopyPurgeWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/inbound_interception.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'email_manager.db')
def load_active_accounts() -> List[dict]:
    """
    Load all active email accounts from database
    
    Returns:
        List of account dictionaries with connection details
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, account_name, email_address,
               imap_host, imap_port, imap_username, imap_password, imap_use_ssl
        FROM email_accounts
        WHERE is_active = 1
    """)
    
    accounts = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return accounts


def decrypt_password(encrypted_password: str) -> str:
    """
    Decrypt account password (if encryption is used)
    
    For now, returns password as-is. Implement proper decryption
    if passwords are encrypted in database.
    
    Args:
        encrypted_password: Encrypted password string
    
    Returns:
        Decrypted password
    """
    # TODO: Implement proper decryption using key.txt
    return encrypted_password
def main():
    """
    Main entry point - start interceptors for all active accounts
    """
    logger.info("=" * 80)
    logger.info("Inbound Email Interceptor Service")
    logger.info("=" * 80)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Load active accounts
    logger.info("Loading active email accounts...")
    accounts = load_active_accounts()
    
    if not accounts:
        logger.warning("No active accounts found. Exiting.")
        return
    
    logger.info(f"Found {len(accounts)} active account(s)")
    
    # Start worker for each account
    workers = []
    for account in accounts:
        logger.info(f"Starting interceptor for: {account['account_name']} ({account['email_address']})")
        
        password = decrypt_password(account['imap_password'])
        
        worker = RapidCopyPurgeWorker(
            account_id=account['id'],
            imap_host=account['imap_host'],
            imap_port=account['imap_port'],
            username=account['imap_username'],
            password=password,
            use_ssl=bool(account['imap_use_ssl'])
        )
        
        worker.start()
        workers.append(worker)    
    logger.info("=" * 80)
    logger.info(f"Started {len(workers)} inbound interception worker(s)")
    logger.info("Monitoring for new emails... Press Ctrl+C to stop")
    logger.info("=" * 80)
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(10)
            
            # Check worker health
            alive_count = sum(1 for w in workers if w.is_alive())
            if alive_count < len(workers):
                logger.warning(f"Worker health check: {alive_count}/{len(workers)} alive")
    
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received...")
    
    # Graceful shutdown
    logger.info("Stopping all workers...")
    for worker in workers:
        worker.stop()
    
    # Wait for threads to finish (with timeout)
    logger.info("Waiting for workers to finish...")
    for worker in workers:
        worker.join(timeout=5)
    
    logger.info("All workers stopped. Goodbye!")


if __name__ == "__main__":
    main()