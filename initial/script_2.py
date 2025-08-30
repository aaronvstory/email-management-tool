# Create the configuration file
config_content = """[SMTP_PROXY]
host = 0.0.0.0
port = 8587
max_message_size = 33554432

[IMAP_SETTINGS]
# Test IMAP settings - replace with your actual IMAP server
imap_server = imap.gmail.com
imap_port = 993
use_ssl = true

[SMTP_RELAY]
# SMTP relay settings for sending approved emails
relay_host = smtp.gmail.com
relay_port = 587
use_tls = true

[WEB_INTERFACE]
host = 127.0.0.1
port = 5000
debug = true
secret_key = your-secret-key-change-this-in-production

[DATABASE]
database_url = sqlite:///data/email_moderation.db

[SECURITY]
# DKIM settings (optional - will be generated if not provided)
dkim_selector = default
dkim_domain = yourdomain.com
# Generate DKIM keys automatically if not provided

[LOGGING]
log_level = INFO
log_file = logs/email_moderation.log
"""

with open("email_moderation_system/config/config.ini", "w") as f:
    f.write(config_content)

print("Created configuration file:")
print(config_content)