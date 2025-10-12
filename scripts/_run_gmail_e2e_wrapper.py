import os
import sys
# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Force env flags for the test
os.environ['ENABLE_LIVE_EMAIL_TESTS'] = '1'
os.environ['E2E_SKIP_ACCOUNT_UPDATE'] = '1'

from scripts.live_gmail_e2e import main

if __name__ == '__main__':
    main()
