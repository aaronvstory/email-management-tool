#!/usr/bin/env python3
"""
Email Connectivity Diagnostics Module
Tests SMTP and IMAP connectivity with detailed logging
"""

import os
import ssl
import socket
import smtplib
import imaplib
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class EmailDiagnostics:
    """Comprehensive email connectivity testing"""
    
    def __init__(self):
        """Initialize with environment variables"""
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'
        
        self.imap_host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.imap_port = int(os.getenv('IMAP_PORT', '993'))
        self.imap_username = os.getenv('IMAP_USERNAME', '')
        self.imap_password = os.getenv('IMAP_PASSWORD', '')
        self.imap_use_ssl = os.getenv('IMAP_USE_SSL', 'true').lower() == 'true'
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'smtp': {},
            'imap': {},
            'network': {},
            'configuration': {}
        }
    
    def test_network_connectivity(self) -> Dict[str, Any]:
        """Test basic network connectivity to email servers"""
        results = {}
        
        # Test SMTP server connectivity
        logger.info(f"Testing network connectivity to SMTP server {self.smtp_host}:{self.smtp_port}")
        try:
            sock = socket.create_connection((self.smtp_host, self.smtp_port), timeout=10)
            sock.close()
            results['smtp_reachable'] = True
            results['smtp_message'] = f"Successfully connected to {self.smtp_host}:{self.smtp_port}"
            logger.info(results['smtp_message'])
        except Exception as e:
            results['smtp_reachable'] = False
            results['smtp_error'] = str(e)
            logger.error(f"Failed to connect to SMTP server: {e}")
        
        # Test IMAP server connectivity
        logger.info(f"Testing network connectivity to IMAP server {self.imap_host}:{self.imap_port}")
        try:
            sock = socket.create_connection((self.imap_host, self.imap_port), timeout=10)
            sock.close()
            results['imap_reachable'] = True
            results['imap_message'] = f"Successfully connected to {self.imap_host}:{self.imap_port}"
            logger.info(results['imap_message'])
        except Exception as e:
            results['imap_reachable'] = False
            results['imap_error'] = str(e)
            logger.error(f"Failed to connect to IMAP server: {e}")
        
        # DNS resolution test
        logger.info("Testing DNS resolution")
        try:
            smtp_ip = socket.gethostbyname(self.smtp_host)
            imap_ip = socket.gethostbyname(self.imap_host)
            results['dns_resolution'] = {
                'smtp_host': self.smtp_host,
                'smtp_ip': smtp_ip,
                'imap_host': self.imap_host,
                'imap_ip': imap_ip,
                'status': 'success'
            }
            logger.info(f"DNS resolution successful: SMTP={smtp_ip}, IMAP={imap_ip}")
        except Exception as e:
            results['dns_resolution'] = {
                'status': 'failed',
                'error': str(e)
            }
            logger.error(f"DNS resolution failed: {e}")
        
        self.results['network'] = results
        return results
    
    def test_smtp_connection(self) -> Dict[str, Any]:
        """Test SMTP server connection and authentication"""
        results = {
            'connection': False,
            'authentication': False,
            'tls_support': False,
            'send_capability': False
        }
        
        logger.info("Testing SMTP connection and authentication")
        smtp_conn = None
        
        try:
            # Create SMTP connection
            if self.smtp_use_ssl:
                logger.info(f"Connecting to SMTP with SSL on port {self.smtp_port}")
                context = ssl.create_default_context()
                smtp_conn = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=30)
            else:
                logger.info(f"Connecting to SMTP on port {self.smtp_port}")
                smtp_conn = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            
            results['connection'] = True
            results['server_response'] = smtp_conn.ehlo()[1].decode() if smtp_conn.ehlo()[1] else "Connected"
            logger.info(f"SMTP connection established: {results['server_response'][:100]}")
            
            # Test TLS if not using SSL
            if not self.smtp_use_ssl and self.smtp_use_tls:
                try:
                    smtp_conn.starttls()
                    results['tls_support'] = True
                    logger.info("TLS encryption enabled successfully")
                except Exception as e:
                    results['tls_error'] = str(e)
                    logger.warning(f"TLS not supported or failed: {e}")
            
            # Test authentication
            if self.smtp_username and self.smtp_password:
                try:
                    smtp_conn.login(self.smtp_username, self.smtp_password)
                    results['authentication'] = True
                    results['authenticated_user'] = self.smtp_username
                    logger.info(f"SMTP authentication successful for {self.smtp_username}")
                    
                    # Test send capability
                    try:
                        smtp_conn.verify(self.smtp_username)
                        results['send_capability'] = True
                        logger.info("SMTP send capability verified")
                    except:
                        # Some servers don't support VRFY command
                        results['send_capability'] = True
                        results['vrfy_not_supported'] = True
                        
                except Exception as e:
                    results['authentication'] = False
                    results['auth_error'] = str(e)
                    logger.error(f"SMTP authentication failed: {e}")
            else:
                results['auth_skipped'] = "No credentials provided"
                logger.warning("SMTP authentication skipped - no credentials")
            
        except Exception as e:
            results['connection'] = False
            results['error'] = str(e)
            logger.error(f"SMTP connection failed: {e}")
        
        finally:
            if smtp_conn:
                try:
                    smtp_conn.quit()
                except:
                    pass
        
        self.results['smtp'] = results
        return results
    
    def test_imap_connection(self) -> Dict[str, Any]:
        """Test IMAP server connection and authentication"""
        results = {
            'connection': False,
            'authentication': False,
            'mailbox_access': False,
            'folder_list': []
        }
        
        logger.info("Testing IMAP connection and authentication")
        imap_conn = None
        
        try:
            # Create IMAP connection
            if self.imap_use_ssl:
                logger.info(f"Connecting to IMAP with SSL on port {self.imap_port}")
                context = ssl.create_default_context()
                imap_conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port, ssl_context=context)
            else:
                logger.info(f"Connecting to IMAP on port {self.imap_port}")
                imap_conn = imaplib.IMAP4(self.imap_host, self.imap_port)
            
            results['connection'] = True
            results['server_response'] = str(imap_conn.welcome)
            logger.info(f"IMAP connection established: {results['server_response'][:100]}")
            
            # Test authentication
            if self.imap_username and self.imap_password:
                try:
                    imap_conn.login(self.imap_username, self.imap_password)
                    results['authentication'] = True
                    results['authenticated_user'] = self.imap_username
                    logger.info(f"IMAP authentication successful for {self.imap_username}")
                    
                    # List available folders
                    try:
                        status, folders = imap_conn.list()
                        if status == 'OK':
                            results['mailbox_access'] = True
                            folder_names = []
                            for folder in folders:
                                if folder:
                                    # Parse folder name from response
                                    parts = folder.decode().split('"')
                                    if len(parts) >= 3:
                                        folder_names.append(parts[-2])
                            results['folder_list'] = folder_names[:10]  # Limit to first 10
                            results['folder_count'] = len(folder_names)
                            logger.info(f"Found {len(folder_names)} folders")
                            
                            # Try to select INBOX
                            status, data = imap_conn.select('INBOX', readonly=True)
                            if status == 'OK':
                                results['inbox_access'] = True
                                results['inbox_message_count'] = int(data[0].decode()) if data[0] else 0
                                logger.info(f"INBOX accessible with {results['inbox_message_count']} messages")
                    except Exception as e:
                        results['mailbox_error'] = str(e)
                        logger.error(f"Failed to access mailboxes: {e}")
                        
                except Exception as e:
                    results['authentication'] = False
                    results['auth_error'] = str(e)
                    logger.error(f"IMAP authentication failed: {e}")
            else:
                results['auth_skipped'] = "No credentials provided"
                logger.warning("IMAP authentication skipped - no credentials")
            
        except Exception as e:
            results['connection'] = False
            results['error'] = str(e)
            logger.error(f"IMAP connection failed: {e}")
        
        finally:
            if imap_conn:
                try:
                    imap_conn.logout()
                except:
                    pass
        
        self.results['imap'] = results
        return results
    
    def test_send_email(self, to_address: Optional[str] = None) -> Dict[str, Any]:
        """Test sending an actual email"""
        results = {'sent': False}
        
        if not to_address:
            to_address = self.smtp_username
        
        if not to_address:
            results['error'] = "No recipient address provided"
            return results
        
        logger.info(f"Testing email send to {to_address}")
        
        try:
            # Create test message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = to_address
            msg['Subject'] = f"Email Diagnostics Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            body = f"""This is a test email from the Email Management Tool diagnostics.

Test Details:
- Timestamp: {datetime.now().isoformat()}
- SMTP Server: {self.smtp_host}:{self.smtp_port}
- From: {self.smtp_username}
- To: {to_address}

If you received this email, your SMTP configuration is working correctly.
"""
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            if self.smtp_use_ssl:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                if self.smtp_use_tls:
                    server.starttls()
            
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            results['sent'] = True
            results['to'] = to_address
            results['subject'] = msg['Subject']
            results['timestamp'] = datetime.now().isoformat()
            logger.info(f"Test email sent successfully to {to_address}")
            
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"Failed to send test email: {e}")
        
        return results
    
    def check_configuration(self) -> Dict[str, Any]:
        """Check if configuration is complete"""
        config = {
            'smtp_configured': bool(self.smtp_host and self.smtp_username and self.smtp_password),
            'imap_configured': bool(self.imap_host and self.imap_username and self.imap_password),
            'credentials_match': self.smtp_username == self.imap_username,
            'smtp_settings': {
                'host': self.smtp_host,
                'port': self.smtp_port,
                'username': self.smtp_username,
                'has_password': bool(self.smtp_password),
                'use_tls': self.smtp_use_tls,
                'use_ssl': self.smtp_use_ssl
            },
            'imap_settings': {
                'host': self.imap_host,
                'port': self.imap_port,
                'username': self.imap_username,
                'has_password': bool(self.imap_password),
                'use_ssl': self.imap_use_ssl
            }
        }
        
        # Check for common issues
        issues = []
        if not config['smtp_configured']:
            issues.append("SMTP configuration incomplete")
        if not config['imap_configured']:
            issues.append("IMAP configuration incomplete")
        if config['smtp_configured'] and config['imap_configured'] and not config['credentials_match']:
            issues.append("SMTP and IMAP usernames don't match")
        if self.smtp_use_ssl and self.smtp_use_tls:
            issues.append("Both SSL and TLS enabled for SMTP - use only one")
        
        config['issues'] = issues
        config['valid'] = len(issues) == 0
        
        self.results['configuration'] = config
        return config
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all diagnostic tests"""
        logger.info("Starting comprehensive email diagnostics")
        
        # Check configuration
        self.check_configuration()
        
        # Test network connectivity
        self.test_network_connectivity()
        
        # Test SMTP
        if self.results['network'].get('smtp_reachable'):
            self.test_smtp_connection()
        
        # Test IMAP
        if self.results['network'].get('imap_reachable'):
            self.test_imap_connection()
        
        # Generate summary
        self.results['summary'] = {
            'configuration_valid': self.results['configuration']['valid'],
            'network_ok': self.results['network'].get('smtp_reachable', False) and 
                         self.results['network'].get('imap_reachable', False),
            'smtp_ok': self.results.get('smtp', {}).get('authentication', False),
            'imap_ok': self.results.get('imap', {}).get('authentication', False),
            'ready_to_use': False
        }
        
        # Determine if system is ready
        self.results['summary']['ready_to_use'] = (
            self.results['summary']['configuration_valid'] and
            self.results['summary']['network_ok'] and
            self.results['summary']['smtp_ok'] and
            self.results['summary']['imap_ok']
        )
        
        logger.info(f"Diagnostics complete. System ready: {self.results['summary']['ready_to_use']}")
        return self.results


def main():
    """Run diagnostics from command line"""
    print("Email Management Tool - Connectivity Diagnostics")
    print("=" * 50)
    
    diagnostics = EmailDiagnostics()
    results = diagnostics.run_all_tests()
    
    # Print results
    print("\n📋 Configuration Status:")
    config = results['configuration']
    print(f"  SMTP Configured: {'✅' if config['smtp_configured'] else '❌'}")
    print(f"  IMAP Configured: {'✅' if config['imap_configured'] else '❌'}")
    if config['issues']:
        print("  ⚠️ Issues found:")
        for issue in config['issues']:
            print(f"    - {issue}")
    
    print("\n🌐 Network Connectivity:")
    network = results['network']
    print(f"  SMTP Server: {'✅ Reachable' if network.get('smtp_reachable') else '❌ Unreachable'}")
    print(f"  IMAP Server: {'✅ Reachable' if network.get('imap_reachable') else '❌ Unreachable'}")
    
    print("\n📤 SMTP Status:")
    smtp = results.get('smtp', {})
    print(f"  Connection: {'✅' if smtp.get('connection') else '❌'}")
    print(f"  Authentication: {'✅' if smtp.get('authentication') else '❌'}")
    print(f"  TLS Support: {'✅' if smtp.get('tls_support') else '❌' if not config['smtp_settings']['use_ssl'] else 'N/A (SSL)'}")
    
    print("\n📥 IMAP Status:")
    imap = results.get('imap', {})
    print(f"  Connection: {'✅' if imap.get('connection') else '❌'}")
    print(f"  Authentication: {'✅' if imap.get('authentication') else '❌'}")
    print(f"  Mailbox Access: {'✅' if imap.get('mailbox_access') else '❌'}")
    if imap.get('inbox_message_count') is not None:
        print(f"  Inbox Messages: {imap['inbox_message_count']}")
    
    print("\n📊 Overall Status:")
    summary = results['summary']
    if summary['ready_to_use']:
        print("  ✅ System is ready to use!")
    else:
        print("  ❌ System is not ready. Please check the issues above.")
    
    # Ask if user wants to send test email
    if summary['smtp_ok']:
        response = input("\nWould you like to send a test email? (y/n): ")
        if response.lower() == 'y':
            to_address = input("Enter recipient email (or press Enter to use configured address): ").strip()
            test_result = diagnostics.test_send_email(to_address if to_address else None)
            if test_result['sent']:
                print(f"  ✅ Test email sent to {test_result['to']}")
            else:
                print(f"  ❌ Failed to send test email: {test_result.get('error', 'Unknown error')}")
    
    return results


if __name__ == "__main__":
    main()