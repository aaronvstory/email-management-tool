# (Moved) See archive/root_docs_20250930/SOLUTION_FOR_BLOCKED_SMTP.md

# Solution for Blocked SMTP Ports

## The Real Issue

Your network/VPN (`45-83-89-131.pool.ovpn.com`) is blocking ALL outbound SMTP ports:

- ❌ Port 587 (STARTTLS) - BLOCKED
- ❌ Port 465 (SSL) - BLOCKED
- ❌ Port 25 (Plain) - BLOCKED
- ✅ Port 443 (HTTPS) - WORKING
- ✅ Port 993 (IMAP) - WORKING

This is **NOT** a credential issue - the passwords are correct.

## Working Solutions

### Solution 1: Disable VPN Temporarily

Since you're on a VPN that blocks SMTP:

1. Disconnect from VPN
2. Send emails
3. Reconnect to VPN

### Solution 2: Use Web-Based Email Relay Service

Since HTTPS (port 443) works, use a relay service:

#### Option A: SendGrid (Free tier available)

```python
# Install: pip install sendgrid
import sendgrid
from sendgrid.helpers.mail import Mail

sg = sendgrid.SendGridAPIClient(api_key='your-api-key')
message = Mail(
    from_email='ndayijecika@gmail.com',
    to_emails='recipient@example.com',
    subject='Test Email',
    plain_text_content='Email body'
)
response = sg.send(message)
```

#### Option B: Mailgun (Free tier available)

```python
# Install: pip install requests
import requests

requests.post(
    "https://api.mailgun.net/v3/YOUR_DOMAIN/messages",
    auth=("api", "YOUR_API_KEY"),
    data={"from": "ndayijecika@gmail.com",
          "to": ["recipient@example.com"],
          "subject": "Test",
          "text": "Email body"})
```

#### Option C: EmailJS (Browser-based, no backend needed)

```javascript
// Works directly from browser
emailjs.send("service_id", "template_id", {
  to_email: "recipient@example.com",
  from_name: "Your Name",
  message: "Email content",
});
```

### Solution 3: Use SOCKS Proxy

Route SMTP through a SOCKS proxy:

```python
import socks
import socket
import smtplib

# Configure SOCKS proxy
socks.set_default_proxy(socks.SOCKS5, "proxy_host", proxy_port)
socket.socket = socks.socksocket

# Now SMTP will work through proxy
server = smtplib.SMTP('smtp.gmail.com', 587)
```

### Solution 4: Use Gmail Web Interface

Since the app already has the passwords:

1. The app can open Gmail in browser
2. Pre-fill the compose form
3. User clicks send

### Solution 5: Configure VPN to Allow SMTP

Contact your VPN provider and:

1. Ask them to unblock SMTP ports
2. Or get a different VPN that allows SMTP
3. Or use split tunneling to exclude email traffic

## Immediate Workaround for Testing

Since the local SMTP proxy (localhost:8587) IS running, I'll modify the app to:

1. Store emails locally when "sent"
2. Queue them for later sending
3. Provide option to export as .eml files
4. Send them when VPN is disabled

## Quick Fix Implementation

I'll modify the compose function to handle this scenario gracefully:
